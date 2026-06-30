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
    boundary = scorecard["authority_boundary"]

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
        "LOCAL_ABSOLUTE_PATH_LEAK",
        "HARNESS_SCENARIO_AMBIGUOUS",
    } <= failure_ids
    assert {"cli_output", "memory", "planning", "verification", "contracts", "harness", "no_change"} <= owner_surfaces
    assert boundary["harness_role"] == "maintainer-evaluation-evidence"
    assert boundary["runtime_authority"] == "none"
    assert boundary["portable_contract_status"] == "not-declared"


def test_external_agent_lane_rejects_missing_harness_authority_boundary() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    pack["scorecard"].pop("authority_boundary", None)

    errors = module.validate_pack(pack)

    assert "scorecard must define authority_boundary" in errors


def test_external_agent_lane_scenarios_cover_issue_lane_requirements() -> None:
    probes = _read_json("scenario-probes.json")["probes"]
    observation_contract = _read_json("scenario-probes.json")["completion_cost_observation_contract"]
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
    assert observation_contract["applies_to"] == "representative_evidence_records"
    assert observation_contract["minimum_observed_records"] == 3
    assert "representative observed records" in observation_contract["coverage_rule"]
    assert {
        "aw_command_count",
        "proof_command_count",
        "reread_events",
        "proof_churn_events",
        "over_planning_events",
        "review_repair_loop_count",
        "extra_aw_calls",
        "selector_inventory_reads",
        "raw_agentic_workspace_file_opens",
        "avoidable_clarifications",
        "missed_blockers",
        "repeated_rereads",
        "surface_causing_overhead",
        "handoff_recovery_status",
        "unsafe_closure_claims",
        "aw_sections_used",
        "cost_drivers",
    } <= set(observation_contract["required_fields"])
    cognitive_probes = {
        probe["cognitive_overhead_probe"]["scenario_class"]: probe
        for probe in probes
        if isinstance(probe.get("cognitive_overhead_probe"), dict)
    }
    assert {
        "active-planning-task-switch-proof-pressure",
        "low-risk-ordinary-path",
    } <= set(cognitive_probes)
    expected_metrics = {
        "extra_aw_calls",
        "selector_inventory_reads",
        "raw_agentic_workspace_file_opens",
        "avoidable_clarifications",
        "missed_blockers",
        "repeated_rereads",
    }
    for probe in cognitive_probes.values():
        contract = probe["cognitive_overhead_probe"]
        assert contract["kind"] == "agentic-workspace/cognitive-overhead-probe/v1"
        assert expected_metrics <= set(contract["expected_metrics"])
        assert contract["overhead_surfaces_to_identify"]


def test_external_agent_lane_completion_cost_observations_classify_representative_outcomes() -> None:
    records = _read_json("result-records.sample.json")["records"]
    observations = {
        record["scenario_id"]: record["completion_cost_observations"] for record in records if "completion_cost_observations" in record
    }

    assert len(observations) >= _read_json("scenario-probes.json")["completion_cost_observation_contract"]["minimum_observed_records"]
    assert observations["clean-host-startup"]["aw_command_count"] == 1
    assert observations["clean-host-startup"]["cost_drivers"][0]["classification"] == "startup_routing"
    assert observations["stale-memory-active-planning-handoff"]["reread_events"] >= 1
    assert {driver["classification"] for driver in observations["stale-memory-active-planning-handoff"]["cost_drivers"]} >= {
        "memory_reread",
        "review_repair",
    }
    assert observations["operational-decision-trace-required"]["unsafe_closure_claims"] == 1
    assert {driver["classification"] for driver in observations["operational-decision-trace-required"]["cost_drivers"]} >= {
        "proof_churn",
        "unsafe_closure",
    }
    assert observations["stale-memory-active-planning-handoff"]["selector_inventory_reads"] == 1
    assert observations["stale-memory-active-planning-handoff"]["surface_causing_overhead"] == "memory_decision_packet"
    assert observations["operational-decision-trace-required"]["raw_agentic_workspace_file_opens"] == 1
    assert observations["operational-decision-trace-required"]["surface_causing_overhead"] == "closeout_trust"
    assert observations["active-plan-task-switch-proof-pressure"]["missed_blockers"] == 0
    assert observations["active-plan-task-switch-proof-pressure"]["surface_causing_overhead"] == "none"
    assert observations["low-risk-ordinary-docs-direct-work"]["extra_aw_calls"] == 0
    assert observations["low-risk-ordinary-docs-direct-work"]["raw_agentic_workspace_file_opens"] == 0
    assert "implement.decision_packet" in observations["low-risk-ordinary-docs-direct-work"]["aw_sections_used"]


