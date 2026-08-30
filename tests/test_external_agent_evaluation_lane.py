from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import posixpath
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
LANE_DIR = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation"
SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "external_agent_evaluation_lane.py"
HARNESS_SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "run_model_cli_harness.py"
SBX_ADAPTER_SCRIPT = REPO_ROOT / "scripts" / "model_cli_harness" / "run_sbx_codex_adapter.py"
CONFIGURED_FIXTURE_SCRIPT = LANE_DIR / "prepare_configured_orchestration_fixture.py"
CONTEXT_COST_BRIDGE_SCRIPT = LANE_DIR / "codex_context_cost_bridge.py"
CONTEXT_COST_CAPTURE_SCRIPT = LANE_DIR / "capture_issue_2818_context_cost.py"


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


def _load_configured_fixture_module():
    spec = importlib.util.spec_from_file_location("prepare_configured_orchestration_fixture", CONFIGURED_FIXTURE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_context_cost_bridge_module():
    spec = importlib.util.spec_from_file_location("codex_context_cost_bridge", CONTEXT_COST_BRIDGE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_codex_context_cost_bridge_projects_only_neutral_metrics() -> None:
    module = _load_context_cost_bridge_module()
    metrics = module.parse_codex_jsonl(
        "\n".join(
            [
                '{"type":"thread.started","thread_id":"secret-thread"}',
                '{"type":"item.completed","item":{"type":"command_execution","command":"secret command"}}',
                '{"type":"item.completed","item":{"type":"agent_message","text":"private transcript"}}',
                '{"type":"turn.completed","usage":{"input_tokens":13117,"cached_input_tokens":8960,"output_tokens":134,"reasoning_output_tokens":118}}',
            ]
        )
    )

    assert metrics == {
        "kind": "agentic-workspace/assignment-transport-metrics/v1",
        "effective_input_tokens": 13117,
        "cached_input_tokens": 8960,
        "output_tokens": 134,
        "orientation_command_count": 1,
    }
    assert "thread" not in json.dumps(metrics)
    assert "secret" not in json.dumps(metrics)
    assert "transcript" not in json.dumps(metrics)


def test_issue_2818_supported_host_cost_evidence_is_bounded_honest_and_actionable() -> None:
    evidence = _read_json("assignment-context-cost-dogfood-2026-08-30.json")
    historical = evidence["historical_regression"]
    host = evidence["supported_host"]
    runs = {run["target"]: run for run in evidence["runs"]}
    comparison = evidence["before_after"]

    assert historical == {
        "source": "tools/model-cli-harness/external-agent-evaluation/nonlocal-delegation-dogfood-2026-08-27.json",
        "assignment_packet_bytes": 3662,
        "rendered_prompt_bytes": 3913,
        "effective_input_tokens": 81752,
        "cached_input_tokens": 62464,
        "output_tokens": 1591,
        "inflation_boundary": "between AW semantic prompt rendering and effective supported-host worker input",
        "token_savings_claimed": False,
    }
    assert host["cli_version"] == "codex-cli 0.151.0"
    assert host["raw_transcript_checked_in"] is False
    assert host["workspace_mutation_observed"] is False
    assert host["provider_event_projection_sha256"] == hashlib.sha256(CONTEXT_COST_BRIDGE_SCRIPT.read_bytes()).hexdigest()
    assert CONTEXT_COST_CAPTURE_SCRIPT.is_file()

    schema = json.loads(
        (REPO_ROOT / "src/agentic_workspace/contracts/schemas/assignment_context_cost.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    for run in runs.values():
        Draft202012Validator(schema).validate(run["context_cost"])
        assert run["status"] == "returned"
        assert run["return_boundary"]["changed_paths"] == []
        assert run["return_boundary"]["stop_conditions_hit"] == []
        assert run["return_boundary"]["worker_proof_authority"] is False
        assert run["return_boundary"]["worker_completion_authority"] is False
        assert run["workspace_mutation_observed"] is False
        assert run["raw_transcript_checked_in"] is False
        assert run["context_cost"]["effective_input_tokens"] > run["context_cost"]["rendered_prompt_bytes"] * 50
        assert run["context_cost"]["unknown_fields"] == ["retry_count", "repair_loop_count"]

    assert comparison["delegated_bounded_luna_total_tokens"] == 491854
    assert comparison["all_strong_local_sol_total_tokens"] == 473287
    assert comparison["delegated_minus_local_tokens"] == 18567
    assert comparison["luna_minus_sol_elapsed_ms"] == -10802
    assert comparison["comparison_posture"] == "observed-context-inflation-retains-current-target"
    assert comparison["economic_context"] == {
        "codex_luna": {"cost_class": "cheap", "latency_class": "fast"},
        "codex_sol": {"cost_class": "premium", "latency_class": "slow"},
        "authority": "maintainer-confirmed target-profile classification",
        "portable_price_normalization": None,
    }
    assert comparison["token_savings_claimed"] is False
    assert evidence["decision_replay"]["decision"] == "assign-current-target"
    assert evidence["decision_replay"]["selected_target"] == "codex_sol"
    assert evidence["decision_replay"]["selected_transport"] == "cli"
    assert evidence["decision_replay"]["context_inflation_guard"]["status"] == "applied"
    assert evidence["decision_replay"]["context_inflation_guard"]["cases"][0]["observed_increase_tokens"] == 18567


def _read_json(name: str) -> dict:
    return json.loads((LANE_DIR / name).read_text(encoding="utf-8"))


def test_external_agent_lane_pack_validates() -> None:
    module = _load_module()
    pack = module.load_pack(repo_root=REPO_ROOT)

    assert module.validate_pack(pack) == []


def test_mixed_provider_availability_is_explicit_and_never_fabricates_fallback_proof() -> None:
    availability = _read_json("provider-availability-2026-08-14.json")
    routes = {item["family"]: item for item in availability["routes"]}

    assert routes["openai-codex"]["status"] == "available-with-current-evidence"
    assert routes["distinct-vendor"]["status"] == "unavailable"
    assert "do not silently substitute" in routes["distinct-vendor"]["fallback"]
    assert routes["separate-strong-tier-live-run"]["status"] == "unavailable"
    assert availability["rule"].startswith("Provider absence is explicit evidence")


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
    live_run = next(item for item in pack["live_results"]["runs"] if item["id"] == "live-memory-trap-aware-20260814T094836Z")

    assert live_run["live_outcome"] == "weak_noncompliant"
    assert live_run["admission_status"] == "admitted_routed_weak_case"
    assert live_run["failure_ids"] == ["HARNESS_SCENARIO_AMBIGUOUS"]
    assert live_run["remediated_failure_ids"] == ["LOCAL_ABSOLUTE_PATH_LEAK"]
    assert live_run["raw_warning_classes"] == ["model_cli_local_path_leak"]
    assert live_run["final_message_repair"]["status"] == "repaired"
    assert live_run["final_message_repair"]["repairs"][0]["replacement"] == "README.md"
    assert live_run["noncompliance"]["disposition"].startswith("retained as current weak-agent evidence")


def test_external_agent_lane_closure_report_is_ready_from_fixture_pack() -> None:
    module = _load_module()
    report = module.build_closure_report(module.load_pack(repo_root=REPO_ROOT))

    assert report["kind"] == "agentic-workspace/external-agent-lane-closure-report/v1"
    assert report["default_external_agent"] == {"adapter": "codex", "model": "gpt-5.3-codex-spark"}
    assert report["live_evaluation_agent"] == {"adapter": "codex", "model": "gpt-5.3-codex-spark"}
    assert report["fixture_closure_state"] == "ready_for_fixture_closure"
    assert report["closure_state"] == "partial_closure"
    assert report["provider_availability"]["configured_orchestration_live_ready"] is False
    assert report["live_evaluation"]["status"] == "clean-with-admitted-weak-cases"
    assert report["live_evaluation"]["clean_run_count"] == 2
    assert report["live_evaluation"]["admitted_weak_run_count"] == 1
    assert report["acceptance"]["scenario_probes_cover_major_phases"] is True
    assert report["acceptance"]["artifact_backed_path_defined"] is True
    assert report["acceptance"]["operating_loop_observable"] is True
    assert report["acceptance"]["completion_cost_observation_contract_exists"] is True
    assert report["acceptance"]["completion_cost_observations_exist"] is True
    assert report["failure_counts"]["PROOF_MISSING_BEFORE_CLAIM"] >= 1
    assert report["failure_counts"]["PARTIAL_PROGRESS_CLAIMED_AS_FULL"] >= 1
    assert report["live_evaluation"]["failure_counts"] == {"HARNESS_SCENARIO_AMBIGUOUS": 1}
    assert report["live_evaluation"]["actionable_remediation_failure_counts"]["HARNESS_SCENARIO_AMBIGUOUS"] >= 1
    assert report["live_evaluation"]["promoted_failure_counts"] == {"HARNESS_SCENARIO_AMBIGUOUS": 1}
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


def test_model_cli_harness_prompt_variants_preserve_scoring_overrides() -> None:
    module = _load_harness_module()

    variants = module._prompt_variants(
        {
            "id": "receipt-aware",
            "prompt_variants": [
                {
                    "id": "submit",
                    "prompt": "Submit it.",
                    "forbidden_write_patterns": [],
                    "required_operation_receipts": [{"operation_id": "correction-event.submit"}],
                },
                {"id": "host-recovery", "prompt": "Recover it.", "scoring_ref": "submit"},
            ],
        }
    )

    assert variants[0]["forbidden_write_patterns"] == []
    assert variants[0]["required_operation_receipts"] == [{"operation_id": "correction-event.submit"}]
    recovered = module._prompt_variants(
        {
            "id": "receipt-aware",
            "prompt_variants": [
                {"id": "submit", "prompt": "Submit it.", "required_artifact_patterns": ["receipt.json"]},
                {"id": "host-recovery", "prompt": "Recover it.", "scoring_ref": "submit"},
            ],
        },
        requested="host-recovery",
    )
    assert recovered[0]["prompt"] == "Recover it."
    assert recovered[0]["required_artifact_patterns"] == ["receipt.json"]


def test_model_cli_harness_requires_executed_correction_receipts_and_idempotent_local_custody(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    store_path = repo / ".agentic-workspace/local/correction-events.json"
    store_path.parent.mkdir(parents=True)
    expected_event = {
        "target_identity_ref": "cheap_docs_worker",
        "target_revision": "rev-b",
        "task_class": "code-change",
        "scope_class": "narrow",
        "phase": "proof",
        "subsystem": "workspace-runtime",
        "surface": "final-response",
    }
    store_path.write_text(json.dumps({"events": [expected_event]}), encoding="utf-8")
    requirement = {
        "operation_id": "correction-event.submit",
        "minimum_result_count": 2,
        "required_statuses": ["stored"],
        "admission_bucket": "admission.low_authority_events",
        "store_ref": ".agentic-workspace/local/correction-events.json",
        "expected_store_event_count": 1,
        "expected_event": expected_event,
    }
    receipt = {
        "kind": "agentic-workspace/correction-event-operation-result/v1",
        "operation_id": "correction-event.submit",
        "status": "stored",
        "mutation_applied": True,
        "store_ref": ".agentic-workspace/local/correction-events.json",
        "admission": {"low_authority_events": [expected_event]},
    }
    stdout = "\n".join(
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "command_execution",
                    "command": "uv run agentic-workspace correction-event submit --format json",
                    "aggregated_output": json.dumps(receipt),
                    "exit_code": 0,
                },
            }
        )
        for _ in range(2)
    )

    warnings = module._metadata_workflow_warnings(
        scenario={"id": "receipt-aware", "required_operation_receipts": [requirement]},
        result={"status": "success", "stdout": stdout, "final_message": "Stored and queried."},
        mutation_summary={"created": [".agentic-workspace/local/correction-events.json"], "modified": [], "deleted": []},
        repo_path=repo,
    )

    assert not [warning for warning in warnings if "operation receipt" in warning["message"].lower()]
    assert not [warning for warning in warnings if "custody store" in warning["message"].lower()]


def test_model_cli_harness_rejects_operation_recognition_without_receipt(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    repo.mkdir()

    warnings = module._metadata_workflow_warnings(
        scenario={
            "id": "receipt-aware",
            "required_operation_receipts": [
                {
                    "operation_id": "correction-event.submit",
                    "minimum_result_count": 1,
                    "store_ref": ".agentic-workspace/local/correction-events.json",
                }
            ],
        },
        result={"status": "success", "final_message": "Use correction-event.submit."},
        mutation_summary={"created": [], "modified": [], "deleted": []},
        repo_path=repo,
    )

    assert any("structured operation receipts" in warning["message"] for warning in warnings)


def test_model_cli_harness_scores_assignment_lifecycle_from_operation_receipts_not_prose(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    artifact = repo / ".agentic-workspace/local/assignment-runs/run-1/export/packet.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps({"kind": "agentic-workspace/assignment-export-packet/v1", "run_id": "run-1"}),
        encoding="utf-8",
    )
    receipt = {
        "kind": "agentic-workspace/assignment-lifecycle-result/v1",
        "operation_id": "assignment.export",
        "transition": "export",
        "status": "handoff-prepared",
        "outcome": "applied",
        "mutation_applied": True,
        "run_id": "run-1",
        "artifact_refs": [artifact.relative_to(repo).as_posix()],
    }
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "command": "agentic-workspace assignment export --format json",
                "aggregated_output": json.dumps(receipt),
                "exit_code": 0,
            },
        }
    )
    requirement = {
        "operation_id": "assignment.export",
        "result_kinds": ["agentic-workspace/assignment-lifecycle-result/v1"],
        "required_statuses": ["handoff-prepared"],
        "required_outcomes": ["applied"],
        "mutation_applied": True,
        "expected_fields": {"transition": "export"},
        "required_artifact_kinds": ["agentic-workspace/assignment-export-packet/v1"],
    }

    warnings = module._metadata_workflow_warnings(
        scenario={"id": "configured-route", "required_operation_receipts": [requirement]},
        result={"status": "success", "stdout": stdout, "final_message": "Prepared the projected action."},
        mutation_summary={"created": [artifact.relative_to(repo).as_posix()], "modified": [], "deleted": []},
        repo_path=repo,
    )
    prose_only = module._metadata_workflow_warnings(
        scenario={"id": "configured-route", "required_operation_receipts": [requirement]},
        result={"status": "success", "final_message": "I will run assignment.export."},
        mutation_summary={"created": [], "modified": [], "deleted": []},
        repo_path=repo,
    )

    assert not [warning for warning in warnings if "operation receipt" in warning["message"].lower()]
    assert any("structured operation receipts" in warning["message"] for warning in prose_only)


