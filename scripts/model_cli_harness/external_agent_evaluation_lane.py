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

OPERATING_LOOP_KIND = "agentic-workspace/operating-loop-decision/v1"
OPERATING_LOOP_CLOSEOUT_STATES = {
    "no_closeout_needed",
    "ready_for_full_closure",
    "partial_claim_only",
    "blocked_missing_proof",
    "blocked_active_planning",
    "residue_routing_required",
}
OPERATING_LOOP_SAFE_CLAIMS = {"none", "full", "partial", "blocked"}
OPERATING_LOOP_RESIDUE_OWNERS = {"memory", "planning", "verification", "docs", "issue", "config", "none"}
OPERATING_LOOP_REQUIRED_ACTIONS = {
    "run_or_refresh_proof",
    "continue_or_close_plan",
    "route_memory_residue",
    "route_external_residue",
}
OPERATING_LOOP_MEMORY_STATES = {"pulled", "dismissed", "not_applicable"}
OPERATING_LOOP_MEMORY_REASONS = {
    "matched_route",
    "no_relevant_route",
    "not_requested",
    "unavailable",
    "explicitly_dismissed",
}
OPERATING_LOOP_MEMORY_CAPTURE = {"none", "recommended", "required"}
OPERATING_LOOP_PLANNING_STATES = {"none", "active", "continuation", "closeout_required"}
OPERATING_LOOP_VERIFICATION_STATES = {
    "proof_not_required",
    "proof_required",
    "proof_selected",
    "proof_missing",
    "proof_stale",
    "proof_skipped",
    "proof_failed",
    "proof_passed",
}
OPERATING_LOOP_REASON_CODES = {
    "proof_missing",
    "proof_stale",
    "proof_failed",
    "active_plan",
    "plan_closeout_required",
    "memory_capture_required",
    "external_residue",
}
COMPLETION_COST_OBSERVATION_KIND = "agentic-workspace/external-agent-completion-cost-observations/v1"
COMPLETION_COST_REQUIRED_FIELDS = {
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
}
COMPLETION_COST_NUMERIC_FIELDS = {
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
    "unsafe_closure_claims",
}
COMPLETION_COST_HANDOFF_STATUSES = {"not_applicable", "success", "partial", "failed"}
COMPLETION_COST_DRIVER_CLASSIFICATIONS = {
    "startup_routing",
    "memory_reread",
    "proof_churn",
    "planning_residue",
    "review_repair",
    "handoff_recovery",
    "unsafe_closure",
    "unused_output",
    "selector_inventory_read",
    "raw_file_open",
    "avoidable_clarification",
    "missed_blocker",
    "repeated_reread",
}
LOCAL_PATH_LEAK_KIND = "agentic-workspace/external-agent-local-path-leak/v1"


