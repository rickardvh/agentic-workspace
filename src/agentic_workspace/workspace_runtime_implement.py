"""Implement-context runtime packet builders for Agentic Workspace.

This module owns implement payload construction while the old monolith keeps
compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, cast

from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.reporting_support import (
    communication_contract_payload,
    compact_communication_contract_payload,
    current_decision_payload,
    evidence_bundle_payload,
    message_economy_payload,
    state_delta_core_payload,
)
from agentic_workspace.review_stack_transitions import command_text, record_review_stack_transition
from agentic_workspace.runtime_source_review import (
    tiny_generated_cli_freshness_payload,
    tiny_runtime_source_edit_review_payload,
)
from agentic_workspace.runtime_symbol_working_set import tiny_runtime_symbol_working_set_payload
from agentic_workspace.workspace_runtime_core import (
    _CONTEXT_TEMPLATES,
    _acceptance_reconciliation_prompt_payload,
    _active_intent_contract_payload,
    _adaptive_routing_payload,
    _applicable_intent_status_payload,
    _architecture_principles_forecast_payload,
    _architecture_principles_payload,
    _as_int,
    _assurance_requirements_report_payload,
    _authority_hierarchy_payload,
    _boundary_warning_for_path,
    _change_impact_path_payload,
    _compact_action_signals_payload,
    _compact_assurance_requirements,
    _compact_continuation_state_contract,
    _compact_intent_evidence,
    _compact_memory_decision_packet,
    _compact_start_delegation_decision,
    _compact_task_posture_packet_projection,
    _compact_tiny_required_proof_commands,
    _completion_boundary_payload,
    _decision_point_source_revision_status,
    _delegation_decision_requires_attention,
    _diagnostic_profile,
    _emit_payload,
    _execution_posture_payload,
    _extract_requested_outcomes,
    _intent_acknowledgement_payload,
    _intent_decision_projection,
    _intent_discovery_dialogue_payload,
    _intent_proof_prompt_payload,
    _intent_satisfaction_matrix_payload,
    _load_decision_point_forecast,
    _load_workspace_config,
    _memory_consult_from_payload,
    _memory_consult_payload,
    _memory_decision_packet_payload,
    _module_operations,
    _operating_loop_decision_payload,
    _ordinary_decision_packet,
    _ownership_payload,
    _package_boundary_payload,
    _parent_intent_status_payload,
    _persist_decision_point_forecast,
    _plan_delegation_packet_payload,
    _read_changed_surface_text,
    _read_task_text_from_file,
    _record_decision_point_confirmation,
    _replacement_or_removal_intent,
    _requested_outcome_present,
    _requirement_grounding_payload,
    _resolve_target_root,
    _reuse_pressure_payload,
    _routine_work_context_payload,
    _select_payload_fields,
    _selector_first_planning_safety_gate,
    _selector_requests,
    _selector_requests_architecture_principles,
    _selector_requests_assurance_requirements,
    _selector_requests_change_impact,
    _selector_requests_plan_delegation_packet,
    _selector_requests_requirement_grounding,
    _selector_requests_reuse_pressure,
    _selector_requests_routine_work_context,
    _selector_requests_task_contract,
    _selector_requests_test_strategy_check,
    _selector_requests_verification,
    _session_improvement_pressure_payload,
    _task_acceptance_payload,
    _task_contract_payload,
    _task_intent_carry_forward_payload,
    _task_intent_evidence_payload,
    _task_posture_packet_changes_routing,
    _task_posture_packet_payload,
    _task_posture_packet_relevant,
    _test_strategy_check_payload,
    _tiny_acceptance_payload,
    _tiny_acceptance_reconciliation,
    _tiny_action_effect,
    _tiny_adaptive_routing_payload,
    _tiny_generated_surface_trust,
    _tiny_objective_drift,
    _tiny_required_proof_commands,
    _tiny_task_intent_promotion_guidance,
    _tiny_work_shape_guidance,
    _tiny_workflow_sufficiency,
    _unplanned_parent_intent_status_payload,
    _vague_outcome_orientation_payload,
    _validate_target_root,
    _workflow_obligations_report_payload,
    _workflow_sufficiency_payload,
    _workspace_disabled_payload,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _authority_marker_for_path,
    _command_with_cli_invoke,
    _generated_surface_trust_payload,
    _list_payload,
    _normalize_changed_paths,
    _selector_requests_generated_surface_trust,
)
from agentic_workspace.workspace_runtime_planning import (
    _active_planning_record_for_report_section,
    _planning_safety_gate_payload,
)
from agentic_workspace.workspace_runtime_proof import (
    _include_tiny_proof_narrowness,
    _proof_selection_for_changed_paths,
    _tiny_proof_obligations_payload,
    _verification_report_payload,
)


def _run_implement_context_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="implement", target_root=target_root)
    task_text = getattr(args, "task", None)
    if task_text and getattr(args, "task_file", None):
        raise WorkspaceUsageError("Use either --task or --task-file, not both.")
    if not task_text:
        task_text = _read_task_text_from_file(target_root=target_root, task_file=getattr(args, "task_file", None))
    config = _load_workspace_config(target_root=target_root)
    if disabled_payload := _workspace_disabled_payload(target_root=target_root, command_name="implement", config=config):
        _emit_payload(payload=disabled_payload, format_name=args.format)
        return 0
    profile = _diagnostic_profile(args, default="tiny")
    selected_fields = getattr(args, "select", None)
    change_impact_selected = _selector_requests_change_impact(selected_fields)
    generated_surface_trust_selected = _selector_requests_generated_surface_trust(selected_fields)
    task_contract_selected = _selector_requests_task_contract(selected_fields)
    assurance_requirements_selected = _selector_requests_assurance_requirements(selected_fields)
    verification_selected = _selector_requests_verification(selected_fields)
    routine_work_context_selected = _selector_requests_routine_work_context(selected_fields)
    reuse_pressure_selected = _selector_requests_reuse_pressure(selected_fields)
    architecture_principles_selected = _selector_requests_architecture_principles(selected_fields)
    requirement_grounding_selected = _selector_requests_requirement_grounding(selected_fields)
    plan_delegation_packet_selected = _selector_requests_plan_delegation_packet(selected_fields)
    test_strategy_check_selected = _selector_requests_test_strategy_check(selected_fields)
    changed_paths = list(getattr(args, "changed", []) or [])
    full_payload = _implement_payload(
        target_root=target_root,
        changed_paths=changed_paths,
        task_text=task_text,
        include_change_impact=(profile != "tiny" or change_impact_selected),
        include_task_contract=(profile != "tiny" or task_contract_selected),
        include_assurance_requirements=(profile != "tiny" or assurance_requirements_selected or routine_work_context_selected),
        include_verification=(profile != "tiny" or verification_selected or routine_work_context_selected),
        include_routine_work_context=(profile != "tiny" or routine_work_context_selected),
        include_reuse_pressure=(profile != "tiny" or reuse_pressure_selected),
    )
    payload = full_payload
    if profile == "tiny":
        payload = _tiny_implement_payload(full_payload)
        if task_contract_selected:
            payload["task_contract"] = full_payload["task_contract"]
        if change_impact_selected:
            payload["change_impact"] = full_payload["change_impact"]
        if generated_surface_trust_selected:
            payload["generated_surface_trust"] = full_payload["generated_surface_trust"]
        if assurance_requirements_selected:
            payload["assurance_requirements"] = full_payload["assurance_requirements"]
        if verification_selected:
            payload["verification"] = full_payload["verification"]
        if routine_work_context_selected:
            payload["routine_work_context"] = full_payload["routine_work_context"]
        if _selector_requests(getattr(args, "select", None), "proof.proof_adequacy") and isinstance(full_payload.get("proof"), dict):
            payload.setdefault("proof", {})["proof_adequacy"] = full_payload["proof"].get("proof_adequacy", {})
        if _selector_requests(getattr(args, "select", None), "active_intent_contract"):
            payload["active_intent_contract"] = full_payload["active_intent_contract"]
        if _selector_requests(getattr(args, "select", None), "intent_satisfaction_matrix"):
            payload["intent_satisfaction_matrix"] = full_payload["intent_satisfaction_matrix"]
        if requirement_grounding_selected:
            payload["requirement_grounding"] = full_payload["requirement_grounding"]
        if architecture_principles_selected:
            payload["architecture_principles"] = full_payload["architecture_principles"]
        if _selector_requests(getattr(args, "select", None), "decision_point_intent_confirmation"):
            payload["decision_point_intent_confirmation"] = full_payload.get("decision_point_intent_confirmation", {})
        if plan_delegation_packet_selected:
            payload["plan_delegation_packet"] = full_payload["plan_delegation_packet"]
        if test_strategy_check_selected:
            payload["test_strategy_check"] = full_payload["test_strategy_check"]
        if reuse_pressure_selected:
            payload["reuse_pressure"] = _reuse_pressure_payload(
                target_root=target_root,
                changed_paths=list(getattr(args, "changed", []) or []),
                compact=True,
                cli_invoke=_load_workspace_config(target_root=target_root).cli_invoke,
            )
    if getattr(args, "select", None):
        payload = _select_payload_fields(payload, select=getattr(args, "select"), source_command="implement")
    if changed_paths and not getattr(args, "select", None):
        transition = record_review_stack_transition(
            target_root=target_root,
            phase="review-correction",
            phase_after="review-proof",
            command=command_text(
                "agentic-workspace", ["implement", *sum((["--changed", path] for path in changed_paths), []), "--format", "json"]
            ),
            outcome="executed",
            next_action_id="run-focused-proof",
            changed_paths=changed_paths,
            command_exit_code=0,
        )
        if transition.get("status") not in {"skipped", ""}:
            payload["review_stack_transition"] = transition
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _objective_drift_payload(*, target_root: Path, changed_paths: list[str], task_text: str | None) -> dict[str, Any]:
    requested_outcomes = _extract_requested_outcomes(task_text)
    acceptance = _task_acceptance_payload(task_text=task_text, requested_outcomes=requested_outcomes)
    action_effect_clear = {
        "force": "advisory",
        "allowed_now": "continue-implementation-and-reconcile-acceptance",
        "blocked_until_reconciled": [],
        "claim_boundary": "acceptance-reconciliation-required-before-completion-claim",
        "resolution_selector": "context.objective_drift",
    }
    if not task_text:
        return {
            "kind": "agentic-workspace/objective-drift/v1",
            "status": "unavailable",
            "reason": "no task text was provided to compare against changed surfaces",
            "requested_outcomes": [],
            "acceptance_item_count": 0,
            "missing_from_changed_surface": [],
            "action_effect": {
                **action_effect_clear,
                "claim_boundary": "no-task-text-objective-comparison-unavailable",
            },
        }
    if not requested_outcomes:
        return {
            "kind": "agentic-workspace/objective-drift/v1",
            "status": "not-enough-explicit-outcomes",
            "reason": "task text did not contain explicit symbols, code identifiers, or backticked outcomes",
            "requested_outcomes": [],
            "acceptance_item_count": len(acceptance.get("items", [])),
            "acceptance_closeout_rule": acceptance.get("closeout_rule", ""),
            "missing_from_changed_surface": [],
            "action_effect": action_effect_clear,
        }
    surface_text = _read_changed_surface_text(target_root=target_root, changed_paths=changed_paths)
    searchable = surface_text.lower()
    replacement_intent = _replacement_or_removal_intent(task_text)
    removed_or_retired: list[str] = []
    replacement_checks: list[dict[str, Any]] = []
    missing: list[str] = []
    for item in requested_outcomes:
        lowered = item.lower()
        intent = replacement_intent.get(lowered)
        if intent:
            replacement = str(intent.get("replacement", "")).strip()
            replacement_present = _requested_outcome_present(searchable, replacement) if replacement else bool(searchable.strip())
            replacement_checks.append(
                {
                    "retired_outcome": item,
                    "classification": intent.get("classification", "removed"),
                    "replacement": replacement,
                    "replacement_present": replacement_present,
                    "phrase": intent.get("phrase", ""),
                }
            )
            if replacement_present:
                removed_or_retired.append(item)
                continue
            if replacement:
                missing.append(replacement)
                continue
        if not _requested_outcome_present(searchable, item):
            missing.append(item)
    status = "warning" if missing and changed_paths else "clear"
    action_effect = {
        **action_effect_clear,
        "force": "required_before_claim" if status == "warning" else "advisory",
        "allowed_now": "continue-implementation-or-inspect-changed-surface",
        "blocked_until_reconciled": ["claim-task-complete"] if status == "warning" else [],
        "claim_boundary": (
            "do-not-claim-complete-until-missing-outcomes-are-delivered-or-explicitly-out-of-scope"
            if status == "warning"
            else "acceptance-reconciliation-required-before-completion-claim"
        ),
        "resolution_selector": "context.objective_drift",
    }
    return {
        "kind": "agentic-workspace/objective-drift/v1",
        "status": status,
        "requested_outcomes": requested_outcomes,
        "removed_or_retired_outcomes": removed_or_retired,
        "replacement_checks": replacement_checks,
        "acceptance_item_count": len(acceptance.get("items", [])),
        "acceptance_closeout_rule": acceptance.get("closeout_rule", ""),
        "missing_from_changed_surface": missing,
        "action_effect": action_effect,
        "rule": "Do not claim completion until each acceptance item and requested outcome is mapped to delivered behavior and proof, or explicitly marked out of scope.",
        "recommended_next_action": "Inspect changed files, exports, docs, and tests for the missing requested outcomes before closeout."
        if status == "warning"
        else "Use acceptance reconciliation before closeout.",
        "heuristic": (
            "identifier and backtick-term overlap between task text and changed file contents; AW does not infer removal or "
            "retirement intent from prompt keywords unless explicit replacement/removal phrasing is paired with replacement "
            "or changed-surface evidence"
        ),
        "agent_owned_decisions": [
            "whether a missing requested outcome was intentionally removed, retired, replaced, or out of scope",
            "whether proof and acceptance reconciliation justify marking the missing outcome satisfied",
        ],
    }


def _optimization_posture_for_path(
    *,
    path_payload: dict[str, Any],
    improvement_latitude: str,
    optimization_bias: str,
) -> dict[str, Any]:
    owner = str(path_payload.get("owner") or "unknown")
    audience_value = str(path_payload.get("audience") or "").strip().lower()
    surface_origin = str(path_payload.get("surface_origin") or "unknown")
    authority = str(path_payload.get("authority") or "unknown")
    hard_blocked = bool(path_payload.get("hard_blockers"))
    ownership = str(path_payload.get("ownership") or "")
    direct_edit_boundary = (
        hard_blocked
        or surface_origin in {"generated", "managed"}
        or ownership
        in {
            "module_managed",
            "managed_fence",
        }
    )
    owner_key = owner.removeprefix("authority:").lower()
    owner_tokens = {token.strip() for token in owner_key.replace("+", ",").replace("/", ",").split(",") if token.strip()}
    has_human = bool(owner_tokens & {"human", "humans", "person", "people"})
    has_agent = bool(owner_tokens & {"agent", "agents"})
    has_machine = bool(owner_tokens & {"machine", "machines"})
    audience_conflict = sum((has_human, has_agent, has_machine)) > 1
    explicit_audience_tokens = {token.strip() for token in audience_value.replace("+", ",").replace("/", ",").split(",") if token.strip()}
    explicit_audience_conflict = len(explicit_audience_tokens & {"human", "agent", "machine"}) > 1
    if audience_value in {"mixed", "hybrid"} or explicit_audience_conflict:
        audience = "mixed"
        audience_source = "explicit"
        effective_target = "mixed-audience-review"
        effective_optimization_bias = "preserve-human-and-agent-usability"
        audience_reason = "explicit mixed-audience surface needs review when human, agent, or machine targets trade off"
        signals = ["mixed-audience", "reviewability", "machine-readable-structure", "tradeoff-review"]
    elif audience_value in {"human", "agent", "machine"}:
        audience = audience_value
        audience_source = "explicit"
        if audience == "human":
            effective_target = "human-readability-control-review"
            effective_optimization_bias = "human-readability-control-review"
            audience_reason = "explicit human-use audience is optimised for human readability, control, and review"
            signals = ["human-readability", "human-control", "reviewability", "authority-boundary"]
        elif audience == "agent":
            effective_target = "agent-efficiency"
            effective_optimization_bias = "agent-efficiency"
            audience_reason = "explicit agent-use audience is optimised for agent efficiency and machine-readable structure"
            signals = ["agent-efficiency", "machine-readable-structure", "low-residue", "authority-boundary"]
        else:
            effective_target = "stable-contract-validation"
            effective_optimization_bias = "stable-contract-validation"
            audience_reason = "explicit machine-use audience is optimised for stable contracts and validation"
            signals = ["stable-contract", "validation", "machine-readable-structure"]
    elif owner_key in {"mixed", "hybrid"} or audience_conflict:
        audience = "mixed"
        audience_source = "owner-inferred"
        effective_target = "mixed-audience-review"
        effective_optimization_bias = "preserve-human-and-agent-usability"
        audience_reason = "mixed-audience surface needs review when human, agent, or machine targets trade off"
        signals = ["mixed-audience", "reviewability", "machine-readable-structure", "tradeoff-review"]
    elif has_human:
        audience = "human"
        audience_source = "owner-inferred"
        effective_target = "human-readability-control-review"
        effective_optimization_bias = "human-readability-control-review"
        audience_reason = "human-use surface is optimised for human readability, control, and review"
        signals = ["human-readability", "human-control", "reviewability", "authority-boundary"]
    elif has_agent:
        audience = "agent"
        audience_source = "owner-inferred"
        effective_target = "agent-efficiency"
        effective_optimization_bias = "agent-efficiency"
        audience_reason = "agent-use surface is optimised for agent efficiency and machine-readable structure"
        signals = ["agent-efficiency", "machine-readable-structure", "low-residue", "authority-boundary"]
    elif has_machine:
        audience = "machine"
        audience_source = "owner-inferred"
        effective_target = "stable-contract-validation"
        effective_optimization_bias = "stable-contract-validation"
        audience_reason = "machine-use surface is optimised for stable contracts and validation"
        signals = ["stable-contract", "validation", "machine-readable-structure"]
    else:
        audience = "unknown"
        audience_source = "none"
        effective_target = optimization_bias
        effective_optimization_bias = optimization_bias
        audience_reason = "configured repo optimisation posture applies to this implementation path"
        signals = ["agent-efficiency", "proactive-improvement", "reuse-pressure", "architecture-boundary", "residue-routing"]
    source_route = "source-or-owner-first" if direct_edit_boundary else "direct"
    status = (
        "review-required" if audience == "mixed" and not direct_edit_boundary else "owner-boundary" if direct_edit_boundary else "active"
    )
    if hard_blocked:
        reason = "direct edit is blocked by authority or generated-surface routing"
    elif surface_origin == "generated":
        reason = "generated projection should route through its source contract before optimisation pressure"
    elif surface_origin == "managed":
        reason = "managed or module-owned surface preserves owner boundary before optimisation pressure"
    elif ownership in {"module_managed", "managed_fence"}:
        reason = "managed ownership preserves owner boundary before optimisation pressure"
    else:
        reason = audience_reason
    closeout_questions = (
        [
            "Was optimisation routed through the canonical source, generated owner, or managed command path before changing this surface?",
            "Was review or escalation routed when the owner or authority boundary matters?",
        ]
        if direct_edit_boundary
        else [
            "Which audience target wins if human, agent, or machine optimisation goals trade off?",
            "Was review or escalation routed instead of silently guessing the effective target?",
        ]
        if audience == "mixed"
        else [
            "Did the implementation improve or preserve the effective optimisation target for this surface?",
            "If the configured repo posture was retargeted for a human-use or agent-use surface, is that audience boundary explicit before completion claims?",
        ]
    )
    review_guidance = (
        "Subsystem-owned implementation surface: keep configured posture active and use subsystem proof/review guidance."
        if owner.startswith("subsystem:")
        else "Use the effective optimisation target for this surface."
    )
    return {
        "status": status,
        "improvement_latitude": improvement_latitude,
        "optimization_bias": optimization_bias,
        "effective_optimization_bias": effective_optimization_bias,
        "configured_posture": {
            "improvement_latitude": improvement_latitude,
            "optimization_bias": optimization_bias,
        },
        "audience": audience,
        "audience_source": audience_source,
        "effective_target": effective_target,
        "optimization_target": effective_target,
        "source_route": source_route,
        "owner": owner,
        "surface_origin": surface_origin,
        "authority": authority,
        "exempt_from_optimization_pressure": direct_edit_boundary,
        "reason": reason,
        "signals": [] if direct_edit_boundary else signals,
        "review_guidance": review_guidance,
        "closeout_questions": closeout_questions,
    }


def _optimization_posture_summary(paths: list[dict[str, Any]]) -> dict[str, Any]:
    posture_items = [_as_dict(path.get("optimization_posture")) for path in paths if isinstance(path, dict)]
    active_count = sum(1 for item in posture_items if item.get("status") == "active")
    exempt_count = sum(1 for item in posture_items if item.get("status") == "owner-boundary")
    review_count = sum(1 for item in posture_items if item.get("status") == "review-required")
    source_routed_count = sum(1 for item in posture_items if item.get("source_route") == "source-or-owner-first")
    audience_overrides = [
        item
        for item in posture_items
        if item.get("audience") in {"human", "agent", "machine", "mixed"} and item.get("status") != "owner-boundary"
    ]
    effective_targets = sorted(
        {str(item.get("effective_target")) for item in posture_items if str(item.get("effective_target") or "").strip()}
    )
    configured_postures = [
        _as_dict(item.get("configured_posture")) for item in posture_items if isinstance(item.get("configured_posture"), dict)
    ]
    configured_posture = configured_postures[0] if configured_postures else {}
    if review_count:
        status = "review-required"
    elif active_count and exempt_count:
        status = "mixed"
    elif active_count:
        status = "active"
    elif exempt_count:
        status = "owner-boundary"
    else:
        status = "unavailable"
    return {
        "kind": "agentic-workspace/optimization-posture-routing/v1",
        "status": status,
        "active_path_count": active_count,
        "owner_boundary_path_count": exempt_count,
        "review_required_path_count": review_count,
        "source_routed_path_count": source_routed_count,
        "audience_override_count": len(audience_overrides),
        "effective_target": effective_targets[0] if len(effective_targets) == 1 else "mixed" if effective_targets else "unknown",
        "configured_posture": configured_posture,
        "closeout_required": bool(active_count or exempt_count or review_count),
        "review_required": bool(review_count),
        "review_guidance": "Review mixed or conflicting audience signals before choosing an optimisation target." if review_count else "",
        "rule": "Configured improvement_latitude and optimization_bias apply to ordinary implementation paths; explicit audience retargets optimisation for human, agent, machine, or mixed use, while managed, generated, and direct-edit-blocked surfaces route through their source or owner path first.",
        "active_closeout_question": "Did the implementation improve or preserve the effective optimisation target for each active surface?",
        "owner_boundary_question": "Was optimisation routed through the source, generated owner, managed command, or authority path before changing an owner-boundary surface?",
    }


def _optimization_posture_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    proof: dict[str, Any],
    cli_invoke: str,
    improvement_latitude: str,
    optimization_bias: str,
) -> dict[str, Any]:
    if not changed_paths:
        return _optimization_posture_summary([])
    ownership_payload = _ownership_payload(target_root=target_root, descriptors=_module_operations())
    paths = [
        _change_impact_path_payload(path=path, ownership_payload=ownership_payload, proof=proof, cli_invoke=cli_invoke)
        for path in changed_paths
    ]
    for path_payload in paths:
        path_payload["optimization_posture"] = _optimization_posture_for_path(
            path_payload=path_payload,
            improvement_latitude=improvement_latitude,
            optimization_bias=optimization_bias,
        )
    return _optimization_posture_summary(paths)


def _change_impact_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    proof: dict[str, Any],
    cli_invoke: str,
    improvement_latitude: str = "reactive",
    optimization_bias: str = "neutral",
) -> dict[str, Any]:
    if not changed_paths:
        return {
            "kind": "agentic-workspace/change-impact/v1",
            "status": "unavailable",
            "reason": "changed paths are required before ownership, generatedness, and proof impact can be projected",
            "paths": [],
            "facts": [],
            "warnings": [],
            "hard_blockers": [],
        }
    ownership_payload = _ownership_payload(target_root=target_root, descriptors=_module_operations())
    paths = [
        _change_impact_path_payload(path=path, ownership_payload=ownership_payload, proof=proof, cli_invoke=cli_invoke)
        for path in changed_paths
    ]
    for path_payload in paths:
        path_payload["optimization_posture"] = _optimization_posture_for_path(
            path_payload=path_payload,
            improvement_latitude=improvement_latitude,
            optimization_bias=optimization_bias,
        )
    facts = [f"{item['path']}: {fact}" for item in paths for fact in item["facts"]]
    warnings = [f"{item['path']}: {warning}" for item in paths for warning in item["warnings"]]
    hard_blockers = [f"{item['path']}: {blocker}" for item in paths for blocker in item["hard_blockers"]]
    generated_count = sum(1 for item in paths if item.get("surface_origin") == "generated")
    managed_count = sum(1 for item in paths if item.get("surface_origin") == "managed")
    unknown_count = sum(1 for item in paths if item.get("owner") == "unknown" or item.get("surface_origin") == "unknown")
    return {
        "kind": "agentic-workspace/change-impact/v1",
        "status": "present",
        "changed_paths": changed_paths,
        "path_count": len(paths),
        "generated_path_count": generated_count,
        "managed_path_count": managed_count,
        "unknown_path_count": unknown_count,
        "warning_count": len(warnings),
        "hard_blocker_count": len(hard_blockers),
        "optimization_posture": _optimization_posture_summary(paths),
        "paths": paths,
        "facts": facts,
        "warnings": warnings,
        "hard_blockers": hard_blockers,
        "proof_impact": {
            "selected_lanes": [str(lane.get("id", "")) for lane in proof.get("selected_lanes", []) if isinstance(lane, dict)],
            "required_commands": list(proof.get("required_commands", [])),
            "detail_command": _command_with_cli_invoke(
                command="agentic-workspace proof --verbose --changed <paths> --format json", cli_invoke=cli_invoke
            ),
        },
        "rule": "Change impact is advisory unless hard_blockers is non-empty; it composes ownership, authority markers, generated-surface guidance, subsystem hints, configured optimisation posture, and proof selection for the changed paths.",
    }


def _implement_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    task_text: str | None = None,
    include_change_impact: bool = True,
    include_task_contract: bool = True,
    include_assurance_requirements: bool = True,
    include_verification: bool = True,
    include_routine_work_context: bool = True,
    include_reuse_pressure: bool = True,
) -> dict[str, Any]:
    implementer_template = _CONTEXT_TEMPLATES["implementer_context"]
    normalized_paths = _normalize_changed_paths(changed_paths)
    config = _load_workspace_config(target_root=target_root)
    proof = (
        _proof_selection_for_changed_paths(
            changed_paths=normalized_paths,
            target_root=target_root,
            include_durable_intent=False,
            task_text=task_text,
            acceptance=_task_acceptance_payload(task_text=task_text, requested_outcomes=_extract_requested_outcomes(task_text)),
            include_assurance_requirements=include_assurance_requirements,
            include_routine_work_context=include_routine_work_context,
        )
        if normalized_paths
        else copy.deepcopy(implementer_template["unknown_scope_proof"])
    )
    path_boundaries = [
        _boundary_warning_for_path(path, agent_instructions_file=config.agent_instructions_file) for path in normalized_paths
    ]
    attention_paths = [item["path"] for item in path_boundaries if item["requires_attention"]]
    inspect_files = normalized_paths or list(implementer_template["default_inspect_files"])
    execution_posture = _execution_posture_payload(
        config=config, changed_paths=normalized_paths, task_text=task_text, target_root=target_root
    )
    planning_safety_gate = _planning_safety_gate_payload(
        target_root=target_root, config=config, changed_paths=normalized_paths, task_text=task_text, execution_posture=execution_posture
    )
    task_intent = _task_intent_carry_forward_payload(
        task_text=task_text, cli_invoke=config.cli_invoke, target_root=target_root, config=config, changed_paths=normalized_paths
    )
    acceptance = task_intent["acceptance"]
    promotion_guidance = task_intent["promotion_guidance"]
    if isinstance(proof, dict):
        proof["intent_proof"] = _intent_proof_prompt_payload(task_text=task_text, acceptance=acceptance, claim_boundary="slice")
        proof["acceptance_guidance"] = {
            "status": "present" if acceptance.get("closeout_required") else "not-task-scoped",
            "rule": acceptance.get("proof_rule", "Proof should demonstrate acceptance satisfaction, not only command success."),
            "acceptance_item_count": len(acceptance.get("items", [])),
            "closeout_required": acceptance.get("closeout_required", False),
        }
    vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
    intent_acknowledgement = _intent_acknowledgement_payload(
        task_text=task_text, execution_posture=execution_posture, vague_orientation=vague_orientation
    )
    intent_discovery = (
        {}
        if normalized_paths
        else _intent_discovery_dialogue_payload(
            task_text=task_text,
            vague_orientation=vague_orientation,
            cli_invoke=config.cli_invoke,
        )
    )
    intent_evidence = _task_intent_evidence_payload(
        task_text=task_text,
        task_intent=task_intent,
        intent_discovery=intent_discovery,
        intent_acknowledgement=intent_acknowledgement,
    )
    generated_surface_trust = _generated_surface_trust_payload(
        target_root=target_root,
        changed_paths=normalized_paths,
        proof=proof,
        cli_invoke=config.cli_invoke,
    )
    active_planning_record_for_intent = _active_planning_record_for_report_section(target_root=target_root)
    parent_completion_boundary = _completion_boundary_payload(active_planning_record=active_planning_record_for_intent)
    parent_intent_status = _parent_intent_status_payload(
        active_planning_record=active_planning_record_for_intent,
        intent_check={},
        completion_boundary=parent_completion_boundary,
    )
    parent_intent_status = _unplanned_parent_intent_status_payload(
        parent_intent_status=parent_intent_status,
        task_text=task_text,
        changed_paths=normalized_paths,
        generated_surface_trust=generated_surface_trust,
    )
    applicable_intent_status = _applicable_intent_status_payload(active_planning_record=active_planning_record_for_intent)
    active_intent_contract = _active_intent_contract_payload(
        task_text=task_text,
        acceptance=acceptance,
        active_planning_record=active_planning_record_for_intent,
    )
    intent_satisfaction_matrix = _intent_satisfaction_matrix_payload(
        active_intent_contract=active_intent_contract,
        acceptance=acceptance,
        proof=proof,
        intent_check={},
        parent_intent_status=parent_intent_status,
    )
    implement_current_need = "changed-path-implementation" if normalized_paths else "unknown-scope-routing"
    payload = {
        "kind": "implementer-context/v1",
        "target": target_root.as_posix(),
        "communication_contract": communication_contract_payload(surface="implementation"),
        "workflow_sufficiency": _workflow_sufficiency_payload(
            surface="implement",
            decision=planning_safety_gate["decision"]
            if not planning_safety_gate["workflow_sufficient"]
            else "enough-for-bounded-implementation"
            if normalized_paths
            else "insufficient-without-changed-paths",
            reason=planning_safety_gate["reason"]
            if not planning_safety_gate["workflow_sufficient"]
            else "Changed paths are known; inspect only the named scope, reconcile acceptance, and run selected proof."
            if normalized_paths
            else "Changed paths are missing, so the package cannot select bounded inspect or proof scope.",
            required_next_action=planning_safety_gate["required_next_action"]
            if not planning_safety_gate["workflow_sufficient"]
            else "inspect changed paths and selected proof"
            if normalized_paths
            else "provide --changed paths or run start/preflight",
            evidence_required=["active planning ownership evidence", "proof execution evidence before closeout"]
            if not planning_safety_gate["workflow_sufficient"]
            else ["proof execution evidence before closeout"]
            if normalized_paths
            else ["changed paths"],
            hard_gate=not planning_safety_gate["workflow_sufficient"],
        ),
        "adaptive_routing": _adaptive_routing_payload(
            surface="implement",
            profile="full",
            current_need=implement_current_need,
            why_this_packet="Changed paths are known, so implement can return bounded inspect files, proof, path warnings, and acceptance checks."
            if normalized_paths
            else "Changed paths are missing, so implement can only route the agent away from broad implementation.",
            required_sections=[
                "changed_paths",
                "inspect_files",
                "proof",
                "acceptance_reconciliation",
                "objective_drift",
                "next_allowed_action",
            ],
            optional_sections=["path_boundaries", "execution_posture", "delegation_decision", "durable_intent", "handoff_requirements"],
            detail_commands={
                "tiny_next_action": _command_with_cli_invoke(
                    command="agentic-workspace implement --changed <paths> --format json", cli_invoke=config.cli_invoke
                ),
                "proof_detail": _command_with_cli_invoke(
                    command="agentic-workspace proof --verbose --changed <paths> --format json", cli_invoke=config.cli_invoke
                ),
                "active_state": _command_with_cli_invoke(
                    command="agentic-workspace summary --changed <paths> --format json", cli_invoke=config.cli_invoke
                ),
                "takeover_or_recovery": _command_with_cli_invoke(
                    command="agentic-workspace preflight --format json", cli_invoke=config.cli_invoke
                ),
            },
            when_to_escalate=[
                "changed paths are missing or incomplete",
                "proof, path authority, or objective-drift warnings appear",
                "task routing says planning is needed",
                "delegation decision requests escalation or handoff",
            ],
            not_needed_now=[
                "full planning summary unless active state or task routing requires it",
                "raw planning files before compact summary points there",
                "unrelated memory notes",
            ],
        ),
        "changed_paths": normalized_paths,
        "inspect_files": inspect_files,
        "files_to_avoid": list(implementer_template["files_to_avoid"]),
        "package_boundary": _package_boundary_payload(target_root=target_root),
        "path_boundaries": path_boundaries,
        "authority_markers": [
            _authority_marker_for_path(path, agent_instructions_file=config.agent_instructions_file)
            for path in normalized_paths or [config.agent_instructions_file]
        ],
        "task_intent": task_intent,
        "acceptance": acceptance,
        "durable_intent_promotion": promotion_guidance,
        "proof": proof,
        "required_validation_commands": proof["required_commands"],
        "acceptance_reconciliation": _acceptance_reconciliation_prompt_payload(task_text=task_text, acceptance=acceptance),
        "intent_acknowledgement": intent_acknowledgement,
        "intent_evidence": intent_evidence,
        "active_intent_contract": active_intent_contract,
        "intent_satisfaction_matrix": intent_satisfaction_matrix,
        "parent_intent_status": parent_intent_status,
        "applicable_intent_status": applicable_intent_status,
        "objective_drift": _objective_drift_payload(target_root=target_root, changed_paths=normalized_paths, task_text=task_text),
        "generated_surface_trust": generated_surface_trust,
        "reuse_pressure": _reuse_pressure_payload(
            target_root=target_root, changed_paths=normalized_paths, cli_invoke=config.cli_invoke, compact=False
        )
        if include_reuse_pressure
        else {
            "kind": "agentic-workspace/reuse-pressure/v1",
            "status": "deferred",
            "state": "selector-required",
            "summary": "Reuse pressure scan is selector-backed for tiny implement output.",
            "detail_selector": "reuse_pressure",
        },
        "memory_consult": _memory_consult_payload(
            target_root=target_root, changed_paths=normalized_paths, compact=True, cli_invoke=config.cli_invoke
        ),
        "architecture_principles": _architecture_principles_payload(
            target_root=target_root,
            changed_paths=normalized_paths,
            cli_invoke=config.cli_invoke,
            compact=False,
        ),
        "orientation": {
            "status": "changed-path-context" if normalized_paths else "unknown-scope",
            "minimum_before_editing": "Inspect the listed files, path boundaries, workflow obligations, and selected proof before editing."
            if normalized_paths
            else "Provide --changed paths or run preflight before broad implementation.",
            "preflight_command": _command_with_cli_invoke(
                command="agentic-workspace preflight --format json", cli_invoke=config.cli_invoke
            ),
            "summary_command": _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke),
            "trust_note": "Skipping workspace orientation may be faster for this edit, but lowers continuation and review trust for planned or high-risk work.",
        },
        "continuation_state": _compact_continuation_state_contract(cli_invoke=config.cli_invoke),
        "authority_hierarchy": _authority_hierarchy_payload(cli_invoke=config.cli_invoke),
        "inference_limits": {
            "rule": "implement --changed derives bounded context from changed paths, config, active planning, and package metadata; it can be used to inspect the live projection shape before contract, schema, or docs changes, but it does not know unstated intent.",
            "can_infer": [
                "path-owned proof lanes",
                "configured workflow obligations visible from the target",
                "active planning assurance when Planning exposes it",
                "path boundary and generated-surface warnings",
                "current implementer-context projection keys for the selected changed paths",
            ],
            "cannot_infer": [
                "whether the human intended a larger lane than the changed paths imply",
                "whether proof commands were actually executed unless evidence is recorded elsewhere",
                "whether missing changed paths hide additional risk",
                "whether external tracker state is authoritative for the repo",
            ],
            "when_uncertain": "Run preflight or summary and promote to checked-in planning before implementation when scope, proof, or continuation is not obvious.",
        },
        "execution_posture": execution_posture,
        "planning_safety_gate": planning_safety_gate,
        "planning_revision": planning_safety_gate.get("planning_revision", {}),
        "active_plan_reliance": planning_safety_gate.get("active_plan_reliance", {}),
        "delegation_decision": execution_posture["delegation_decision"],
        "durable_intent": _intent_decision_projection(target_root=target_root, config=config, changed_paths=normalized_paths, compact=True),
        "handoff_requirements": copy.deepcopy(implementer_template["handoff_requirements"]),
        "next_allowed_action": "Provide --changed paths or use start/preflight before broad implementation."
        if not normalized_paths
        else implementer_template["next_allowed_action"]["attention"]
        if attention_paths
        else implementer_template["next_allowed_action"]["default"],
    }
    subsystem_intents = _list_payload(_as_dict(payload["durable_intent"].get("subsystem_intent")).get("matches"))
    principles = _list_payload(_as_dict(payload.get("architecture_principles")).get("matched_principles"))
    forecast_carry = _load_decision_point_forecast(target_root=target_root, task_text=task_text)
    if not forecast_carry and (subsystem_intents or principles) and target_root is not None:
        committed_forecast = _architecture_principles_forecast_payload(
            target_root=target_root,
            planned_paths=normalized_paths,
            scope_source="implement.changed_paths",
            cli_invoke=config.cli_invoke,
        )
        carry_result = _persist_decision_point_forecast(
            target_root=target_root,
            forecast=committed_forecast,
            task_text=task_text,
        )
        if carry_result.get("status") != "not-created":
            forecast_carry = carry_result
        elif carry_result:
            payload["decision_point_intent_carry"] = carry_result
    if subsystem_intents or principles or forecast_carry:
        forecast_identity = _as_dict(forecast_carry.get("forecast_identity"))
        forecast_paths = _normalize_changed_paths(_list_payload(forecast_identity.get("planned_paths")))
        actual_basis = {
            "actual_paths": normalized_paths,
            "system_principle_ids": [str(item.get("id", "")) for item in principles[:2]],
            "subsystem_intent_ids": [str(item.get("id", "")) for item in subsystem_intents[:2]],
        }
        actual_digest = hashlib.sha256(json.dumps(actual_basis, sort_keys=True).encode()).hexdigest()[:16]
        revision_status = _decision_point_source_revision_status(target_root=target_root, carry=forecast_carry)
        correction_required = bool(
            forecast_identity
            and (
                set(forecast_identity.get("planned_paths", [])) != set(normalized_paths)
                or forecast_identity.get("system_principle_ids", []) != actual_basis["system_principle_ids"]
                or forecast_identity.get("subsystem_intent_ids", []) != actual_basis["subsystem_intent_ids"]
                or revision_status["status"] == "changed"
            )
        )
        confirmation = {
            "kind": "agentic-workspace/decision-point-intent-confirmation/v1",
            "status": "corrected-from-changed-paths"
            if correction_required
            else "confirmed-from-changed-paths"
            if forecast_identity
            else "unresolved",
            "phase": "implementation",
            "changed_paths": normalized_paths,
            "system_principles": principles[:2],
            "subsystem_intents": subsystem_intents[:2],
            "forecast_scope": forecast_paths,
            "forecast_identity": forecast_identity,
            "forecast_digest": forecast_identity.get("digest", ""),
            "actual_scope_digest": actual_digest,
            "correction_required": correction_required,
            "source_revision_confirmation": revision_status,
            "closeout_accounting": "corrected" if correction_required else "preserved",
            "proof_claim_boundary": "proof must apply the actual changed-path intent boundary",
            "carry_forward": {
                "status": "required",
                "record_digest": actual_digest,
                "required_consumers": ["proof", "planning.closeout"],
            },
            "rule": "Actual changed paths confirm or correct the pre-edit intent forecast; proof and closeout must preserve the confirmed owning boundary.",
        }
        payload["decision_point_intent_confirmation"] = _record_decision_point_confirmation(
            target_root=target_root, phase="implementation", confirmation=confirmation, task_text=task_text
        )
    if not planning_safety_gate["workflow_sufficient"]:
        payload["next_allowed_action"] = "Create or promote an active execplan before continuing implementation."
        payload["handoff_requirements"]["stop_when"] = [
            "planning safety gate requires active planning ownership",
            *payload["handoff_requirements"]["stop_when"],
        ]
    memory_consult = _memory_consult_from_payload(payload)
    payload["memory_decision_packet"] = _memory_decision_packet_payload(
        stage="implement",
        cli_invoke=config.cli_invoke,
        memory_consult=memory_consult,
        changed_paths=normalized_paths,
        task_text=task_text,
        force="required_before_claim" if normalized_paths and memory_consult.get("status") == "recommended" else None,
    )
    payload["operating_loop"] = _operating_loop_decision_payload(
        claim_context="implement",
        memory_decision_packet=payload["memory_decision_packet"],
        planning_safety_gate=planning_safety_gate,
        active_plan_reliance=_as_dict(payload.get("active_plan_reliance")),
        proof=proof if isinstance(proof, dict) else {},
    )
    if include_task_contract:
        payload["task_contract"] = _task_contract_payload(
            changed_paths=normalized_paths,
            task_intent=task_intent,
            acceptance=acceptance,
            proof=proof,
            execution_posture=execution_posture,
            planning_safety_gate=planning_safety_gate,
            intent_acknowledgement=payload["intent_acknowledgement"],
            handoff_requirements=payload["handoff_requirements"],
        )
    if include_change_impact:
        payload["change_impact"] = _change_impact_payload(
            target_root=target_root,
            changed_paths=normalized_paths,
            proof=proof,
            cli_invoke=config.cli_invoke,
            improvement_latitude=config.improvement_latitude,
            optimization_bias=config.optimization_bias,
        )
        payload["optimization_posture"] = payload["change_impact"].get("optimization_posture", {})
    else:
        payload["optimization_posture"] = _optimization_posture_payload(
            target_root=target_root,
            changed_paths=normalized_paths,
            proof=proof,
            cli_invoke=config.cli_invoke,
            improvement_latitude=config.improvement_latitude,
            optimization_bias=config.optimization_bias,
        )
    if include_assurance_requirements:
        payload["assurance_requirements"] = _assurance_requirements_report_payload(
            config=config,
            target_root=target_root,
            active_planning_record=None,
            task_text=task_text,
            changed_paths=normalized_paths,
        )
    if include_verification:
        assurance_for_verification = payload.get("assurance_requirements", {})
        if not isinstance(assurance_for_verification, dict):
            assurance_for_verification = _assurance_requirements_report_payload(
                config=config,
                target_root=target_root,
                active_planning_record=None,
                task_text=task_text,
                changed_paths=normalized_paths,
            )
        payload["verification"] = _verification_report_payload(
            target_root=target_root,
            changed_paths=normalized_paths,
            task_text=task_text,
            assurance_requirements=assurance_for_verification,
        )
    assurance_for_grounding = payload.get("assurance_requirements", {})
    if not isinstance(assurance_for_grounding, dict):
        assurance_for_grounding = _assurance_requirements_report_payload(
            config=config,
            target_root=target_root,
            active_planning_record=None,
            task_text=task_text,
            changed_paths=normalized_paths,
        )
    verification_for_grounding = payload.get("verification", {})
    if not isinstance(verification_for_grounding, dict):
        verification_for_grounding = _verification_report_payload(
            target_root=target_root,
            changed_paths=normalized_paths,
            task_text=task_text,
            assurance_requirements=assurance_for_grounding,
        )
    issue_scope_evidence = _as_dict(planning_safety_gate.get("issue_scope_evidence"))
    payload["requirement_grounding"] = _requirement_grounding_payload(
        target_root=target_root,
        task_text=task_text,
        changed_paths=normalized_paths,
        active_planning_record=active_planning_record_for_intent,
        issue_scope_evidence=issue_scope_evidence,
        assurance_requirements=assurance_for_grounding,
        verification=verification_for_grounding,
    )
    payload["plan_delegation_packet"] = _plan_delegation_packet_payload(
        target_root=target_root,
        config=config,
        proof=proof if isinstance(proof, dict) else {},
        task_text=task_text,
        changed_paths=normalized_paths,
    )
    payload["test_strategy_check"] = _test_strategy_check_payload(
        target_root=target_root,
        changed_paths=normalized_paths,
        task_text=task_text,
        verification=verification_for_grounding,
    )
    workflow_obligations = _workflow_obligations_report_payload(
        config=config,
        active_planning_record=active_planning_record_for_intent,
        task_text=task_text,
        changed_paths=normalized_paths,
    )
    improvement_pressure = _session_improvement_pressure_payload(
        target_root=target_root,
        config=config,
        task_text=task_text,
        cli_invoke=config.cli_invoke,
        active_planning_present=bool(active_planning_record_for_intent),
    )
    task_posture_packet = _task_posture_packet_payload(
        config=config,
        surface="implement",
        task_text=task_text,
        changed_paths=normalized_paths,
        workflow_obligations=workflow_obligations,
        skill_routing={},
        planning_safety_gate=planning_safety_gate,
        proof=proof,
        improvement_pressure=improvement_pressure,
        compact=False,
    )
    if (
        _task_posture_packet_relevant(task_text=task_text, changed_paths=normalized_paths, surface="implement")
        or task_posture_packet.get("improvement_obligations")
        or task_posture_packet.get("dogfooding_obligations")
    ) and _task_posture_packet_changes_routing(task_posture_packet):
        payload["task_posture_packet"] = task_posture_packet
    if include_routine_work_context:
        payload["routine_work_context"] = _routine_work_context_payload(
            source_payload=payload,
            surface="implement",
            cli_invoke=config.cli_invoke,
            target_root=target_root,
            changed_paths=normalized_paths,
            task_text=task_text,
            compact=False,
        )
    return payload


def _tiny_proof_route_maintenance_payload(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    suggestions = [
        {
            "reason": str(item.get("reason", "")),
            "route_id": str(item.get("route_id", "")),
            "target_surface": str(item.get("target_surface", "")),
            "target_surface_status": str(item.get("target_surface_status", "")),
            "recommended_state": str(item.get("recommended_state", "")),
        }
        for item in value.get("suggested_updates", [])
        if isinstance(item, dict)
    ][:1]
    return {
        "kind": value.get("kind", "proof-route-maintenance/v1"),
        "status": value.get("status", "unknown"),
        "material_to_current_work": bool(value.get("material_to_current_work", False)),
        "fallback_selected_count": int(value.get("fallback_selected_count", 0) or 0),
        "stale_route_count": int(value.get("stale_route_count", 0) or 0),
        "invalid_authority_count": int(value.get("invalid_authority_count", 0) or 0),
        "manual_obligation_count": int(value.get("manual_obligation_count", 0) or 0),
        "sample_suggested_updates": suggestions,
        "closeout_rule": value.get("closeout_rule", ""),
    }


def _tiny_proof_command_tiers_payload(value: Any, *, required_commands: list[str]) -> dict[str, Any]:
    packet = value if isinstance(value, dict) else {}
    raw_tiers = packet.get("tiers", [])
    tiers: list[dict[str, Any]] = []
    for tier in raw_tiers if isinstance(raw_tiers, list) else []:
        if not isinstance(tier, dict):
            continue
        raw_commands = tier.get("commands", [])
        commands = [
            {
                "command": str(item.get("command", "")),
                "evidence_type": str(item.get("evidence_type", "")),
                **(
                    {"extra_evidence": str(item.get("duplicates_ok_reason", ""))}
                    if str(item.get("duplicates_ok_reason", "")).strip()
                    else {}
                ),
            }
            for item in raw_commands
            if isinstance(item, dict) and str(item.get("command", "")).strip()
        ][:1]
        if commands:
            tiers.append({"id": str(tier.get("id", "")), "commands": commands})
    if len(tiers) <= 1 and not required_commands:
        return {}
    minimal_required = ""
    for tier in tiers:
        if tier["id"] == "must_run" and tier["commands"]:
            minimal_required = tier["commands"][0]["command"]
            break
    if not minimal_required and required_commands:
        minimal_required = required_commands[0]
    if len(tiers) <= 1 and minimal_required:
        return {
            "status": "required-commands-present",
            "detail_selector": "proof.proof_command_tiers",
        }
    return {
        "selected_set": {
            key: _as_dict(packet.get("selected_set")).get(key)
            for key in ("status",)
            if _as_dict(packet.get("selected_set")).get(key) not in (None, "", [], {})
        },
        "status": "present" if tiers else "empty",
        "minimal_required_command": minimal_required,
        "tiers": tiers,
        "closeout_rule": "List overlap only when it adds extra_evidence.",
    }


def _implement_tiny_proof_narrowness_payload(value: Any) -> dict[str, Any]:
    packet = value if isinstance(value, dict) else {}
    if not _include_tiny_proof_narrowness(packet):
        return {}
    compact = {"status": packet.get("status", "unknown")}
    if packet.get("status") == "broad_required":
        raw_triggers = packet.get("expansion_triggers")
        expansion_triggers: list[Any] = raw_triggers if isinstance(raw_triggers, list) else []
        first_trigger = next((item for item in expansion_triggers if isinstance(item, dict) and item.get("lane")), {})
        boundary = _as_dict(packet.get("broad_suite_boundary"))
        compact.update(
            {
                "expansion_trigger_lane": str(first_trigger.get("lane", "")) if first_trigger else "",
                "broad_suite_boundary_status": str(boundary.get("status", "")),
            }
        )
    return {key: payload for key, payload in compact.items() if payload not in ("", [], {}, None)}


def _tiny_implement_payload(payload: dict[str, Any]) -> dict[str, Any]:
    target_root = Path(str(payload.get("target", ".")))
    config = _load_workspace_config(target_root=target_root)
    path_warnings = [
        {"path": item.get("path"), "authority": item.get("authority"), "warning": item.get("warning")}
        for item in payload.get("path_boundaries", [])
        if isinstance(item, dict) and item.get("requires_attention")
    ]
    next_action = payload.get("next_allowed_action", "")
    planning_safety_gate = payload.get("planning_safety_gate", {})
    if isinstance(planning_safety_gate, dict) and planning_safety_gate.get("workflow_sufficient") is False:
        next_action = "Create or promote an active execplan before continuing implementation."
    elif not payload.get("changed_paths"):
        next_action = "Provide --changed paths or use start/preflight before broad implementation."
    proof_payload = payload.get("proof", {})
    proof_commands = (
        _tiny_required_proof_commands(proof_payload)
        if isinstance(proof_payload, dict)
        else _compact_tiny_required_proof_commands(payload.get("required_validation_commands", []))
    )
    primary_command = proof_commands[0] if isinstance(proof_commands, list) and proof_commands else None
    execution_posture = payload.get("execution_posture", {})
    intent_acknowledgement = payload.get("intent_acknowledgement", {})
    reuse_pressure = payload.get("reuse_pressure", {})
    if isinstance(reuse_pressure, dict):
        reuse_pressure = dict(reuse_pressure)
    test_strategy_check = payload.get("test_strategy_check", {})
    test_strategy_check = test_strategy_check if isinstance(test_strategy_check, dict) else {}
    test_strategy_applicable = str(test_strategy_check.get("status") or "").strip() not in {"", "not-applicable"}
    workflow_sufficiency = _tiny_workflow_sufficiency(payload.get("workflow_sufficiency"))
    context_reuse_pressure = {
        "status": reuse_pressure.get("status") if isinstance(reuse_pressure, dict) else None,
        "detail_selector": "reuse_pressure",
    }
    if not (isinstance(reuse_pressure, dict) and reuse_pressure.get("status") == "deferred"):
        context_reuse_pressure["state"] = reuse_pressure.get("state") if isinstance(reuse_pressure, dict) else None
        context_reuse_pressure["summary"] = reuse_pressure.get("summary") if isinstance(reuse_pressure, dict) else None
    optimization_posture = _as_dict(payload.get("optimization_posture"))
    delegation_decision = execution_posture.get("delegation_decision", {}) if isinstance(execution_posture, dict) else {}
    delegation_attention = _delegation_decision_requires_attention(delegation_decision)
    advisory_selectors = [
        "context.reuse_pressure",
        "context.guidance",
        "architecture_principles",
        "requirement_grounding",
        "plan_delegation_packet",
        "routine_work_context",
    ]
    if test_strategy_applicable:
        advisory_selectors.insert(-1, "test_strategy_check")
    if delegation_attention:
        advisory_selectors.insert(2, "context.delegation_decision")
    detail_commands = {
        "full_context": _command_with_cli_invoke(
            command="agentic-workspace implement --verbose --changed <paths> --format json", cli_invoke=config.cli_invoke
        ),
        "proof_detail": _command_with_cli_invoke(
            command="agentic-workspace proof --verbose --changed <paths> --format json", cli_invoke=config.cli_invoke
        ),
        "task_scoped_state": _command_with_cli_invoke(
            command="agentic-workspace summary --changed <paths> --format json", cli_invoke=config.cli_invoke
        ),
        "takeover_or_recovery": _command_with_cli_invoke(command="agentic-workspace preflight --format json", cli_invoke=config.cli_invoke),
    }
    communication_contract = compact_communication_contract_payload(surface="implementation")
    decision_packet = _ordinary_decision_packet(
        surface="implement",
        phase_question="What narrow working set is safe to touch now?",
        next_action=next_action,
        blocked_actions=[str(item) for item in _as_dict(payload.get("applicable_intent_status")).get("blocked_claims", [])],
        required_commands=[str(item) for item in proof_commands if str(item).strip()],
        claim_boundary=_as_dict(payload.get("parent_intent_status")).get("proof_boundary")
        or "claim after changed-path proof and acceptance reconciliation",
        residue_owner="active continuation state"
        if _as_dict(payload.get("planning_safety_gate")).get("active_planning_present")
        else "none",
        reasons=[
            f"changed_path_count={len(_normalize_changed_paths(payload.get('changed_paths', [])))}",
            f"workflow={workflow_sufficiency.get('sufficiency_result', workflow_sufficiency.get('decision', 'unknown'))}"
            if isinstance(workflow_sufficiency, dict)
            else "workflow=unknown",
        ],
        detail_routes={
            "proof_detail": _command_with_cli_invoke(
                command="agentic-workspace proof --target . --changed <paths> --format json", cli_invoke=config.cli_invoke
            ),
            "why_blocked": _command_with_cli_invoke(
                command="agentic-workspace implement --changed <paths> --select context.planning_safety_gate,next,proof --format json",
                cli_invoke=config.cli_invoke,
            ),
            "omitted_diagnostics": detail_commands["full_context"],
        },
        shown_because=[
            "command_phase=implement",
            "changed_path_ownership=present" if payload.get("changed_paths") else "changed_path_ownership=absent",
            "proof_selection=changed_paths",
        ],
        absence_states={
            "full_selector_inventory": "hidden_behind_detail_route",
            "architecture_detail": "not_action_changing",
            "raw_workspace_files": "not_action_changing",
        },
    )
    state_delta_missing_evidence = [str(item) for item in proof_commands if str(item).strip()] or [
        "proof execution evidence before hard completion claim"
    ]
    state_delta_core = state_delta_core_payload(
        surface="implementation",
        decision_packet=decision_packet,
        communication_contract=communication_contract,
        evidence_basis=[
            "implement.decision_packet",
            "implement.proof.required_commands",
            "implement.context.scope.changed_paths",
        ],
        missing_evidence=state_delta_missing_evidence,
        safe_probe=primary_command or detail_commands["proof_detail"],
    )
    current_decision = current_decision_payload(
        surface="implementation",
        decision_packet=decision_packet,
        state_delta_core=state_delta_core,
    )
    projected = {
        "kind": "implementer-context-tiny/v1",
        "target": payload.get("target"),
        "communication_contract": communication_contract,
        "action_signals": _compact_action_signals_payload(
            surface="implement",
            allowed_next_action=str(next_action),
            hard_blockers=[
                *(
                    [str(planning_safety_gate.get("gate_result") or planning_safety_gate.get("decision"))]
                    if isinstance(planning_safety_gate, dict) and planning_safety_gate.get("workflow_sufficient") is False
                    else []
                ),
            ],
            implementation_allowed=(
                bool(planning_safety_gate.get("implementation_allowed"))
                if isinstance(planning_safety_gate, dict) and "implementation_allowed" in planning_safety_gate
                else None
            ),
            read_only_allowed=(
                bool(planning_safety_gate.get("read_only_allowed"))
                if isinstance(planning_safety_gate, dict) and "read_only_allowed" in planning_safety_gate
                else True
            ),
            proof_required=bool(proof_commands),
            proof_commands=proof_commands,
            changed_signals=[
                *(
                    [
                        f"planning_safety={planning_safety_gate.get('status')}:{planning_safety_gate.get('gate_result') or planning_safety_gate.get('decision')}"
                    ]
                    if isinstance(planning_safety_gate, dict) and planning_safety_gate.get("status") not in {None, "", "clear"}
                    else []
                ),
                *([f"path_authority_attention={len(path_warnings)}"] if path_warnings else []),
                *(
                    [f"generated_surface_trust={payload.get('generated_surface_trust', {}).get('status')}"]
                    if isinstance(payload.get("generated_surface_trust"), dict)
                    and payload.get("generated_surface_trust", {}).get("status") == "present"
                    else []
                ),
                *(
                    ["generated_cli_freshness=" + str(payload.get("proof", {}).get("generated_cli_freshness", {}).get("status"))]
                    if isinstance(payload.get("proof"), dict) and isinstance(payload.get("proof", {}).get("generated_cli_freshness"), dict)
                    else []
                ),
                *(
                    [f"runtime_symbol_working_set={payload.get('proof', {}).get('runtime_symbol_working_set', {}).get('file_count')}"]
                    if isinstance(payload.get("proof"), dict)
                    and isinstance(payload.get("proof", {}).get("runtime_symbol_working_set"), dict)
                    and payload.get("proof", {}).get("runtime_symbol_working_set", {}).get("status") == "present"
                    else []
                ),
                *(
                    [f"reuse_pressure={reuse_pressure.get('state')}"]
                    if isinstance(reuse_pressure, dict) and reuse_pressure.get("state") not in {None, "", "none_found"}
                    else []
                ),
                *(
                    [f"architecture_principles={payload.get('architecture_principles', {}).get('matched_count')}"]
                    if isinstance(payload.get("architecture_principles"), dict)
                    and int(payload.get("architecture_principles", {}).get("matched_count", 0) or 0) > 0
                    else []
                ),
                *(
                    [f"local_overlay={payload.get('proof', {}).get('local_overlay', {}).get('active_count')}"]
                    if isinstance(payload.get("proof"), dict)
                    and isinstance(payload.get("proof", {}).get("local_overlay"), dict)
                    and payload.get("proof", {}).get("local_overlay", {}).get("status") == "active"
                    else []
                ),
                *(
                    [f"high_risk_overlay={payload.get('proof', {}).get('high_risk_overlay', {}).get('active_count')}"]
                    if isinstance(payload.get("proof"), dict)
                    and isinstance(payload.get("proof", {}).get("high_risk_overlay"), dict)
                    and payload.get("proof", {}).get("high_risk_overlay", {}).get("status") == "active"
                    else []
                ),
            ],
            advisory_selectors=advisory_selectors,
            agent_judgment="Agent owns semantic work shape and completion judgment after proof and acceptance reconciliation.",
        ),
        "next": {
            "action": next_action,
            "summary": next_action,
            "command": primary_command,
            "run": primary_command,
            "commands": proof_commands if isinstance(proof_commands, list) else [],
            "status": payload.get("orientation", {}).get("status", "unknown"),
            "ask_human_only_if": "blocked",
        },
        "decision_packet": decision_packet,
        "current_decision": current_decision,
        "message_economy": message_economy_payload(
            surface="implementation",
            communication_contract=communication_contract,
            state_delta_core=state_delta_core,
        ),
        "evidence_bundle": evidence_bundle_payload(
            surface="implementation",
            current_decision=current_decision,
            state_delta_core=state_delta_core,
        ),
        "proof": {
            "kind": payload.get("proof", {}).get("kind", "proof-selection/v1")
            if isinstance(payload.get("proof"), dict)
            else "proof-selection/v1",
            "required_commands": proof_commands,
            "tiny_surface_compatibility_review": payload.get("proof", {}).get("tiny_surface_compatibility_review", {})
            if isinstance(payload.get("proof"), dict)
            else {},
            "acceptance_guidance": payload.get("proof", {}).get("acceptance_guidance", {})
            if isinstance(payload.get("proof"), dict)
            else {},
            "generated_cli_freshness": tiny_generated_cli_freshness_payload(payload.get("proof", {}).get("generated_cli_freshness", {}))
            if isinstance(payload.get("proof"), dict) and isinstance(payload.get("proof", {}).get("generated_cli_freshness"), dict)
            else {},
            "runtime_source_edit_review": tiny_runtime_source_edit_review_payload(
                payload.get("proof", {}).get("runtime_source_edit_review", {})
            )
            if isinstance(payload.get("proof"), dict) and isinstance(payload.get("proof", {}).get("runtime_source_edit_review"), dict)
            else {},
            "runtime_symbol_working_set": tiny_runtime_symbol_working_set_payload(
                payload.get("proof", {}).get("runtime_symbol_working_set", {})
            )
            if isinstance(payload.get("proof"), dict) and isinstance(payload.get("proof", {}).get("runtime_symbol_working_set"), dict)
            else {},
            "proof_obligations": _tiny_proof_obligations_payload(
                payload.get("proof", {}).get("proof_obligations", {}), required_commands=proof_commands
            )
            if isinstance(payload.get("proof"), dict) and isinstance(payload.get("proof", {}).get("proof_obligations"), dict)
            else {},
            "proof_command_tiers": _tiny_proof_command_tiers_payload(
                payload.get("proof", {}).get("proof_command_tiers", {}), required_commands=proof_commands
            )
            if isinstance(payload.get("proof"), dict) and isinstance(payload.get("proof", {}).get("proof_command_tiers"), dict)
            else {},
            "proof_narrowness": _implement_tiny_proof_narrowness_payload(payload.get("proof", {}).get("proof_narrowness", {}))
            if isinstance(payload.get("proof"), dict)
            else {},
            "proof_route_maintenance": _tiny_proof_route_maintenance_payload(payload.get("proof", {}).get("proof_route_maintenance", {}))
            if isinstance(payload.get("proof"), dict)
            and isinstance(payload.get("proof", {}).get("proof_route_maintenance"), dict)
            and payload.get("proof", {}).get("proof_route_maintenance", {}).get("status") == "attention"
            else {},
            "local_overlay": {
                "status": payload.get("proof", {}).get("local_overlay", {}).get("status"),
                "active_count": payload.get("proof", {}).get("local_overlay", {}).get("active_count", 0),
                "detail_selector": "proof.local_overlay",
            }
            if isinstance(payload.get("proof"), dict)
            and isinstance(payload.get("proof", {}).get("local_overlay"), dict)
            and payload.get("proof", {}).get("local_overlay", {}).get("status") == "active"
            else {},
            "high_risk_overlay": {
                "status": payload.get("proof", {}).get("high_risk_overlay", {}).get("status"),
                "active_count": payload.get("proof", {}).get("high_risk_overlay", {}).get("active_count", 0),
                "detail_selector": "proof.high_risk_overlay",
            }
            if isinstance(payload.get("proof"), dict)
            and isinstance(payload.get("proof", {}).get("high_risk_overlay"), dict)
            and payload.get("proof", {}).get("high_risk_overlay", {}).get("status") == "active"
            else {},
            "detail_command": _command_with_cli_invoke(
                command="agentic-workspace proof --verbose --changed <paths> --format json", cli_invoke=config.cli_invoke
            ),
        },
        **(
            {"task_posture_packet": _compact_task_posture_packet_projection(payload["task_posture_packet"])}
            if isinstance(payload.get("task_posture_packet"), dict)
            else {}
        ),
        "memory_decision_packet": _compact_memory_decision_packet(payload.get("memory_decision_packet", {})),
        "operating_loop": payload.get("operating_loop", {}),
        "context": {
            "workflow_sufficiency": workflow_sufficiency,
            "adaptive_routing": _tiny_adaptive_routing_payload(
                surface="implement",
                current_need="changed-path-next-action" if payload.get("changed_paths") else "unknown-scope-routing",
                why_this_packet="Tiny implement returns one primary next action, with scoped proof and diagnostics behind context selectors.",
                detail_commands=detail_commands,
                when_to_escalate=[
                    "changed paths are missing or wrong",
                    "proof commands are insufficient",
                    "objective drift is warning",
                    "delegation or planning routing changes the next action",
                ],
                not_needed_now=[
                    "package boundary detail when there are no warnings",
                    "full execution posture unless delegation is selected",
                    "raw workspace files",
                ],
            ),
            "scope": {
                "changed_paths": payload.get("changed_paths", []),
                "inspect_files": payload.get("inspect_files", []),
                "warnings": path_warnings,
            },
            "task_intent": {
                "status": payload.get("task_intent", {}).get("status", "absent")
                if isinstance(payload.get("task_intent"), dict)
                else "absent",
                "requested_outcomes": payload.get("task_intent", {}).get("requested_outcomes", [])
                if isinstance(payload.get("task_intent"), dict)
                else [],
            },
            "intent_evidence": _compact_intent_evidence(payload.get("intent_evidence", {})),
            "parent_intent_status": {
                key: payload.get("parent_intent_status", {}).get(key)
                for key in (
                    "kind",
                    "status",
                    "original_intent",
                    "current_slice",
                    "proof_boundary",
                    "proof_is_slice_only",
                    "residual_parent_intent",
                    "continuation_owner",
                )
                if isinstance(payload.get("parent_intent_status"), dict) and key in payload.get("parent_intent_status", {})
            },
            "applicable_intent_status": {
                key: payload.get("applicable_intent_status", {}).get(key)
                for key in (
                    "kind",
                    "status",
                    "conflicts",
                    "missing_authority",
                    "manual_verification_needed",
                    "blocked_claims",
                    "closeout_blocked",
                )
                if isinstance(payload.get("applicable_intent_status"), dict) and key in payload.get("applicable_intent_status", {})
            },
            "acceptance": _tiny_acceptance_payload(payload.get("acceptance", {})),
            "acceptance_reconciliation": _tiny_acceptance_reconciliation(payload.get("acceptance_reconciliation", {})),
            "objective_drift": _tiny_objective_drift(payload.get("objective_drift", {})),
            "reuse_pressure": context_reuse_pressure,
            "optimization_posture": {
                "status": optimization_posture.get("status", "unavailable"),
                "effective_target": optimization_posture.get("effective_target", "unknown"),
                "configured_posture": "/".join(
                    str(optimization_posture.get("configured_posture", {}).get(key, ""))
                    for key in ("improvement_latitude", "optimization_bias")
                    if str(optimization_posture.get("configured_posture", {}).get(key, "")).strip()
                ),
                **(
                    {"audience_overrides": optimization_posture.get("audience_override_count", 0)}
                    if optimization_posture.get("audience_override_count", 0)
                    else {}
                ),
                **(
                    {"source_routed_paths": optimization_posture.get("source_routed_path_count", 0)}
                    if optimization_posture.get("source_routed_path_count", 0)
                    else {}
                ),
            },
            "generated_surface_trust": {
                "status": payload.get("generated_surface_trust", {}).get("status", "not-applicable")
                if isinstance(payload.get("generated_surface_trust"), dict)
                else "not-applicable",
                "changed_path_count": payload.get("generated_surface_trust", {}).get("changed_path_count", 0)
                if isinstance(payload.get("generated_surface_trust"), dict)
                else 0,
                "action_effect": _tiny_action_effect(
                    payload.get("generated_surface_trust", {}).get("action_effect", {}), include_allowed=False
                )
                if isinstance(payload.get("generated_surface_trust"), dict)
                else {},
                "detail_selector": "generated_surface_trust",
            },
            "architecture_principles": _architecture_principles_payload(
                target_root=target_root,
                changed_paths=payload.get("changed_paths", []) if isinstance(payload.get("changed_paths"), list) else [],
                cli_invoke=config.cli_invoke,
                compact=True,
            ),
            "durable_intent_promotion": _tiny_task_intent_promotion_guidance(payload.get("durable_intent_promotion", {})),
            "guidance": {
                "work_shape_guidance": _tiny_work_shape_guidance(planning_safety_gate.get("work_shape_guidance"))
                if isinstance(planning_safety_gate, dict)
                else None,
                "planning_safety": planning_safety_gate.get("status") if isinstance(planning_safety_gate, dict) else None,
                "rule": "AW exposes facts, blockers, and guidelines; the agent owns work-shape and proof proportionality judgment.",
            },
            **(
                {"delegation_decision": _compact_start_delegation_decision(delegation_decision, include_manual_handoff_detail=False)}
                if delegation_attention
                else {}
            ),
            "requirement_grounding": {
                "status": payload.get("requirement_grounding", {}).get("status", "not-applicable")
                if isinstance(payload.get("requirement_grounding"), dict)
                else "not-applicable",
                "requirement_ref_count": len(payload.get("requirement_grounding", {}).get("requirement_refs", []))
                if isinstance(payload.get("requirement_grounding"), dict)
                else 0,
                "known_gap_count": len(payload.get("requirement_grounding", {}).get("known_gaps", []))
                if isinstance(payload.get("requirement_grounding"), dict)
                else 0,
                "blocked_claims": payload.get("requirement_grounding", {}).get("closeout_claims", {}).get("blocked", [])
                if isinstance(payload.get("requirement_grounding"), dict)
                and isinstance(payload.get("requirement_grounding", {}).get("closeout_claims"), dict)
                else [],
                "detail_selector": "requirement_grounding",
            },
            "plan_delegation_packet": {
                "status": payload.get("plan_delegation_packet", {}).get("status", "unavailable")
                if isinstance(payload.get("plan_delegation_packet"), dict)
                else "unavailable",
                "delegation_ready": payload.get("plan_delegation_packet", {}).get("delegation_ready", False)
                if isinstance(payload.get("plan_delegation_packet"), dict)
                else False,
                "delegation_recommended": payload.get("plan_delegation_packet", {}).get("delegation_recommended", False)
                if isinstance(payload.get("plan_delegation_packet"), dict)
                else False,
                "recommended_route": payload.get("plan_delegation_packet", {}).get("recommended_route", "")
                if isinstance(payload.get("plan_delegation_packet"), dict)
                else "",
                "missing_fields": payload.get("plan_delegation_packet", {}).get("missing_fields", [])
                if isinstance(payload.get("plan_delegation_packet"), dict)
                else [],
                "ambiguous_fields": payload.get("plan_delegation_packet", {}).get("ambiguous_fields", [])
                if isinstance(payload.get("plan_delegation_packet"), dict)
                else [],
                "detail_selector": "plan_delegation_packet",
            },
            "test_strategy_check": {
                "status": test_strategy_check.get("status", "not-applicable"),
                "changed_test_paths": test_strategy_check.get("changed_test_paths", []),
                "hotspot_file_count": test_strategy_check.get("hotspot_file_count", 0),
                "scenario_matrix_candidate_count": test_strategy_check.get("scenario_matrix_candidate_count", 0),
                "budget_drift_status": _as_dict(test_strategy_check.get("budget_drift")).get("status", "not-applicable"),
                "changed_hotspot_files": _as_dict(test_strategy_check.get("budget_drift")).get("changed_hotspot_files", [])[:8],
                "pre_test_guardrail_status": _as_dict(test_strategy_check.get("pre_test_evidence_guardrail")).get(
                    "status", "not-applicable"
                ),
                "evidence_owner_options": test_strategy_check.get("evidence_owner_options", [])[:8],
                "pre_test_decision_questions": test_strategy_check.get("pre_test_decision_questions", [])[:3],
                "detail_selector": "test_strategy_check",
            },
        },
        "drill_down": {
            "ordinary_profile": "primary=next;proof=summary;context=selector-backed diagnostics",
            "detail_command": detail_commands["full_context"],
            "detail_commands": detail_commands,
            "available_selectors": [
                "next",
                "operating_loop",
                "proof",
                "context.scope",
                "context.workflow_sufficiency",
                "context.acceptance",
                "context.intent_evidence",
                "active_intent_contract",
                "intent_satisfaction_matrix",
                "context.parent_intent_status",
                "context.applicable_intent_status",
                "context.acceptance_reconciliation",
                "context.objective_drift",
                "context.reuse_pressure",
                "reuse_pressure",
                "task_contract",
                "change_impact",
                "generated_surface_trust",
                "proof.runtime_source_edit_review",
                "proof.runtime_symbol_working_set",
                "architecture_principles",
                "assurance_requirements",
                "verification",
                "routine_work_context",
                "context.delegation_decision",
                "context.guidance",
                "context.requirement_grounding",
                "context.plan_delegation_packet",
                "context.test_strategy_check",
                "requirement_grounding",
                "plan_delegation_packet",
                "test_strategy_check",
            ],
        },
    }

    def remove_available_selector(selector: str) -> None:
        drill_down = projected.get("drill_down", {})
        if not isinstance(drill_down, dict):
            return
        drill_down = cast(dict[str, Any], drill_down)
        selectors = drill_down.get("available_selectors", [])
        if isinstance(selectors, list):
            drill_down["available_selectors"] = [item for item in selectors if item != selector]

    if not delegation_attention:
        remove_available_selector("context.delegation_decision")
    if not test_strategy_applicable:
        tiny_context_for_test_strategy = projected.get("context", {})
        if isinstance(tiny_context_for_test_strategy, dict):
            tiny_context_for_test_strategy.pop("test_strategy_check", None)
        remove_available_selector("context.test_strategy_check")
        remove_available_selector("test_strategy_check")
    if isinstance(payload.get("generated_surface_trust"), dict) and payload["generated_surface_trust"].get("status") == "present":
        tiny_context = projected.get("context", {})
        if isinstance(tiny_context, dict):
            tiny_context.pop("active_intent_contract", None)
            tiny_context.pop("intent_satisfaction_matrix", None)
        remove_available_selector("context.active_intent_contract")
        remove_available_selector("context.intent_satisfaction_matrix")
    tiny_context = projected.get("context", {})
    if isinstance(tiny_context, dict):
        absence_states = {
            **_as_dict(tiny_context.get("absence_states")),
            "adaptive_routing": "detail_omitted",
            "architecture_principles": "hidden_behind_detail_route",
            "work_shape_guidance": "detail_omitted",
        }
        tiny_context["absence_states"] = absence_states
        tiny_context.pop("adaptive_routing", None)
        tiny_context.pop("guidance", None)
        parent_packet = tiny_context.get("parent_intent_status", {})
        parent_status = str(parent_packet.get("status") or "").strip() if isinstance(parent_packet, dict) else ""
        if parent_status in {"", "guidance-only", "not-recorded", "needs-planning"}:
            tiny_context.pop("parent_intent_status", None)
            remove_available_selector("context.parent_intent_status")
        applicable_packet = tiny_context.get("applicable_intent_status", {})
        applicable_status = str(applicable_packet.get("status") or "").strip() if isinstance(applicable_packet, dict) else ""
        if applicable_status in {"", "guidance-only", "not-recorded"}:
            tiny_context.pop("applicable_intent_status", None)
            remove_available_selector("context.applicable_intent_status")
        architecture_packet = tiny_context.get("architecture_principles", {})
        architecture_matches = _as_int(architecture_packet.get("matched_count")) if isinstance(architecture_packet, dict) else 0
        if architecture_matches <= 0:
            tiny_context.pop("architecture_principles", None)
            remove_available_selector("architecture_principles")
            action_signals = projected.get("action_signals", {})
            if isinstance(action_signals, dict):
                advisory_detail = action_signals.get("advisory_detail", {})
                if isinstance(advisory_detail, dict):
                    advisory_detail = cast(dict[str, Any], advisory_detail)
                    advisory_selectors = advisory_detail.get("selectors", [])
                    if isinstance(advisory_selectors, list):
                        advisory_detail["selectors"] = [item for item in advisory_selectors if item != "architecture_principles"]
        else:
            absence_states["architecture_principles"] = "present"
    generated_surface_trust = payload.get("generated_surface_trust", {})
    if isinstance(generated_surface_trust, dict) and generated_surface_trust.get("status") == "present":
        projected["generated_surface_trust"] = _tiny_generated_surface_trust(generated_surface_trust)
    assurance_requirements = payload.get("assurance_requirements", {})
    if isinstance(assurance_requirements, dict) and int(assurance_requirements.get("active_count", 0) or 0) > 0:
        projected["assurance_requirements"] = _compact_assurance_requirements(assurance_requirements)
    compatibility_review = projected["proof"].get("tiny_surface_compatibility_review", {})
    if not (isinstance(compatibility_review, dict) and compatibility_review.get("status") == "required"):
        projected["proof"].pop("tiny_surface_compatibility_review", None)
    generated_cli_freshness = projected["proof"].get("generated_cli_freshness", {})
    if not (isinstance(generated_cli_freshness, dict) and generated_cli_freshness.get("kind")):
        projected["proof"].pop("generated_cli_freshness", None)
    proof_narrowness = projected["proof"].get("proof_narrowness", {})
    if not (isinstance(proof_narrowness, dict) and proof_narrowness.get("status")):
        projected["proof"].pop("proof_narrowness", None)
    runtime_source_review = projected["proof"].get("runtime_source_edit_review", {})
    if not (
        isinstance(runtime_source_review, dict)
        and runtime_source_review.get("changed_paths")
        and runtime_source_review.get("status") != "not-applicable"
    ):
        projected["proof"].pop("runtime_source_edit_review", None)
        remove_available_selector("proof.runtime_source_edit_review")
    runtime_symbol_working_set = projected["proof"].get("runtime_symbol_working_set", {})
    if not (
        isinstance(runtime_symbol_working_set, dict)
        and runtime_symbol_working_set.get("status") == "present"
        and runtime_symbol_working_set.get("files")
    ):
        projected["proof"].pop("runtime_symbol_working_set", None)
        remove_available_selector("proof.runtime_symbol_working_set")
    task_argument_mode = payload.get("task_intent", {}).get("task_argument_mode") if isinstance(payload.get("task_intent"), dict) else ""
    intent_proof = payload.get("proof", {}).get("intent_proof") if isinstance(payload.get("proof"), dict) else None
    acceptance_reconciliation = payload.get("acceptance_reconciliation", {})
    requested_outcomes = acceptance_reconciliation.get("requested_outcomes", []) if isinstance(acceptance_reconciliation, dict) else []
    if (task_argument_mode == "task-file" or requested_outcomes) and intent_proof:
        projected["proof"]["intent_proof"] = intent_proof
    if isinstance(planning_safety_gate, dict):
        compact_gate = _selector_first_planning_safety_gate(planning_safety_gate)
        authoritative_route = _as_dict(planning_safety_gate.get("route_decision"))
        if authoritative_route.get("kind") == "agentic-planning/route-decision/v1":
            compact_gate["route_decision"] = {
                key: authoritative_route.get(key)
                for key in (
                    "task_relation",
                    "owner_posture",
                    "required_transition",
                    "allowed_claims",
                    "blocked_claims",
                    "implementation_allowed",
                    "mutation_authority",
                    "proof_expectation",
                    "state_update_policy",
                    "next_safe_action",
                )
                if authoritative_route.get(key) not in (None, "", [], {})
            }
        compact_gate.pop("planning_revision", None)
        compact_gate.pop("work_shape_guidance", None)
        if compact_gate.get("status") in {"clear", "satisfied"}:
            active_plan_reliance = _as_dict(compact_gate.get("active_plan_reliance"))
            candidate_pressure = _as_dict(compact_gate.get("candidate_pressure"))
            custody_planning = _as_dict(compact_gate.get("custody_planning"))
            issue_scope_evidence = _as_dict(compact_gate.get("issue_scope_evidence"))
            route_decision = _as_dict(compact_gate.get("route_decision"))
            keep_active_plan_reliance = active_plan_reliance.get("permission_claim") != "direct-work-no-active-plan" and not route_decision
            changed_path_facts = _as_dict(compact_gate.get("changed_path_facts"))
            compact_changed_path_facts = {
                key: changed_path_facts.get(key)
                for key in (
                    "dirty_shape",
                    "surface_roots",
                    "surface_root_count",
                    "scope_growth_detected",
                    "scope_growth_reasons",
                    "archived_planning_residue",
                )
                if key in changed_path_facts
            }
            compact_gate = {
                key: compact_gate.get(key)
                for key in (
                    "kind",
                    "label",
                    "provenance",
                    "status",
                    "gate_result",
                    "workflow_sufficient",
                    "required_next_action",
                    "implementation_allowed",
                    "delegation_decision_required",
                    "custody_planning",
                    "route_decision",
                    "detail_selector",
                )
                if key in compact_gate
            }
            if not custody_planning:
                compact_gate.pop("custody_planning", None)
            if not route_decision:
                compact_gate.pop("route_decision", None)
            if compact_changed_path_facts:
                compact_gate["changed_path_facts"] = compact_changed_path_facts
            if candidate_pressure.get("status") == "observed":
                compact_gate["candidate_pressure"] = candidate_pressure
                if issue_scope_evidence:
                    compact_gate["issue_scope_evidence"] = issue_scope_evidence
            if keep_active_plan_reliance:
                compact_gate["active_plan_reliance"] = active_plan_reliance
        if (
            compact_gate.get("status") in {"clear", "satisfied"}
            and _as_dict(compact_gate.get("candidate_pressure")).get("status") != "observed"
        ):
            compact_gate.pop("candidate_pressure", None)
            compact_gate.pop("issue_scope_evidence", None)
        if not (
            isinstance(generated_surface_trust, dict)
            and generated_surface_trust.get("status") == "present"
            and compact_gate.get("status") in {"clear", "satisfied"}
        ):
            projected["context"]["planning_safety_gate"] = compact_gate
    if isinstance(intent_acknowledgement, dict) and intent_acknowledgement.get("decision") == "proceed-with-stated-assumption":
        projected["context"]["intent_acknowledgement"] = {
            "decision": intent_acknowledgement.get("decision"),
            "fields": intent_acknowledgement.get("before_editing", []),
            "proceed_unless_corrected": True,
            "clarify_only_if_blocked": True,
        }
    return projected
