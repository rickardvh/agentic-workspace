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
SBX_ADAPTER_SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "run_sbx_codex_adapter.py"


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


def _load_sbx_adapter_module():
    spec = importlib.util.spec_from_file_location("run_sbx_codex_adapter", SBX_ADAPTER_SCRIPT)
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
        "intent_satisfaction",
        "ownership",
        "recovery",
    } <= dimensions
    assert {
        "MEMORY_PULL_MISSING",
        "PLANNING_CONTINUITY_MISSING",
        "PROOF_MISSING_BEFORE_CLAIM",
        "PARTIAL_PROGRESS_CLAIMED_AS_FULL",
        "LOCAL_MEMORY_ROUTE_MISSING",
        "CONFIG_RECOVERY_NOT_SURFACED",
        "PROOF_COMMAND_DRIFT_UNDETECTED",
        "DELEGATION_NOISE_DISTRACTS_DIRECT_WORK",
        "OPERATIONAL_TRACE_INSUFFICIENT",
        "ARTIFACT_INSTALL_EVIDENCE_MISSING",
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
        "local-command-memory-route",
        "obsolete-config-startup-recovery",
        "documented-proof-command-drift",
        "bounded-direct-work-delegation-quiet",
        "operational-decision-trace-required",
    } <= probe_ids
    assert {
        "startup",
        "work_shape",
        "memory_pull",
        "planning_continuity",
        "proof",
        "closeout",
        "intent_satisfaction",
        "ownership",
        "recovery",
    } <= covered_dimensions
    assert any(probe.get("artifact_backed") for probe in probes)
    artifact_probe = next(probe for probe in probes if probe["id"] == "artifact-backed-host-startup")
    assert {"artifact_source", "artifact_checksum", "installed_entrypoint"} <= set(artifact_probe["artifact_evidence"]["required_fields"])


def test_external_agent_lane_historical_fixtures_map_to_result_records() -> None:
    fixtures = _read_json("historical-failure-fixtures.json")["fixtures"]
    records = {record["id"]: record for record in _read_json("result-records.sample.json")["records"]}

    assert len(fixtures) >= 4
    assert any("proof" in fixture["id"] for fixture in fixtures)
    assert any("memory" in fixture["id"] for fixture in fixtures)
    assert {fixture["status"] for fixture in fixtures} <= {
        "active_regression_guard",
        "historical_calibration",
        "retired",
    }
    assert any(fixture["id"] == "partial-slice-claimed-parent-closed" for fixture in fixtures)
    for fixture in fixtures:
        assert fixture["result_record_ref"] in records
        assert fixture["failure_ids"]
        assert fixture["current_aw_signals"]
        assert fixture["owner_surface_if_repeats"]


def test_external_agent_lane_rejects_fixture_failures_absent_from_result_record() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    pack["historical"]["fixtures"][0]["failure_ids"].append("MEMORY_PULL_MISSING")

    errors = module.validate_pack(pack)

    assert any("failure MEMORY_PULL_MISSING is not represented by sample-broad-work-regression" in error for error in errors)


def test_external_agent_lane_rejects_trace_required_record_without_decisions() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    record = next(item for item in pack["results"]["records"] if item["scenario_id"] == "operational-decision-trace-required")
    record["decisions"] = {"memory": {"status": "dismissed"}}

    errors = module.validate_pack(pack)

    assert any("must include operational decision trace keys" in error for error in errors)


def test_external_agent_lane_rejects_invalid_historical_fixture_status() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    pack["historical"]["fixtures"][0]["status"] = "regression-guard"

    errors = module.validate_pack(pack)

    assert any("has invalid status" in error for error in errors)


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
    assert report["failure_counts"]["PARTIAL_PROGRESS_CLAIMED_AS_FULL"] >= 1
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


def test_model_cli_harness_preflight_resolves_adapter_executable_candidates(tmp_path: Path) -> None:
    module = _load_harness_module()
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir()
    sbx = tool_dir / "sbx.exe"
    sbx.write_text("", encoding="utf-8")

    preflight = module._adapter_preflight(
        {
            "adapter_executable": {
                "name": "sbx",
                "candidate_paths": ["{tool_dir}/sbx.exe"],
                "add_parent_to_path": True,
            }
        },
        command=["sbx", "run", "codex"],
        replacements={"tool_dir": str(tool_dir)},
    )

    assert preflight["status"] == "ready"
    assert preflight["requirements"][0]["resolved_path"] == str(sbx)
    assert preflight["path_prepend"] == [str(tool_dir)]