def _validate_local_path_leak_packet(
    packet: Any,
    *,
    prefix: str,
    errors: list[str],
) -> None:
    _require(isinstance(packet, dict), f"{prefix} local_path_leak must be an object", errors)
    if not isinstance(packet, dict):
        return
    _require(packet.get("kind") == LOCAL_PATH_LEAK_KIND, f"{prefix} local_path_leak kind is invalid", errors)
    _require(packet.get("status") == "detected", f"{prefix} local_path_leak status is invalid", errors)
    _require(packet.get("warning_class") == "model_cli_local_path_leak", f"{prefix} local_path_leak warning_class is invalid", errors)
    _require(packet.get("failure_id") == "LOCAL_ABSOLUTE_PATH_LEAK", f"{prefix} local_path_leak failure_id is invalid", errors)
    _require(packet.get("owner_surface") == "harness", f"{prefix} local_path_leak owner_surface must be harness", errors)
    _require(bool(str(packet.get("followup_ref") or "").strip()), f"{prefix} local_path_leak must route to a followup_ref", errors)
    _require(
        "repo-relative" in str(packet.get("allowed_path_rule") or ""),
        f"{prefix} local_path_leak allowed_path_rule must preserve repo-relative evidence",
        errors,
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pack(*, repo_root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    lane_dir = repo_root / "tools" / "model-cli-harness" / "external-agent-evaluation"
    return {name: _load_json(lane_dir / relative_path) for name, relative_path in PACK_FILES.items()}


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _record_failure_ids(record: dict[str, Any] | None) -> set[str]:
    if not isinstance(record, dict):
        return set()
    return {failure_id for failure_id in record.get("failure_ids", []) if isinstance(failure_id, str)}


def _actionable_remediation(decision: dict[str, Any]) -> bool:
    return (
        decision.get("decision") == "promote"
        and decision.get("closure_effect") == "routed"
        and bool(str(decision.get("followup_ref") or "").strip())
        and decision.get("remediation_kind") == "actionable-issue"
    )


def _validate_operating_loop_packet(
    packet: Any,
    *,
    prefix: str,
    owner_surfaces: set[str],
    errors: list[str],
) -> None:
    _require(isinstance(packet, dict), f"{prefix} must include operating_loop packet", errors)
    if not isinstance(packet, dict):
        return
    _require(packet.get("kind") == OPERATING_LOOP_KIND, f"{prefix} operating_loop kind is invalid", errors)
    _require(packet.get("closeout_state") in OPERATING_LOOP_CLOSEOUT_STATES, f"{prefix} operating_loop closeout_state is invalid", errors)
    _require(packet.get("safe_claim") in OPERATING_LOOP_SAFE_CLAIMS, f"{prefix} operating_loop safe_claim is invalid", errors)
    _require(packet.get("residue_owner") in OPERATING_LOOP_RESIDUE_OWNERS, f"{prefix} operating_loop residue_owner is invalid", errors)
    if packet.get("residue_owner") != "none":
        _require(packet.get("residue_owner") in owner_surfaces, f"{prefix} operating_loop residue_owner is not an owner surface", errors)
    for action in packet.get("required_before_full_closure", []):
        _require(action in OPERATING_LOOP_REQUIRED_ACTIONS, f"{prefix} operating_loop required action is invalid", errors)

    memory = packet.get("memory", {})
    planning = packet.get("planning", {})
    verification = packet.get("verification", {})
    _require(isinstance(memory, dict), f"{prefix} operating_loop memory must be an object", errors)
    _require(isinstance(planning, dict), f"{prefix} operating_loop planning must be an object", errors)
    _require(isinstance(verification, dict), f"{prefix} operating_loop verification must be an object", errors)
    if isinstance(memory, dict):
        _require(memory.get("state") in OPERATING_LOOP_MEMORY_STATES, f"{prefix} operating_loop memory.state is invalid", errors)
        _require(memory.get("reason_code") in OPERATING_LOOP_MEMORY_REASONS, f"{prefix} operating_loop memory.reason_code is invalid", errors)
        _require(memory.get("capture") in OPERATING_LOOP_MEMORY_CAPTURE, f"{prefix} operating_loop memory.capture is invalid", errors)
    if isinstance(planning, dict):
        _require(planning.get("state") in OPERATING_LOOP_PLANNING_STATES, f"{prefix} operating_loop planning.state is invalid", errors)
        _require(isinstance(planning.get("blocks_full_closure"), bool), f"{prefix} operating_loop planning.blocks_full_closure is invalid", errors)
    if isinstance(verification, dict):
        _require(
            verification.get("state") in OPERATING_LOOP_VERIFICATION_STATES,
            f"{prefix} operating_loop verification.state is invalid",
            errors,
        )
        _require(isinstance(verification.get("blocks_full_closure"), bool), f"{prefix} operating_loop verification.blocks_full_closure is invalid", errors)
    for reason in packet.get("reasons", []):
        _require(isinstance(reason, dict), f"{prefix} operating_loop reason must be an object", errors)
        if isinstance(reason, dict):
            _require(reason.get("code") in OPERATING_LOOP_REASON_CODES, f"{prefix} operating_loop reason code is invalid", errors)
            _require(reason.get("owner") in OPERATING_LOOP_RESIDUE_OWNERS, f"{prefix} operating_loop reason owner is invalid", errors)


def _validate_completion_cost_observations(
    observations: Any,
    *,
    prefix: str,
    scenario_id: str,
    owner_surfaces: set[str],
    errors: list[str],
) -> None:
    _require(isinstance(observations, dict), f"{prefix} completion_cost_observations must be an object", errors)
    if not isinstance(observations, dict):
        return
    _require(observations.get("kind") == COMPLETION_COST_OBSERVATION_KIND, f"{prefix} completion_cost_observations kind is invalid", errors)
    _require(observations.get("scenario_id") == scenario_id, f"{prefix} completion_cost_observations scenario_id must match record", errors)
    missing_fields = COMPLETION_COST_REQUIRED_FIELDS.difference(observations)
    _require(not missing_fields, f"{prefix} completion_cost_observations missing fields: {', '.join(sorted(missing_fields))}", errors)
    for field in COMPLETION_COST_NUMERIC_FIELDS:
        value = observations.get(field)
        _require(isinstance(value, int) and value >= 0, f"{prefix} completion_cost_observations {field} must be a non-negative integer", errors)
    _require(
        observations.get("handoff_recovery_status") in COMPLETION_COST_HANDOFF_STATUSES,
        f"{prefix} completion_cost_observations handoff_recovery_status is invalid",
        errors,
    )
    sections = observations.get("aw_sections_used", [])
    _require(isinstance(sections, list), f"{prefix} completion_cost_observations aw_sections_used must be a list", errors)
    for section in (sections if isinstance(sections, list) else []):
        _require(isinstance(section, str) and bool(section.strip()), f"{prefix} completion_cost_observations aw_sections_used entry is invalid", errors)
    _require(
        isinstance(observations.get("surface_causing_overhead"), str) and bool(observations.get("surface_causing_overhead", "").strip()),
        f"{prefix} completion_cost_observations surface_causing_overhead must be a non-empty string",
        errors,
    )
    drivers = observations.get("cost_drivers", [])
    _require(isinstance(drivers, list), f"{prefix} completion_cost_observations cost_drivers must be a list", errors)
    for index, driver in enumerate(drivers if isinstance(drivers, list) else []):
        driver_prefix = f"{prefix} completion_cost_observations cost_drivers[{index}]"
        _require(isinstance(driver, dict), f"{driver_prefix} must be an object", errors)
        if not isinstance(driver, dict):
            continue
        for field in ("source", "signal", "owner_surface", "classification"):
            _require(bool(str(driver.get(field) or "").strip()), f"{driver_prefix} must include {field}", errors)
        _require(driver.get("owner_surface") in owner_surfaces, f"{driver_prefix} owner_surface is invalid", errors)
        _require(driver.get("classification") in COMPLETION_COST_DRIVER_CLASSIFICATIONS, f"{driver_prefix} classification is invalid", errors)


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
    boundary = scorecard.get("authority_boundary")
    _require(isinstance(boundary, dict), "scorecard must define authority_boundary", errors)
    if isinstance(boundary, dict):
        _require(
            boundary.get("harness_role") == "maintainer-evaluation-evidence",
            "scorecard authority_boundary.harness_role must be maintainer-evaluation-evidence",
            errors,
        )
        _require(boundary.get("runtime_authority") == "none", "scorecard authority_boundary.runtime_authority must be none", errors)
        _require(
            boundary.get("portable_contract_status") in {"not-declared", "declared"},
            "scorecard authority_boundary.portable_contract_status is invalid",
            errors,
        )
        _require(
            bool(str(boundary.get("promotion_rule") or "").strip()),
            "scorecard authority_boundary must name promotion_rule",
            errors,
        )
        _require(
            bool(str(boundary.get("agent_decision") or "").strip()),
            "scorecard authority_boundary must name agent_decision",
            errors,
        )

    observation_contract = pack["scenarios"].get("completion_cost_observation_contract")
    minimum_observed_records = 1
    _require(isinstance(observation_contract, dict), "scenarios must define completion_cost_observation_contract", errors)
    if isinstance(observation_contract, dict):
        _require(
            observation_contract.get("kind") == "agentic-workspace/external-agent-completion-cost-observation-contract/v1",
            "completion_cost_observation_contract kind is invalid",
            errors,
        )
        _require(
            observation_contract.get("status") == "maintainer-evaluation-only",
            "completion_cost_observation_contract status must be maintainer-evaluation-only",
            errors,
        )
        _require(
            observation_contract.get("applies_to") == "representative_evidence_records",
            "completion_cost_observation_contract must apply to representative_evidence_records",
            errors,
        )
        _require(
            int(observation_contract.get("minimum_observed_records", 0) or 0) >= 1,
            "completion_cost_observation_contract must define minimum_observed_records",
            errors,
        )
        minimum_observed_records = int(observation_contract.get("minimum_observed_records", 0) or 0)
        required_fields = {str(item) for item in observation_contract.get("required_fields", [])}
        _require(
            COMPLETION_COST_REQUIRED_FIELDS.issubset(required_fields),
            "completion_cost_observation_contract is missing required fields",
            errors,
        )

    for invariant in pack["invariants"].get("invariants", []):
        _require(invariant.get("dimension") in dimensions, f"invariant {invariant.get('id')} references unknown dimension", errors)

    scenario_ids: set[str] = set()
    trace_required_scenarios: set[str] = set()
    artifact_backed_scenarios: set[str] = set()
    for probe in pack["scenarios"].get("probes", []):
        probe_id = str(probe.get("id"))
        scenario_ids.add(probe_id)
        if probe.get("requires_operational_trace") is True:
            trace_required_scenarios.add(probe_id)
        if probe.get("artifact_backed"):
            artifact_backed_scenarios.add(probe_id)
            artifact_evidence = probe.get("artifact_evidence", {})
            _require(isinstance(artifact_evidence, dict), f"artifact-backed probe {probe_id} must define artifact_evidence", errors)
            required_fields = artifact_evidence.get("required_fields", []) if isinstance(artifact_evidence, dict) else []
            _require(
                {"artifact_source", "artifact_checksum", "installed_entrypoint"}.issubset(
                    {str(item) for item in required_fields if isinstance(item, str)}
                ),
                f"artifact-backed probe {probe_id} must require artifact source, checksum, and installed entrypoint",
                errors,
            )
        for dimension in probe.get("expected_dimensions", []):
            _require(dimension in dimensions, f"probe {probe.get('id')} references unknown dimension {dimension}", errors)
        for failure_id in probe.get("failure_ids", []):
            _require(failure_id in failure_ids, f"probe {probe.get('id')} references unknown failure id {failure_id}", errors)
    _require(any(probe.get("artifact_backed") for probe in pack["scenarios"].get("probes", [])), "artifact-backed probe is missing", errors)

    record_ids: set[str] = set()
    records_by_id: dict[str, dict[str, Any]] = {}
    failure_ids_seen: set[str] = set()
    required_decision_keys = {"route", "memory", "planning", "verification", "residue_owner", "safe_claim"}
    for record in pack["results"].get("records", []):
        record_id = str(record.get("id"))
        scenario_id = str(record.get("scenario_id") or "")
        record_ids.add(record_id)
        records_by_id[record_id] = record
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
        if "LOCAL_ABSOLUTE_PATH_LEAK" in record.get("failure_ids", []):
            _validate_local_path_leak_packet(
                record.get("local_path_leak"),
                prefix=f"record {record.get('id')}",
                errors=errors,
            )
        if "completion_cost_observations" in record:
            _validate_completion_cost_observations(
                record.get("completion_cost_observations"),
                prefix=f"record {record.get('id')}",
                scenario_id=scenario_id,
                owner_surfaces=owner_surfaces,
                errors=errors,
            )
        decisions = record.get("decisions", {})
        if scenario_id in trace_required_scenarios:
            _require(
                isinstance(decisions, dict) and required_decision_keys.issubset(set(decisions)),
                f"record {record.get('id')} must include operational decision trace keys",
                errors,
            )
            _validate_operating_loop_packet(
                record.get("operating_loop"),
                prefix=f"record {record.get('id')}",
                owner_surfaces=owner_surfaces,
                errors=errors,
            )
        if scenario_id in artifact_backed_scenarios:
            identity = record.get("aw_identity", {})
            _require(
                isinstance(identity, dict)
                and bool(str(identity.get("source") or "").strip())
                and "artifact_checksum" in identity,
                f"record {record.get('id')} must include artifact source and checksum evidence",
                errors,
            )
    for record in pack.get("live_results", {}).get("runs", []):
        record_id = str(record.get("id"))
        record_ids.add(record_id)
        records_by_id[record_id] = record
        _require(record.get("scenario_id") in scenario_ids, f"live run {record.get('id')} references unknown scenario", errors)
        if "operating_loop" in record:
            _validate_operating_loop_packet(
                record.get("operating_loop"),
                prefix=f"live run {record.get('id')}",
                owner_surfaces=owner_surfaces,
                errors=errors,
            )
        for failure_id in record.get("failure_ids", []):
            _require(failure_id in failure_ids, f"live run {record.get('id')} references unknown failure id {failure_id}", errors)
        if "LOCAL_ABSOLUTE_PATH_LEAK" in record.get("failure_ids", []):
            _validate_local_path_leak_packet(
                record.get("local_path_leak"),
                prefix=f"live run {record.get('id')}",
                errors=errors,
            )
        if "completion_cost_observations" in record:
            _validate_completion_cost_observations(
                record.get("completion_cost_observations"),
                prefix=f"live run {record.get('id')}",
                scenario_id=str(record.get("scenario_id") or ""),
                owner_surfaces=owner_surfaces,
                errors=errors,
            )

    allowed_fixture_statuses = {"active_regression_guard", "historical_calibration", "retired"}
    for fixture in pack["historical"].get("fixtures", []):
        result_record_ref = str(fixture.get("result_record_ref") or "")
        referenced_record = records_by_id.get(result_record_ref)
        _require(result_record_ref in record_ids, f"historical fixture {fixture.get('id')} has unknown record ref", errors)
        _require(
            fixture.get("status") in allowed_fixture_statuses,
            f"historical fixture {fixture.get('id')} has invalid status",
            errors,
        )
        _require(
            bool(fixture.get("current_aw_signals")) and bool(fixture.get("owner_surface_if_repeats")),
            f"historical fixture {fixture.get('id')} must name current AW signals and repeat owner",
            errors,
        )
        for failure_id in fixture.get("failure_ids", []):
            _require(failure_id in failure_ids, f"historical fixture {fixture.get('id')} references unknown failure id", errors)
            _require(
                failure_id in _record_failure_ids(referenced_record),
                f"historical fixture {fixture.get('id')} failure {failure_id} is not represented by {result_record_ref}",
                errors,
            )
    _require(len(pack["historical"].get("fixtures", [])) >= 3, "at least three historical fixtures are required", errors)

    for decision in pack["promotions"].get("decisions", []):
        for failure_id in decision.get("failure_ids", []):
            _require(failure_id in failure_ids, f"promotion {decision.get('id')} references unknown failure id", errors)
            if decision.get("evidence_record_ids"):
                referenced_failures = set().union(
                    *(_record_failure_ids(records_by_id.get(str(record_id))) for record_id in decision.get("evidence_record_ids", []))
                )
                _require(
                    failure_id in referenced_failures,
                    f"promotion {decision.get('id')} failure {failure_id} is not represented by its evidence records",
                    errors,
                )
        for record_id in decision.get("evidence_record_ids", []):
            _require(record_id in record_ids, f"promotion {decision.get('id')} references unknown record id", errors)
        _require(decision.get("owner_surface") in owner_surfaces, f"promotion {decision.get('id')} has unknown owner surface", errors)
        _require(decision.get("decision") in {"promote", "dismiss"}, f"promotion {decision.get('id')} has invalid decision", errors)
        if decision.get("decision") == "promote":
            _require(
                _actionable_remediation(decision),
                f"promotion {decision.get('id')} must route to an actionable remediation owner",
                errors,
            )

    surface_decisions = {"keep_visible", "route", "merge", "generate", "remove", "keep_reasoning_complement"}
    for decision in pack["surfaces"].get("decisions", []):
        _require(decision.get("decision") in surface_decisions, f"surface decision {decision.get('id')} is invalid", errors)
        _require(decision.get("owner") in owner_surfaces, f"surface decision {decision.get('id')} has unknown owner", errors)
        for evidence_ref in decision.get("evidence_refs", []):
            _require(
                evidence_ref in record_ids or evidence_ref in scenario_ids,
                f"surface decision {decision.get('id')} references unknown evidence {evidence_ref}",
                errors,
            )

    _require("PROOF_MISSING_BEFORE_CLAIM" in failure_ids_seen, "sample records must include proof claim-safety failure evidence", errors)
    _require("MEMORY_PULL_MISSING" in failure_ids_seen, "sample records must include Memory routing failure evidence", errors)
    observed_record_count = sum(
        1 for record in pack["results"].get("records", []) if isinstance(record.get("completion_cost_observations"), dict)
    )
    _require(
        observed_record_count >= minimum_observed_records,
        "sample records must include representative completion-cost observation evidence",
        errors,
    )
    return errors


def _completion_cost_observability(records: list[dict[str, Any]]) -> dict[str, Any]:
    observed = [record["completion_cost_observations"] for record in records if isinstance(record.get("completion_cost_observations"), dict)]
    totals = {field: sum(int(item.get(field, 0) or 0) for item in observed) for field in sorted(COMPLETION_COST_NUMERIC_FIELDS)}
    driver_counts = Counter(
        driver.get("classification")
        for item in observed
        for driver in item.get("cost_drivers", [])
        if isinstance(driver, dict) and driver.get("classification")
    )
    owner_counts = Counter(
        driver.get("owner_surface")
        for item in observed
        for driver in item.get("cost_drivers", [])
        if isinstance(driver, dict) and driver.get("owner_surface")
    )
    section_counts = Counter(section for item in observed for section in item.get("aw_sections_used", []) if isinstance(section, str))
    handoff_counts = Counter(item.get("handoff_recovery_status") for item in observed if item.get("handoff_recovery_status"))
    return {
        "kind": "agentic-workspace/external-agent-completion-cost-observability/v1",
        "record_count": len(observed),
        "scenario_ids": sorted({str(item.get("scenario_id")) for item in observed if item.get("scenario_id")}),
        "totals": totals,
        "driver_classification_counts": dict(sorted(driver_counts.items())),
        "owner_surface_counts": dict(sorted(owner_counts.items())),
        "aw_sections_used_counts": dict(sorted(section_counts.items())),
        "handoff_recovery_status_counts": dict(sorted(handoff_counts.items())),
    }


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
    live_record_ids = {str(run.get("id")) for run in live_runs}
    promotions = pack["promotions"]["decisions"]
    live_promoted_failures = Counter(
        failure_id
        for decision in promotions
        if decision.get("decision") == "promote" and live_record_ids.intersection({str(item) for item in decision.get("evidence_record_ids", [])})
        for failure_id in decision.get("failure_ids", [])
    )
    live_actionable_failures = Counter(
        failure_id
        for decision in promotions
        if _actionable_remediation(decision)
        and live_record_ids.intersection({str(item) for item in decision.get("evidence_record_ids", [])})
        for failure_id in decision.get("failure_ids", [])
    )
    operating_loop_records = [record for record in [*records, *live_runs] if isinstance(record.get("operating_loop"), dict)]
    operating_loop_closeout_states = Counter(record["operating_loop"].get("closeout_state") for record in operating_loop_records)
    operating_loop_safe_claims = Counter(record["operating_loop"].get("safe_claim") for record in operating_loop_records)
    operating_loop_residue_owners = Counter(record["operating_loop"].get("residue_owner") for record in operating_loop_records)
    completion_cost_observability = _completion_cost_observability([*records, *live_runs])

    operating_loop_observability = {
        "kind": "agentic-workspace/external-agent-operating-loop-observability/v1",
        "record_count": len(operating_loop_records),
        "closeout_state_counts": dict(sorted(operating_loop_closeout_states.items())),
        "safe_claim_counts": dict(sorted(operating_loop_safe_claims.items())),
        "residue_owner_counts": dict(sorted(operating_loop_residue_owners.items())),
    }
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
        "operating_loop_observable": operating_loop_observability["record_count"] > 0,
        "completion_cost_observation_contract_exists": isinstance(pack["scenarios"].get("completion_cost_observation_contract"), dict),
        "completion_cost_observations_exist": completion_cost_observability["record_count"] > 0,
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
        "live_evaluation_agent": pack.get("live_results", {}).get("agent", {}),
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
            "promoted_failure_counts": dict(sorted(live_promoted_failures.items())),
            "actionable_remediation_failure_counts": dict(sorted(live_actionable_failures.items())),
        },
        "dimension_counts": dimension_counts,
        "failure_counts": dict(sorted(failure_counts.items())),
        "promotion_count": len(promoted),
        "dismissal_count": len(dismissed),
        "surface_decision_counts": dict(sorted(surface_decisions.items())),
        "operating_loop_observability": operating_loop_observability,
        "completion_cost_observability": completion_cost_observability,
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
