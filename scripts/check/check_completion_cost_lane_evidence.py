from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LANE_PATH = REPO_ROOT / ".agentic-workspace" / "planning" / "lanes" / "github-1680-reduce-aw-induced-completion-cost.lane.json"
STATIC_CLOSEOUT = REPO_ROOT / ".agentic-workspace" / "planning" / "closeout-evidence" / "github-1680-static-schema-cost-analysis.closeout.json"
CORPUS_CLOSEOUT = REPO_ROOT / ".agentic-workspace" / "planning" / "closeout-evidence" / "github-1680-json-corpus-cost-ranking.closeout.json"
EXTERNAL_LANE_SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "external_agent_evaluation_lane.py"
LIVE_BEHAVIOR_PROOF_SCRIPT = REPO_ROOT / "scripts" / "check" / "check_completion_cost_live_behavior_proof.py"
SURFACE_DECISIONS = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "surface-decisions.sample.json"
BEFORE_AFTER_CLOSEOUT = (
    REPO_ROOT
    / ".agentic-workspace"
    / "planning"
    / "closeout-evidence"
    / "github-1680-before-after-closure-evidence.closeout.json"
)


def _repo_relative(path: Path) -> str:
    return os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{_repo_relative(path)} must contain a JSON object")
    return payload


def _load_external_lane_module():
    spec = importlib.util.spec_from_file_location("external_agent_evaluation_lane", EXTERNAL_LANE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_repo_relative(EXTERNAL_LANE_SCRIPT)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_live_behavior_proof_module():
    spec = importlib.util.spec_from_file_location("check_completion_cost_live_behavior_proof", LIVE_BEHAVIOR_PROOF_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_repo_relative(LIVE_BEHAVIOR_PROOF_SCRIPT)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _completed_slice_ids(lane: dict[str, Any]) -> list[str]:
    return [
        str(item.get("id"))
        for item in lane.get("slice_sequence", [])
        if isinstance(item, dict) and item.get("status") == "completed" and item.get("id")
    ]


def _slice_status(lane: dict[str, Any], slice_id: str) -> str:
    for item in lane.get("slice_sequence", []):
        if isinstance(item, dict) and item.get("id") == slice_id:
            return str(item.get("status", ""))
    return ""


def _surface_decision_summary(decisions_payload: dict[str, Any]) -> dict[str, Any]:
    decisions = [item for item in decisions_payload.get("decisions", []) if isinstance(item, dict)]
    by_decision = Counter(str(item.get("decision")) for item in decisions if item.get("decision"))
    before_after = [
        {
            "id": str(item.get("id")),
            "surface": str(item.get("surface")),
            "decision": str(item.get("decision")),
            "before_after_cost_signal": str(item.get("before_after_cost_signal")),
            "rollback_condition": str(item.get("rollback_condition")),
        }
        for item in decisions
        if item.get("before_after_cost_signal")
    ]
    return {
        "kind": "agentic-workspace/completion-cost-surface-decision-summary/v1",
        "decision_count": len(decisions),
        "counts_by_decision": dict(sorted(by_decision.items())),
        "before_after_signal_count": len(before_after),
        "surfaces_with_before_after": before_after,
    }


def _before_after_closeout_summary(closeout: dict[str, Any] | None) -> dict[str, Any]:
    if closeout is None:
        return {
            "status": "missing",
            "evidence_ref": _repo_relative(BEFORE_AFTER_CLOSEOUT),
            "rule": "Before/after signals exist for landed reductions, but retained closeout evidence is not present.",
        }

    closure_check = closeout.get("closure_check", {})
    measured_count = int(str(closure_check.get("measured_improvement_count", "0") or "0"))
    satisfied_count = int(str(closure_check.get("satisfied_pending_close_count", "0") or "0"))
    remaining_count = int(str(closure_check.get("remaining_cost_source_count", "0") or "0"))
    recorded = closure_check.get("before_after_evidence_status") == "recorded"

    return {
        "status": "present" if recorded else "partial",
        "evidence_ref": _repo_relative(BEFORE_AFTER_CLOSEOUT),
        "measured_improvement_count": measured_count,
        "child_issue_reconciliation": {
            "status": closure_check.get("child_issue_reconciliation_status", ""),
            "satisfied_pending_close_count": satisfied_count,
            "remaining_cost_source_count": remaining_count,
        },
        "parent_close_permission": closure_check.get("parent_close_permission", ""),
        "closure_decision": closure_check.get("closure decision", ""),
        "rule": "Retained before/after closeout evidence is present; parent closure still depends on explicit close permission and remaining-cost routing.",
    }


def build_lane_evidence_report() -> dict[str, Any]:
    lane = _load_json(LANE_PATH)
    external = _load_external_lane_module()
    external_report = external.build_closure_report(external.load_pack(repo_root=REPO_ROOT))
    live_behavior_proof = _load_live_behavior_proof_module().build_live_behavior_proof_report()
    static_closeout = _load_json(STATIC_CLOSEOUT)
    corpus_closeout = _load_json(CORPUS_CLOSEOUT)
    surface_summary = _surface_decision_summary(_load_json(SURFACE_DECISIONS))
    before_after_closeout = _load_json(BEFORE_AFTER_CLOSEOUT) if BEFORE_AFTER_CLOSEOUT.exists() else None
    before_after_summary = _before_after_closeout_summary(before_after_closeout)

    completion_cost = external_report["completion_cost_observability"]
    completed_slices = _completed_slice_ids(lane)
    behavior_slice_status = _slice_status(lane, "long-horizon-behavior-proof")
    behavior_evidence_present = completion_cost["record_count"] >= 3 and bool(completion_cost["driver_classification_counts"])
    behavior_proof_complete = behavior_slice_status == "completed"
    reductions_present = surface_summary["before_after_signal_count"] >= 3
    measurement_present = STATIC_CLOSEOUT.exists() and CORPUS_CLOSEOUT.exists()

    stages = {
        "static_schema_analysis": {
            "status": "present" if STATIC_CLOSEOUT.exists() else "missing",
            "evidence_ref": _repo_relative(STATIC_CLOSEOUT),
            "issue": "GitHub #1690",
            "closeout_title": static_closeout.get("title", ""),
        },
        "actual_json_corpus": {
            "status": "present" if CORPUS_CLOSEOUT.exists() else "missing",
            "evidence_ref": _repo_relative(CORPUS_CLOSEOUT),
            "issue": "GitHub #1691",
            "closeout_title": corpus_closeout.get("title", ""),
        },
        "long_horizon_behavior_evidence": {
            "status": "present" if behavior_evidence_present else "missing",
            "observation_support_status": "present" if behavior_evidence_present else "missing",
            "proof_status": "completed" if behavior_proof_complete else behavior_slice_status or "missing",
            "actual_long_horizon_proof_complete": behavior_proof_complete,
            "live_behavior_proof_status": live_behavior_proof["status"],
            "live_run_count": live_behavior_proof["live_evaluation"]["run_count"],
            "live_clean_run_count": live_behavior_proof["live_evaluation"]["clean_run_count"],
            "live_failure_counts": live_behavior_proof["live_evaluation"]["failure_counts"],
            "live_failure_routes": live_behavior_proof["live_failure_routes"],
            "source": "tools/model-cli-harness/external-agent-evaluation",
            "model": live_behavior_proof["live_evaluation_agent"].get("model"),
            "completion_cost_record_count": completion_cost["record_count"],
            "driver_classification_counts": completion_cost["driver_classification_counts"],
            "live_evaluation_status": external_report["live_evaluation"]["status"],
        },
        "landed_reductions": {
            "status": "present" if reductions_present else "missing",
            "source": _repo_relative(SURFACE_DECISIONS),
            "summary": surface_summary,
        },
        "before_after_closure_evidence": before_after_summary,
    }
    blockers = []
    if not measurement_present:
        blockers.append("static schema and actual JSON corpus evidence are both required")
    if not behavior_evidence_present:
        blockers.append("long-horizon behavior evidence must include completion-cost observations")
    if behavior_evidence_present and not behavior_proof_complete:
        blockers.extend(live_behavior_proof["closure_boundary"]["remaining_blockers"])
    if not reductions_present:
        blockers.append("at least one landed reduction must have before/after evidence")
    if stages["before_after_closure_evidence"]["status"] != "present":
        blockers.append("full before/after closure evidence and remaining-cost routing are not complete")
    elif stages["before_after_closure_evidence"]["parent_close_permission"] != "granted":
        blockers.append("parent close permission is not granted")
        if stages["before_after_closure_evidence"]["child_issue_reconciliation"]["remaining_cost_source_count"]:
            blockers.append("remaining cost sources are not fully reconciled")

    return {
        "kind": "agentic-workspace/completion-cost-lane-evidence/v1",
        "lane": "#1680",
        "lane_file": _repo_relative(LANE_PATH),
        "status": "partial-closure-evidence" if blockers else "ready-for-closeout-review",
        "current_slice": lane.get("current_slice", ""),
        "completed_slice_ids": completed_slices,
        "stages": stages,
        "closure_boundary": {
            "may_close_parent_issue": not blockers,
            "rule": lane.get("acceptance_boundary", ""),
            "remaining_blockers": blockers,
        },
    }


def _format_text(payload: dict[str, Any]) -> str:
    lines = [
        f"completion-cost lane evidence: {payload['status']}",
        f"completed slices: {', '.join(payload['completed_slice_ids']) or 'none'}",
    ]
    for name, stage in payload["stages"].items():
        lines.append(f"- {name}: {stage['status']}")
    for blocker in payload["closure_boundary"]["remaining_blockers"]:
        lines.append(f"blocker: {blocker}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate #1680 completion-cost lane evidence without claiming closure prematurely.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)

    payload = build_lane_evidence_report()
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))
    missing_required = [
        name
        for name, stage in payload["stages"].items()
        if name != "before_after_closure_evidence" and stage.get("status") == "missing"
    ]
    return 1 if missing_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