def test_model_cli_harness_captures_repo_local_sandbox_share_file(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    sandbox_share = repo / ".agentic-workspace" / "local" / "scratch" / "model-cli-harness" / "session.md"
    sandbox_share.parent.mkdir(parents=True)
    sandbox_share.write_text("sandbox final\n", encoding="utf-8")
    share_path = tmp_path / "run" / "session.md"

    capture = module._capture_adapter_artifacts(
        {
            "artifact_capture": {
                "share_path_candidates": ["{repo}/.agentic-workspace/local/scratch/model-cli-harness/session.md"],
                "cleanup_captured": True,
            }
        },
        replacements={"repo": str(repo)},
        share_path=share_path,
    )

    assert capture["share_captured"] is True
    assert share_path.read_text(encoding="utf-8") == "sandbox final\n"
    assert not sandbox_share.exists()


def test_model_cli_harness_codex_sbx_dry_run_marks_sandbox(tmp_path: Path) -> None:
    module = _load_harness_module()

    payload = module.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="codex-sbx",
        model=None,
        scenario_filter="startup-orientation",
        execute=False,
        output_root=tmp_path,
        timeout_seconds=None,
    )

    result = payload["results"][0]
    assert result["adapter_id"] == "codex-sbx"
    assert result["command"][0].endswith(("python", "python.exe"))
    assert result["command"][1].replace("\\", "/").endswith("scripts/model_cli_harness/run_sbx_codex_adapter.py")
    assert "--sandbox-name" in result["command"]
    assert "--template" in result["command"]
    assert "agentic-workspace/codex-sbx:local" in result["command"]
    assert "--prompt-file" in result["command"]
    assert result["prompt_transport"]["mode"] == "prompt-file"
    assert result["sandbox"]["kind"] == "agentic-workspace/model-cli-sandbox-adapter/v1"
    assert result["sandbox"]["evidence"] == "sandbox-backed"
    assert result["sandbox"]["backend"] == "docker-sandbox"
    assert result["sandbox"]["template"] == "agentic-workspace/codex-sbx:local"
    pyproject = Path(result["repo_path"]) / "pyproject.toml"
    pyproject_text = pyproject.read_text(encoding="utf-8")
    assert "agentic_workspace-0.4.3-py3-none-any.whl" in pyproject_text
    assert "agentic_memory-0.4.3-py3-none-any.whl" not in pyproject_text
    assert "[tool.uv.sources]" not in pyproject_text


def test_sbx_codex_adapter_removes_named_sandbox_after_failed_run(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_sbx_adapter_module()
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        returncode = 17 if command[:5] == ["sbx", "exec", "aw-test", "codex", "exec"] else 0
        return subprocess.CompletedProcess(command, returncode, stdout="", stderr="")

    monkeypatch.setattr(module, "_run", fake_run)

    result = module.main(
        [
            "--sbx",
            "sbx",
            "--sandbox-name",
            "aw-test",
            "--repo",
            "work/repo",
            "--model",
            "gpt-test",
            "--share-path",
            "work/share/final.md",
            "--prompt",
            "do work",
        ]
    )

    assert result == 17
    assert commands[-1] == ["sbx", "rm", "--force", "aw-test"]


def test_model_cli_harness_local_wheelhouse_mode_overrides_release_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_harness_module()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()

    monkeypatch.setattr(module, "_build_local_aw_wheelhouse", lambda output_root: wheelhouse)
    monkeypatch.setattr(
        module,
        "_fixture_local_wheel_dependency",
        lambda *, repo_path, source_wheelhouse, adapter: "agentic-workspace @ file:///fixture-wheelhouse/agentic_workspace.whl",
    )

    payload = module.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="codex-sbx",
        model=None,
        scenario_filter="startup-orientation",
        execute=False,
        output_root=tmp_path / "runs",
        timeout_seconds=None,
        aw_dependency_mode="local-wheelhouse",
    )

    pyproject_text = (Path(payload["results"][0]["repo_path"]) / "pyproject.toml").read_text(encoding="utf-8")
    assert "fixture-wheelhouse/agentic_workspace.whl" in pyproject_text
    assert "releases/download/v0.4.3" not in pyproject_text
