from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
LANE_DIR = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation"
SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "external_agent_evaluation_lane.py"
HARNESS_SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "run_model_cli_harness.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("external_agent_evaluation_lane", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_harness_module():
    spec = importlib.util.spec_from_file_location("run_model_cli_harness", HARNESS_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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


def test_external_agent_lane_rejects_fixture_failures_absent_from_result_record() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    pack["historical"]["fixtures"][0]["failure_ids"].append("MEMORY_PULL_MISSING")

    errors = module.validate_pack(pack)

    assert any("failure MEMORY_PULL_MISSING is not represented by sample-broad-work-regression" in error for error in errors)


def test_external_agent_lane_rejects_promotions_without_actionable_remediation() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    live_promotion = next(item for item in pack["promotions"]["decisions"] if item["id"] == "promote-live-local-path-leak")
    live_promotion["followup_ref"] = "#1601"
    live_promotion.pop("remediation_kind", None)

    errors = module.validate_pack(pack)

    assert any("promote-live-local-path-leak must route to an actionable remediation owner" in error for error in errors)


def test_external_agent_lane_closure_report_is_ready_from_fixture_pack() -> None:
    module = _load_module()
    report = module.build_closure_report(module.load_pack(repo_root=REPO_ROOT))

    assert report["kind"] == "agentic-workspace/external-agent-lane-closure-report/v1"
    assert report["default_external_agent"] == {"adapter": "codex", "model": "gpt-5.3-codex-spark"}
    assert report["fixture_closure_state"] == "ready_for_fixture_closure"
    assert report["closure_state"] == "partial_closure"
    assert report["live_evaluation"]["status"] == "unresolved-failures"
    assert report["live_evaluation"]["clean_run_count"] == 3
    assert report["acceptance"]["scenario_probes_cover_major_phases"] is True
    assert report["acceptance"]["artifact_backed_path_defined"] is True
    assert report["failure_counts"]["PROOF_MISSING_BEFORE_CLAIM"] >= 1
    assert report["live_evaluation"]["failure_counts"]["OWNERSHIP_BOUNDARY_LEAK"] == 1
    assert report["live_evaluation"]["promoted_failure_counts"]["OWNERSHIP_BOUNDARY_LEAK"] == 1
    assert report["live_evaluation"]["actionable_remediation_failure_counts"]["OWNERSHIP_BOUNDARY_LEAK"] == 1
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


def test_model_cli_harness_scores_source_checkout_aw_invocation_as_package_cli() -> None:
    module = _load_harness_module()
    executed = module._normalized_command_text("uv run python scripts/run_agentic_workspace.py start --target . --format json")

    assert module._command_requirement_satisfied(required="uv run agentic-workspace start", executed_command_text=executed)


def test_model_cli_harness_prepares_fixture_git_repo_for_diff_commands(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is required for fixture git preparation")
    module = _load_harness_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    readme = repo / "README.md"
    readme.write_text("before\n", encoding="utf-8")

    module._prepare_fixture_git_repository(repo)
    readme.write_text("after\n", encoding="utf-8")
    result = subprocess.run(
        ["git", "diff", "--", "README.md"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0
    assert "-before" in result.stdout
    assert "+after" in result.stdout


def test_model_cli_harness_source_checkout_config_uses_local_schema(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    workspace = repo / ".agentic-workspace"
    workspace.mkdir(parents=True)

    module._prepare_source_checkout_invocation(repo)
    local_config = (workspace / "config.local.toml").read_text(encoding="utf-8")

    assert "schema_version = 1" in local_config
    assert 'cli_invoke = "uv run agentic-workspace"' in local_config