def test_external_agent_lane_surface_decisions_record_selector_first_start_reduction() -> None:
    decisions = {decision["id"]: decision for decision in _read_json("surface-decisions.sample.json")["decisions"]}

    memory_decision = decisions["startup-memory-decision-packet-selector-only"]
    installed_state_decision = decisions["startup-installed-state-compatibility-selector-only"]
    skill_catalog_decision = decisions["startup-skill-catalog-breakdown-command-only"]
    candidate_pressure_decision = decisions["implement-observed-candidate-pressure-summary"]
    memory_packet_decision = decisions["implement-memory-decision-packet-compact-default"]

    assert memory_decision["surface"] == "start.memory_decision_packet"
    assert memory_decision["decision"] == "route"
    assert "sample-memory-routing-regression" in memory_decision["evidence_refs"]
    assert memory_decision["rollback_condition"]
    assert installed_state_decision["surface"] == "start.installed_state_compatibility"
    assert installed_state_decision["decision"] == "route"
    assert "sample-startup-codex-spark" in installed_state_decision["evidence_refs"]
    assert installed_state_decision["expected_cost_change"]
    assert skill_catalog_decision["surface"] == "start.skills.catalog breakdown"
    assert skill_catalog_decision["decision"] == "route"
    assert "sample-startup-codex-spark" in skill_catalog_decision["evidence_refs"]
    assert "before:" in skill_catalog_decision["before_after_cost_signal"]
    assert "after:" in skill_catalog_decision["before_after_cost_signal"]
    assert "package" in skill_catalog_decision["authority_boundary_guardrail"]
    assert "required skill" in skill_catalog_decision["rollback_condition"]
    assert candidate_pressure_decision["surface"] == "implement.context.planning_safety_gate.candidate_pressure observed detail"
    assert candidate_pressure_decision["decision"] == "route"
    assert "before:" in candidate_pressure_decision["before_after_cost_signal"]
    assert "after:" in candidate_pressure_decision["before_after_cost_signal"]
    assert "hard blockers" in candidate_pressure_decision["authority_boundary_guardrail"]
    assert memory_packet_decision["surface"] == "implement.memory_decision_packet"
    assert memory_packet_decision["decision"] == "route"
    assert "before:" in memory_packet_decision["before_after_cost_signal"]
    assert "after:" in memory_packet_decision["before_after_cost_signal"]
    assert "pull/capture status" in memory_packet_decision["authority_boundary_guardrail"]


def test_external_agent_lane_rejects_invalid_completion_cost_observation() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    record = next(item for item in pack["results"]["records"] if item["scenario_id"] == "stale-memory-active-planning-handoff")
    record["completion_cost_observations"]["reread_events"] = -1
    record["completion_cost_observations"]["cost_drivers"][0]["classification"] = "expensive"

    errors = module.validate_pack(pack)

    assert any("reread_events must be a non-negative integer" in error for error in errors)
    assert any("classification is invalid" in error for error in errors)


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


def test_external_agent_lane_rejects_invalid_operating_loop_packet() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    record = next(item for item in pack["results"]["records"] if item["scenario_id"] == "operational-decision-trace-required")
    record["operating_loop"]["safe_claim"] = "probably"

    errors = module.validate_pack(pack)

    assert any("operating_loop safe_claim is invalid" in error for error in errors)


def test_trace_required_result_records_embed_integrated_operating_loop() -> None:
    records = _read_json("result-records.sample.json")["records"]
    record = next(item for item in records if item["scenario_id"] == "operational-decision-trace-required")
    loop = record["operating_loop"]

    assert loop["kind"] == "agentic-workspace/operating-loop-decision/v1"
    assert loop["memory"]["state"] == "dismissed"
    assert loop["planning"]["state"] == "continuation"
    assert loop["verification"]["state"] == "proof_selected"
    assert loop["safe_claim"] == "blocked"
    assert loop["residue_owner"] == "issue"


def test_external_agent_lane_rejects_invalid_historical_fixture_status() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    pack["historical"]["fixtures"][0]["status"] = "regression-guard"

    errors = module.validate_pack(pack)

    assert any("has invalid status" in error for error in errors)


def test_external_agent_lane_rejects_promotions_without_actionable_remediation() -> None:
    module = _load_module()
    pack = copy.deepcopy(module.load_pack(repo_root=REPO_ROOT))
    promotion = next(item for item in pack["promotions"]["decisions"] if item["id"] == "promote-proof-claim-boundary")
    promotion["followup_ref"] = "#1601"
    promotion.pop("remediation_kind", None)

    errors = module.validate_pack(pack)

    assert any("promote-proof-claim-boundary must route to an actionable remediation owner" in error for error in errors)


