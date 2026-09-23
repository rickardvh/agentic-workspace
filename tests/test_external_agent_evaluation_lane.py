from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]


LANE_DIR = REPO_ROOT / "src" / "tooling" / "model-cli-harness" / "external-agent-evaluation"


SCRIPT = REPO_ROOT / "src" / "tooling" / "model-cli-harness" / "external_agent_evaluation_lane.py"


HARNESS_SCRIPT = REPO_ROOT / "src" / "tooling" / "model-cli-harness" / "run_model_cli_harness.py"


SBX_ADAPTER_SCRIPT = REPO_ROOT / "src" / "tooling" / "model-cli-harness" / "run_sbx_codex_adapter.py"


CONTEXT_COST_BRIDGE_SCRIPT = LANE_DIR / "codex_context_cost_bridge.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("external_agent_evaluation_lane", SCRIPT)
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

    schema = json.loads((REPO_ROOT / "src/tooling/contracts/schemas/assignment_context_cost.schema.json").read_text(encoding="utf-8"))
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


def test_current_adapter_guidance_live_evidence_is_head_bound_and_honest() -> None:
    evidence_root = REPO_ROOT / "src" / "tooling" / "model-cli-harness" / "external-agent-evaluation"
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


def test_retired_sbx_launcher_cannot_create_or_remove_sandboxes(capsys):
    module = _load_sbx_adapter_module()
    assert module.main(["--sandbox-name", "existing-user-sandbox"]) == 2
    assert "Retired launcher" in capsys.readouterr().err
    assert not hasattr(module, "_run")