def test_model_cli_harness_rejects_blocked_or_wrong_transition_assignment_receipt(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    receipt = {
        "kind": "agentic-workspace/assignment-lifecycle-result/v1",
        "operation_id": "assignment.export",
        "transition": "import",
        "status": "blocked",
        "outcome": "blocked",
        "mutation_applied": False,
    }
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "command": "agentic-workspace assignment export --format json",
                "aggregated_output": json.dumps(receipt),
                "exit_code": 0,
            },
        }
    )

    warnings = module._metadata_workflow_warnings(
        scenario={
            "id": "configured-route",
            "required_operation_receipts": [
                {
                    "operation_id": "assignment.export",
                    "required_statuses": ["handoff-prepared"],
                    "required_outcomes": ["applied"],
                    "mutation_applied": True,
                    "expected_fields": {"transition": "export"},
                }
            ],
        },
        result={"status": "success", "stdout": stdout, "final_message": "Exported."},
        mutation_summary={"created": [], "modified": [], "deleted": []},
        repo_path=repo,
    )

    assert any("structured operation receipts" in warning["message"] for warning in warnings)


def test_current_adapter_guidance_live_evidence_is_head_bound_and_honest() -> None:
    evidence_root = REPO_ROOT / "tools" / "model-cli-harness" / "external-agent-evaluation"
    payload = json.loads((evidence_root / "live-results-2026-08-14-adapter-guidance.json").read_text(encoding="utf-8"))
    availability = json.loads((evidence_root / "provider-availability-2026-08-14.json").read_text(encoding="utf-8"))

    current_head = "2bfdf2ac3061d531742fbe37657fc8e4142b29fd"
    assert payload["evaluated_implementation_head"] == current_head
    current_runs = [run for run in payload["runs"] if run.get("evaluated_implementation_head") == current_head]
    current_outcomes = {run["prompt_variant"]: run["live_outcome"] for run in current_runs}
    assert current_outcomes["explicit-correction-capture"] == "pass-first-request-executed"
    assert current_outcomes["missed-correction-host-recovery"] == "pass-host-normalized-recovery-executed"
    assert all(run["warning_classes"] == [] for run in current_runs)
    assert all(run["operation_evidence"]["submit_receipt_count"] == 2 for run in current_runs)
    assert all(run["operation_evidence"]["query_receipt_count"] == 1 for run in current_runs)
    assert all(run["operation_evidence"]["duplicate_mutation_applied"] is False for run in current_runs)
    assert all(run["operation_evidence"]["matching_stored_event_count"] == 1 for run in current_runs)
    assert any(run["live_outcome"] == "miss" for run in payload["runs"])
    recovery = next(run for run in payload["runs"] if run["live_outcome"] == "recovered-on-second-request")
    assert recovery["requests_to_completion"] == 2
    historical_outcomes = {run["prompt_variant"]: run["live_outcome"] for run in payload["runs"] if run not in current_runs}
    assert historical_outcomes["changed-requirement-negative"].startswith("pass")
    assert historical_outcomes["later-context-retrieval"].startswith("pass")
    assert historical_outcomes["violation-recovery-consequence"].startswith("pass")
    assert availability["routes"][0]["evaluated_implementation_head"] == current_head

    evaluation = payload["evaluation_operation"]
    assert evaluation["operation"] == "evaluation.observe"
    assert evaluation["admitted_observation_count"] == 5
    assert evaluation["observed_criterion_count"] == 3
    assert set(evaluation["current_criterion_states"].values()) == {"satisfied"}
    assert evaluation["lifecycle"] == "collecting"
    assert evaluation["conclusion_readiness"]["ready"] is False

    codex = next(route for route in availability["routes"] if route["family"] == "openai-codex")
    assert codex["evidence_ref"] == "live-results-2026-08-14-adapter-guidance.json"
    assert codex["evaluated_implementation_head"] == payload["evaluated_implementation_head"]
    assert {route["status"] for route in availability["routes"] if route["family"] != "openai-codex"} == {"unavailable"}


