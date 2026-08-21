from __future__ import annotations

import importlib.util
import json
from dataclasses import replace
from pathlib import Path

import pytest

from agentic_workspace import workspace_runtime_core as runtime
from agentic_workspace.module_contract import (
    DiscoveredModule,
    ModuleContractError,
    discover_module_contracts,
    invoke_module_operation,
    module_contribution,
    validate_module_contract,
)

MATRIX_PATH = Path("tools/model-cli-harness/external-agent-evaluation/module-extension-scenario-matrix.json")
FIXTURE_PATH = Path("tests/fixtures/external_signals_module/src/external_signals/__init__.py")
MEASUREMENT_RUNNER_PATH = Path("scripts/model_cli_harness/module_extension_scenarios.py")


def _matrix() -> dict:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _fixture_module():
    spec = importlib.util.spec_from_file_location("aw_external_signals_matrix_fixture", FIXTURE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _measurement_module():
    spec = importlib.util.spec_from_file_location("aw_module_extension_measurements", MEASUREMENT_RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _EntryPoint:
    module = "external_signals"
    attr = "provider"

    def __init__(self, name: str, provider) -> None:
        self.name = name
        self._provider = provider

    def load(self):
        return self._provider


def test_module_extension_matrix_is_complete_ordinary_and_measurement_bearing() -> None:
    matrix = _matrix()
    assert matrix["kind"] == "agentic-workspace/module-extension-scenario-matrix/v1"
    assert {scenario["state_class"] for scenario in matrix["scenarios"]} == {
        "base",
        "first-party",
        "independent",
        "partial-capability",
        "conflicting",
        "incompatible",
        "removed",
        "irrelevant",
    }
    metric_fields = set(matrix["ordinary_use_metrics"])
    assert all({key.removeprefix("max_") for key in scenario["budgets"]} == metric_fields for scenario in matrix["scenarios"])
    assert all(value >= 0 for scenario in matrix["scenarios"] for value in scenario["budgets"].values())
    forbidden_prompt_fragments = (
        "agentic_workspace.modules",
        "module slot",
        "module map",
        "module_contract.py",
        "external-signals.refresh",
    )
    assert all(
        not any(fragment in scenario["ordinary_prompt"] for fragment in forbidden_prompt_fragments) for scenario in matrix["scenarios"]
    )
    assert {case["id"] for case in matrix["weak_non_compliant_cases"]} == {
        "raw-module-probing",
        "routed-contribution-ignored",
        "module-fact-globalized",
        "module-success-overclaim",
    }
    assert matrix["selective_live_evidence"]["status"] == "unavailable"
    assert matrix["selective_live_evidence"]["leaderboard"] is False


def test_module_extension_metrics_are_derived_from_executed_ordinary_routes() -> None:
    matrix = _matrix()
    result_path = Path(matrix["measurement"]["result_ref"])
    committed = json.loads(result_path.read_text(encoding="utf-8"))
    measured = _measurement_module().collect_measurements(matrix=matrix)
    assert measured == committed
    assert measured["provider_mode"] == "deterministic-ordinary-route"
    assert measured["live_provider_status"] == "unavailable"

    scenarios = {scenario["id"]: scenario for scenario in matrix["scenarios"]}
    for result in measured["results"]:
        assert result["trace"]
        assert len(result["first_line_sha256"]) == 64
        budgets = scenarios[result["id"]]["budgets"]
        for metric, value in result["metrics"].items():
            assert value <= budgets[f"max_{metric}"], f"{result['id']} exceeded {metric} budget"


def test_module_matrix_deterministic_probes_cover_progressive_disclosure_failure_and_restart() -> None:
    fixture = _fixture_module()
    available = discover_module_contracts(
        entry_points=[
            _EntryPoint("external-signals", fixture.provider),
            _EntryPoint("external-signals-conflict", fixture.conflicting_provider),
            _EntryPoint("external-signals-future", fixture.future_provider),
        ]
    )
    by_name = {item.name: item for item in available}
    contract = by_name["external-signals"].contract

    assert module_contribution(contract, task="Fix one README typo and run the narrow proof.", changed_paths=[]) is None
    relevant = module_contribution(
        contract,
        task="Inspect the external build signal and refresh the selected revision if needed.",
        changed_paths=[],
    )
    assert relevant is not None
    assert relevant["module"] == "external-signals"
    assert relevant["operations"] == [{"id": "external-signals.refresh", "result_schema": "external-signals/result/v1"}]
    assert "proof" not in relevant and "closeout" not in relevant

    partial = json.loads(json.dumps(contract))
    partial["name"] = "external-signals-read-only"
    partial["capabilities"]["operations"] = []
    partial["compatibility"]["required_capabilities"] = ["module-resources-v1"]
    partial_contract = validate_module_contract(partial)
    partial_contribution = module_contribution(partial_contract, task="Read the latest external build signal", changed_paths=[])
    assert partial_contribution is not None
    assert partial_contribution["operations"] == []
    assert all(key not in partial_contract for key in ("workflow_phases", "reconcile", "posture", "closeout"))

    descriptors = {
        name: runtime._external_module_descriptor(discovered) for name, discovered in by_name.items() if discovered.status == "available"
    }
    with pytest.raises(runtime.ModuleSelectionError, match="ownership collision"):
        runtime._validate_selected_module_contract(
            selected_modules=["external-signals", "external-signals-conflict"],
            descriptors=descriptors,
        )
    with pytest.raises(runtime.ModuleSelectionError, match="incompatible"):
        runtime._validate_selected_module_contract(
            selected_modules=["external-signals-future"],
            descriptors={"external-signals-future": runtime._external_module_descriptor(by_name["external-signals-future"])},
        )
    assert discover_module_contracts(entry_points=[]) == []


def test_module_matrix_result_and_extension_effort_boundaries_are_enforced() -> None:
    fixture = _fixture_module()
    discovered = discover_module_contracts(entry_points=[_EntryPoint("external-signals", fixture.provider)])[0]
    result = invoke_module_operation(discovered, operation_id="external-signals.refresh", arguments={"revision": "r9"})
    assert result["result"]["requested_revision"] == "r9"
    assert "cannot grant mutation, proof, parent-intent, or completion authority" in result["authority_exclusions"]

    widened = DiscoveredModule(
        name=discovered.name,
        entry_point=discovered.entry_point,
        contract=discovered.contract,
        operations={"external-signals.refresh": lambda _arguments: {"status": "ok", "effects": ["repo-write"]}},
    )
    with pytest.raises(ModuleContractError, match="undeclared effects"):
        invoke_module_operation(widened, operation_id="external-signals.refresh", arguments={})

    matrix = _matrix()
    ledger = Path(matrix["extension_effort"]["ledger_ref"]).read_text(encoding="utf-8")
    assert "No core name list, enum, phase, slot, posture fragment, skill, proof branch, closeout branch" in ledger
    assert matrix["extension_effort"]["failure_class"] == "module-specific-semantic-coupling"
    assert set(matrix["extension_effort"]["allowed_non_module_change_classes"]) == {
        "generic-infrastructure",
        "test-package-harness",
    }


def test_independent_module_reaches_the_ordinary_posture_packet_only_when_relevant(monkeypatch) -> None:
    fixture = _fixture_module()
    discovered = discover_module_contracts(entry_points=[_EntryPoint("external-signals", fixture.provider)])[0]
    descriptor = runtime._external_module_descriptor(discovered)
    config = replace(runtime._load_workspace_config(target_root=Path.cwd()), enabled_modules=("external-signals",))
    monkeypatch.setattr(runtime, "_module_operations", lambda: {"external-signals": descriptor})

    relevant = runtime._task_posture_packet_payload(
        config=config,
        surface="startup",
        task_text="Inspect the external build signal and refresh the selected revision if needed.",
        changed_paths=[],
        compact=True,
    )
    irrelevant = runtime._task_posture_packet_payload(
        config=config,
        surface="startup",
        task_text="Fix one README typo and run the narrow proof.",
        changed_paths=["README.md"],
        compact=True,
    )

    assert [item["module"] for item in relevant["module_contributions"]] == ["external-signals"]
    assert relevant["dynamic_instruction_projection"]["provenance_preserved"] is True
    assert irrelevant["module_contributions"] == []
    assert {"source": "module_registry", "matched_module_count": 0} in irrelevant["provenance"]
