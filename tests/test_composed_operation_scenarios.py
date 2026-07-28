from __future__ import annotations

import copy
import importlib.util
import subprocess
import tempfile
from pathlib import Path

from agentic_workspace.composed_operation_scenarios import (
    ACTIVE_RELEASE_GATE_SCENARIOS,
    observe_composed_operation_authority,
)


def _checker_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ordinary_direct_implement_packet() -> dict[str, object]:
    return {
        "context": {
            "planning_safety_gate": {"gate_result": "direct-work-allowed", "implementation_allowed": True},
            "operation_authority": {
                "kind": "agentic-workspace/operation-authority-projection/v1",
                "producer_module": "agentic_workspace.workspace_runtime_implement",
                "surface": "implement",
                "status": "admitted",
                "decision": {
                    "owner": "direct-work",
                    "terminal_state": "continue",
                    "typed_action": "implement",
                    "effect_scope": "changed-paths-only",
                    "mutation_precondition": "clean-baseline",
                    "proof_claim_boundary": "proof-before-completion-claim",
                    "next_transition": "run-focused-proof",
                },
                "typed_invocation": {"status": "observed", "surface": "implement"},
                "effect_authority": {
                    "status": "admitted",
                    "write_requested_paths": {"class": "write-requested-paths", "decision": "allow"},
                    "write_outside_scope": {"class": "write-outside-scope", "decision": "requires-explicit-authority"},
                },
                "mutation_authority": {
                    "status": "clean-baseline",
                    "baseline_id": "baseline-1",
                    "head": "abc123",
                    "allowed_paths": ["README.md"],
                    "changed_paths": ["README.md"],
                    "enforcement_fingerprint": "sha256:abc",
                },
                "proof_authority": {
                    "status": "required-before-claim",
                    "detail_route": "agentic-workspace proof --target . --changed <paths> --format json",
                    "safe_claim": "blocked",
                    "verification_state": "proof_missing",
                    "required_before_full_closure": ["run_or_refresh_proof"],
                },
                "field_authority": {
                    "owner": "planning_safety_gate",
                    "terminal_state": "planning_safety_gate+operating_loop",
                    "typed_action": "decision_packet.surface",
                    "effect_scope": "authority_envelope.side_effect_decisions",
                    "mutation_precondition": "authority_envelope.mutation_baseline",
                    "proof_claim_boundary": "operating_loop+proof.detail_route",
                    "next_transition": "operating_loop.required_before_full_closure+proof.detail_route",
                },
            },
        },
        "decision_packet": {
            "kind": "agentic-workspace/ordinary-decision-packet/v1",
            "surface": "implement",
            "required_commands": [],
            "detail_routes": {"proof_detail": "agentic-workspace proof --target . --changed <paths> --format json"},
        },
    }


def test_composed_operation_scenario_matrix_is_release_gate_ready() -> None:
    module = _checker_module()
    assert module.validate_matrix(module.load_matrix()) == []
    assert module.execute_matrix(module.load_matrix()) == []


def test_composed_operation_scenario_contract_rejects_divergence() -> None:
    module = _checker_module()
    matrix = module.load_matrix()
    scenario = copy.deepcopy(matrix["scenarios"][0])
    with tempfile.TemporaryDirectory(prefix="aw-composed-negative-") as directory:
        target = Path(directory)
        subprocess.run(["git", "init", "--quiet", str(target)], check=True, capture_output=True, text=True)
        (target / "README.md").write_text("scenario fixture\n", encoding="utf-8")
        module._commit_fixture_baseline(target)
        module._run_cli("init", "--target", str(target))
        packets, metrics = module._execute_composed_workspace_path(target=target, scenario=scenario)
        divergent = {**scenario, "owner": "wrong-owner", "terminal_state": "blocked"}
        errors = module._assert_scenario_contract(
            scenario=divergent,
            observation=packets["_scenario_contract"],
            metrics=metrics,
            budget=matrix["execution_budget"],
        )
    assert any("owner mismatch" in error for error in errors)
    assert any("terminal_state mismatch" in error for error in errors)


def test_composed_operation_contract_is_not_derived_from_fixture_oracles() -> None:
    repo = Path(__file__).resolve().parents[1]
    checker_source = (repo / "scripts" / "check" / "check_composed_operation_scenarios.py").read_text(encoding="utf-8")
    observer_source = (repo / "src" / "agentic_workspace" / "composed_operation_scenarios.py").read_text(encoding="utf-8")
    implement_source = (repo / "src" / "agentic_workspace" / "workspace_runtime_implement.py").read_text(encoding="utf-8")
    admission_source = (repo / "src" / "agentic_workspace" / "operation_authority_admissions.py").read_text(encoding="utf-8")

    assert "FIXTURE_CONTRACT_ORACLE" not in checker_source
    assert "owner-admission" not in checker_source
    assert "_owner_contract_packet" not in observer_source
    assert "contract_observation" not in observer_source
    assert "producer_receipt" not in observer_source
    assert "recovery_sequence" not in observer_source
    assert "composed-operation-owner-results" not in checker_source
    assert "scenario_fault_ref" not in checker_source
    assert "_ordinary_route_owner_packets" not in observer_source
    assert 'get("composed_operation_owner_packets")' not in observer_source
    assert "_composed_operation_owner_packets" not in implement_source
    assert '"composed_operation_owner_packets"' not in implement_source
    assert "external-intent/issue-2300.json" not in implement_source
    assert "<stale proof command>" not in implement_source
    assert "def admission_packet(" not in admission_source
    assert "operation_owner_repairs" not in admission_source
    assert "def _normalize_owner_decision_packet(owner_packet: dict[str, Any])" in admission_source