def test_configured_orchestration_evaluation_matrix_covers_receipts_failures_cost_and_availability() -> None:
    module = _load_module()
    pack = module.load_pack()

    assert module.validate_pack(pack) == []
    matrix = pack["configured_orchestration"]
    routes = {item["id"]: item for item in matrix["routes"]}
    assert routes["ordinary-nonlocal-export"]["prompt_activation_terms"] == []
    assert routes["ordinary-nonlocal-export"]["expected_operations"] == ["assignment.export"]
    assert routes["selected-current-direct"]["expected_operations"] == []
    assert routes["manual-return-lifecycle"]["expected_operations"] == [
        "assignment.export",
        "assignment.import",
        "assignment.admit",
        "assignment.integrate",
    ]
    failure_cases = {item["case"] for item in matrix["failure_matrix"]}
    assert {"stale-return-revision", "malformed-return", "worker-refused-or-blocked", "tie-or-uncertainty", "no-safe-route"}.issubset(
        failure_cases
    )
    comparisons = {item["id"]: item for item in matrix["total_successful_completion_cost"]["comparisons"]}
    assert comparisons["bounded-mechanical-docs"]["preferred"] == "delegated"
    assert comparisons["bounded-mechanical-docs"]["delegated"]["total"] < comparisons["bounded-mechanical-docs"]["stay_local"]["total"]
    assert comparisons["judgment-heavy-contract-review"]["preferred"] == "stay-local"
    assert (
        comparisons["judgment-heavy-contract-review"]["stay_local"]["total"]
        < comparisons["judgment-heavy-contract-review"]["delegated"]["total"]
    )

    availability = pack["provider_availability"]
    assert availability["checked_at"] == "2026-08-24"
    routes_by_family = {route["family"]: route for route in availability["routes"]}
    assert routes_by_family["openai-codex"]["status"] == "cli-available-current-head-behavioral-pass"
    assert routes_by_family["openai-codex"]["proof_class"] == "available-agent-behavioral"
    assert routes_by_family["openai-codex"]["evidence_ref"] == "configured-orchestration-live-evidence-2026-08-24.json"
    assert all("pass" not in route["status"] for family, route in routes_by_family.items() if family != "openai-codex")
    assert any(route["family"] == "manual-general-purpose-agent" for route in availability["routes"])
    report = module.build_closure_report(pack)
    assert report["closure_state"] == "partial_closure"
    assert report["provider_availability"]["configured_orchestration_live_ready"] is False
    assert report["provider_availability"]["unavailable_or_unobserved"]


