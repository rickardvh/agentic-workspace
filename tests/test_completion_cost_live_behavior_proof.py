from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check" / "check_completion_cost_live_behavior_proof.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_completion_cost_live_behavior_proof", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_live_behavior_proof_reports_checked_in_codex_spark_gate() -> None:
    checker = _load_checker()

    payload = checker.build_live_behavior_proof_report()

    assert payload["kind"] == "agentic-workspace/completion-cost-live-behavior-proof/v1"
    assert payload["lane"] == "#1680"
    assert payload["default_external_agent"]["model"] == "gpt-5.3-codex-spark"
    assert payload["evidence_present"] is True
    assert payload["proof_complete"] is False
    assert payload["status"] == "blocked"
    assert payload["live_evaluation"]["run_count"] >= 4
    assert payload["live_evaluation"]["clean_run_count"] >= 3
    assert payload["live_evaluation"]["failure_counts"]["OWNERSHIP_BOUNDARY_LEAK"] == 1
    assert payload["live_evaluation"]["failure_counts"]["LOCAL_ABSOLUTE_PATH_LEAK"] == 1
    assert payload["closure_boundary"]["may_complete_long_horizon_behavior_proof"] is False
    assert payload["closure_boundary"]["missing_live_failure_routes"] == []
    assert any("unresolved failures" in blocker for blocker in payload["closure_boundary"]["remaining_blockers"])


def test_live_behavior_proof_keeps_actionable_failure_route_visible() -> None:
    checker = _load_checker()

    payload = checker.build_live_behavior_proof_report()
    routes = payload["live_failure_routes"]

    assert routes
    assert set(routes[0]["failure_ids"]) == {"OWNERSHIP_BOUNDARY_LEAK", "LOCAL_ABSOLUTE_PATH_LEAK"}
    assert routes[0]["followup_ref"] == "#1616"
    assert routes[0]["remediation_kind"] == "actionable-issue"
    assert routes[0]["closure_effect"] == "routed"


def test_live_behavior_proof_cli_outputs_json(capsys) -> None:
    checker = _load_checker()

    status = checker.main(["--format", "json"])

    assert status == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/completion-cost-live-behavior-proof/v1"