def test_composed_operation_owner_receipt_does_not_smuggle_contract_fields() -> None:
    module = _checker_module()
    matrix = module.load_matrix()
    scenario = copy.deepcopy(matrix["scenarios"][0])
    with tempfile.TemporaryDirectory(prefix="aw-composed-receipt-") as directory:
        target = Path(directory)
        receipt_ref = module._write_owner_receipt(target, scenario)
        receipt = module._read_json_if_present(target / receipt_ref)
    assert "contract" not in receipt
    assert "owner" not in receipt
    assert receipt["fixture"] == scenario["fixture"]


def test_composed_operation_checker_accepts_ordinary_direct_work_packet() -> None:
    module = _checker_module()
    matrix = module.load_matrix()
    scenario = copy.deepcopy(matrix["scenarios"][0])
    authority_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id=str(scenario["id"]),
        active_planning=False,
        start={},
        implement=_ordinary_direct_implement_packet(),
        summary={},
        closeout={},
    )
    observation = {"status": "observed", "authority_packet": authority_packet}
    contract = module._derive_contract_from_authority(fault_observation=observation, packets={"implement": {}})
    for field in module.CONTRACT_FIELDS:
        if field == "semantic_parity":
            assert field not in authority_packet
        else:
            assert contract[field] == scenario[field]
    assert authority_packet["ordinary_packet_ref"]["producer_module"] == "agentic_workspace.workspace_runtime_implement"
    assert authority_packet["ordinary_packet_ref"]["mutation_authority"]["baseline_id"] == "baseline-1"
    assert "owner_packet" not in authority_packet


def test_composed_operation_checker_does_not_certify_inactive_rows() -> None:
    module = _checker_module()
    matrix = module.load_matrix()
    scenarios = [scenario for scenario in matrix["scenarios"] if isinstance(scenario, dict)]
    active = module._active_release_gate_scenarios(scenarios)
    assert {scenario["id"] for scenario in active} == ACTIVE_RELEASE_GATE_SCENARIOS
    assert len(active) < len(scenarios)
    inactive_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id="stale-mutation-owner",
        active_planning=True,
        start={},
        implement=_ordinary_direct_implement_packet(),
        summary={},
        closeout={},
    )
    assert inactive_packet == {}


def test_composed_operation_contract_rejects_scenario_authored_ordinary_ref() -> None:
    module = _checker_module()
    authority_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id="fresh-direct-work",
        active_planning=False,
        start={},
        implement=_ordinary_direct_implement_packet(),
        summary={},
        closeout={},
    )
    authority_packet["ordinary_packet_ref"]["producer_module"] = "agentic_workspace.composed_operation_scenarios"
    contract = module._derive_contract_from_authority(
        fault_observation={"status": "observed", "authority_packet": authority_packet},
        packets={"implement": {"operating_loop": {"safe_claim": "blocked"}}},
    )
    assert contract == {}


def test_composed_operation_contract_rejects_missing_proof_route() -> None:
    implement = _ordinary_direct_implement_packet()
    implement["decision_packet"]["detail_routes"] = {}
    authority_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id="fresh-direct-work",
        active_planning=False,
        start={},
        implement=implement,
        summary={},
        closeout={},
    )
    assert authority_packet == {}


def test_composed_operation_contract_rejects_missing_baseline_authority() -> None:
    implement = _ordinary_direct_implement_packet()
    implement["context"]["operation_authority"]["mutation_authority"]["status"] = "missing-or-stale"
    implement["context"]["operation_authority"]["mutation_authority"]["baseline_id"] = ""
    implement["context"]["operation_authority"]["decision"]["mutation_precondition"] = ""
    implement["context"]["operation_authority"]["status"] = "incomplete"
    authority_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id="fresh-direct-work",
        active_planning=False,
        start={},
        implement=implement,
        summary={},
        closeout={},
    )
    assert authority_packet == {}


def test_composed_operation_contract_rejects_widened_effect_authority() -> None:
    implement = _ordinary_direct_implement_packet()
    implement["context"]["operation_authority"]["effect_authority"]["status"] = "missing-or-conflicting"
    implement["context"]["operation_authority"]["effect_authority"]["write_outside_scope"]["decision"] = "allow"
    implement["context"]["operation_authority"]["decision"]["effect_scope"] = ""
    implement["context"]["operation_authority"]["status"] = "incomplete"
    authority_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id="fresh-direct-work",
        active_planning=False,
        start={},
        implement=implement,
        summary={},
        closeout={},
    )
    assert authority_packet == {}


def test_composed_operation_contract_rejects_missing_typed_invocation() -> None:
    implement = _ordinary_direct_implement_packet()
    implement["context"]["operation_authority"]["typed_invocation"]["status"] = "missing"
    implement["context"]["operation_authority"]["decision"]["typed_action"] = ""
    implement["context"]["operation_authority"]["status"] = "incomplete"
    authority_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id="fresh-direct-work",
        active_planning=False,
        start={},
        implement=implement,
        summary={},
        closeout={},
    )
    assert authority_packet == {}


def test_composed_operation_contract_rejects_conflicting_proof_transition_authority() -> None:
    implement = _ordinary_direct_implement_packet()
    implement["context"]["operation_authority"]["proof_authority"]["status"] = "missing-or-conflicting"
    implement["context"]["operation_authority"]["proof_authority"]["safe_claim"] = "allowed"
    implement["context"]["operation_authority"]["decision"]["proof_claim_boundary"] = ""
    implement["context"]["operation_authority"]["decision"]["next_transition"] = ""
    implement["context"]["operation_authority"]["status"] = "incomplete"
    authority_packet = observe_composed_operation_authority(
        target=Path("."),
        scenario_id="fresh-direct-work",
        active_planning=False,
        start={},
        implement=implement,
        summary={},
        closeout={},
    )
    assert authority_packet == {}