def test_configured_orchestration_fixture_preparation_is_copy_local(tmp_path: Path) -> None:
    module = _load_configured_fixture_module()
    config = tmp_path / ".agentic-workspace" / "config.local.toml"
    config.parent.mkdir(parents=True)
    config.write_text('schema_version = 1\n\n[delegation]\nmode = "auto"\n', encoding="utf-8")

    module.configure(tmp_path, task="Make a bounded mechanical documentation edit to add one compact README troubleshooting example.")

    payload = tomllib.loads(config.read_text(encoding="utf-8"))
    assert payload["delegation"] == {
        "mode": "auto",
        "execution_role": "orchestrator",
        "assignment_policy": "required-best-fit",
        "current_target": "strong_planner",
        "manual_transport_policy": "allowed",
    }
    assert (tmp_path / ".agentic-workspace/planning/execplans/configured-orchestration-fixture.plan.json").is_file()
    assert (tmp_path / ".agentic-workspace/planning/assignments/configured-orchestration-assignment.assignment.json").is_file()


def test_configured_orchestration_ordinary_start_executes_revision_bound_export(tmp_path: Path) -> None:
    fixture = REPO_ROOT / "tools/model-cli-harness/fixtures/aw-configured-host-repo"
    repo = tmp_path / "repo"
    shutil.copytree(fixture, repo)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "fixture baseline"], cwd=repo, check=True, capture_output=True, text=True)
    task = "Make a bounded mechanical documentation edit that adds one compact troubleshooting example to the setup guide."
    _load_configured_fixture_module().configure(repo, task=task)

    start = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/run_agentic_workspace.py"),
            "start",
            "--target",
            str(repo),
            "--task",
            task,
            "--format",
            "json",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    decision = json.loads(start.stdout)["decision_packet"]
    assert decision["action"]["id"] == "export-assigned-handoff"
    assert decision["action"]["operation"] == {"operation_id": "assignment.export"}
    assert decision["action"]["command_effect"] == "mutating"
    assert decision["effects"]["implementation_allowed"] is False
    assert "implement the selected worker slice locally" in decision["effects"]["forbidden_actions"]

    assignment = json.loads(
        (repo / ".agentic-workspace/planning/assignments/configured-orchestration-assignment.assignment.json").read_text(encoding="utf-8")
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/run_agentic_workspace.py"),
            "assignment",
            "export",
            "--target",
            str(repo),
            "--assignment-id",
            assignment["assignment_id"],
            "--assignment-revision",
            assignment["current_revision"],
            "--run-id",
            assignment["current_attempt"]["run_id"],
            "--target-name",
            assignment["target_name"],
            "--transport",
            "manual",
            "--format",
            "json",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(result.stdout)
    assert receipt["operation_id"] == "assignment.export"
    assert receipt["status"] == "handoff-prepared"
    assert receipt["outcome"] == "applied"
    assert (repo / ".agentic-workspace/local/assignment-runs/configured-orchestration-run-1/export/packet.json").is_file()
    assert (repo / ".agentic-workspace/local/assignment-runs/configured-orchestration-run-1/export/prompt.md").is_file()


def test_future_context_live_evaluation_is_head_bound_and_cost_complete() -> None:
    evidence = json.loads((REPO_ROOT / "docs" / "reviews" / "future-context-live-evaluation-2026-08-24.json").read_text(encoding="utf-8"))

    assert evidence["evaluated_implementation_head"] == "543e45c4f766809bfd4971e425073aadc98d3c3b"
    assert evidence["current_restacked_implementation_head"] == "070c15c3e01f313a2e9bd6c2c619cb0c38b7978b"
    assert evidence["restack_equivalence"]["product_diff_paths"] == []
    assert evidence["restack_equivalence"]["planning_diff_paths"] == [
        ".agentic-workspace/planning/lanes/open-issues-future-context.lane.json"
    ]
    assert evidence["execution"] == "real-provider-executed"
    assert evidence["prompt_policy"]["memory_or_capture_commands_named"] is False
    assert len(evidence["current_replay"]["runs"]) == 2
    assert all(run["selector_calls"] == 0 for run in evidence["current_replay"]["runs"])
    assert evidence["current_replay"]["median_against_historical"]["raw_repository_reads_delta_percent"] < 0
    assert evidence["current_replay"]["median_against_historical"]["package_context_bytes_delta"] > 0
    assert evidence["no_context_control"]["decision_has_read_first"] is False
    assert evidence["no_context_control"]["decision_has_memory_attention"] is False
    assert evidence["non_correction_post_action"]["product_outcome"] == "pass-visible-unresolved-with-owner-route"
    assert evidence["non_correction_post_action"]["model_outcome"] == "missed-visible-signal"
    for section in (evidence["historical_underuse"]["run"], *evidence["current_replay"]["runs"]):
        assert {"commands", "package_context_bytes", "selector_calls", "reconciliation_actions", "retained_residue"} <= section.keys()


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
    projection = payload["shared_evaluation_observation"]
    assert projection["domain"] == "dogfooding-feedback"
    assert projection["producer"] == "model-cli-harness.run-suite"
    assert projection["lifecycle_owner"] == "evaluation.observe"
    assert projection["delivery_owner"] == "evaluation report/delivery operations"


def test_model_cli_harness_includes_setup_jumpstart_discovery_scenario(tmp_path: Path) -> None:
    module = _load_harness_module()
    suite_path = REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json"
    suite = module._load_json(suite_path)
    scenarios = {scenario["id"]: scenario for scenario in suite["scenarios"]}

    scenario = scenarios["setup-jumpstart-discovery"]
    assert "uv run agentic-workspace setup" in scenario["required_executed_commands"]
    assert "workspace-setup-jumpstart" in scenario["required_command_mentions"]
    assert "config-policy" in scenario["required_command_mentions"]
    assert scenario["forbidden_write_patterns"] == ["**/*"]
    assert any("pre-write and pre-seed discovery" in note for note in scenario["expected_signals"])
    assert any("structured configuration concerns" in note for note in scenario["expected_signals"])
    assert any("zero-interaction" in note for note in scenario["expected_signals"])
    assert any("direct managed config edits" in note for note in scenario["expected_signals"])
    assert "choose a module" in scenario["forbidden_response_phrases"]

    payload = module.run_suite(
        suite_path=suite_path,
        adapter_id="codex",
        model="gpt-5.4-mini",
        scenario_filter="setup-jumpstart-discovery",
        execute=False,
        output_root=tmp_path / "runs",
        timeout_seconds=None,
    )

    result = payload["results"][0]
    assert result["scenario_id"] == "setup-jumpstart-discovery"
    assert "uses setup as pre-write and pre-seed discovery" in result["expected_signals"]
    assert "starts from structured configuration concerns and bounded strong evidence" in result["expected_signals"]
    assert result["mutation_summary"]["status"] == "not-run"


def test_model_cli_harness_defines_compact_startup_weak_agent_probes(tmp_path: Path) -> None:
    module = _load_harness_module()
    suite_path = REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json"
    suite = module._load_json(suite_path)
    scenarios = {scenario["id"]: scenario for scenario in suite["scenarios"]}
    scenario_ids = (
        "compact-startup-direct-routing",
        "compact-startup-planning-gate-routing",
        "compact-startup-module-rich-routing",
    )

    for scenario_id in scenario_ids:
        scenario = scenarios[scenario_id]
        assert scenario["proportionality_guardrail"] is True
        assert scenario["proportionality_limits"]["workspace_command_count"] == 1
        assert scenario["proportionality_limits"]["verbose_or_full_diagnostic_count"] == 0
        assert scenario["required_executed_commands"] == ["agentic-workspace start"]
        assert scenario["ignored_write_patterns"] == [".agentic-workspace/local/projection-cache/**"]
        assert {"--select", "--verbose", "agentic-workspace report", "agentic-workspace summary"} <= set(
            scenario["forbidden_executed_commands"]
        )
        assert any("only the default start decision packet" in signal for signal in scenario["expected_signals"])

        payload = module.run_suite(
            suite_path=suite_path,
            adapter_id="codex",
            model="gpt-5.4-mini",
            scenario_filter=scenario_id,
            execute=False,
            output_root=tmp_path / "runs" / scenario_id,
            timeout_seconds=None,
        )
        result = payload["results"][0]
        assert result["scenario_id"] == scenario_id
        assert result["proportionality_metrics"]["status"] == "not-run"

    planning_setup = scenarios["compact-startup-planning-gate-routing"]["setup_commands"]
    assert planning_setup[0][:5] == ["uv", "run", "agentic-workspace", "planning", "new-plan"]
    assert "--activate" in planning_setup[0]
    assert scenarios["compact-startup-module-rich-routing"]["fixture"] == "aw-memory-host-repo"

    for fixture in ("aw-minimal-host-repo", "aw-memory-host-repo"):
        guidance = (REPO_ROOT / "tools" / "model-cli-harness" / "fixtures" / fixture / "AGENTS.md").read_text(encoding="utf-8")
        assert "authoritative `decision_packet`" in guidance
        assert "do not omit `--format json`" in guidance
        assert "do not open raw config files to rediscover it" in guidance
        assert "`communication_contract` as optional selector-backed" in guidance
        assert "Use the returned `communication_contract`" not in guidance

    memory_scenario = scenarios["memory-consult-before-edit"]
    variants = {item["id"]: item["prompt"] for item in memory_scenario["prompt_variants"]}
    partial_prompt = variants["future-context-partial-compliance"]
    assert "README.md" in partial_prompt
    assert "memory" not in partial_prompt.lower()
    assert "capture" not in partial_prompt.lower()
    assert scenarios["future-context-no-context-control"]["prompt"] == partial_prompt
    post_action = scenarios["future-context-post-action-residue"]
    assert "correction" not in post_action["prompt"].lower()
    assert post_action["required_executed_commands"] == ["uv run agentic-workspace start"]
    manifest = (
        REPO_ROOT
        / "tools"
        / "model-cli-harness"
        / "fixtures"
        / "aw-memory-host-repo"
        / ".agentic-workspace"
        / "memory"
        / "repo"
        / "manifest.toml"
    ).read_text(encoding="utf-8")
    assert '[notes.".agentic-workspace/memory/repo/testing-and-packaging.md"]' in manifest
    assert 'routes_from = ["README.md", "pyproject.toml", "tests/**/*.py"]' in manifest

    evidence = json.loads((REPO_ROOT / "docs" / "maintainer" / "startup-compression-2679.json").read_text(encoding="utf-8"))
    external = evidence["external_agent_evidence"]
    assert external["status"] == "verified"
    assert external["fixture_runtime_provenance"] == "verified"
    assert external["interaction_summary"] == {
        "scenario_count": 3,
        "requests_to_completion": 3,
        "workspace_command_count": 3,
        "follow_up_workspace_reads": 0,
        "selector_calls": 0,
        "verbose_or_full_diagnostic_calls": 0,
        "raw_workspace_reads": 0,
        "finding_count": 0,
    }
    recorded = external["scenarios"]
    assert {entry["scenario_id"] for entry in recorded.values()} == set(scenario_ids)
    assert all(entry["workspace_command_count"] == 1 for entry in recorded.values())
    assert all(entry["raw_workspace_reads"] == 0 for entry in recorded.values())
    assert all(entry["selector_calls"] == 0 for entry in recorded.values())
    assert recorded["planning_gate"]["blocked_claims"] == [
        "claim-active-plan-progress",
        "claim-active-plan-complete",
        "silently-abandon-active-plan",
    ]
    assert recorded["module_rich"]["irrelevant_module_follow_up_reads"] == 0


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


def test_model_cli_harness_plain_codex_large_prompt_uses_file_reference_transport(tmp_path: Path) -> None:
    module = _load_harness_module()
    suite = module._load_json(REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json")
    adapter = suite["adapters"]["codex"]
    large_prompt = "large evaluator prompt\n" * 1000

    command, prompt_transport, _ = module._adapter_invocation_command(
        adapter,
        adapter_id="codex",
        model=adapter["default_model"],
        replacements={
            "repo": str(tmp_path / "repo"),
            "run_root": str(tmp_path / "run"),
            "share_path": str(tmp_path / "run" / "share.md"),
            "postmortem_cwd": str(tmp_path / "run" / "postmortem-context"),
            "transcript_path": str(tmp_path / "run" / "transcript.jsonl"),
            "prompt": large_prompt,
        },
        run_root=tmp_path / "run",
        prompt_id="large-evaluator",
    )

    prompt_file = Path(prompt_transport["prompt_file"])
    assert prompt_transport["mode"] == "file-reference"
    assert prompt_file.exists()
    assert prompt_file.read_text(encoding="utf-8") == large_prompt
    assert large_prompt not in command
    assert command[-1].startswith("Read the complete prompt from this file")
    assert str(prompt_file) in command[-1]


def test_sbx_codex_adapter_copies_prompt_file_into_sandbox_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_sbx_adapter_module()
    commands: list[list[str]] = []
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("large prompt\n" * 100, encoding="utf-8")
    share_path = tmp_path / "work" / "share" / "final.md"

    def fake_run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:5] == ["sbx", "exec", "aw-test", "sh", "-lc"] and "codex exec" in command[-1]:
            share_path.parent.mkdir(parents=True, exist_ok=True)
            share_path.write_text("Done.", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def fake_subprocess_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert "--attempt-file" in command
        assert command[command.index("--attempt-file") + 1] == str(share_path)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"kind": "agentic-workspace/final-response-admission-result/v1", "status": "accepted_terminal_final"}),
            stderr="",
        )

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module, "WINDOWS_COMMAND_LINE_LIMIT", 1000)

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
            str(share_path),
            "--prompt-file",
            str(prompt_file),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert captured.err == ""
    sandbox_prompt_dir = posixpath.join(posixpath.sep, "tmp", "agentic-workspace-model-cli-harness")
    sandbox_prompt_path = posixpath.join(sandbox_prompt_dir, "prompt.txt")
    sandbox_share_dir = module._sandbox_path(str(share_path.parent))
    assert commands[0] == ["sbx", "create", "--name", "aw-test", "codex", "work/repo"]
    assert commands[1] == [
        "sbx",
        "exec",
        "aw-test",
        "sh",
        "-lc",
        f"mkdir -p {sandbox_share_dir} {sandbox_prompt_dir}",
    ]
    assert commands[2] == [
        "sbx",
        "cp",
        str(prompt_file),
        f"aw-test:{sandbox_prompt_path}",
    ]
    assert commands[3][:5] == ["sbx", "exec", "aw-test", "sh", "-lc"]
    assert "codex exec" in commands[3][-1]
    assert f"- < {sandbox_prompt_path}" in commands[3][-1]
    assert "large prompt" not in subprocess.list2cmdline(commands[3])
    assert commands[-1] == ["sbx", "rm", "--force", "aw-test"]
    assert share_path.read_text(encoding="utf-8") == "Done."
    assert json.loads(Path(f"{share_path}.admission.json").read_text(encoding="utf-8"))["status"] == "accepted_terminal_final"


