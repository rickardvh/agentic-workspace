from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace import workspace_runtime_core as runtime
from agentic_workspace.module_contract import (
    MODULE_CONTRACT_VERSION,
    DiscoveredModule,
    ModuleContractError,
    discover_module_contracts,
    invoke_module_operation,
    module_contribution,
    validate_module_contract,
)


def _contract(
    *,
    name: str = "signals",
    required_capabilities: list[str] | None = None,
    roots: list[str] | None = None,
    effects: list[str] | None = None,
    operations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": MODULE_CONTRACT_VERSION,
        "name": name,
        "description": "Independent build-signal capability.",
        "compatibility": {
            "reader_epoch": 1,
            "required_capabilities": required_capabilities or ["module-resources-v1"],
        },
        "ownership": {
            "roots": roots or [],
            "effect_classes": effects or [],
            "authority_exclusions": ["cannot grant mutation, proof, or completion authority"],
        },
        "relevance": {
            "task_terms": ["build signal"],
            "path_prefixes": ["build/signals/"],
        },
        "capabilities": {
            "resources": [{"id": "signals.latest", "ref": "signals://latest", "read_only": True}],
            "skills": [],
            "operations": operations or [],
        },
        "result_semantics": {
            "schema_version": "signals/result/v1",
            "guaranteed_fields": ["status"],
            "effect_fields": ["effects"],
            "warning_fields": ["warnings"],
        },
    }


class _EntryPoint:
    module = "independent_signals"
    attr = "provider"

    def __init__(self, name: str, value: Any) -> None:
        self.name = name
        self._value = value

    def load(self) -> Any:
        return self._value


def test_read_only_module_omits_dummy_workflow_dimensions() -> None:
    contract = validate_module_contract(_contract())

    assert contract["capabilities"]["operations"] == []
    assert "workflow_phases" not in contract
    assert "startup_steps" not in contract
    assert "closeout" not in contract
    assert module_contribution(contract, task="update README", changed_paths=[]) is None

    contribution = module_contribution(contract, task="inspect the build signal", changed_paths=[])
    assert contribution is not None
    assert contribution["resources"][0]["id"] == "signals.latest"
    assert contribution["operations"] == []
    assert "Planning" not in json.dumps(contribution)


def test_entry_point_discovery_is_identity_agnostic_and_removal_is_clean() -> None:
    discovered = discover_module_contracts(entry_points=[_EntryPoint("signals", lambda: _contract())])

    assert [(item.name, item.status) for item in discovered] == [("signals", "available")]
    descriptor = runtime._external_module_descriptor(discovered[0])
    assert descriptor.kind == "external"
    assert descriptor.commands
    assert descriptor.startup_steps == ()
    assert descriptor.public_contract is not None
    assert discover_module_contracts(entry_points=[]) == []


def test_unknown_required_capability_fails_closed_only_when_selected(tmp_path: Path) -> None:
    discovered = discover_module_contracts(entry_points=[_EntryPoint("signals", _contract(required_capabilities=["future-capability-v9"]))])
    descriptor = runtime._external_module_descriptor(discovered[0])
    assert descriptor.availability == "unsupported-capability"

    with pytest.raises(runtime.ModuleSelectionError, match="unsupported required capabilities"):
        runtime._validate_selected_module_contract(selected_modules=["signals"], descriptors={"signals": descriptor})


def test_module_operation_reconciles_only_declared_effects() -> None:
    contract = _contract(
        effects=["signals-cache"],
        operations=[{"id": "signals.refresh", "result_schema": "signals/result/v1"}],
    )
    discovered = DiscoveredModule(
        name="signals",
        entry_point="independent_signals:provider",
        contract=validate_module_contract(contract),
        operations={"signals.refresh": lambda _arguments: {"status": "ok", "effects": ["signals-cache"]}},
    )

    result = invoke_module_operation(discovered, operation_id="signals.refresh", arguments={})
    assert result["result"]["status"] == "ok"
    assert "cannot grant mutation, proof, or completion authority" in result["authority_exclusions"]

    widened = DiscoveredModule(
        name="signals",
        entry_point="independent_signals:provider",
        contract=discovered.contract,
        operations={"signals.refresh": lambda _arguments: {"status": "ok", "effects": ["repo-write"]}},
    )
    with pytest.raises(ModuleContractError, match="undeclared effects"):
        invoke_module_operation(widened, operation_id="signals.refresh", arguments={})


def test_selected_module_ownership_collisions_name_both_owners() -> None:
    first = runtime._external_module_descriptor(
        DiscoveredModule(
            name="signals-a",
            entry_point="a:provider",
            contract=validate_module_contract(_contract(name="signals-a", roots=["shared/root"])),
            operations={},
        )
    )
    second = runtime._external_module_descriptor(
        DiscoveredModule(
            name="signals-b",
            entry_point="b:provider",
            contract=validate_module_contract(_contract(name="signals-b", roots=["shared/root"])),
            operations={},
        )
    )

    with pytest.raises(runtime.ModuleSelectionError, match="signals-a.*signals-b.*shared/root"):
        runtime._validate_selected_module_contract(
            selected_modules=["signals-a", "signals-b"],
            descriptors={"signals-a": first, "signals-b": second},
        )


def test_malformed_provider_is_diagnosable_without_loading_raw_source() -> None:
    discovered = discover_module_contracts(entry_points=[_EntryPoint("broken", {"description": "missing contract"})])

    assert discovered[0].status == "malformed"
    assert "schema_version" in discovered[0].reason


def test_first_party_registry_uses_same_public_contract_and_generic_loop() -> None:
    registry = runtime._MODULE_REGISTRY_MANIFEST
    assert [step["id"] for step in registry["participation_model"]["recommended_loop"]] == [
        "resolve",
        "act",
        "reconcile",
    ]
    for module in registry["modules"]:
        public_contract = validate_module_contract(module["public_contract"])
        assert public_contract["name"] == module["name"]


def test_public_contract_schema_allows_additive_optional_metadata() -> None:
    contract = _contract()
    contract["vendor_extension"] = {"safe_optional_hint": True}
    assert validate_module_contract(contract)["vendor_extension"] == {"safe_optional_hint": True}
