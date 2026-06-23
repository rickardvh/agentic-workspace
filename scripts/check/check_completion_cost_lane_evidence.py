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
SURFACE_DECISIONS = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation" / "surface-decisions.sample.json"


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


def build_lane_evidence_report() -> dict[str, Any]:
    lane = _load_json(LANE_PATH)
    external = _load_external_lane_module()
    external_report = external.build_closure_report(external.load_pack(repo_root=REPO_ROOT))
    static_closeout = _load_json(STATIC_CLOSEOUT)
    corpus_closeout = _load_json(CORPUS_CLOSEOUT)
    surface_summary = _surface_decision_summary(_load_json(SURFACE_DECISIONS))

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
            "source": "tools/model-cli-harness/external-agent-evaluation",
            "model": external_report["default_external_agent"].get("model"),
            "completion_cost_record_count": completion_cost["record_count"],
            "driver_classification_counts": completion_cost["driver_classification_counts"],
            "live_evaluation_status": external_report["live_evaluation"]["status"],
        },
        "landed_reductions": {
            "status": "present" if reductions_present else "missing",
            "source": _repo_relative(SURFACE_DECISIONS),
            "summary": surface_summary,
        },
        "before_after_closure_evidence": {
            "status": "partial" if reductions_present and measurement_present else "missing",
            "rule": "Before/after signals exist for landed reductions, but full lane closure still requires explicit remaining-cost routing and a final closure decision.",
        },
    }
    blockers = []
    if not measurement_present:
        blockers.append("static schema and actual JSON corpus evidence are both required")
    if not behavior_evidence_present:
        blockers.append("long-horizon behavior evidence must include completion-cost observations")
    if behavior_evidence_present and not behavior_proof_complete:
        blockers.append("actual long-horizon behavior proof is not complete")
    if not reductions_present:
        blockers.append("at least one landed reduction must have before/after evidence")
    if stages["before_after_closure_evidence"]["status"] != "present":
        blockers.append("full before/after closure evidence and remaining-cost routing are not complete")

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