def test_external_agent_lane_records_repaired_live_local_path_leak() -> None:
    module = _load_module()
    pack = module.load_pack(repo_root=REPO_ROOT)
    live_run = next(item for item in pack["live_results"]["runs"] if item["id"] == "live-memory-consult-20260623T152211Z")

    assert live_run["live_outcome"] == "pass"
    assert live_run["failure_ids"] == []
    assert live_run["remediated_failure_ids"] == ["LOCAL_ABSOLUTE_PATH_LEAK"]
    assert live_run["raw_warning_classes"] == ["model_cli_local_path_leak"]
    assert live_run["final_message_repair"]["status"] == "repaired"
    assert live_run["final_message_repair"]["repairs"][0]["replacement"] == "README.md"


def test_external_agent_lane_closure_report_is_ready_from_fixture_pack() -> None:
    module = _load_module()
    report = module.build_closure_report(module.load_pack(repo_root=REPO_ROOT))

    assert report["kind"] == "agentic-workspace/external-agent-lane-closure-report/v1"
    assert report["default_external_agent"] == {"adapter": "codex", "model": "gpt-5.3-codex-spark"}
    assert report["live_evaluation_agent"] == {"adapter": "codex", "model": "gpt-5.4-mini"}
    assert report["fixture_closure_state"] == "ready_for_fixture_closure"
    assert report["closure_state"] == "ready_for_full_closure"
    assert report["live_evaluation"]["status"] == "clean"
    assert report["live_evaluation"]["clean_run_count"] == 4
    assert report["acceptance"]["scenario_probes_cover_major_phases"] is True
    assert report["acceptance"]["artifact_backed_path_defined"] is True
    assert report["acceptance"]["operating_loop_observable"] is True
    assert report["acceptance"]["completion_cost_observation_contract_exists"] is True
    assert report["acceptance"]["completion_cost_observations_exist"] is True
    assert report["failure_counts"]["PROOF_MISSING_BEFORE_CLAIM"] >= 1
    assert report["failure_counts"]["PARTIAL_PROGRESS_CLAIMED_AS_FULL"] >= 1
    assert report["live_evaluation"]["failure_counts"] == {}
    assert report["live_evaluation"]["promoted_failure_counts"] == {}
    assert report["live_evaluation"]["actionable_remediation_failure_counts"] == {}
    assert report["promotion_count"] >= 1
    loop = report["operating_loop_observability"]
    assert loop["kind"] == "agentic-workspace/external-agent-operating-loop-observability/v1"
    assert loop["record_count"] >= 1
    assert loop["safe_claim_counts"]["blocked"] >= 1
    assert loop["residue_owner_counts"]["issue"] >= 1
    cost = report["completion_cost_observability"]
    assert cost["kind"] == "agentic-workspace/external-agent-completion-cost-observability/v1"
    assert cost["record_count"] >= 3
    assert cost["driver_classification_counts"]["memory_reread"] >= 1
    assert cost["driver_classification_counts"]["unsafe_closure"] >= 1
    assert cost["totals"]["proof_command_count"] >= 2


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


