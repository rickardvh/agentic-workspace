from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

from agentic_workspace.composed_operation_scenarios import observe_composed_operation_authority


def test_composed_operation_scenario_matrix_is_release_gate_ready() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.validate_matrix(module.load_matrix()) == []
    assert module.execute_matrix(module.load_matrix()) == []


def test_composed_operation_scenario_contract_rejects_divergence() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
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


def test_composed_operation_contract_is_not_derived_from_parallel_oracle() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    source = path.read_text(encoding="utf-8")
    producer_source = (Path(__file__).resolve().parents[1] / "src" / "agentic_workspace" / "composed_operation_scenarios.py").read_text(
        encoding="utf-8"
    )
    assert "FIXTURE_CONTRACT_ORACLE" not in source
    assert "def _authority(" not in source
    assert "_fixture_admission_inputs" not in source
    assert "owner-admission" not in source
    assert "_from_fact" not in source
    assert "OWNER_RESULT_NORMALIZATION" not in source
    assert "result_type" not in source
    assert "_record_owner_result" not in source
    assert "_observe_owner_result" not in source
    assert "_owner_contract_packet" not in producer_source
    assert "contract_observation" not in producer_source
    assert "producer_receipt" not in producer_source
    assert "recovery_sequence" not in producer_source
    assert "composed-operation-owner-results" not in source
    assert "scenario_fault_ref" not in source
    assert "_with_fault_ref" not in source
    assert "_decision_from_mutation_admission" not in source
    assert "_decision_from_ordinary_state" not in source
    assert "_decision_from_route_packet" not in source
    assert "_decision_from_runtime" not in source
    assert "proof-admission" not in source
    assert "returned-worker-admission" not in source


def test_composed_operation_owner_receipt_does_not_smuggle_contract_fields() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    matrix = module.load_matrix()
    scenario = copy.deepcopy(matrix["scenarios"][0])
    with tempfile.TemporaryDirectory(prefix="aw-composed-receipt-") as directory:
        target = Path(directory)
        receipt_ref = module._write_owner_receipt(target, scenario)
        receipt = module._read_json_if_present(target / receipt_ref)
    assert "contract" not in receipt
    assert "owner" not in receipt
    assert receipt["fixture"] == scenario["fixture"]


def test_composed_operation_checker_consumes_producer_authority_packet() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    matrix = module.load_matrix()
    scenario = copy.deepcopy(matrix["scenarios"][0])
    with tempfile.TemporaryDirectory(prefix="aw-composed-authority-") as directory:
        target = Path(directory)
        authority_packet = observe_composed_operation_authority(
            target=target,
            scenario_id=str(scenario["id"]),
            active_planning=False,
            start={},
            implement={"context": {"planning_safety_gate": {"gate_result": "direct-work-allowed"}}},
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
    assert authority_packet["producer_module"] == "agentic_workspace.composed_operation_scenarios"
    owner_packet = authority_packet["owner_packet"]
    assert owner_packet["admission"]["stable_reason"] == scenario["mutation_precondition"]
    assert owner_packet["owner"] == scenario["owner"]
    assert "contract_observation" not in owner_packet
    assert "producer_receipt" not in owner_packet
    assert not (target / ".agentic-workspace" / "local" / "composed-operation-owner-results").exists()


def test_composed_operation_contract_rejects_accepted_stale_or_rejected_shortcut() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    matrix = module.load_matrix()
    scenario = copy.deepcopy(matrix["scenarios"][0])
    with tempfile.TemporaryDirectory(prefix="aw-composed-authority-shortcut-") as directory:
        target = Path(directory)
        authority_packet = observe_composed_operation_authority(
            target=target,
            scenario_id=str(scenario["id"]),
            active_planning=False,
            start={},
            implement={"context": {"planning_safety_gate": {"gate_result": "direct-work-allowed"}}},
            summary={},
            closeout={},
        )

    shortcut = json.loads(json.dumps(authority_packet))
    shortcut["decision"]["mutation_precondition"] = "stale-cas-rejected"
    shortcut["owner_packet"]["admission"]["stable_reason"] = "stale-cas-rejected"
    shortcut["owner_packet"]["admission"]["admitted"] = True
    shortcut["owner_packet"]["status"] = "admitted"
    shortcut["owner_packet"]["admitted"] = True
    shortcut["protected_action"]["accepted"] = True
    shortcut["repair_revalidation"] = {"status": "valid-terminal-after-repair", "stale_prior_rejected": True}

    contract = module._derive_contract_from_authority(
        fault_observation={"status": "observed", "authority_packet": shortcut},
        packets={"implement": {"operating_loop": {"safe_claim": "blocked"}}},
    )

    assert contract == {}


def test_composed_operation_contract_requires_repair_revalidation_for_rejected_paths() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="aw-composed-repair-required-") as directory:
        target = Path(directory)
        subprocess.run(["git", "init", "--quiet", str(target)], check=True, capture_output=True, text=True)
        (target / "README.md").write_text("scenario fixture\nchanged after baseline\n", encoding="utf-8")
        module._commit_fixture_baseline(target)
        module._run_cli("init", "--target", str(target))
        authority_packet = observe_composed_operation_authority(
            target=target,
            scenario_id="stale-mutation-owner",
            active_planning=True,
            start={},
            implement={},
            summary={},
            closeout={},
            changed_paths=["README.md"],
        )
    authority_packet["repair_revalidation"] = {"status": "typed-repair-required", "stale_prior_rejected": True}
    contract = module._derive_contract_from_authority(
        fault_observation={"status": "observed", "authority_packet": authority_packet},
        packets={"implement": {"operating_loop": {"safe_claim": "blocked"}}},
    )
    assert contract == {}
