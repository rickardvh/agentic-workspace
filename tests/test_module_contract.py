from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace import workspace_runtime_core as runtime
from agentic_workspace.instruction_clause_ir import compile_instruction_program
from agentic_workspace.module_contract import (
    MODULE_CONTRACT_VERSION,
    DiscoveredModule,
    ModuleContractError,
    discover_module_contracts,
    invoke_module_operation,
    module_contribution,
    module_relevance,
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
        "facts": [],
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


def test_module_fact_is_source_bound_and_consumed_by_existing_instruction_ir() -> None:
    contract = _contract(required_capabilities=["module-facts-v1"])
    contract["facts"] = [
        {
            "id": "signals.build-risk",
            "type": "string",
            "value": "elevated",
            "source": {"owner": "signals", "revision": "r1", "current": True},
        }
    ]
    contribution = module_contribution(validate_module_contract(contract), task="inspect build signal", changed_paths=[])
    assert contribution is not None
    fact = contribution["facts"][0]
    program = {
        "kind": "agentic-workspace/instruction-program/v1",
        "facts": [fact],
        "clauses": [
            {
                "id": "repo:surface-risk-guidance",
                "source": {"owner": "repo-scoped-instructions", "revision": "policy-r1", "current": True},
                "when": {"fact": "signals.build-risk", "operator": "is", "value": "elevated"},
                "effects": [{"kind": "surface", "target": "surface:build-risk-guidance"}],
                "authority": {"effects": ["surface"], "target_patterns": ["surface:build-risk-guidance"]},
            }
        ],
        "capabilities": [],
    }
    compiled = compile_instruction_program(program)
    assert compiled["status"] == "compiled"
    assert compiled["effects"]["surface"][0]["target"] == "surface:build-risk-guidance"
    program["facts"][0]["source"]["current"] = False
    stale = compile_instruction_program(program)
    assert stale["effects"]["surface"] == []


def test_module_facts_are_optional_and_absent_from_factless_contributions() -> None:
    contract = _contract()
    contract.pop("facts")
    validated = validate_module_contract(contract)
    assert "facts" not in validated
    contribution = module_contribution(validated, task="inspect build signal", changed_paths=[])
    assert contribution is not None
    assert "facts" not in contribution


@pytest.mark.parametrize(
    ("fact", "message"),
    [
        (
            {
                "id": "signals.build-risk",
                "type": "boolean",
                "value": "yes",
                "source": {"owner": "signals", "revision": "r1", "current": True},
            },
            "value must be a boolean",
        ),
        (
            {
                "id": "signals.build-risk",
                "type": "string",
                "value": "clear",
                "source": {"owner": "another-module", "revision": "r1", "current": True},
            },
            "source.owner must match module identity",
        ),
        (
            {
                "id": "signals.labels",
                "type": "string-set",
                "value": ["clear", "clear"],
                "source": {"owner": "signals", "revision": "r1", "current": True},
            },
            "unique list of strings",
        ),
    ],
)
def test_module_fact_validation_fails_closed(fact: dict[str, Any], message: str) -> None:
    contract = _contract(required_capabilities=["module-facts-v1"])
    contract["facts"] = [fact]
    with pytest.raises(ModuleContractError, match=message):
        validate_module_contract(contract)


def test_module_operation_can_refresh_only_declared_fact_identity_and_type() -> None:
    contract = _contract(
        required_capabilities=["module-facts-v1", "module-operations-v1", "module-results-v1"],
        operations=[{"id": "signals.refresh", "result_schema": "signals/result/v1"}],
    )
    contract["facts"] = [
        {
            "id": "signals.build-risk",
            "type": "string",
            "value": "elevated",
            "source": {"owner": "signals", "revision": "r1", "current": True},
        }
    ]
    discovered = DiscoveredModule(
        name="signals",
        entry_point="independent_signals:provider",
        contract=validate_module_contract(contract),
        operations={
            "signals.refresh": lambda _arguments: {
                "status": "ok",
                "facts": [
                    {
                        "id": "signals.build-risk",
                        "type": "string",
                        "value": "clear",
                        "source": {"owner": "signals", "revision": "r2", "current": True},
                    }
                ],
            }
        },
    )
    result = invoke_module_operation(discovered, operation_id="signals.refresh", arguments={})
    assert result["result"]["facts"][0]["source"]["revision"] == "r2"
    discovered.operations["signals.refresh"] = lambda _arguments: {
        "status": "ok",
        "facts": [
            {
                "id": "signals.unknown",
                "type": "string",
                "value": "clear",
                "source": {"owner": "signals", "revision": "r2", "current": True},
            }
        ],
    }
    with pytest.raises(ModuleContractError, match="undeclared fact"):
        invoke_module_operation(discovered, operation_id="signals.refresh", arguments={})


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


def test_selected_module_fact_collisions_fail_closed() -> None:
    first_contract = _contract(name="signals-a")
    second_contract = _contract(name="signals-b")
    for contract in (first_contract, second_contract):
        contract["facts"] = [
            {
                "id": "shared.build-risk",
                "type": "string",
                "value": "clear",
                "source": {"owner": contract["name"], "revision": "r1", "current": True},
            }
        ]
    descriptors = {
        name: runtime._external_module_descriptor(
            DiscoveredModule(
                name=name,
                entry_point=f"{name}:provider",
                contract=validate_module_contract(contract),
                operations={},
            )
        )
        for name, contract in (("signals-a", first_contract), ("signals-b", second_contract))
    }
    with pytest.raises(runtime.ModuleSelectionError, match="fact collision.*signals-a.*signals-b.*shared.build-risk"):
        runtime._validate_selected_module_contract(selected_modules=["signals-a", "signals-b"], descriptors=descriptors)


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


def test_separately_installed_out_of_tree_module_uses_only_the_public_entry_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture_source = Path("tests/fixtures/external_signals_module").resolve()
    external_source = tmp_path / "external-source"
    install_root = tmp_path / "external-install"
    shutil.copytree(fixture_source, external_source)
    uv = shutil.which("uv")
    assert uv is not None
    subprocess.run(
        [uv, "pip", "install", "--target", str(install_root), "--no-deps", str(external_source)],
        check=True,
        capture_output=True,
        text=True,
    )

    monkeypatch.syspath_prepend(str(install_root))
    installed = {item.name: item for item in discover_module_contracts() if item.name.startswith("external-signals")}

    assert set(installed) == {"external-signals", "external-signals-conflict", "external-signals-future"}
    assert installed["external-signals"].entry_point == "external_signals:provider"
    assert installed["external-signals-future"].status == "incompatible"

    contract = installed["external-signals"].contract
    assert module_relevance(contract, task="edit README", changed_paths=[])["status"] == "irrelevant"
    assert module_relevance(contract, task="inspect external build signal", changed_paths=[])["status"] == "relevant"
    contribution = module_contribution(contract, task="inspect external build signal", changed_paths=[])
    assert contribution is not None
    assert contribution["resources"] == [{"id": "external-signals.latest", "ref": "signals://latest", "read_only": True}]
    assert contribution["facts"][0]["id"] == "external-signals.build-risk"

    result = invoke_module_operation(installed["external-signals"], operation_id="external-signals.refresh", arguments={"revision": "r7"})
    assert result["result"] == {
        "status": "refreshed",
        "effects": ["external-signals-cache"],
        "requested_revision": "r7",
        "facts": [
            {
                "id": "external-signals.build-risk",
                "type": "string",
                "value": "clear",
                "subject": "external-build",
                "source": {"owner": "external-signals", "revision": "r7", "current": True},
            }
        ],
    }

    descriptors = {
        name: runtime._external_module_descriptor(discovered) for name, discovered in installed.items() if discovered.status == "available"
    }
    with pytest.raises(runtime.ModuleSelectionError, match="external-signals.*external-signals-conflict"):
        runtime._validate_selected_module_contract(
            selected_modules=["external-signals", "external-signals-conflict"], descriptors=descriptors
        )

    monkeypatch.undo()
    restarted = {item.name for item in discover_module_contracts() if item.name.startswith("external-signals")}
    assert restarted == set()