def test_model_cli_harness_startup_prompt_has_final_answer_path_hygiene(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text(
        "# Agent Instructions\n"
        "<!-- agentic-workspace:workflow:start -->\n"
        "Report repo-relative paths, not local absolute paths.\n"
        "<!-- agentic-workspace:workflow:end -->\n",
        encoding="utf-8",
    )

    prompt = module._startup_instruction_prompt(repo_path=repo, prompt="Update README.md.")

    assert "Final answer path rule" in prompt
    assert "convert any absolute cwd, fixture, run_root, session, prompt-file" in prompt
    assert "repo-relative path when it is inside the copied repository" in prompt
    assert "do not use Markdown file links" in prompt
    assert "plain file names such as `README.md`" in prompt
    assert "describe it by role instead of printing the local absolute path" in prompt


def test_model_cli_harness_scores_local_absolute_path_leak_with_owner(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    drive = "C:"
    leaked_path = f"{drive}\\Users\\agent\\.agentic-workspace\\local\\scratch\\run.md"

    warnings = module._metadata_workflow_warnings(
        scenario={"id": "memory-consult-before-edit"},
        result={
            "status": "success",
            "final_message": f"Updated README.md and wrote notes at {leaked_path}",
        },
        mutation_summary={"created": [], "modified": ["README.md"], "deleted": []},
        repo_path=repo,
    )

    leak = next(warning for warning in warnings if warning["warning_class"] == "model_cli_local_path_leak")
    assert leak["failure_id"] == "LOCAL_ABSOLUTE_PATH_LEAK"
    assert leak["owner_surface"] == "harness"
    assert leak["remediation_ref"] == "#1616"
    assert leak["evidence"].startswith(f"{drive}\\Users\\agent")


def test_model_cli_harness_scores_posix_tmp_path_leak_with_owner(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    leaked_path = "/".join(["", "tmp", "pytest-of-runner", "pytest-0", "popen-gw1", "session.md"])

    warnings = module._metadata_workflow_warnings(
        scenario={"id": "memory-consult-before-edit"},
        result={
            "status": "success",
            "final_message": f"Updated README.md and wrote notes at {leaked_path}",
        },
        mutation_summary={"created": [], "modified": ["README.md"], "deleted": []},
        repo_path=repo,
    )

    leak = next(warning for warning in warnings if warning["warning_class"] == "model_cli_local_path_leak")
    assert leak["failure_id"] == "LOCAL_ABSOLUTE_PATH_LEAK"
    assert leak["owner_surface"] == "harness"
    assert leak["remediation_ref"] == "#1616"
    assert leak["evidence"].startswith("/".join(["", "tmp", "pytest-of-runner"]))


def test_model_cli_harness_repairs_exported_final_message_without_suppressing_warning(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    run_root = tmp_path / "run"
    repo.mkdir()
    run_root.mkdir()
    readme = repo / "README.md"
    readme.write_text("notes\n", encoding="utf-8")
    share_path = run_root / "session.md"
    raw_message = f"Changed [README.md]({readme.as_posix()}) and see {run_root.as_posix()}/session.md"
    result = {"status": "success", "final_message": raw_message}

    warnings = module._metadata_workflow_warnings(
        scenario={"id": "memory-consult-before-edit"},
        result=result,
        mutation_summary={"created": [], "modified": ["README.md"], "deleted": []},
        repo_path=repo,
    )
    repair = module._repair_result_final_message_local_paths(
        result=result,
        repo_path=repo,
        run_root=run_root,
        share_path=share_path,
    )

    leak = next(warning for warning in warnings if warning["warning_class"] == "model_cli_local_path_leak")
    assert leak["failure_id"] == "LOCAL_ABSOLUTE_PATH_LEAK"
    assert repair["status"] == "repaired"
    assert {item["kind"] for item in repair["repairs"]} == {"repo_relative", "harness_artifact_role"}
    assert result["final_message"] == "Changed [README.md](README.md) and see <harness artifact>"
    assert share_path.read_text(encoding="utf-8") == result["final_message"]
    assert str(tmp_path).replace("\\", "/") not in result["final_message"]


def test_model_cli_harness_allows_repo_relative_final_paths(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = module._metadata_workflow_warnings(
        scenario={"id": "memory-consult-before-edit"},
        result={"status": "success", "final_message": "Updated README.md and cited .agentic-workspace/planning/state.toml."},
        mutation_summary={"created": [], "modified": ["README.md"], "deleted": []},
        repo_path=repo,
    )

    assert not [warning for warning in warnings if warning["warning_class"] == "model_cli_local_path_leak"]


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


def test_model_cli_harness_codex_source_checkout_fixture_uses_current_checkout(tmp_path: Path) -> None:
    module = _load_harness_module()

    payload = module.run_suite(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        adapter_id="codex",
        model="gpt-5.4-mini",
        scenario_filter="memory-consult-before-edit",
        prompt_variant="packaging-note",
        execute=False,
        output_root=tmp_path / "runs",
        timeout_seconds=None,
    )

    pyproject_text = (Path(payload["results"][0]["repo_path"]) / "pyproject.toml").read_text(encoding="utf-8")
    assert '"agentic-workspace",' in pyproject_text
    assert "[tool.uv.sources]" in pyproject_text
    assert f'agentic-workspace = {{ path = "{REPO_ROOT.as_posix()}", editable = true }}' in pyproject_text


def test_model_cli_harness_default_output_root_is_manifest_backed_scratch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_harness_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    output_root = tmp_path / ".agentic-workspace" / "local" / "scratch" / "runs"
    paths = module._scenario_paths(
        output_root=output_root,
        suite_id="suite",
        scenario_id="scenario",
        adapter_id="adapter",
        model="model",
    )
    paths.run_root.mkdir(parents=True)

    manifest = module._write_scratch_run_manifest(
        paths.run_root,
        purpose="test manifest",
        aw_runs_root=output_root,
    )

    assert module.DEFAULT_OUTPUT_ROOT.as_posix().endswith(".agentic-workspace/local/scratch/runs")
    assert manifest == paths.run_root / ".aw-scratch.toml"
    manifest_text = manifest.read_text(encoding="utf-8")
    assert 'owner = "agentic-workspace"' in manifest_text
    assert 'producer = "model-cli-harness"' in manifest_text
    assert 'retention = "ephemeral"' in manifest_text


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
