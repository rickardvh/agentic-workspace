"""Validate and report the external-agent evaluation lane pack."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LANE_DIR = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation"

PACK_FILES = {
    "scorecard": "scorecard-taxonomy.json",
    "invariants": "evaluator-invariants.json",
    "scenarios": "scenario-probes.json",
    "historical": "historical-failure-fixtures.json",
    "results": "result-records.sample.json",
    "live_results": "live-results-2026-06-18.json",
    "promotions": "promotion-decisions.sample.json",
    "surfaces": "surface-decisions.sample.json",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pack(*, repo_root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    lane_dir = repo_root / "tools" / "model-cli-harness" / "external-agent-evaluation"
    return {name: _load_json(lane_dir / relative_path) for name, relative_path in PACK_FILES.items()}


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_pack(pack: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    scorecard = pack["scorecard"]
    dimensions = {item["id"] for item in scorecard.get("dimensions", [])}
    failure_ids = {item["id"] for item in scorecard.get("failure_taxonomy", [])}
    owner_surfaces = set(scorecard.get("owner_surfaces", []))
    result_values = set(scorecard.get("result_values", []))
    claim_safety_values = set(scorecard.get("claim_safety_values", []))

    _require(scorecard.get("kind") == "agentic-workspace/external-agent-scorecard/v1", "scorecard kind is invalid", errors)
    _require(len(dimensions) >= 8, "scorecard must define the major AW loop dimensions", errors)
    _require(len(failure_ids) >= 10, "scorecard must define stable failure ids", errors)

    for invariant in pack["invariants"].get("invariants", []):
        _require(invariant.get("dimension") in dimensions, f"invariant {invariant.get('id')} references unknown dimension", errors)

    scenario_ids: set[str] = set()
    for probe in pack["scenarios"].get("probes", []):
        scenario_ids.add(str(probe.get("id")))
        for dimension in probe.get("expected_dimensions", []):
            _require(dimension in dimensions, f"probe {probe.get('id')} references unknown dimension {dimension}", errors)
        for failure_id in probe.get("failure_ids", []):
            _require(failure_id in failure_ids, f"probe {probe.get('id')} references unknown failure id {failure_id}", errors)
    _require(any(probe.get("artifact_backed") for probe in pack["scenarios"].get("probes", [])), "artifact-backed probe is missing", errors)

    record_ids: set[str] = set()
    failure_ids_seen: set[str] = set()
    for record in pack["results"].get("records", []):
        record_ids.add(str(record.get("id")))
        _require(record.get("scenario_id") in scenario_ids, f"record {record.get('id')} references unknown scenario", errors)
        _require(record.get("loop_outcome") in result_values, f"record {record.get('id')} has invalid loop_outcome", errors)
        _require(record.get("claim_safety") in claim_safety_values, f"record {record.get('id')} has invalid claim_safety", errors)
        record_dimensions = record.get("dimensions", {})
        for dimension, value in record_dimensions.items():
            _require(dimension in dimensions, f"record {record.get('id')} references unknown dimension {dimension}", errors)
            _require(value in result_values, f"record {record.get('id')} has invalid result value {value}", errors)
        for failure_id in record.get("failure_ids", []):
            failure_ids_seen.add(failure_id)
            _require(failure_id in failure_ids, f"record {record.get('id')} references unknown failure id {failure_id}", errors)
        for owner in record.get("repair_surface_hints", []):
            _require(owner in owner_surfaces, f"record {record.get('id')} references unknown owner surface {owner}", errors)
    for record in pack.get("live_results", {}).get("runs", []):
        record_ids.add(str(record.get("id")))
        _require(record.get("scenario_id") in scenario_ids, f"live run {record.get('id')} references unknown scenario", errors)
        for failure_id in record.get("failure_ids", []):
            _require(failure_id in failure_ids, f"live run {record.get('id')} references unknown failure id {failure_id}", errors)

    for fixture in pack["historical"].get("fixtures", []):
        _require(fixture.get("result_record_ref") in record_ids, f"historical fixture {fixture.get('id')} has unknown record ref", errors)
        for failure_id in fixture.get("failure_ids", []):
            _require(failure_id in failure_ids, f"historical fixture {fixture.get('id')} references unknown failure id", errors)
    _require(len(pack["historical"].get("fixtures", [])) >= 3, "at least three historical fixtures are required", errors)

    for decision in pack["promotions"].get("decisions", []):
        for failure_id in decision.get("failure_ids", []):
            _require(failure_id in failure_ids, f"promotion {decision.get('id')} references unknown failure id", errors)
        for record_id in decision.get("evidence_record_ids", []):
            _require(record_id in record_ids, f"promotion {decision.get('id')} references unknown record id", errors)
        _require(decision.get("owner_surface") in owner_surfaces, f"promotion {decision.get('id')} has unknown owner surface", errors)
        _require(decision.get("decision") in {"promote", "dismiss"}, f"promotion {decision.get('id')} has invalid decision", errors)

    surface_decisions = {"keep_visible", "route", "merge", "generate", "remove", "keep_reasoning_complement"}
    for decision in pack["surfaces"].get("decisions", []):
        _require(decision.get("decision") in surface_decisions, f"surface decision {decision.get('id')} is invalid", errors)
        _require(decision.get("owner") in owner_surfaces, f"surface decision {decision.get('id')} has unknown owner", errors)

    _require("PROOF_MISSING_BEFORE_CLAIM" in failure_ids_seen, "sample records must include proof claim-safety failure evidence", errors)
    _require("MEMORY_PULL_MISSING" in failure_ids_seen, "sample records must include Memory routing failure evidence", errors)
    return errors


def build_closure_report(pack: dict[str, dict[str, Any]]) -> dict[str, Any]:
    records = pack["results"]["records"]
    live_runs = pack.get("live_results", {}).get("runs", [])
    dimensions = [item["id"] for item in pack["scorecard"]["dimensions"]]
    dimension_counts: dict[str, dict[str, int]] = {}
    for dimension in dimensions:
        dimension_counts[dimension] = dict(Counter(record.get("dimensions", {}).get(dimension, "not_applicable") for record in records))

    failure_counts = Counter(failure_id for record in records for failure_id in record.get("failure_ids", []))
    promoted = [item for item in pack["promotions"]["decisions"] if item.get("decision") == "promote"]
    dismissed = [item for item in pack["promotions"]["decisions"] if item.get("decision") == "dismiss"]
    artifact_probe_count = sum(1 for item in pack["scenarios"]["probes"] if item.get("artifact_backed"))
    surface_decisions = Counter(item.get("decision") for item in pack["surfaces"]["decisions"])
    live_failure_counts = Counter(failure_id for run in live_runs for failure_id in run.get("failure_ids", []))
    live_warning_counts = Counter(warning for run in live_runs for warning in run.get("warning_classes", []))
    live_clean_count = sum(1 for run in live_runs if run.get("live_outcome") == "pass")

    acceptance = {
        "scorecard_exists": bool(pack["scorecard"].get("dimensions") and pack["scorecard"].get("failure_taxonomy")),
        "scenario_probes_cover_major_phases": set(dimensions).issubset(
            {dimension for probe in pack["scenarios"]["probes"] for dimension in probe.get("expected_dimensions", [])}
        ),
        "compact_result_records_exist": len(records) >= 1,
        "failure_taxonomy_referenced": bool(failure_counts),
        "promotion_path_exists": bool(promoted or dismissed),
        "historical_fixtures_exist": len(pack["historical"]["fixtures"]) >= 3,
        "artifact_backed_path_defined": artifact_probe_count > 0,
        "surface_simplification_decisions_exist": bool(pack["surfaces"]["decisions"]),
        "operational_trace_protocol_exists": (LANE_DIR / "operational-decision-trace.md").exists(),
    }
    fixture_closure_state = "ready_for_fixture_closure" if all(acceptance.values()) else "continued_work"
    live_status = "not-run"
    if live_runs:
        live_status = "clean" if live_clean_count == len(live_runs) else "unresolved-failures"
    closure_state = "ready_for_full_closure" if fixture_closure_state == "ready_for_fixture_closure" and live_status == "clean" else "continued_work"
    if closure_state == "continued_work" and any(acceptance.values()):
        closure_state = "partial_closure"

    return {
        "kind": "agentic-workspace/external-agent-lane-closure-report/v1",
        "lane": "#1600",
        "default_external_agent": pack["scenarios"].get("default_external_agent"),
        "scorecard_dimension_count": len(dimensions),
        "scenario_probe_count": len(pack["scenarios"]["probes"]),
        "result_record_count": len(records),
        "historical_fixture_count": len(pack["historical"]["fixtures"]),
        "artifact_backed_probe_count": artifact_probe_count,
        "live_evaluation": {
            "status": live_status,
            "run_count": len(live_runs),
            "clean_run_count": live_clean_count,
            "failure_counts": dict(sorted(live_failure_counts.items())),
            "warning_counts": dict(sorted(live_warning_counts.items())),
        },
        "dimension_counts": dimension_counts,
        "failure_counts": dict(sorted(failure_counts.items())),
        "promotion_count": len(promoted),
        "dismissal_count": len(dismissed),
        "surface_decision_counts": dict(sorted(surface_decisions.items())),
        "acceptance": acceptance,
        "fixture_closure_state": fixture_closure_state,
        "closure_state": closure_state,
        "residue": [
            {
                "owner": "maintainer",
                "summary": "Live Codex Spark runs are recorded. Remaining failures must be promoted or fixed before closing the parent lane as fully complete.",
            }
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "report"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pack = load_pack()
    errors = validate_pack(pack)
    if args.command == "validate":
        payload = {"status": "ok" if not errors else "error", "errors": errors}
    else:
        payload = build_closure_report(pack)
        if errors:
            payload["validation_errors"] = errors
            payload["closure_state"] = "continued_work"

    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "validate":
        print("external-agent evaluation lane: ok" if not errors else "external-agent evaluation lane: invalid")
        for error in errors:
            print(f"- {error}")
    else:
        print(f"external-agent evaluation lane: {payload['closure_state']}")
        print(f"scenarios: {payload['scenario_probe_count']}; records: {payload['result_record_count']}; failures: {len(payload['failure_counts'])}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
