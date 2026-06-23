from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_LANE_SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "external_agent_evaluation_lane.py"
ALLOWED_MODELS = {"gpt-5.3-codex-spark", "gpt-5.4-codex-mini", "gpt-5.4-mini"}


def _load_external_lane_module():
    spec = importlib.util.spec_from_file_location("external_agent_evaluation_lane", EXTERNAL_LANE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {EXTERNAL_LANE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _live_failure_routes(pack: dict[str, dict[str, Any]], live_failure_ids: set[str]) -> list[dict[str, Any]]:
    live_run_ids = {str(run.get("id")) for run in pack.get("live_results", {}).get("runs", [])}
    routes = []
    for decision in pack.get("promotions", {}).get("decisions", []):
        if decision.get("decision") != "promote":
            continue
        evidence_refs = {str(item) for item in decision.get("evidence_record_ids", [])}
        failure_ids = {str(item) for item in decision.get("failure_ids", [])}
        if not live_run_ids.intersection(evidence_refs) or not live_failure_ids.intersection(failure_ids):
            continue
        routes.append(
            {
                "id": decision.get("id", ""),
                "failure_ids": sorted(live_failure_ids.intersection(failure_ids)),
                "owner_surface": decision.get("owner_surface", ""),
                "followup_ref": decision.get("followup_ref", ""),
                "remediation_kind": decision.get("remediation_kind", ""),
                "closure_effect": decision.get("closure_effect", ""),
            }
        )
    return routes


def build_live_behavior_proof_report() -> dict[str, Any]:
    external = _load_external_lane_module()
    pack = external.load_pack(repo_root=REPO_ROOT)
    report = external.build_closure_report(pack)
    live = report["live_evaluation"]
    model = str(report["default_external_agent"].get("model") or "")
    live_failure_ids = set(live["failure_counts"])
    routes = _live_failure_routes(pack, live_failure_ids)
    routed_failure_ids = {failure_id for route in routes for failure_id in route["failure_ids"]}

    missing_routes = sorted(live_failure_ids.difference(routed_failure_ids))
    model_allowed = model in ALLOWED_MODELS
    evidence_present = live["run_count"] > 0 and model_allowed
    proof_complete = live["status"] == "clean" and live["run_count"] > 0 and model_allowed

    blockers = []
    if not model_allowed:
        blockers.append(f"live evaluation model is not allowed for #1680: {model or 'missing'}")
    if live["run_count"] == 0:
        blockers.append("live long-horizon behavior proof has no recorded runs")
    if live["status"] != "clean":
        blockers.append("live long-horizon behavior proof has unresolved failures")
    if missing_routes:
        blockers.append("unresolved live failures are not fully routed")

    return {
        "kind": "agentic-workspace/completion-cost-live-behavior-proof/v1",
        "lane": "#1680",
        "status": "complete" if proof_complete else "blocked",
        "evidence_present": evidence_present,
        "proof_complete": proof_complete,
        "default_external_agent": report["default_external_agent"],
        "allowed_models": sorted(ALLOWED_MODELS),
        "live_evaluation": live,
        "fixture_closure_state": report["fixture_closure_state"],
        "external_lane_closure_state": report["closure_state"],
        "completion_cost_observability": report["completion_cost_observability"],
        "live_failure_routes": routes,
        "closure_boundary": {
            "may_complete_long_horizon_behavior_proof": proof_complete,
            "remaining_blockers": blockers,
            "missing_live_failure_routes": missing_routes,
            "rule": "Live behavior proof for #1680 requires allowed-model live runs and clean live evaluation status; routed failures remain evidence, not proof completion.",
        },
    }


def _format_text(payload: dict[str, Any]) -> str:
    lines = [
        f"completion-cost live behavior proof: {payload['status']}",
        f"model: {payload['default_external_agent'].get('model')}",
        f"live runs: {payload['live_evaluation']['run_count']}",
        f"clean runs: {payload['live_evaluation']['clean_run_count']}",
    ]
    for blocker in payload["closure_boundary"]["remaining_blockers"]:
        lines.append(f"blocker: {blocker}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check #1680 live long-horizon behavior proof without claiming closure prematurely.")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)

    payload = build_live_behavior_proof_report()
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_text(payload))
    return 1 if not payload["evidence_present"] or payload["closure_boundary"]["missing_live_failure_routes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