def test_sbx_codex_adapter_reinvokes_after_rejected_final_and_preserves_admission_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_sbx_adapter_module()
    commands: list[list[str]] = []
    share_path = tmp_path / "session.md"
    admission_payloads = [
        {
            "kind": "agentic-workspace/final-response-admission-result/v1",
            "status": "rejected_auto_resumed",
            "continuation_operation": {
                "invoked_operation": "proof.report",
                "exit_code": 0,
            },
        },
        {
            "kind": "agentic-workspace/final-response-admission-result/v1",
            "status": "accepted_terminal_final",
        },
    ]
    admission_attempts: list[str] = []

    def fake_run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:5] == ["sbx", "exec", "aw-test", "codex", "exec"]:
            share_path.write_text("Done too early.", encoding="utf-8")
        if command[:5] == ["sbx", "exec", "aw-test", "sh", "-lc"] and "codex exec" in command[-1]:
            share_path.write_text("Actually delivered.", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def fake_subprocess_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[3:5] == ["final-response", "admit"]
        assert command[command.index("--target") + 1] == str(tmp_path / "repo")
        assert command[command.index("--attempt-file") + 1] == str(share_path)
        admission_attempts.append(share_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(admission_payloads[len(admission_attempts) - 1]), stderr="")

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)

    result = module.main(
        [
            "--sbx",
            "sbx",
            "--sandbox-name",
            "aw-test",
            "--repo",
            str(tmp_path / "repo"),
            "--model",
            "gpt-test",
            "--share-path",
            str(share_path),
            "--prompt",
            "do work",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "rejected terminal output" in captured.err
    assert admission_attempts == ["Done too early.", "Actually delivered."]
    assert share_path.read_text(encoding="utf-8") == "Actually delivered."
    assert json.loads(Path(f"{share_path}.admission.json").read_text(encoding="utf-8")) == admission_payloads[-1]
    assert any(command[:3] == ["sbx", "cp", str(share_path) + ".continuation-2.txt"] for command in commands)
    assert (
        sum(1 for command in commands if command[:3] == ["sbx", "exec", "aw-test"] and "codex exec" in subprocess.list2cmdline(command))
        == 2
    )
    assert commands[-1] == ["sbx", "rm", "--force", "aw-test"]


def test_sbx_codex_adapter_keeps_custody_after_compatibility_slice_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_sbx_adapter_module()
    commands: list[list[str]] = []
    share_path = tmp_path / "session.md"
    final_messages = ["Done too early 1.", "Done too early 2.", "Actually delivered."]
    admission_payloads = [
        {
            "kind": "agentic-workspace/final-response-admission-result/v1",
            "status": "rejected_auto_resumed",
            "continuation_operation": {
                "invoked_operation": "proof.report",
                "exit_code": 0,
            },
        },
        {
            "kind": "agentic-workspace/final-response-admission-result/v1",
            "status": "rejected_auto_resumed",
            "continuation_operation": {
                "invoked_operation": "proof.report",
                "exit_code": 0,
            },
        },
        {
            "kind": "agentic-workspace/final-response-admission-result/v1",
            "status": "accepted_terminal_final",
        },
    ]
    admission_attempts: list[str] = []
    codex_invocations = 0

    def fake_run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
        nonlocal codex_invocations
        commands.append(command)
        if command[:5] == ["sbx", "exec", "aw-test", "codex", "exec"] or (
            command[:5] == ["sbx", "exec", "aw-test", "sh", "-lc"] and "codex exec" in command[-1]
        ):
            share_path.write_text(final_messages[codex_invocations], encoding="utf-8")
            codex_invocations += 1
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def fake_subprocess_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        admission_attempts.append(share_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(admission_payloads[len(admission_attempts) - 1]), stderr="")

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)

    result = module.main(
        [
            "--sbx",
            "sbx",
            "--sandbox-name",
            "aw-test",
            "--repo",
            str(tmp_path / "repo"),
            "--model",
            "gpt-test",
            "--share-path",
            str(share_path),
            "--prompt",
            "do work",
            "--max-admission-slices",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "slice budget" in captured.err
    assert "not an authorized terminal outcome" in captured.err
    assert admission_attempts == final_messages
    assert share_path.read_text(encoding="utf-8") == "Actually delivered."
    assert json.loads(Path(f"{share_path}.admission.json").read_text(encoding="utf-8")) == admission_payloads[-1]
    assert codex_invocations == 3
    assert sum(1 for command in commands if command[:3] == ["sbx", "cp", str(share_path) + ".continuation-2.txt"]) == 1
    assert sum(1 for command in commands if command[:3] == ["sbx", "cp", str(share_path) + ".continuation-3.txt"]) == 1
    assert commands[-1] == ["sbx", "rm", "--force", "aw-test"]


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
        "_fixture_local_wheel_metadata",
        lambda *, repo_path, source_wheelhouse, adapter: (
            ["agentic-workspace"],
            {"agentic-workspace": {"path": "fixture-wheelhouse/agentic_workspace.whl"}},
        ),
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
    pyproject = tomllib.loads(pyproject_text)
    assert "fixture-wheelhouse/agentic_workspace.whl" in pyproject_text
    assert pyproject["project"]["dependencies"] == ["agentic-workspace"]
    assert pyproject["tool"]["uv"]["sources"]["agentic-workspace"]["path"] == "fixture-wheelhouse/agentic_workspace.whl"
    assert "releases/download/v0.4.3" not in pyproject_text


def test_model_cli_harness_classifies_owned_runtime_receipt_without_weakening_mutation_checks(tmp_path: Path) -> None:
    module = _load_harness_module()
    receipt = tmp_path / ".agentic-workspace" / "local" / "improvement-pressure" / "consequence-history.jsonl"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "kind": "workspace-improvement-pressure-consequence-event/v1",
                "owner_kind": "workspace-improvement-pressure/v1",
                "source": "workspace.start",
                "event": "observed",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    after = {
        "README.md": {"size": 1, "sha256": "changed"},
        receipt.relative_to(tmp_path).as_posix(): {"size": receipt.stat().st_size, "sha256": "receipt"},
        "src/unexpected.py": {"size": 1, "sha256": "unexpected"},
    }

    result = module._snapshot_diff(
        {"README.md": {"size": 1, "sha256": "before"}},
        after,
        root=tmp_path,
        allowed_write_patterns=["README.md"],
    )

    assert result["mutation_classes"]["expected_task_or_product_mutations"] == ["README.md"]
    assert result["mutation_classes"]["admitted_runtime_receipts"] == [
        ".agentic-workspace/local/improvement-pressure/consequence-history.jsonl"
    ]
    assert result["runtime_receipt_count"] == 1
    assert result["mutation_classes"]["forbidden_or_unclassified_mutations"] == ["src/unexpected.py"]


def test_model_cli_harness_does_not_admit_unowned_local_mutation(tmp_path: Path) -> None:
    module = _load_harness_module()
    random_path = ".agentic-workspace/local/random.json"
    result = module._snapshot_diff({}, {random_path: {"size": 1, "sha256": "random"}}, root=tmp_path)

    assert result["mutation_classes"]["admitted_runtime_receipts"] == []
    assert result["mutation_classes"]["expected_task_or_product_mutations"] == []
    assert result["mutation_classes"]["forbidden_or_unclassified_mutations"] == [random_path]


def test_model_cli_harness_runtime_receipt_path_comes_from_owner_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_harness_module()
    receipt = tmp_path / ".agentic-workspace" / "local" / "alternate" / "events.jsonl"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "kind": "owner-event/v1",
                "owner_kind": "workspace-improvement-pressure/v1",
                "source": "fixture-owner",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module,
        "consequence_receipt_contract",
        lambda: {
            "relative_path": ".agentic-workspace/local/alternate/events.jsonl",
            "record_kind": "owner-event/v1",
            "producer": "fixture-owner",
        },
    )

    assert module._is_admitted_aw_runtime_receipt(tmp_path, receipt.relative_to(tmp_path).as_posix()) is True


def test_model_cli_harness_local_wheelhouse_environment_is_fixture_bound(tmp_path: Path) -> None:
    module = _load_harness_module()
    source_environment = str(tmp_path / "source" / ".venv")

    result = module._fixture_runtime_environment(
        {"VIRTUAL_ENV": source_environment, "UV_PROJECT_ENVIRONMENT": source_environment, "PATH": "bin"},
        repo_path=tmp_path / "fixture",
    )

    assert "VIRTUAL_ENV" not in result
    assert Path(result["UV_PROJECT_ENVIRONMENT"]) == tmp_path / "fixture" / ".venv"
    assert Path(result["UV_CACHE_DIR"]) == tmp_path / "fixture" / ".uv-cache"
    assert result["UV_LINK_MODE"] == "copy"
    assert result["PATH"] == "bin"


def test_model_cli_harness_provenance_distinguishes_fixture_wheel_from_source_retarget(tmp_path: Path) -> None:
    module = _load_harness_module()
    repo = tmp_path / "source" / ".agentic-workspace" / "local" / "scratch" / "runs" / "fixture" / "repo"
    wheel = repo / ".agentic-workspace" / "local" / "model-cli-harness" / "wheelhouse" / "agentic_workspace.whl"
    wheel_pyproject = f'[project]\nname = "fixture"\nversion = "0"\ndependencies = ["agentic-workspace @ {wheel.as_uri()}"]\n'
    source_pyproject = (
        "[project]\n"
        'name = "fixture"\n'
        'version = "0"\n'
        'dependencies = ["agentic-workspace"]\n\n'
        "[tool.uv.sources]\n"
        f'agentic-workspace = {{ path = "{module.REPO_ROOT.as_posix()}", editable = true }}\n'
    )

    assert module._pyproject_retargets_source_checkout(pyproject_text=wheel_pyproject, repo_path=repo) is False
    assert module._pyproject_retargets_source_checkout(pyproject_text=source_pyproject, repo_path=repo) is True


def test_model_cli_harness_does_not_misclassify_reported_read_only_owner_as_raw_read() -> None:
    module = _load_harness_module()
    scenario = {"id": "compact-startup-planning-gate-routing", "proportionality_guardrail": True}
    result = {
        "final_message": (
            "Owner is `.agentic-workspace/planning/execplans/protected-owner.plan.json`; its state update policy is read-only."
        ),
        "stdout": "",
        "stderr": "",
    }

    metrics = module._proportionality_metrics(
        scenario=scenario,
        result=result,
        mutation_summary={"created": [], "modified": [], "deleted": []},
        package_read_surface_summary={"command_count": 1, "output_bytes": 100, "output_lines": 4},
    )
    assert metrics["raw_workspace_file_mentions"] == 1
    assert metrics["raw_workspace_read_count"] == 0

    result["final_message"] = "I ran Get-Content .agentic-workspace/planning/state.toml."
    raw_metrics = module._proportionality_metrics(
        scenario=scenario,
        result=result,
        mutation_summary={"created": [], "modified": [], "deleted": []},
        package_read_surface_summary={"command_count": 1, "output_bytes": 100, "output_lines": 4},
    )
    assert raw_metrics["raw_workspace_read_count"] == 1


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific local-wheelhouse black-box")
def test_model_cli_harness_windows_local_wheelhouse_black_box_uses_fixture_runtime(tmp_path: Path) -> None:
    module = _load_harness_module()
    output_root = tmp_path / "runs"
    wheelhouse = module._build_local_aw_wheelhouse(output_root)
    paths = module._scenario_paths(
        output_root=output_root,
        suite_id="fixture-provenance",
        scenario_id="startup",
        adapter_id="fixture",
        model="local",
        prompt_variant_id="default",
    )
    module._prepare_fixture(
        suite_path=REPO_ROOT / "tools/model-cli-harness/suites/copilot-workflow-smoke.json",
        scenario={"id": "startup", "fixture": "aw-minimal-host-repo"},
        paths=paths,
        adapter={},
        local_aw_wheelhouse=wheelhouse,
    )
    env = module._fixture_runtime_environment(dict(os.environ), repo_path=paths.repo_path)

    result = module._fixture_runtime_provenance(repo_path=paths.repo_path, env=env, timeout_seconds=120)

    assert result["status"] == "verified", result
    assert result["proof_class"] == "ordinary"
    assert all(result["checks"].values())
    assert Path(result["identity"]["executable"]).resolve().is_relative_to((paths.repo_path / ".venv").resolve())
    assert Path(result["identity"]["package"]).resolve().is_relative_to((paths.repo_path / ".venv").resolve())


def test_model_cli_harness_fixture_runtime_mismatch_is_fallback_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_harness_module()
    repo = tmp_path / "fixture"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0'\n", encoding="utf-8")
    responses = iter(
        [
            {"returncode": 0, "stdout": ""},
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {"executable": str(tmp_path / "ambient/python.exe"), "package": str(REPO_ROOT / "src/agentic_workspace/__init__.py")}
                ),
            },
            {"returncode": 0, "stdout": "{}"},
            {"returncode": 0, "stdout": "{}"},
        ]
    )
    monkeypatch.setattr(module, "_run_command", lambda *args, **kwargs: next(responses))

    result = module._fixture_runtime_provenance(repo_path=repo, env={}, timeout_seconds=10)

    assert result["status"] == "blocked-mismatch-or-unavailable"
    assert result["proof_class"] == "degraded-fallback-only"
    assert result["checks"]["package_from_fixture_venv"] is False
    assert result["recovery_command"]


