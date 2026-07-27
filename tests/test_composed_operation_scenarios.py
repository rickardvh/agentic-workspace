from __future__ import annotations

import copy
import importlib.util
import subprocess
import tempfile
from pathlib import Path


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
    assert "FIXTURE_CONTRACT_ORACLE" not in source
    assert "def _authority(" not in source


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


def test_composed_operation_owner_admission_does_not_smuggle_contract_fields() -> None:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_composed_operation_scenarios.py"
    spec = importlib.util.spec_from_file_location("composed_operation_scenarios", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    matrix = module.load_matrix()
    scenario = copy.deepcopy(matrix["scenarios"][0])
    with tempfile.TemporaryDirectory(prefix="aw-composed-admission-") as directory:
        target = Path(directory)
        domain, fact_type, signals = module._fixture_admission_inputs(str(scenario["fixture"]))
        admission_ref = module._write_owner_admission(
            target,
            scenario_id=str(scenario["id"]),
            owner_domain=domain,
            fact_type=fact_type,
            signals=signals,
        )
        admission = module._read_json_if_present(target / admission_ref)
    for field in module.CONTRACT_FIELDS:
        assert field not in admission
    assert admission["owner_domain"] == domain
    assert admission["fact_type"] == fact_type
