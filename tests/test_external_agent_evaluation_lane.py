from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LANE_DIR = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation"
SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "external_agent_evaluation_lane.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("external_agent_evaluation_lane", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(name: str) -> dict:
    return json.loads((LANE_DIR / name).read_text(encoding="utf-8"))


def test_external_agent_lane_pack_validates() -> None:
    module = _load_module()
    pack = module.load_pack(repo_root=REPO_ROOT)

    assert module.validate_pack(pack) == []


def test_external_agent_lane_scorecard_has_contract_ids_and_owner_surfaces() -> None:
    scorecard = _read_json("scorecard-taxonomy.json")

    dimensions = {item["id"] for item in scorecard["dimensions"]}
    failure_ids = {item["id"] for item in scorecard["failure_taxonomy"]}
    owner_surfaces = set(scorecard["owner_surfaces"])

    assert {
        "startup",
        "work_shape",
        "memory_pull",
        "memory_capture",
        "planning_continuity",
        "proof",
        "closeout",
        "ownership",
        "recovery",
    } <= dimensions
    assert {
        "MEMORY_PULL_MISSING",
        "PLANNING_CONTINUITY_MISSING",
        "PROOF_MISSING_BEFORE_CLAIM",
        "CLOSEOUT_RESIDUE_MISSING",
        "OWNERSHIP_BOUNDARY_LEAK",
        "HARNESS_SCENARIO_AMBIGUOUS",
    } <= failure_ids
    assert {"cli_output", "memory", "planning", "verification", "contracts", "harness", "no_change"} <= owner_surfaces


def test_external_agent_lane_scenarios_cover_issue_lane_requirements() -> None:
    probes = _read_json("scenario-probes.json")["probes"]
    covered_dimensions = {dimension for probe in probes for dimension in probe["expected_dimensions"]}
    probe_ids = {probe["id"] for probe in probes}

    assert {
        "clean-host-startup",
        "stale-memory-active-planning-handoff",
        "failed-proof-claim-boundary",
        "ownership-boundary-trap",
        "artifact-backed-host-startup",
    } <= probe_ids
    assert {
        "startup",
        "work_shape",
        "memory_pull",
        "planning_continuity",
        "proof",
        "closeout",
        "ownership",
        "recovery",
    } <= covered_dimensions
    assert any(probe.get("artifact_backed") for probe in probes)


def test_external_agent_lane_historical_fixtures_map_to_result_records() -> None:
    fixtures = _read_json("historical-failure-fixtures.json")["fixtures"]
    records = {record["id"]: record for record in _read_json("result-records.sample.json")["records"]}

    assert len(fixtures) >= 3
    assert any("proof" in fixture["id"] for fixture in fixtures)
    assert any("memory" in fixture["id"] for fixture in fixtures)
    for fixture in fixtures:
        assert fixture["result_record_ref"] in records
        assert fixture["failure_ids"]


def test_external_agent_lane_closure_report_is_ready_from_fixture_pack() -> None:
    module = _load_module()
    report = module.build_closure_report(module.load_pack(repo_root=REPO_ROOT))

    assert report["kind"] == "agentic-workspace/external-agent-lane-closure-report/v1"
    assert report["default_external_agent"] == {"adapter": "codex", "model": "gpt-5.3-codex-spark"}
    assert report["fixture_closure_state"] == "ready_for_fixture_closure"
    assert report["closure_state"] == "partial_closure"
    assert report["live_evaluation"]["status"] == "unresolved-failures"
    assert report["acceptance"]["scenario_probes_cover_major_phases"] is True
    assert report["acceptance"]["artifact_backed_path_defined"] is True
    assert report["failure_counts"]["PROOF_MISSING_BEFORE_CLAIM"] >= 1
    assert report["live_evaluation"]["failure_counts"]["MEMORY_PULL_MISSING"] >= 1
    assert report["promotion_count"] >= 1


def test_operational_decision_trace_avoids_chain_of_thought_requirement() -> None:
    text = (LANE_DIR / "operational-decision-trace.md").read_text(encoding="utf-8")

    assert "without asking agents to reveal private chain-of-thought" in text
    assert "Memory used, dismissed, or not applicable" in text
    assert "Verification/proof decision and safe claim boundary" in text
    assert "once the next safe action is clear, proceed with work instead of narrating" in text


def test_model_cli_harness_doc_links_external_agent_lane_pack() -> None:
    text = (REPO_ROOT / "docs" / "maintainer" / "model-cli-dogfooding-harness.md").read_text(encoding="utf-8")

    assert "tools/model-cli-harness/external-agent-evaluation/" in text
    assert "scripts/model_cli_harness/external_agent_evaluation_lane.py validate" in text
    assert "scripts/model_cli_harness/external_agent_evaluation_lane.py report --format json" in text