def test_model_cli_harness_local_wheelhouse_windows_docker_uses_platform_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_harness_module()
    source = tmp_path / "source-wheelhouse"
    source.mkdir()
    for wheel_prefix in (
        "agentic_workspace",
        "agentic_workspace_memory",
        "agentic_workspace_planning",
        "agentic_workspace_verification",
    ):
        (source / f"{wheel_prefix}-1.2.3-py3-none-any.whl").write_text("wheel", encoding="utf-8")

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module, "_local_aw_version", lambda: "1.2.3")

    dependencies, uv_sources = module._fixture_local_wheel_metadata(
        repo_path=tmp_path / "repo",
        source_wheelhouse=source,
        adapter={"sandbox": {"backend": "docker-sandbox"}},
    )

    assert dependencies == [
        "agentic-workspace",
        "agentic-workspace-memory",
        "agentic-workspace-planning",
        "agentic-workspace-verification",
    ]
    assert uv_sources == {
        "agentic-workspace-memory": [
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/host/agentic_workspace_memory-1.2.3-py3-none-any.whl",
                "marker": "sys_platform == 'win32'",
            },
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/sandbox/agentic_workspace_memory-1.2.3-py3-none-any.whl",
                "marker": "sys_platform != 'win32'",
            },
        ],
        "agentic-workspace-planning": [
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/host/agentic_workspace_planning-1.2.3-py3-none-any.whl",
                "marker": "sys_platform == 'win32'",
            },
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/sandbox/agentic_workspace_planning-1.2.3-py3-none-any.whl",
                "marker": "sys_platform != 'win32'",
            },
        ],
        "agentic-workspace-verification": [
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/host/agentic_workspace_verification-1.2.3-py3-none-any.whl",
                "marker": "sys_platform == 'win32'",
            },
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/sandbox/agentic_workspace_verification-1.2.3-py3-none-any.whl",
                "marker": "sys_platform != 'win32'",
            },
        ],
        "agentic-workspace": [
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/host/agentic_workspace-1.2.3-py3-none-any.whl",
                "marker": "sys_platform == 'win32'",
            },
            {
                "path": ".agentic-workspace/local/model-cli-harness/wheelhouse/sandbox/agentic_workspace-1.2.3-py3-none-any.whl",
                "marker": "sys_platform != 'win32'",
            },
        ],
    }


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-host local-wheelhouse Docker fixture validation proof")
def test_model_cli_harness_local_wheelhouse_windows_docker_fixture_runs_host_validation(tmp_path: Path) -> None:
    module = _load_harness_module()
    output_root = tmp_path / "runs"
    local_aw_wheelhouse = module._build_local_aw_wheelhouse(output_root)
    paths = module.HarnessPaths(
        run_root=output_root / "validation",
        fixture_root=output_root / "validation" / "fixture",
        repo_path=output_root / "validation" / "repo",
        transcript_path=output_root / "validation" / "transcript.jsonl",
        share_path=output_root / "validation" / "share.md",
    )

    module._prepare_fixture(
        suite_path=REPO_ROOT / "tools" / "model-cli-harness" / "suites" / "copilot-workflow-smoke.json",
        scenario={"id": "startup-orientation", "fixture": "aw-minimal-host-repo"},
        paths=paths,
        adapter={"sandbox": {"backend": "docker-sandbox", "agent": "codex"}},
        local_aw_wheelhouse=local_aw_wheelhouse,
    )

    pyproject = tomllib.loads((paths.repo_path / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["dependencies"] == [
        "agentic-workspace",
        "agentic-workspace-memory",
        "agentic-workspace-planning",
        "agentic-workspace-verification",
    ]
    sources = pyproject["tool"]["uv"]["sources"]["agentic-workspace"]
    assert [source["marker"] for source in sources] == ["sys_platform == 'win32'", "sys_platform != 'win32'"]
    assert sources[0]["path"].startswith(".agentic-workspace/local/model-cli-harness/wheelhouse/host/")
    assert sources[1]["path"].startswith(".agentic-workspace/local/model-cli-harness/wheelhouse/sandbox/")

    env = dict(module.os.environ)
    env["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")
    env["UV_LINK_MODE"] = "copy"
    env["UV_PROJECT_ENVIRONMENT"] = str(tmp_path / "fixture-venv")
    result = module._run_command(
        ["uv", "run", "agentic-workspace", "summary", "--format", "json"],
        cwd=paths.repo_path,
        timeout_seconds=240,
        env=env,
    )

    assert result["returncode"] == 0, f"stdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"
    payload = json.loads(result["stdout"])
    assert payload["kind"]
    assert "wheelhouse/sandbox" not in result["stderr"].replace("\\", "/")


def test_model_cli_harness_windows_host_sandbox_file_url_requires_drive_path() -> None:
    module = _load_harness_module()

    assert module._windows_host_path_as_sandbox_file_url("C:" + r"\awlh\repo\wheelhouse") == "file:///c/awlh/repo/wheelhouse"
    assert module._windows_host_path_as_sandbox_file_url("D:" + "/runs/wheelhouse") == "file:///d/runs/wheelhouse"
    with pytest.raises(ValueError, match="drive-qualified Windows host path"):
        module._windows_host_path_as_sandbox_file_url("/" + "tmp/runs/wheelhouse")


def test_model_cli_harness_prompt_file_transport_uses_absolute_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_harness_module()
    monkeypatch.chdir(tmp_path)

    command, prompt_transport, replacements = module._adapter_invocation_command(
        {
            "prompt_transport": {
                "threshold_chars": 1,
                "file_args": ["--prompt-file", "{prompt_file}"],
                "file_prompt": "Read {prompt_file}.",
            },
            "command": ["agent", "{prompt}", "{prompt_transport_args}"],
        },
        adapter_id="fake",
        model="model",
        replacements={"prompt": "large prompt", "repo": "repo"},
        run_root=Path("relative-run-root"),
        prompt_id="phase-one",
    )

    prompt_file = Path(prompt_transport["prompt_file"])
    assert prompt_file.is_absolute()
    assert prompt_file.exists()
    assert replacements["prompt_file"] == str(prompt_file)
    assert str(prompt_file) in command
