from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_completion_cost_lane_evidence.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_completion_cost_lane_evidence", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_completion_cost_lane_evidence_aggregates_required_stages() -> None:
    checker = _load_checker()

    payload = checker.build_lane_evidence_report()

    assert payload["kind"] == "agentic-workspace/completion-cost-lane-evidence/v1"
    assert payload["lane"] == "#1680"
    assert payload["status"] == "partial-closure-evidence"
    assert payload["stages"]["static_schema_analysis"]["status"] == "present"
    assert payload["stages"]["actual_json_corpus"]["status"] == "present"
    assert payload["stages"]["long_horizon_behavior_evidence"]["status"] == "present"
    assert payload["stages"]["long_horizon_behavior_evidence"]["observation_support_status"] == "present"
    assert payload["stages"]["long_horizon_behavior_evidence"]["proof_status"] == "active"
    assert payload["stages"]["long_horizon_behavior_evidence"]["actual_long_horizon_proof_complete"] is False
    assert payload["stages"]["long_horizon_behavior_evidence"]["live_behavior_proof_status"] == "blocked"
    assert payload["stages"]["long_horizon_behavior_evidence"]["live_run_count"] >= 4
    assert payload["stages"]["long_horizon_behavior_evidence"]["live_clean_run_count"] >= 3
    assert payload["stages"]["long_horizon_behavior_evidence"]["live_failure_counts"]["OWNERSHIP_BOUNDARY_LEAK"] == 1
    assert payload["stages"]["long_horizon_behavior_evidence"]["live_failure_routes"][0]["followup_ref"] == "#1616"
    assert payload["stages"]["landed_reductions"]["status"] == "present"
    before_after = payload["stages"]["before_after_closure_evidence"]
    assert before_after["status"] == "present"
    assert (
        before_after["evidence_ref"]
        == ".agentic-workspace/planning/closeout-evidence/github-1680-before-after-closure-evidence.closeout.json"
    )
    assert before_after["measured_improvement_count"] >= 3
    assert before_after["child_issue_reconciliation"]["status"] == "partial"
    assert before_after["child_issue_reconciliation"]["remaining_cost_source_count"] >= 1
    assert payload["closure_boundary"]["may_close_parent_issue"] is False
    assert any("unresolved failures" in blocker for blocker in payload["closure_boundary"]["remaining_blockers"])
    assert any("parent close permission is not granted" in blocker for blocker in payload["closure_boundary"]["remaining_blockers"])


def test_completion_cost_lane_evidence_keeps_reduction_guardrails_visible() -> None:
    checker = _load_checker()

    payload = checker.build_lane_evidence_report()
    reductions = payload["stages"]["landed_reductions"]["summary"]

    assert reductions["before_after_signal_count"] >= 3
    assert reductions["counts_by_decision"]["route"] >= 1
    assert all(item["rollback_condition"] for item in reductions["surfaces_with_before_after"])


def test_completion_cost_lane_evidence_cli_outputs_json(capsys) -> None:
    checker = _load_checker()

    status = checker.main(["--format", "json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/completion-cost-lane-evidence/v1"
