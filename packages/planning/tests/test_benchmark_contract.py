from __future__ import annotations

import json
from pathlib import Path

from repo_planning_bootstrap._benchmark import benchmark_contract
from repo_planning_bootstrap.installer import install_bootstrap


def test_benchmark_contract_is_structured() -> None:
    contract = benchmark_contract()
    assert contract["status"] == "present"
    assert contract["schema"] == "benchmark_contract/v1"
    assert contract["human_policy_spec"]["schema"] == "benchmark_human_policy/v1"
    assert contract["judge_rubric"]["schema"] == "benchmark_judge_rubric/v1"
    assert contract["scenario_spec"]["schema"] == "benchmark_scenario/v1"
    assert "human_role" in contract["roles"]
    assert "worker_role" in contract["roles"]
    assert "judge_role" in contract["roles"]
    assert "blank_or_unmanaged_repo" in contract["fixture_spec"]["first_fixture_set"]
    assert "files_opened_before_safe_action" in {metric["id"] for metric in contract["efficiency_metrics"]}


def test_benchmark_fixture_set_is_present() -> None:
    fixtures_root = Path(__file__).resolve().parent / "fixtures" / "benchmark"
    scenario_specs_path = fixtures_root / "scenario-specs.json"
    assert scenario_specs_path.exists()
    scenario_specs = json.loads(scenario_specs_path.read_text(encoding="utf-8"))
    assert scenario_specs["schema"] == "benchmark_scenario/v1"
    assert len(scenario_specs["scenarios"]) == 3
    for fixture_name in ("blank_or_unmanaged_repo", "docs_heavy_existing_repo", "partial_or_placeholder_state"):
        assert (fixtures_root / fixture_name / "README.md").exists()


def test_install_bootstrap_includes_benchmark_contract_doc(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    assert not (tmp_path / "docs" / "benchmarking-contract.md").exists()
