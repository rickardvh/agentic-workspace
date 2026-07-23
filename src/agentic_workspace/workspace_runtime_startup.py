"""Startup runtime packet builders for Agentic Workspace.

This module owns start/startup payload construction while the old monolith keeps
compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from agentic_workspace.config import DEFAULT_CLI_INVOKE, WORKSPACE_CONFIG_PATH, WORKSPACE_LOCAL_CONFIG_PATH, WorkspaceConfig
from agentic_workspace.current_work_context import startup_route_identity
from agentic_workspace.reporting_support import (
    communication_contract_payload,
    compact_communication_contract_payload,
    continuation_capsule_payload,
    current_decision_payload,
    evidence_bundle_payload,
    message_economy_payload,
    state_delta_core_payload,
)
from agentic_workspace.workspace_runtime_core import (
    _CONTEXT_TEMPLATES,
    _active_intent_contract_payload,
    _active_plan_touched_scope_paths,
    _applicable_intent_status_payload,
    _apply_lane_shaping_gate_to_start_payload,
    _architecture_principles_forecast_payload,
    _assurance_requirements_report_payload,
    _attach_start_router_fields,
    _authority_markers_for_startup,
    _available_selectors_for_payload,
    _boundary_warning_for_path,
    _cli_compatibility_payload,
    _cli_invocation_payload,
    _compact_action_signals_payload,
    _compact_assurance_requirements,
    _compact_continuation_state_contract,
    _compact_installed_state_drift_triage,
    _compact_intent_evidence,
    _compact_repair_plan_profile,
    _compact_repo_posture_projection,
    _compact_selector_next_safe_action,
    _compact_start_closeout_obligations,
    _compact_start_delegation_decision,
    _compact_start_local_footprint_advisory,
    _compact_start_prep_only_handoff,
    _compact_start_proof_payload,
    _compact_start_workflow_obligations,
    _compact_startup_installed_state_signal,
    _compact_task_posture_packet_projection,
    _completion_boundary_payload,
    _completion_closeout_inspection_payload,
    _context_router_family_payload,
    _continuation_reorientation_payload,
    _emit_payload,
    _execution_posture_payload,
    _fast_installed_modules,
    _fast_planning_active_summary,
    _feature_tier_payload,
    _guidance_with_cli_invoke,
    _installed_state_compatibility_payload,
    _installed_state_drift_triage_payload,
    _intent_acknowledgement_payload,
    _intent_custody_payload,
    _intent_decision_projection,
    _intent_discovery_dialogue_payload,
    _intent_elicitation_protocol_payload,
    _intent_satisfaction_matrix_payload,
    _invoked_cli_identity_payload,
    _is_config_posture_task,
    _is_prep_only_handoff_task,
    _issue_reference_intent_payload,
    _load_workspace_config,
    _local_chat_checkpoint_projection,
    _local_footprint_payload,
    _local_work_threads_default_visible,
    _local_work_threads_projection,
    _maintainer_mode_payload,
    _memory_consult_from_payload,
    _memory_consult_payload,
    _memory_decision_packet_payload,
    _module_operations,
    _module_registry,
    _next_safe_action_packet,
    _open_issue_intake_payload,
    _operating_posture_payload,
    _ordinary_decision_packet,
    _package_boundary_payload,
    _parent_intent_status_payload,
    _pre_test_evidence_guardrail_payload,
    _prep_only_handoff_payload,
    _read_only_response_posture_payload,
    _repo_posture_payload,
    _resolve_target_root,
    _routine_work_context_payload,
    _run_preflight_command,
    _select_payload_fields,
    _selector_first_planning_safety_gate,
    _selector_prevalidation_error,
    _selector_requests,
    _session_improvement_pressure_payload,
    _sibling_repo_aw_freshness_payload,
    _start_profile_for_select,
    _start_tiny_payload_fast,
    _startup_closeout_report_route,
    _startup_continuation_view_payload,
    _startup_skill_routing_payload,
    _startup_skills_projection,
    _task_intent_carry_forward_payload,
    _task_intent_evidence_payload,
    _task_mentioned_existing_paths,
    _task_path_reference_payload,
    _task_posture_packet_changes_routing,
    _task_posture_packet_payload,
    _task_posture_packet_relevant,
    _tiny_acceptance_payload,
    _tiny_adaptive_routing_payload,
    _tiny_durable_intent,
    _tiny_required_proof_commands,
    _tiny_task_intent_promotion_guidance,
    _tiny_workflow_sufficiency,
    _uv_cache_guidance_payload,
    _vague_outcome_orientation_payload,
    _validate_target_root,
    _workflow_sufficiency_payload,
    _workspace_absence_startup_review,
    _workspace_disabled_payload,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _command_with_cli_invoke,
    _list_payload,
    _normalize_changed_paths,
)
from agentic_workspace.workspace_runtime_planning import (
    _active_planning_record_for_report_section,
    _planning_safety_gate_payload,
    _raw_active_planning_record_for_closeout,
)
from agentic_workspace.workspace_runtime_projection import _workflow_participation_payload
from agentic_workspace.workspace_runtime_proof import (
    _proof_selection_for_changed_paths,
)
from agentic_workspace.workspace_selector_validation import _selector_inventory_selected_payload


def _startup_route_binding(*, route_decision: dict[str, Any], target_root: Path, task_text: str | None, cli_invoke: str) -> dict[str, Any]:
    """Describe whether startup's read-only route forecast can be relied on yet."""
    transition = str(route_decision.get("required_transition") or "none")
    identity_effects = [str(effect) for effect in _list_payload(route_decision.get("identity_effects")) if str(effect).strip()]
    provisional = transition != "none" or bool(identity_effects)
    identity = startup_route_identity(root=target_root, task=str(task_text or ""))
    selected_identity = _as_dict(route_decision.get("selected_owner_identity"))
    selected_ref = str(selected_identity.get("ref") or route_decision.get("selected_owner") or "").strip()
    if selected_ref:
        observed = _as_dict(identity.get("observed"))
        observed["selected_owner"] = {"id": str(selected_identity.get("id") or ""), "ref": selected_ref}
        identity["observed"] = observed
        identity["fingerprint"] = hashlib.sha256(json.dumps(observed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
    rebind_command = _command_with_cli_invoke(
        command="agentic-workspace start --target . --task <same-task> --format json",
        cli_invoke=cli_invoke,
    )
    return {
        "status": "provisional" if provisional else "bound",
        "state_commit": "none",
        "rule": "Startup projects a route only; it never commits selection or carry state before an explicit transition is used.",
        "invalidate_when": ["branch", "head", "worktree", "target", "current-work", "selected-owner"],
        "identity": identity,
        "adoption_guard": {
            "status": "required",
            "expected_fingerprint": identity["fingerprint"],
            "comparison_fields": identity["comparison_fields"],
            "on_mismatch": "reject-stale-projection-and-re-resolve",
            "rebind_command": rebind_command,
            "enforced_before": ["route-adoption", "planning-mutation"],
        },
        "reason": "structured-identity-transition"
        if identity_effects
        else "transition-required"
        if provisional
        else "current-identity-observed",
    }


def _compact_start_route_decision(value: Any) -> dict[str, Any]:
    route = _as_dict(value)
    if route.get("kind") != "agentic-planning/route-decision/v1":
        return {}
    compact = {
        key: copy.deepcopy(route[key])
        for key in (
            "kind",
            "task_relation",
            "owner_posture",
            "required_transition",
            "selected_owner",
            "selected_owner_identity",
            "owner_admission",
            "allowed_claims",
            "blocked_claims",
            "implementation_allowed",
            "mutation_authority",
            "proof_expectation",
            "state_update_policy",
            "reconciliation_proposal",
            "next_safe_action",
            "binding",
        )
        if route.get(key) not in (None, "", [], {})
    }
    selected_identity = _as_dict(compact.get("selected_owner_identity"))
    if selected_identity and not selected_identity.get("ref"):
        compact.pop("selected_owner_identity", None)
    binding = _as_dict(compact.get("binding"))
    identity = _as_dict(binding.get("identity"))
    guard = _as_dict(binding.get("adoption_guard"))
    if identity or guard:
        compact["binding"] = {
            key: copy.deepcopy(binding[key]) for key in ("status", "state_commit", "reason") if binding.get(key) not in (None, "", [], {})
        }
        if identity.get("fingerprint"):
            compact["binding"]["identity"] = {"fingerprint": identity["fingerprint"]}
        if guard:
            compact["binding"]["adoption_guard"] = {
                key: copy.deepcopy(guard[key])
                for key in ("status", "expected_fingerprint", "on_mismatch")
                if guard.get(key) not in (None, "", [], {})
            }
    return compact


def _tiny_start_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Project startup context to the smallest schema-compatible first-contact answer."""
    immediate = copy.deepcopy(payload["immediate_next_allowed_action"])
    if (
        immediate.get("action") not in {"ask-intent-discovery-question", "present-lane-shaping-prompt"}
        and not immediate.get("command")
        and (not immediate.get("read_first"))
    ):
        immediate["required_inputs"] = []
        immediate["next_proof"] = "select proof after changed paths are known"
    skill_routing = payload.get("skill_routing", {})
    preferred_routes = [
        {"fit_signal": str(item.get("fit_signal", item.get("task_shape", ""))), "skill": str(item.get("skill", ""))}
        for item in (skill_routing.get("preferred_routes", []) if isinstance(skill_routing, dict) else [])[:2]
        if isinstance(item, dict)
    ]
    task_intent = payload.get("task_intent", {})
    detail_commands = {
        "known_changed_paths": "agentic-workspace implement --changed <paths> --format json",
        "active_state": "agentic-workspace summary --format json",
        "task_scoped_state": "agentic-workspace summary --task <task> --format json",
        "takeover_or_recovery": "agentic-workspace preflight --format json",
        "startup_reference": "agentic-workspace defaults --section startup --format json",
    }
    if isinstance(task_intent, dict) and task_intent.get("implement_changed_command"):
        detail_commands["known_changed_paths"] = "Use task_intent.implement_changed_command after changed paths are known."
    feature_tier = payload.get("feature_tier", {})
    active_tier = feature_tier.get("active", {}) if isinstance(feature_tier, dict) else {}
    compact_active_tier = {
        key: active_tier.get(key) for key in ("id", "modules", "preset", "source") if isinstance(active_tier, dict) and key in active_tier
    }
    identity = payload.get("invoked_cli_identity", {})
    compact_identity = {
        key: identity.get(key)
        for key in ("kind", "package", "version", "source_class", "module_path", "target_relation", "compatibility")
        if isinstance(identity, dict) and key in identity
    }
    read_only_response = payload.get("read_only_response", {})
    read_only_compact_default = bool(isinstance(read_only_response, dict) and read_only_response.get("compact_default") is True)
    projected = {
        "kind": payload["kind"],
        "target": ".",
        "adaptive_routing": _tiny_adaptive_routing_payload(
            surface="start",
            current_need=payload.get("adaptive_routing", {}).get("current_need", "first-contact-routing"),
            why_this_packet=payload.get("adaptive_routing", {}).get(
                "why_this_packet",
                "Tiny startup returns only identity, next action, active-state summary, obligations, and direct detail commands.",
            ),
            detail_commands=detail_commands,
            when_to_escalate=[
                "changed paths are known",
                "active planning or handoff state matters",
                "takeover or recovery is needed",
                "config or proof selection becomes the question",
            ],
            not_needed_now=["raw planning files", "full summary", "historical audit detail", "full memory tree"],
        ),
        "invoked_cli_identity": compact_identity,
        "cli_invocation": payload.get("cli_invocation", {}),
        "startup_sequence": payload["startup_sequence"][:1],
        "context_router": {
            "kind": "workspace-context-router-family/v1",
            "first_view": "start",
            "rule": "This tiny profile is the first-contact answer; run detail commands only when the next action says why.",
            "detail_commands": detail_commands,
        },
        "communication_contract": compact_communication_contract_payload(surface="startup"),
        "feature_tier": {
            "active": compact_active_tier,
            "detail_command": feature_tier.get("detail_command", "agentic-workspace modules --target ./repo --format json")
            if isinstance(feature_tier, dict)
            else "agentic-workspace modules --target ./repo --format json",
        },
        "active_state_summary": payload["active_state_summary"],
        "planning_revision": payload.get("planning_revision", {}),
        "active_plan_reliance": payload.get("active_plan_reliance", {}),
        **({"route_decision": _compact_start_route_decision(payload.get("route_decision"))} if payload.get("route_decision") else {}),
        "workflow_sufficiency": payload.get("workflow_sufficiency"),
        **({"planning_safety_gate": payload["planning_safety_gate"]} if "planning_safety_gate" in payload else {}),
        **({"lane_shaping_gate": payload["lane_shaping_gate"]} if "lane_shaping_gate" in payload else {}),
        "package_boundary": payload["package_boundary"],
        "authority_markers": payload["authority_markers"][:1],
        "immediate_next_allowed_action": immediate,
        "workflow_obligations": {
            "status": payload.get("workflow_obligations", {}).get("status", "unknown"),
            "match_count": payload.get("workflow_obligations", {}).get("match_count", 0),
            "detail_command": payload.get("workflow_obligations", {}).get("detail_command", "agentic-workspace preflight --format json"),
        },
        "closeout_obligations": {
            "status": payload.get("closeout_obligations", {}).get("status", "unknown"),
            "activation_rule": payload.get("closeout_obligations", {}).get(
                "activation_rule",
                "closeout obligations apply after implementation or lane closeout, not ordinary first-contact orientation",
            ),
            "detail_command": payload.get("closeout_obligations", {}).get(
                "detail_command", "agentic-workspace report --target ./repo --section closeout_trust --format json"
            ),
            "ordinary_closeout_route": payload.get("closeout_obligations", {}).get("ordinary_closeout_route", {}),
        },
        "memory_consult": {
            "status": payload.get("memory_consult", {}).get("status", "unknown"),
            "read_first": payload.get("memory_consult", {}).get("read_first", []),
            "do_not_bulk_read": payload.get("memory_consult", {}).get("do_not_bulk_read", True),
        },
        **(
            {"local_chat_checkpoint": payload["local_chat_checkpoint"]}
            if isinstance(payload.get("local_chat_checkpoint"), dict)
            and _local_chat_checkpoint_default_visible(payload["local_chat_checkpoint"], payload=payload)
            else {}
        ),
        "memory_decision_packet": payload.get("memory_decision_packet", {}),
        **({"continuation_view": payload["continuation_view"]} if isinstance(payload.get("continuation_view"), dict) else {}),
        **(
            {"continuation_reorientation": payload["continuation_reorientation"]}
            if isinstance(payload.get("continuation_reorientation"), dict)
            and payload["continuation_reorientation"].get("status") == "required"
            else {}
        ),
        **({"routine_work_context": payload.get("routine_work_context", {})} if not read_only_compact_default else {}),
        "operating_posture": {
            "status": payload.get("operating_posture", {}).get("status", "unknown"),
            "required_behavior_summary": payload.get("operating_posture", {}).get("required_behavior_summary", ""),
        },
        "repo_posture": _compact_repo_posture_projection(payload.get("repo_posture", {})),
        "delegation_decision": _compact_start_delegation_decision(payload.get("delegation_decision", {})),
        **({"task_path_references": payload["task_path_references"]} if isinstance(payload.get("task_path_references"), dict) else {}),
        **(
            {"architecture_principles_forecast": payload["architecture_principles_forecast"]}
            if isinstance(payload.get("architecture_principles_forecast"), dict)
            else {}
        ),
        **(
            {"decision_point_intent_carry": payload["decision_point_intent_carry"]}
            if isinstance(payload.get("decision_point_intent_carry"), dict)
            else {}
        ),
        **({"pre_test_evidence_guardrail": payload["pre_test_evidence_guardrail"]} if "pre_test_evidence_guardrail" in payload else {}),
        **({"pr_comment_attention": payload["pr_comment_attention"]} if isinstance(payload.get("pr_comment_attention"), dict) else {}),
        **(
            {"dogfooding_signal_status": payload["dogfooding_signal_status"]}
            if isinstance(payload.get("dogfooding_signal_status"), dict)
            else {}
        ),
        "skill_routing": {
            "status": skill_routing.get("status", "unknown") if isinstance(skill_routing, dict) else "unknown",
            "rule": "Use listed skills only when directly relevant; otherwise proceed from the next action.",
            "query": skill_routing.get("query", 'agentic-workspace skills --target ./repo --task "<task>" --format json')
            if isinstance(skill_routing, dict)
            else 'agentic-workspace skills --target ./repo --task "<task>" --format json',
            "preferred_routes": preferred_routes,
            **({"task_search": skill_routing["task_search"]} if isinstance(skill_routing, dict) and "task_search" in skill_routing else {}),
        },
    }
    if isinstance(payload.get("parent_intent_status"), dict):
        projected["parent_intent_status"] = {
            key: payload["parent_intent_status"].get(key)
            for key in (
                "status",
                "original_intent",
                "current_slice",
                "proof_boundary",
                "proof_is_slice_only",
                "residual_parent_intent",
                "parent_proof_required",
            )
            if key in payload["parent_intent_status"]
        }
    if isinstance(payload.get("applicable_intent_status"), dict):
        projected["applicable_intent_status"] = {
            key: payload["applicable_intent_status"].get(key)
            for key in (
                "status",
                "conflicts",
                "missing_authority",
                "manual_verification_needed",
                "blocked_claims",
                "closeout_blocked",
            )
            if key in payload["applicable_intent_status"]
        }
    task_posture_packet = payload.get("task_posture_packet", {})
    if isinstance(task_posture_packet, dict) and task_posture_packet:
        projected["task_posture_packet"] = _compact_task_posture_packet_projection(task_posture_packet)
    assurance_requirements = payload.get("assurance_requirements", {})
    if isinstance(assurance_requirements, dict) and int(assurance_requirements.get("active_count", 0) or 0) > 0:
        projected["assurance_requirements"] = _compact_assurance_requirements(assurance_requirements)
    proof = payload.get("proof", {})
    if isinstance(proof, dict) and proof.get("kind") == "proof-selection/v1":
        projected["proof"] = _compact_start_proof_payload(proof)
        immediate["next_proof"] = "run the selected required validation commands before closeout"
    repair_profile = payload.get("repair_plan_profile", {})
    if isinstance(repair_profile, dict) and repair_profile.get("status") == "direct-no-plan":
        projected["repair_plan_profile"] = repair_profile
    cli_compatibility = payload.get("cli_compatibility", {})
    if isinstance(cli_compatibility, dict) and cli_compatibility.get("status") in {
        "advisory-drift",
        "blocking-drift",
        "warning-drift",
    }:
        projected["cli_compatibility"] = cli_compatibility
    installed_state = payload.get("installed_state_compatibility", {})
    if isinstance(installed_state, dict) and installed_state.get("status") not in {None, "", "compatible"}:
        projected["installed_state_compatibility"] = _compact_startup_installed_state_signal(installed_state)
    installed_state_triage = payload.get("installed_state_drift_triage", {})
    if isinstance(installed_state_triage, dict) and installed_state_triage.get("status") not in {None, "", "not_applicable"}:
        projected["installed_state_drift_triage"] = _compact_installed_state_drift_triage(installed_state_triage)
    sibling_freshness = payload.get("sibling_repo_aw_freshness", {})
    if isinstance(sibling_freshness, dict) and sibling_freshness.get("status") not in {None, "", "not-referenced"}:
        projected["sibling_repo_aw_freshness"] = sibling_freshness
    maintainer_mode = payload.get("maintainer_mode", {})
    if isinstance(maintainer_mode, dict) and maintainer_mode.get("status") == "enabled":
        primary_next_action = maintainer_mode.get("primary_next_action", {})
        projected["maintainer_mode"] = {
            "kind": maintainer_mode.get("kind"),
            "status": maintainer_mode.get("status"),
            "source": maintainer_mode.get("source"),
            "config_field": maintainer_mode.get("config_field"),
            "dogfooding_reports": [
                {key: route.get(key) for key in ("section", "command") if isinstance(route, dict) and key in route}
                for route in maintainer_mode.get("dogfooding_reports", [])[:3]
                if isinstance(route, dict)
            ],
            "primary_next_action": {
                key: primary_next_action.get(key)
                for key in ("action", "summary", "command", "risk")
                if isinstance(primary_next_action, dict) and key in primary_next_action
            },
        }
    closeout_inspection = payload.get("closeout_trust_inspection", {})
    if isinstance(closeout_inspection, dict) and closeout_inspection.get("status") in {"required", "clear"}:
        projected["closeout_trust_inspection"] = closeout_inspection
        projected["closeout_report_route"] = _startup_closeout_report_route(closeout_inspection)
    vague_orientation = payload.get("vague_outcome_orientation", {})
    if isinstance(vague_orientation, dict) and vague_orientation.get("applies_to_current_task") is True:
        if isinstance(task_intent, dict) and task_intent.get("task_argument_mode") == "task-file":
            projected["vague_outcome_orientation"] = {
                "status": vague_orientation.get("status", "applicable"),
                "applies_to_current_task": True,
                "answer_contract": ["state intent/slice/non-goals; proceed unless corrected"],
                "raw_read_rule": vague_orientation.get("raw_read_rule", ""),
            }
        else:
            projected["vague_outcome_orientation"] = vague_orientation
    intent_discovery = payload.get("intent_discovery_dialogue", {})
    if isinstance(intent_discovery, dict) and intent_discovery.get("applies_to_current_task") is True:
        projected["intent_discovery_dialogue"] = {
            "kind": intent_discovery.get("kind", "agentic-workspace/intent-discovery-dialogue/v1"),
            "status": intent_discovery.get("status"),
            "skill": intent_discovery.get("skill"),
            "inferred_intent_confidence": intent_discovery.get("inferred_intent_confidence"),
            "stakes_if_wrong": intent_discovery.get("stakes_if_wrong"),
            "required_next_action": intent_discovery.get("required_next_action"),
            "candidate_interpretations": intent_discovery.get("candidate_interpretations", [])[:3],
            "dialogue_packet": intent_discovery.get("dialogue_packet", {}),
            "output_shape": intent_discovery.get("output_shape", {}),
            "loop_control": intent_discovery.get("loop_control", {}),
            "visible_residue_when_proceeding_without_answer": intent_discovery.get("visible_residue_when_proceeding_without_answer", []),
            "examples": intent_discovery.get("examples", []),
        }
    intent_acknowledgement = payload.get("intent_acknowledgement", {})
    if (
        isinstance(intent_acknowledgement, dict)
        and intent_acknowledgement.get("decision") == "proceed-with-stated-assumption"
        and (not (isinstance(task_intent, dict) and task_intent.get("task_argument_mode") == "task-file"))
    ):
        projected["intent_acknowledgement"] = {
            "decision": intent_acknowledgement.get("decision"),
            "fields": intent_acknowledgement.get("before_editing", []),
            "proceed_unless_corrected": True,
            "clarify_only_if_blocked": True,
        }
    durable_intent = payload.get("durable_intent", {})
    subsystem_intent = durable_intent.get("subsystem_intent", {}) if isinstance(durable_intent, dict) else {}
    matched_count = int(subsystem_intent.get("matched_count", 0) or 0) if isinstance(subsystem_intent, dict) else 0
    if isinstance(durable_intent, dict) and durable_intent.get("status") == "present" and matched_count:
        projected["durable_intent"] = _tiny_durable_intent(durable_intent)
    if "intent_evidence" in payload:
        projected["intent_evidence"] = _compact_intent_evidence(payload.get("intent_evidence", {}))
    if "issue_reference_intent" in payload:
        projected["issue_reference_intent"] = payload["issue_reference_intent"]
    if "open_issue_intake" in payload:
        projected["open_issue_intake"] = payload["open_issue_intake"]
    if isinstance(task_intent, dict) and task_intent.get("status") == "present":
        acceptance = task_intent.get("acceptance", {})
        read_only_response = payload.get("read_only_response", {})
        read_only_compact_default = bool(isinstance(read_only_response, dict) and read_only_response.get("compact_default") is True)
        projected["task_intent"] = {
            "status": "present",
            "carry_forward_rule": task_intent.get("carry_forward_rule", ""),
            "requested_outcomes": task_intent.get("requested_outcomes", [])[:8],
            "implement_changed_command": task_intent.get("implement_changed_command"),
        }
        if read_only_compact_default:
            projected["task_intent"]["response_posture"] = read_only_response
            projected["read_only_response"] = read_only_response
        else:
            projected["task_intent"]["acceptance"] = _tiny_acceptance_payload(acceptance)
            projected["acceptance"] = _tiny_acceptance_payload(acceptance)
        if isinstance(task_intent.get("promotion_guidance"), dict):
            projected["durable_intent_promotion"] = _tiny_task_intent_promotion_guidance(task_intent["promotion_guidance"])
        for optional_key in ("task_argument_mode", "task_file", "task_file_instruction", "task_excerpt", "task_digest", "task_text_length"):
            if optional_key in task_intent:
                projected["task_intent"][optional_key] = task_intent[optional_key]
    startup_review = payload.get("startup_review", {})
    if isinstance(startup_review, dict) and startup_review.get("status") == "attention":
        projected["startup_review"] = startup_review
    if "prep_only_handoff" in payload:
        projected["prep_only_handoff"] = _compact_start_prep_only_handoff(payload["prep_only_handoff"])
    projected["next_safe_action"] = _next_safe_action_packet(
        immediate=immediate,
        workflow_sufficiency=payload.get("workflow_sufficiency"),
        skill_routing=payload.get("skill_routing"),
        memory_consult=payload.get("memory_consult"),
    )
    local_footprint = payload.get("local_footprint", {})
    local_footprint_attention = isinstance(local_footprint, dict) and local_footprint.get("status") == "attention"
    if local_footprint_attention:
        projected["local_footprint"] = local_footprint
    projected["action_signals"] = _compact_action_signals_payload(
        surface="start",
        allowed_next_action=str(projected["next_safe_action"].get("next_safe_action", "")),
        hard_blockers=projected["next_safe_action"].get("closure_blockers", []),
        implementation_allowed=bool(projected["next_safe_action"].get("implementation_allowed")),
        read_only_allowed=bool(projected["next_safe_action"].get("read_only_allowed")),
        proof_required=bool(projected["next_safe_action"].get("proof_required")),
        proof_commands=_tiny_required_proof_commands(payload.get("proof", {})) if isinstance(payload.get("proof"), dict) else [],
        changed_signals=["local_footprint=attention"] if local_footprint_attention else [],
        advisory_selectors=[
            "skill_routing",
            "workflow_sufficiency",
            *(["local_footprint"] if local_footprint_attention else []),
            *(["pre_test_evidence_guardrail"] if "pre_test_evidence_guardrail" in payload else []),
        ],
        agent_judgment="Agent owns work-shape unless blocked.",
    )
    startup_proof_commands = _tiny_required_proof_commands(payload.get("proof", {})) if isinstance(payload.get("proof"), dict) else []
    projected["decision_packet"] = _ordinary_decision_packet(
        surface="start",
        phase_question="Startup posture?",
        next_action=str(projected["next_safe_action"].get("next_safe_action", "")),
        blocked_actions=[str(item) for item in projected["next_safe_action"].get("forbidden_actions", []) if str(item).strip()],
        required_commands=list(
            dict.fromkeys(
                str(item)
                for item in [
                    projected["next_safe_action"].get("preferred_cli"),
                    immediate.get("command") if isinstance(immediate, dict) else "",
                    *startup_proof_commands,
                ]
                if item not in (None, "", []) and str(item).strip() and str(item).strip().lower() != "none"
            )
        ),
        claim_boundary=projected["next_safe_action"].get("claim_boundary", "completion claim requires proof"),
        residue_owner="active continuation state" if payload.get("active_state_summary", {}).get("active_execplan") else "none",
        reasons=list(projected["action_signals"].get("changed_signals", []))[:6],
        detail_routes={
            "why_blocked": "agentic-workspace start --target . --select next_safe_action,action_signals --format json",
            "active_plan": (
                "agentic-workspace start --target . --select active_state_summary,continuation_view --format json"
                if _active_state_has_planning(payload.get("active_state_summary", {}))
                else "agentic-workspace summary --target . --format json"
            ),
            "proof_detail": "agentic-workspace proof --target . --changed <paths> --format json",
        },
        shown_because=["command_phase=start", *list(projected["action_signals"].get("changed_signals", []))[:3]],
        absence_states={
            "full_selector_inventory": "hidden_behind_detail_route",
            "verbose_planning_detail": "detail_omitted",
        },
    )
    state_delta_core = state_delta_core_payload(
        surface="startup",
        decision_packet=projected["decision_packet"],
        communication_contract=compact_communication_contract_payload(surface="startup"),
        evidence_basis=[
            "next_safe_action",
            "action_signals",
            "active planning summary" if payload.get("active_state_summary", {}).get("active_execplan") else "startup routing state",
        ],
        safe_probe=str(
            projected["next_safe_action"].get("preferred_cli")
            or projected["decision_packet"].get("detail_routes", {}).get("active_plan")
            or ""
        ),
    )
    projected["message_economy"] = message_economy_payload(
        surface="startup",
        communication_contract=compact_communication_contract_payload(surface="startup"),
        state_delta_core=state_delta_core,
    )
    projected["current_decision"] = current_decision_payload(
        surface="startup",
        decision_packet=projected["decision_packet"],
        state_delta_core=state_delta_core,
    )
    projected["evidence_bundle"] = evidence_bundle_payload(
        surface="startup",
        current_decision=projected["current_decision"],
        state_delta_core=state_delta_core,
    )
    return projected


def _local_chat_checkpoint_default_visible(local_checkpoint: dict[str, Any], *, payload: dict[str, Any]) -> bool:
    status = str(local_checkpoint.get("status") or "").strip()
    if status in {"stale", "unreadable"}:
        return True
    if status != "present":
        return False
    routes = local_checkpoint.get("planning_candidate_routes", {})
    if isinstance(routes, dict) and routes.get("status") == "matched":
        return True
    task_intent = payload.get("task_intent", {})
    task_text = json.dumps(task_intent, sort_keys=True).lower() if isinstance(task_intent, dict) else ""
    return any(token in task_text for token in ("resume", "checkpoint", "continue", "handoff", "takeover"))


def _start_payload(
    *, target_root: Path, changed_paths: list[str], task_text: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    startup_template = _CONTEXT_TEMPLATES["startup_context"]
    config = _load_workspace_config(target_root=target_root)
    if profile in {None, "tiny"}:
        payload = _start_tiny_payload_fast(
            target_root=target_root, changed_paths=changed_paths, task_text=task_text, config=config, startup_template=startup_template
        )
        payload["work_threads"] = _local_work_threads_projection(target_root=target_root, cli_invoke=config.cli_invoke, task_text=task_text)
        normalized_paths = _normalize_changed_paths(changed_paths)
        improvement_pressure = _session_improvement_pressure_payload(
            target_root=target_root,
            config=config,
            task_text=task_text,
            cli_invoke=config.cli_invoke,
        )
        task_posture_packet = _task_posture_packet_payload(
            config=config,
            surface="start",
            task_text=task_text,
            changed_paths=normalized_paths,
            workflow_obligations=payload.get("workflow_obligations", {}),
            skill_routing=payload.get("skill_routing", {}),
            planning_safety_gate=payload.get("planning_safety_gate", {}),
            proof=payload.get("proof", {}),
            improvement_pressure=improvement_pressure,
            compact=True,
        )
        if (
            _task_posture_packet_relevant(task_text=task_text, changed_paths=normalized_paths, surface="start")
            or task_posture_packet.get("improvement_obligations")
            or task_posture_packet.get("dogfooding_obligations")
        ):
            task_posture_relevant = True
        else:
            task_posture_relevant = False
        if task_posture_relevant and _task_posture_packet_changes_routing(task_posture_packet):
            payload["task_posture_packet"] = task_posture_packet
        if profile is None:
            return _selector_first_start_payload(payload, cli_invoke=config.cli_invoke, target_root=target_root)
        return payload
    descriptors = _module_operations()
    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    installed_modules = [entry.name for entry in registry if entry.installed]
    preflight = _run_preflight_command(target_root=target_root, task_text=task_text, changed_paths=changed_paths, profile="full")
    active_state = preflight.get("active_planning_state", {})
    selected_modules = list(config.enabled_modules)
    if not installed_modules and isinstance(active_state, dict):
        active_count = active_state.get("todo", {}).get("active_count", 0)
        if active_count or active_state.get("planning_record", {}).get("status") == "present":
            selected_modules = ["planning"]
    planning_record = active_state.get("planning_record", {})
    active_contract = active_state.get("active_contract", {})
    active_execplans = active_state.get("execplans", {}).get("active_execplans", [])
    active_execplan = active_execplans[0].get("path") if active_execplans else None
    admitted_active_summary = _fast_planning_active_summary(target_root=target_root)
    if isinstance(admitted_active_summary, dict):
        active_execplan = admitted_active_summary.get("active_execplan")
    next_action = ""
    if isinstance(planning_record, dict):
        next_action = str(planning_record.get("next_action", "") or "")
    if not next_action and isinstance(active_contract, dict):
        next_action = str(active_contract.get("todo_item", {}).get("why_now", "") or "")
    if not next_action:
        active_items = active_state.get("todo", {}).get("active_items", [])
        if active_items:
            next_action = str(active_items[0].get("next_action", "") or active_items[0].get("why_now", "") or "")
    if not next_action:
        next_action = str(startup_template["fallback_next_action"])
    startup_sequence = copy.deepcopy(startup_template["startup_sequence"])
    for step in startup_sequence:
        if step["id"] == "entrypoint":
            step["surface"] = str(step["surface"]).format(
                agent_instructions_file=preflight.get("resolved_config", {}).get("agent_instructions_file", "AGENTS.md")
            )
        step["command"] = _command_with_cli_invoke(command=step.get("command"), cli_invoke=config.cli_invoke)
    active_planning_present = bool(
        isinstance(planning_record, dict)
        and (
            planning_record.get("status") == "present"
            or active_state.get("todo", {}).get("active_count", 0)
            or active_state.get("execplans", {}).get("active_execplans")
        )
    )
    primary_command = (
        _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke)
        if active_planning_present
        else None
    )
    workflow_obligations = preflight.get("workflow_obligations", {})
    compact_workflow_obligations = _compact_start_workflow_obligations(workflow_obligations)
    assurance_requirements = _assurance_requirements_report_payload(
        config=config,
        target_root=target_root,
        active_planning_record=planning_record if isinstance(planning_record, dict) else None,
        task_text=task_text,
        changed_paths=changed_paths,
    )
    raw_planning_record = (
        _raw_active_planning_record_for_closeout(planning_record=planning_record, target_root=target_root)
        if active_planning_present and isinstance(planning_record, dict)
        else {}
    )
    active_parent_record = raw_planning_record or (planning_record if isinstance(planning_record, dict) else {})
    completion_boundary = _completion_boundary_payload(active_planning_record=active_parent_record)
    parent_intent_status = _parent_intent_status_payload(
        active_planning_record=active_parent_record,
        intent_check={},
        completion_boundary=completion_boundary,
    )
    applicable_intent_status = _applicable_intent_status_payload(
        active_planning_record=active_parent_record,
        assurance_requirements=assurance_requirements,
    )
    current_need = "continue-active-planning" if active_planning_present else "first-contact-routing"
    if changed_paths:
        current_need = "changed-path-startup"
    elif _is_config_posture_task(task_text):
        current_need = "config-posture-routing"
    elif _is_prep_only_handoff_task(task_text):
        current_need = "prep-only-planning-routing"
    startup_cli_compatibility = _cli_compatibility_payload(config=config, compact=True)
    installed_state_compatibility = _installed_state_compatibility_payload(
        config=config,
        selected_modules=selected_modules,
        installed_modules=installed_modules,
        cli_compatibility=startup_cli_compatibility,
        compact=True,
    )
    payload: dict[str, Any] = {
        "kind": "startup-context/v1",
        "target": target_root.as_posix(),
        "workflow_participation": _workflow_participation_payload(surface="start", compact=True),
        "invoked_cli_identity": _invoked_cli_identity_payload(target_root=target_root, compact=True),
        "startup_sequence": startup_sequence,
        "context_router": _context_router_family_payload(cli_invoke=config.cli_invoke, compact=True),
        "adaptive_routing": {
            "current_need": current_need,
            "read_budget": f"{profile}; raw files only by detail command",
            "detail_commands": {
                "c": _command_with_cli_invoke(
                    command="agentic-workspace implement --changed <paths> --format json", cli_invoke=config.cli_invoke
                ),
                "t": _command_with_cli_invoke(
                    command='agentic-workspace summary --task "<task>" --format json', cli_invoke=config.cli_invoke
                ),
            },
            "escalate_when": ["changed paths", "handoff", "lane/epic"],
        },
        "feature_tier": _feature_tier_payload(
            selected_modules=selected_modules,
            installed_modules=installed_modules or None,
            resolved_preset=None,
            config=config,
            compact=True,
        ),
        "active_state_summary": {
            "todo_active_count": admitted_active_summary.get("todo_active_count", active_state.get("todo", {}).get("active_count", 0)),
            "active_execplan": active_execplan,
            "planning_status": admitted_active_summary.get(
                "planning_status", planning_record.get("status", "unavailable") if isinstance(planning_record, dict) else "unavailable"
            ),
            **(
                {"owner_admission": admitted_active_summary["owner_admission"]}
                if isinstance(admitted_active_summary.get("owner_admission"), dict)
                else {}
            ),
            **(
                {
                    "orientation_delta": {
                        "status": "embedded",
                        "summary_equivalent_for_first_contact": True,
                        "detail_selectors": ["active_state_summary", "continuation_view", "next_safe_action", "action_signals"],
                        "full_detail_command": _command_with_cli_invoke(
                            command="agentic-workspace summary --target . --format json", cli_invoke=config.cli_invoke
                        ),
                        "rule": "Startup carries the compact active-planning facts needed for first-contact routing; run summary only for explicit detail or refresh.",
                    }
                }
                if active_planning_present
                else {}
            ),
        },
        "workflow_sufficiency": _workflow_sufficiency_payload(
            surface="start",
            decision="startup-orientation-embedded" if active_planning_present else "enough-for-first-contact-routing",
            reason="Active planning exists; compact startup includes the first-contact summary facts."
            if active_planning_present
            else "No active planning detected; choose the smallest shape and wait for changed paths before proof.",
            required_next_action="follow startup next_safe_action" if active_planning_present else "choose-smallest-workflow-shape",
            evidence_required=["embedded compact active planning orientation"] if active_planning_present else [],
        ),
        "package_boundary": _package_boundary_payload(target_root=target_root),
        "authority_markers": _authority_markers_for_startup(
            active_execplan=active_execplan, agent_instructions_file=config.agent_instructions_file
        ),
        "immediate_next_allowed_action": {
            "action": "continue-active-planning-record" if active_planning_present else "choose-smallest-workflow-shape",
            "summary": next_action,
            "command": primary_command,
            "run": primary_command,
            "risk": "read-only routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "run proof selection once changed paths are known",
            "read_first": [],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        },
        "workflow_obligations": compact_workflow_obligations,
        "closeout_obligations": _compact_start_closeout_obligations(
            preflight.get("closeout_obligations", {}),
            cli_invoke=config.cli_invoke,
            target_root=target_root,
        ),
        "communication_contract": communication_contract_payload(surface="startup"),
        "memory_consult": _memory_consult_payload(
            target_root=target_root, changed_paths=changed_paths, compact=True, cli_invoke=config.cli_invoke
        ),
        "local_chat_checkpoint": _local_chat_checkpoint_projection(target_root=target_root, cli_invoke=config.cli_invoke),
        "work_threads": _local_work_threads_projection(target_root=target_root, cli_invoke=config.cli_invoke, task_text=task_text),
        "maintainer_mode": _maintainer_mode_payload(config=config, target_root=target_root, compact=True),
        "continuation_state": _compact_continuation_state_contract(cli_invoke=config.cli_invoke),
        "operating_posture": _operating_posture_payload(config=config, surface="start", compact=True),
        "skill_routing": _guidance_with_cli_invoke(
            value=_startup_skill_routing_payload(
                cli_invoke=config.cli_invoke,
                enabled_advanced_features=config.advanced_features,
                compact=True,
                target_root=target_root,
                task_text=task_text,
            ),
            cli_invoke=config.cli_invoke,
        ),
    }
    local_footprint = _compact_start_local_footprint_advisory(
        _local_footprint_payload(target_root=target_root, cli_invoke=config.cli_invoke),
        cli_invoke=config.cli_invoke,
    )
    if local_footprint.get("status") == "attention":
        payload["local_footprint"] = local_footprint
    pre_test_guardrail = _pre_test_evidence_guardrail_payload(
        target_root=target_root,
        changed_paths=changed_paths,
        task_text=task_text,
        config=config,
        compact=True,
    )
    if pre_test_guardrail.get("status") == "advisory":
        payload["pre_test_evidence_guardrail"] = pre_test_guardrail
    payload["memory_decision_packet"] = _memory_decision_packet_payload(
        stage="startup",
        cli_invoke=config.cli_invoke,
        memory_consult=_memory_consult_from_payload(payload),
        changed_paths=changed_paths,
        task_text=task_text,
    )
    if installed_state_compatibility["status"] != "compatible":
        payload["installed_state_compatibility"] = installed_state_compatibility
        payload["installed_state_drift_triage"] = _installed_state_drift_triage_payload(
            installed_state=installed_state_compatibility,
            task_text=task_text,
            changed_paths=changed_paths,
            cli_invoke=config.cli_invoke,
        )
    if parent_intent_status.get("status") != "guidance-only":
        payload["parent_intent_status"] = parent_intent_status
    if applicable_intent_status.get("status") != "guidance-only":
        payload["applicable_intent_status"] = applicable_intent_status
    if active_planning_present:
        payload["continuation_view"] = _startup_continuation_view_payload(target_root=target_root)
    if int(assurance_requirements.get("configured_count", 0) or 0) > 0:
        payload["assurance_requirements"] = assurance_requirements
    startup_review = _workspace_absence_startup_review(target_root=target_root, config=config)
    if startup_review["status"] == "attention":
        payload["startup_review"] = startup_review
    task_intent = _task_intent_carry_forward_payload(
        task_text=task_text, cli_invoke=config.cli_invoke, target_root=target_root, config=config, changed_paths=changed_paths
    )
    if task_intent["status"] == "present":
        payload["task_intent"] = task_intent
        payload["acceptance"] = task_intent["acceptance"]
        payload["durable_intent_promotion"] = task_intent["promotion_guidance"]
    read_only_response = _read_only_response_posture_payload(task_text=task_text, changed_paths=changed_paths)
    if read_only_response["status"] == "read-only-reporting":
        payload["read_only_response"] = read_only_response
    task_mentioned_paths = _task_mentioned_existing_paths(task_text=task_text, target_root=target_root)
    task_path_references = _task_path_reference_payload(task_text=task_text, detected_paths=task_mentioned_paths)
    if task_path_references["status"] == "present":
        payload["task_path_references"] = task_path_references
    forecast_paths = []
    forecast_scope_source = ""
    if task_path_references.get("path_reference_kind") == "path-scoped-work":
        forecast_paths = _list_payload(task_path_references.get("path_scoped_paths")) or task_mentioned_paths
        forecast_scope_source = "task_path_references.path_scoped_paths"
    elif active_planning_present:
        forecast_paths = _active_plan_touched_scope_paths(active_parent_record)
        forecast_scope_source = "active_planning_record.touched_scope"
    forecast_missing_scope = (
        bool(task_intent.get("status") == "present")
        and not forecast_paths
        and not changed_paths
        and not _is_config_posture_task(task_text)
        and read_only_response.get("status") != "read-only-reporting"
        and not _is_prep_only_handoff_task(task_text)
    )
    if (forecast_paths or forecast_missing_scope) and not changed_paths and not _is_config_posture_task(task_text):
        architecture_forecast = _architecture_principles_forecast_payload(
            target_root=target_root,
            planned_paths=forecast_paths,
            scope_source=forecast_scope_source or "missing_planned_scope",
            cli_invoke=config.cli_invoke,
        )
        architecture_forecast["commit_policy"] = {
            "state": "provisional",
            "commit_on": ["stateful action", "explicit checkpoint"],
            "invalidate_on": ["branch", "worktree", "repository", "target", "current-work", "selected-owner"],
            "rule": "Startup projects intent but does not create decision-point carry residue.",
        }
        if architecture_forecast.get("status") in {"provisional-match", "needs-planned-scope"} or architecture_forecast.get(
            "relevant_intent"
        ):
            payload["architecture_principles_forecast"] = architecture_forecast
    vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
    if vague_orientation["applies_to_current_task"]:
        payload["vague_outcome_orientation"] = vague_orientation
    intent_discovery = _intent_discovery_dialogue_payload(
        task_text=task_text,
        vague_orientation=vague_orientation,
        cli_invoke=config.cli_invoke,
    )
    if intent_discovery["applies_to_current_task"]:
        payload["intent_discovery_dialogue"] = intent_discovery
    if changed_paths:
        durable_intent = _intent_decision_projection(target_root=target_root, config=config, changed_paths=changed_paths, compact=True)
        subsystem_projection = durable_intent.get("subsystem_intent", {})
        subsystem_matched_count = int(subsystem_projection.get("matched_count", 0) or 0) if isinstance(subsystem_projection, dict) else 0
        if subsystem_matched_count:
            payload["durable_intent"] = durable_intent
    execution_posture = _execution_posture_payload(
        config=config, changed_paths=_normalize_changed_paths(changed_paths), task_text=task_text, target_root=target_root
    )
    payload["delegation_decision"] = _compact_start_delegation_decision(execution_posture["delegation_decision"])
    planning_safety_gate = _planning_safety_gate_payload(
        target_root=target_root,
        config=config,
        changed_paths=_normalize_changed_paths(changed_paths),
        task_text=task_text,
        execution_posture=execution_posture,
    )
    payload["planning_revision"] = planning_safety_gate.get("planning_revision", {})
    payload["active_plan_reliance"] = planning_safety_gate.get("active_plan_reliance", {})
    custody_planning = planning_safety_gate.get("custody_planning", {})
    custody_applies = isinstance(custody_planning, dict) and custody_planning.get("status") not in (None, "", "not-applicable")
    owner_admission = planning_safety_gate.get("owner_admission", {})
    owner_admission_rejected = isinstance(owner_admission, dict) and owner_admission.get("status") == "rejected"
    route_decision = planning_safety_gate.get("route_decision", {})
    if isinstance(route_decision, dict) and route_decision.get("kind") == "agentic-planning/route-decision/v1":
        route_decision = copy.deepcopy(route_decision)
        route_decision["binding"] = _startup_route_binding(
            route_decision=route_decision,
            target_root=target_root,
            task_text=task_text,
            cli_invoke=config.cli_invoke,
        )
        planning_safety_gate["route_decision"] = route_decision
        payload["route_decision"] = route_decision
    route_transition = str(route_decision.get("required_transition") or "") if isinstance(route_decision, dict) else ""
    route_relation = str(route_decision.get("task_relation") or "") if isinstance(route_decision, dict) else ""
    task_switch_visible_by_default = route_transition in {"closeout-or-archive", "ask-for-route-decision", "reconcile"}
    if (
        planning_safety_gate["status"] not in {"satisfied", "clear"}
        or custody_applies
        or task_switch_visible_by_default
        or owner_admission_rejected
    ):
        payload["planning_safety_gate"] = planning_safety_gate
    if isinstance(route_decision, dict) and route_transition in {
        "closeout-or-archive",
        "ask-for-route-decision",
        "inspect-current-task-scope",
        "reconcile",
        "none",
    }:
        next_packet = route_decision.get("next_safe_action", {})
        if isinstance(next_packet, dict):
            evidence_required = (
                ["completed active-plan route accepted or dismissed"]
                if route_transition == "closeout-or-archive"
                else ["active-plan claim boundary preserved"]
                if route_relation == "bounded-independent"
                else ["current-task proof", "active-plan claim boundary preserved"]
                if route_relation == "bounded-independent"
                else ["current-task route chosen without claiming active-plan progress"]
            )
            payload["workflow_sufficiency"] = _workflow_sufficiency_payload(
                surface="start",
                decision=planning_safety_gate["decision"],
                reason=planning_safety_gate["reason"],
                required_next_action=planning_safety_gate["required_next_action"],
                evidence_required=evidence_required,
            )
            payload["immediate_next_allowed_action"] = next_packet
    if not planning_safety_gate["workflow_sufficient"] and (not _is_config_posture_task(task_text)):
        repair_route = planning_safety_gate.get("repair_route", {})
        repair_command = (
            str(repair_route.get("claim_current_slice_command") or "")
            if isinstance(repair_route, dict) and repair_route.get("status") == "available"
            else ""
        )
        study = planning_safety_gate.get("work_shape_study", {})
        study_probes = study.get("safe_probes", []) if isinstance(study, dict) else []
        study_command = str(study_probes[0].get("command") or "") if study_probes and isinstance(study_probes[0], dict) else ""
        next_command = repair_command or study_command or planning_safety_gate["promotion_command"]
        payload["workflow_sufficiency"] = _workflow_sufficiency_payload(
            surface="start",
            decision=planning_safety_gate["decision"],
            reason=planning_safety_gate["reason"],
            required_next_action=planning_safety_gate["required_next_action"],
            evidence_required=["active planning ownership evidence"],
            hard_gate=True,
        )
        payload["immediate_next_allowed_action"] = {
            "action": planning_safety_gate["required_next_action"],
            "summary": planning_safety_gate["reason"],
            "command": next_command,
            "run": next_command,
            "risk": "planning-required-before-implementation",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "run summary after creating or promoting the active execplan",
            "read_first": [next_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        }
    issue_reference_intent = _issue_reference_intent_payload(
        issue_scope_evidence=planning_safety_gate.get("issue_scope_evidence", {}), cli_invoke=config.cli_invoke
    )
    if (
        issue_reference_intent.get("status") == "details-needed"
        and not active_planning_present
        and not changed_paths
        and not _is_config_posture_task(task_text)
        and not _is_prep_only_handoff_task(task_text)
    ):
        payload["issue_reference_intent"] = issue_reference_intent
        command = str(issue_reference_intent.get("next_command") or "")
        if payload["immediate_next_allowed_action"].get("action") == "choose-smallest-workflow-shape":
            payload["immediate_next_allowed_action"] = {
                "action": "refresh-external-issue-intent",
                "summary": (
                    "The task names external issue ref(s). Fetch issue details before treating the issue body as confirmed "
                    "scope; this is missing issue evidence, not user-intent ambiguity."
                ),
                "command": command,
                "run": command,
                "risk": "read-only issue intent grounding",
                "required_inputs": ["target repo", "issue ref(s)"],
                "next_proof": "rerun start or implement after refresh and use the fetched issue evidence for scope.",
                "read_first": [command],
                "open_execplan_only_when": startup_template["open_execplan_only_when"],
            }
    intent_acknowledgement = _intent_acknowledgement_payload(
        task_text=task_text, execution_posture=execution_posture, vague_orientation=vague_orientation
    )
    if (
        intent_acknowledgement["decision"] != "silent-ok"
        and task_intent.get("task_argument_mode") != "task-file"
        and (not _is_config_posture_task(task_text))
        and (not _is_prep_only_handoff_task(task_text))
    ):
        payload["intent_acknowledgement"] = intent_acknowledgement
    intent_evidence = _task_intent_evidence_payload(
        task_text=task_text,
        task_intent=task_intent,
        intent_discovery=intent_discovery,
        intent_acknowledgement=intent_acknowledgement,
    )
    if (
        intent_evidence["status"] == "present"
        and (
            intent_evidence["assumption_state"] != "low-risk-direct"
            or intent_evidence.get("issue_refs")
            or intent_discovery.get("applies_to_current_task")
        )
        and task_intent.get("task_argument_mode") != "task-file"
        and not _is_prep_only_handoff_task(task_text)
    ):
        payload["intent_evidence"] = intent_evidence
    active_intent_contract = _active_intent_contract_payload(
        task_text=task_text,
        acceptance=task_intent.get("acceptance", {}) if isinstance(task_intent, dict) else {},
        active_planning_record=active_parent_record,
        issue_reference_intent=issue_reference_intent,
    )
    intent_satisfaction_matrix = _intent_satisfaction_matrix_payload(
        active_intent_contract=active_intent_contract,
        acceptance=task_intent.get("acceptance", {}) if isinstance(task_intent, dict) else {},
        proof=payload.get("proof", {}),
        intent_check={},
        parent_intent_status=parent_intent_status,
    )
    if active_intent_contract["status"] == "present":
        payload["active_intent_contract"] = active_intent_contract
        payload["intent_satisfaction_matrix"] = intent_satisfaction_matrix
    if (
        intent_discovery.get("status") == "ask-human"
        and not active_planning_present
        and not changed_paths
        and not _is_config_posture_task(task_text)
        and not _is_prep_only_handoff_task(task_text)
    ):
        question = str(intent_discovery.get("dialogue_packet", {}).get("question_to_user", ""))
        payload["workflow_sufficiency"] = _workflow_sufficiency_payload(
            surface="start",
            decision="intent-discovery-required",
            reason="Task intent is low-confidence and the stakes of silently choosing a slice are high.",
            required_next_action="ask-intent-discovery-question",
            evidence_required=["captured clarified intent before implementation or Planning"],
        )
        payload["immediate_next_allowed_action"] = {
            "action": "ask-intent-discovery-question",
            "summary": "Ask one bounded intent-discovery question before implementation or Planning narrows the work.",
            "command": None,
            "run": None,
            "risk": "human-intent ambiguity",
            "required_inputs": ["why/outcome/non-goals/acceptable first slice"],
            "next_proof": "carry captured_intent_after_reply into task_intent, acceptance, durable_intent, Memory, Planning, or an issue",
            "read_first": [],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
            "question_to_user": question,
        }
    if (
        not active_planning_present
        and task_path_references.get("path_reference_kind") == "path-scoped-work"
        and (not changed_paths)
        and (not _is_config_posture_task(task_text))
    ):
        path_scoped_paths = _list_payload(task_path_references.get("path_scoped_paths")) or task_mentioned_paths
        implement_command = str(task_intent.get("implement_changed_command", "")) if isinstance(task_intent, dict) else ""
        if implement_command:
            implement_command = implement_command.replace("<paths>", " ".join(path_scoped_paths))
        else:
            implement_command = _command_with_cli_invoke(
                command=f"agentic-workspace implement --changed {' '.join(path_scoped_paths)} --format json",
                cli_invoke=config.cli_invoke,
            )
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-known-task-paths",
            "summary": "The task text explicitly asks for work on existing repo paths. Run the implement surface for those paths before broader startup or raw workspace reads.",
            "command": implement_command,
            "run": implement_command,
            "risk": "read-only changed-path routing",
            "required_inputs": ["target repo", "named path(s)"],
            "next_proof": "use the proof.required_commands from implement output",
            "read_first": [implement_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
            "detected_paths": path_scoped_paths,
            "path_reference_kind": task_path_references.get("path_reference_kind"),
            "matched_action_terms": _list_payload(task_path_references.get("matched_action_terms")),
        }
    elif not active_planning_present and _is_prep_only_handoff_task(task_text):
        prep_only = _prep_only_handoff_payload(config=config)
        planning_command = prep_only["first_command"]
        summary_command = prep_only["after_write"]
        payload["prep_only_handoff"] = prep_only
        payload["immediate_next_allowed_action"] = {
            "action": "create-prep-only-planning-state",
            "summary": "Prep-only durable handoff requested. Run the prep-only new-plan command, create or continue canonical Planning state, verify with summary, then stop; do not create product source, tests, fixtures, README feature docs, dependencies, or app scaffolding until implementation is requested.",
            "command": planning_command,
            "run": planning_command,
            "risk": "planning-only write routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": summary_command,
            "read_first": [],
            "open_execplan_only_when": "compact summary reports a blocking Planning problem after the prep-only scaffold is created",
        }
    elif _is_config_posture_task(task_text):
        config_command = _command_with_cli_invoke(command="agentic-workspace config --format json", cli_invoke=config.cli_invoke)
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-effective-config",
            "summary": "The task asks about configured operating, reporting, closeout, or delegation posture. Run the tiny config surface before raw config files; use compact or full only if the tiny answer is insufficient.",
            "command": config_command,
            "run": config_command,
            "risk": "read-only config routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "no file proof unless the task later becomes an edit",
            "read_first": [config_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        }
    closeout_inspection = _completion_closeout_inspection_payload(target_root=target_root, config=config, task_text=task_text)
    if closeout_inspection["status"] in {"required", "clear"}:
        payload["closeout_trust_inspection"] = closeout_inspection
        payload["closeout_report_route"] = _startup_closeout_report_route(closeout_inspection)
    if closeout_inspection["status"] == "required":
        command = str(closeout_inspection["required_next_inspection"])
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-closeout-trust-before-completion-answer",
            "summary": "Completion/status question detected; inspect closeout_trust before claiming broad work is done.",
            "command": command,
            "run": command,
            "risk": "read-only closeout trust routing",
            "required_inputs": ["target repo", "completion/status question"],
            "next_proof": "answer completion only after closeout_trust and intent satisfaction are reconciled",
            "read_first": [command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        }
    if not planning_safety_gate["workflow_sufficient"] and (not _is_config_posture_task(task_text)):
        repair_route = planning_safety_gate.get("repair_route", {})
        repair_command = (
            str(repair_route.get("claim_current_slice_command") or "")
            if isinstance(repair_route, dict) and repair_route.get("status") == "available"
            else ""
        )
        study = planning_safety_gate.get("work_shape_study", {})
        study_probes = study.get("safe_probes", []) if isinstance(study, dict) else []
        study_command = str(study_probes[0].get("command") or "") if study_probes and isinstance(study_probes[0], dict) else ""
        next_command = repair_command or study_command or planning_safety_gate["promotion_command"]
        payload["workflow_sufficiency"] = _workflow_sufficiency_payload(
            surface="start",
            decision=planning_safety_gate["decision"],
            reason=planning_safety_gate["reason"],
            required_next_action=planning_safety_gate["required_next_action"],
            evidence_required=["active planning ownership evidence"],
        )
        payload["immediate_next_allowed_action"] = {
            "action": planning_safety_gate["required_next_action"],
            "summary": planning_safety_gate["reason"],
            "command": next_command,
            "run": next_command,
            "risk": "planning-required-before-implementation",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "run summary after creating or promoting the active execplan",
            "read_first": [next_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        }
    _apply_lane_shaping_gate_to_start_payload(
        payload=payload,
        config=config,
        planning_safety_gate=planning_safety_gate,
        task_text=task_text,
        changed_paths=_normalize_changed_paths(changed_paths),
        startup_template=startup_template,
    )
    cli_compatibility = startup_cli_compatibility
    if cli_compatibility["configured"]:
        payload["cli_compatibility"] = cli_compatibility
    sibling_freshness = _sibling_repo_aw_freshness_payload(target_root=target_root, task_text=task_text, cli_invoke=config.cli_invoke)
    if sibling_freshness["status"] != "not-referenced":
        payload["sibling_repo_aw_freshness"] = sibling_freshness
    normalized_paths = _normalize_changed_paths(changed_paths)
    if normalized_paths and not active_planning_present:
        proof_payload = _proof_selection_for_changed_paths(
            changed_paths=normalized_paths, target_root=target_root, include_durable_intent=False, task_text=task_text
        )
        proof_command = str(
            _command_with_cli_invoke(
                command=f"agentic-workspace proof --changed {' '.join(normalized_paths)} --format json",
                cli_invoke=config.cli_invoke,
            )
        )
        if planning_safety_gate["workflow_sufficient"]:
            payload["immediate_next_allowed_action"] = {
                "action": "select-changed-path-proof",
                "summary": "Changed paths are known. Run changed-path proof selection before claiming implementation is ready.",
                "command": proof_command,
                "run": proof_command,
                "risk": "read-only proof routing",
                "required_inputs": ["target repo", "changed path(s)"],
                "next_proof": proof_command,
                "read_first": [proof_command],
                "open_execplan_only_when": startup_template["open_execplan_only_when"],
            }
        payload["proof"] = _compact_start_proof_payload(proof_payload)
        strategy_preservation = _as_dict(proof_payload.get("proof_route_strategy_preservation"))
        if strategy_preservation:
            payload["proof_route_strategy_preservation"] = strategy_preservation
        if str(strategy_preservation.get("claim_effect", "")) == "claim-blocked":
            payload["immediate_next_allowed_action"] = {
                "action": str(
                    _as_dict(strategy_preservation.get("consumers")).get("start", {}).get("next_action") or "route-refinement-required"
                ),
                "summary": "Proof route strategy blocks the completion claim; resolve route refinement or structured escalation before closeout.",
                "command": proof_command,
                "run": proof_command,
                "risk": "claim-blocking proof-route decision",
                "required_inputs": ["target repo", "changed path(s)", "proof_route_strategy_preservation.decision_id"],
                "next_proof": proof_command,
                "read_first": [proof_command],
                "open_execplan_only_when": startup_template["open_execplan_only_when"],
            }
        repair_profile = _compact_repair_plan_profile(changed_paths=normalized_paths, task_text=task_text, proof_command=proof_command)
        if repair_profile["status"] == "direct-no-plan":
            payload["repair_plan_profile"] = repair_profile
        payload["path_boundaries"] = [
            _boundary_warning_for_path(path, agent_instructions_file=config.agent_instructions_file) for path in normalized_paths
        ]
    elif normalized_paths:
        proof_payload = _proof_selection_for_changed_paths(
            changed_paths=normalized_paths, target_root=target_root, include_durable_intent=False, task_text=task_text
        )
        payload["proof"] = _compact_start_proof_payload(proof_payload)
        strategy_preservation = _as_dict(proof_payload.get("proof_route_strategy_preservation"))
        if strategy_preservation:
            payload["proof_route_strategy_preservation"] = strategy_preservation
        proof_command = str(
            _command_with_cli_invoke(
                command=f"agentic-workspace proof --changed {' '.join(normalized_paths)} --format json",
                cli_invoke=config.cli_invoke,
            )
        )
        if str(strategy_preservation.get("claim_effect", "")) == "claim-blocked":
            payload["immediate_next_allowed_action"] = {
                "action": str(
                    _as_dict(strategy_preservation.get("consumers")).get("start", {}).get("next_action") or "route-refinement-required"
                ),
                "summary": "Proof route strategy blocks the completion claim; resolve route refinement or structured escalation before closeout.",
                "command": proof_command,
                "run": proof_command,
                "risk": "claim-blocking proof-route decision",
                "required_inputs": ["target repo", "changed path(s)", "proof_route_strategy_preservation.decision_id"],
                "next_proof": proof_command,
                "read_first": [proof_command],
                "open_execplan_only_when": startup_template["open_execplan_only_when"],
            }
        repair_profile = _compact_repair_plan_profile(
            changed_paths=normalized_paths,
            task_text=task_text,
            proof_command=proof_command,
        )
        if repair_profile["status"] == "direct-no-plan":
            payload["repair_plan_profile"] = repair_profile
        payload["path_boundaries"] = [
            _boundary_warning_for_path(path, agent_instructions_file=config.agent_instructions_file) for path in normalized_paths
        ]
    improvement_pressure = _session_improvement_pressure_payload(
        target_root=target_root,
        config=config,
        task_text=task_text,
        cli_invoke=config.cli_invoke,
        active_planning_present=active_planning_present,
    )
    task_posture_packet = _task_posture_packet_payload(
        config=config,
        surface="start",
        task_text=task_text,
        changed_paths=normalized_paths,
        workflow_obligations=workflow_obligations,
        skill_routing=payload.get("skill_routing", {}),
        planning_safety_gate=planning_safety_gate,
        proof=payload.get("proof", {}),
        improvement_pressure=improvement_pressure,
        compact=(profile == "tiny"),
    )
    if (
        _task_posture_packet_relevant(task_text=task_text, changed_paths=normalized_paths, surface="start")
        or task_posture_packet.get("improvement_obligations")
        or task_posture_packet.get("dogfooding_obligations")
    ) and _task_posture_packet_changes_routing(task_posture_packet):
        payload["task_posture_packet"] = task_posture_packet
    _apply_required_payload_target_start_gate(
        payload=payload,
        target_root=target_root,
        config=config,
        startup_template=startup_template,
    )
    if profile == "tiny":
        payload["routine_work_context"] = _routine_work_context_payload(
            source_payload=payload,
            surface="start",
            cli_invoke=config.cli_invoke,
            target_root=target_root,
            changed_paths=normalized_paths,
            task_text=task_text,
            compact=True,
        )
        payload["cli_invocation"] = _cli_invocation_payload(config=config)
        return _tiny_start_payload(payload)
    return payload


def _hydrate_selected_start_advisory_payloads(
    *,
    payload: dict[str, Any],
    select: str | None,
    target_root: Path,
    task_text: str | None,
    config: WorkspaceConfig,
) -> None:
    state_delta_requested = any(
        _selector_requests(select, field)
        for field in (
            "decision_packet",
            "current_decision",
            "message_economy",
            "evidence_bundle",
            "continuation_capsule",
        )
    )
    if _selector_requests(select, "next_safe_action") or _selector_requests(select, "action_signals") or state_delta_requested:
        _attach_start_router_fields(payload)
    if state_delta_requested:
        next_safe_action = payload.get("next_safe_action", {}) if isinstance(payload.get("next_safe_action"), dict) else {}
        action_signals = payload.get("action_signals", {}) if isinstance(payload.get("action_signals"), dict) else {}
        startup_proof_commands = _tiny_required_proof_commands(payload.get("proof", {})) if isinstance(payload.get("proof"), dict) else []
        if "decision_packet" not in payload:
            payload["decision_packet"] = _ordinary_decision_packet(
                surface="start",
                phase_question="Startup posture?",
                next_action=str(next_safe_action.get("next_safe_action", "")),
                blocked_actions=[str(item) for item in next_safe_action.get("forbidden_actions", []) if str(item).strip()],
                required_commands=list(
                    dict.fromkeys(
                        str(item)
                        for item in [
                            next_safe_action.get("preferred_cli"),
                            payload.get("immediate_next_allowed_action", {}).get("command")
                            if isinstance(payload.get("immediate_next_allowed_action"), dict)
                            else "",
                            *startup_proof_commands,
                        ]
                        if item not in (None, "", []) and str(item).strip() and str(item).strip().lower() != "none"
                    )
                ),
                claim_boundary=next_safe_action.get("claim_boundary", "completion claim requires proof"),
                residue_owner="active continuation state" if payload.get("active_state_summary", {}).get("active_execplan") else "none",
                reasons=list(action_signals.get("changed_signals", []))[:6],
                detail_routes={
                    "why_blocked": f"{config.cli_invoke} start --target . --select next_safe_action,action_signals --format json",
                    "active_plan": (
                        f"{config.cli_invoke} start --target . --select active_state_summary,continuation_view --format json"
                        if _active_state_has_planning(payload.get("active_state_summary", {}))
                        else f"{config.cli_invoke} summary --target . --format json"
                    ),
                    "proof_detail": f"{config.cli_invoke} proof --target . --changed <paths> --format json",
                },
                shown_because=["command_phase=start", *list(action_signals.get("changed_signals", []))[:3]],
                absence_states={
                    "full_selector_inventory": "hidden_behind_detail_route",
                    "verbose_planning_detail": "detail_omitted",
                },
            )
        state_delta_core = state_delta_core_payload(
            surface="startup",
            decision_packet=payload["decision_packet"],
            communication_contract=compact_communication_contract_payload(surface="startup"),
            evidence_basis=[
                "next_safe_action",
                "action_signals",
                "active planning summary"
                if isinstance(payload.get("active_state_summary"), dict) and payload["active_state_summary"].get("active_execplan")
                else "startup routing state",
            ],
            safe_probe=str(
                next_safe_action.get("preferred_cli") or payload["decision_packet"].get("detail_routes", {}).get("active_plan") or ""
            ),
        )
        payload["message_economy"] = message_economy_payload(
            surface="startup",
            communication_contract=compact_communication_contract_payload(surface="startup"),
            state_delta_core=state_delta_core,
        )
        payload["current_decision"] = current_decision_payload(
            surface="startup",
            decision_packet=payload["decision_packet"],
            state_delta_core=state_delta_core,
        )
        payload["evidence_bundle"] = evidence_bundle_payload(
            surface="startup",
            current_decision=payload["current_decision"],
            state_delta_core=state_delta_core,
        )
        if _selector_requests(select, "continuation_capsule") and isinstance(payload.get("continuation_view"), dict):
            continuation_answers = (
                payload.get("continuation_view", {}).get("answers", {}) if isinstance(payload.get("continuation_view"), dict) else {}
            )
            payload["continuation_capsule"] = continuation_capsule_payload(
                surface="startup",
                current_decision=payload["current_decision"],
                message_economy=payload["message_economy"],
                preserved_intent=str(continuation_answers.get("preserved_intent", "")) if isinstance(continuation_answers, dict) else "",
                state_delta_core=state_delta_core,
                work_shape_study=(payload.get("planning_safety_gate", {}) or {}).get("work_shape_study", {}),
            )
    vague_orientation: dict[str, Any] | None = None
    if _selector_requests(select, "vague_outcome_orientation"):
        vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
        payload.setdefault("vague_outcome_orientation", vague_orientation)
    if _selector_requests(select, "intent_discovery_dialogue"):
        if vague_orientation is None:
            vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
        payload.setdefault(
            "intent_discovery_dialogue",
            _intent_discovery_dialogue_payload(
                task_text=task_text,
                vague_orientation=vague_orientation,
                cli_invoke=config.cli_invoke,
            ),
        )
    if _selector_requests(select, "local_footprint") and "local_footprint" not in payload:
        payload["local_footprint"] = _compact_start_local_footprint_advisory(
            _local_footprint_payload(target_root=target_root, cli_invoke=config.cli_invoke),
            cli_invoke=config.cli_invoke,
        )

    if _selector_requests(select, "intent_elicitation_protocol"):
        payload.setdefault(
            "intent_elicitation_protocol",
            _intent_elicitation_protocol_payload(task_text=task_text, cli_invoke=config.cli_invoke),
        )
    if _selector_requests(select, "intent_acknowledgement"):
        if vague_orientation is None:
            vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
        execution_posture = _execution_posture_payload(config=config, changed_paths=[], task_text=task_text, target_root=target_root)
        payload.setdefault(
            "intent_acknowledgement",
            _intent_acknowledgement_payload(
                task_text=task_text,
                execution_posture=execution_posture,
                vague_orientation=vague_orientation,
            ),
        )
    if _selector_requests(select, "repo_posture"):
        payload["repo_posture"] = _repo_posture_payload(config=config, surface="start", compact=False)
    if _selector_requests(select, "planning_safety_gate"):
        execution_posture = _execution_posture_payload(config=config, changed_paths=[], task_text=task_text, target_root=target_root)
        gate = _planning_safety_gate_payload(
            target_root=target_root,
            config=config,
            changed_paths=[],
            task_text=task_text,
            execution_posture=execution_posture,
        )
        route = _as_dict(gate.get("route_decision"))
        if route.get("kind") == "agentic-planning/route-decision/v1":
            route = copy.deepcopy(route)
            route["binding"] = _startup_route_binding(
                route_decision=route,
                target_root=target_root,
                task_text=task_text,
                cli_invoke=config.cli_invoke,
            )
            gate["route_decision"] = route
        payload["planning_safety_gate"] = gate
    if _selector_requests(select, "issue_reference_intent"):
        gate = payload.get("planning_safety_gate")
        if not isinstance(gate, dict):
            execution_posture = _execution_posture_payload(config=config, changed_paths=[], task_text=task_text, target_root=target_root)
            gate = _planning_safety_gate_payload(
                target_root=target_root,
                config=config,
                changed_paths=[],
                task_text=task_text,
                execution_posture=execution_posture,
            )
        if _list_payload(gate.get("issue_refs")):
            payload["issue_reference_intent"] = _issue_reference_intent_payload(
                issue_scope_evidence=gate.get("issue_scope_evidence", {}), cli_invoke=config.cli_invoke
            )
    if _selector_requests(select, "open_issue_intake"):
        payload["open_issue_intake"] = _open_issue_intake_payload(
            target_root=target_root,
            task_text=task_text,
            cli_invoke=config.cli_invoke,
            explicit_request=True,
        )
    if _selector_requests(select, "local_chat_checkpoint"):
        payload["local_chat_checkpoint"] = _local_chat_checkpoint_projection(target_root=target_root, cli_invoke=config.cli_invoke)
    if _selector_requests(select, "work_threads"):
        payload["work_threads"] = _local_work_threads_projection(target_root=target_root, cli_invoke=config.cli_invoke, task_text=task_text)
    if _selector_requests(select, "installed_state_compatibility") or _selector_requests(select, "installed_state_drift_triage"):
        installed_modules = _fast_installed_modules(target_root=target_root)
        selected_modules = list(config.enabled_modules)
        payload["installed_state_compatibility"] = _installed_state_compatibility_payload(
            config=config,
            selected_modules=selected_modules,
            installed_modules=installed_modules,
            cli_compatibility=_cli_compatibility_payload(config=config, compact=True),
            compact=True,
        )
        payload["installed_state_drift_triage"] = _installed_state_drift_triage_payload(
            installed_state=payload["installed_state_compatibility"],
            task_text=task_text,
            changed_paths=[],
            cli_invoke=config.cli_invoke,
        )
    if _selector_requests(select, "intent_custody"):
        payload["intent_custody"] = _intent_custody_payload(
            task_text=task_text,
            task_intent=_as_dict(payload.get("task_intent")),
            intent_evidence=_as_dict(payload.get("intent_evidence")),
            active_intent_contract=_as_dict(payload.get("active_intent_contract")),
            active_planning_record=_active_planning_record_for_report_section(target_root=target_root),
            durable_intent=_as_dict(payload.get("durable_intent")),
            cli_invoke=config.cli_invoke,
        )
    if _selector_requests(select, "continuation_reorientation"):
        active_summary = _as_dict(payload.get("active_state_summary"))
        active_planning_present = bool(active_summary.get("todo_active_count") or active_summary.get("active_execplan"))
        active_planning_record = (
            _raw_active_planning_record_for_closeout(planning_record={}, target_root=target_root) if active_planning_present else {}
        )
        active_intent_contract = _as_dict(payload.get("active_intent_contract"))
        if active_planning_present and active_intent_contract.get("status") != "present":
            active_intent_contract = _active_intent_contract_payload(
                task_text=task_text,
                acceptance=_as_dict(payload.get("acceptance")),
                active_planning_record=active_planning_record,
            )
        if active_planning_present and not isinstance(payload.get("continuation_view"), dict):
            payload["continuation_view"] = _startup_continuation_view_payload(target_root=target_root)
        payload["continuation_reorientation"] = _continuation_reorientation_payload(
            config=config,
            target_root=target_root,
            active_planning_present=active_planning_present,
            payload=payload,
            task_text=task_text,
            active_planning_record=active_planning_record,
            active_intent_contract=active_intent_contract,
        )
    if _selector_requests(select, "closeout_trust_inspection"):
        payload.setdefault(
            "closeout_trust_inspection",
            _completion_closeout_inspection_payload(
                target_root=target_root,
                config=config,
                task_text=task_text,
                explicit_request=True,
            ),
        )


def _selector_first_closeout_obligations(payload: dict[str, Any]) -> dict[str, Any]:
    obligations = payload.get("closeout_obligations", {})
    if not isinstance(obligations, dict):
        return {}
    task_intent = _as_dict(payload.get("task_intent"))
    requested_text = " ".join(
        [
            *(str(item) for item in _list_payload(task_intent.get("requested_outcomes"))),
            str(task_intent.get("implement_changed_command") or ""),
        ]
    ).lower()
    route_relevant = bool(payload.get("closeout_report_route")) or any(
        marker in requested_text
        for marker in ("planned", "plan", "lane", "release", "status", "complete", "completion", "closeout", "merge")
    )
    if not route_relevant:
        return {}
    compact = {
        key: obligations.get(key)
        for key in ("status", "activation_rule", "detail_command")
        if key in obligations and obligations.get(key) not in (None, "", [], {})
    }
    raw_route = _as_dict(obligations.get("ordinary_closeout_route"))
    route = {
        key: raw_route.get(key)
        for key in ("status", "first_inspection", "substitute_command", "top_level_closeout_command")
        if raw_route.get(key) not in (None, "", [], {})
    }
    if route:
        compact["ordinary_closeout_route"] = route
    return compact


def _compact_start_continuation_view(view: Any) -> dict[str, Any]:
    if not isinstance(view, dict):
        return {}
    answers = _as_dict(view.get("answers"))
    proof_state = _as_dict(view.get("proof_state"))
    claim_boundary = _as_dict(view.get("claim_boundary"))
    resume_predicate = _as_dict(view.get("resume_predicate"))
    drill_down = _as_dict(view.get("drill_down"))
    return {
        "kind": view.get("kind", "agentic-planning/continuation-view/v1"),
        "status": view.get("status", "unknown"),
        "answers": {
            key: answers.get(key)
            for key in ("claim_allowed", "next_safe_action", "trust_basis")
            if answers.get(key) not in (None, "", [], {})
        },
        "proof_state": {
            key: proof_state.get(key) for key in ("status", "summary", "known_gap") if proof_state.get(key) not in (None, "", [], {})
        },
        "claim_boundary": {
            key: claim_boundary.get(key)
            for key in ("status", "claim_level_allowed", "required_next_action", "blocked_claim_classes")
            if claim_boundary.get(key) not in (None, "", [], {})
        },
        "resume_predicate": {
            key: resume_predicate.get(key)
            for key in ("status", "failed", "required_next_action")
            if resume_predicate.get(key) not in (None, "", [], {})
        },
        "detail_routes": {
            key: drill_down.get(key)
            for key in ("summary_verbose", "planning_record", "proof", "claim_boundary", "owner_sources")
            if drill_down.get(key)
        },
    }


def _compact_start_continuation_reorientation(packet: Any) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return {}
    next_action = _as_dict(packet.get("next_safe_action"))
    proof_boundary = _as_dict(packet.get("proof_claim_boundary"))
    return {
        "kind": packet.get("kind", "agentic-workspace/continuation-reorientation/v1"),
        "status": packet.get("status", "unknown"),
        "active_intent_refs": packet.get("active_intent_refs", [])[:4],
        "next_safe_action": {
            key: next_action.get(key)
            for key in ("action", "summary", "risk", "next_proof")
            if next_action.get(key) not in (None, "", [], {})
        },
        "proof_claim_boundary": {
            key: proof_boundary.get(key) for key in ("proof", "claim_allowed") if proof_boundary.get(key) not in (None, "", [], {})
        },
        "detail_routes": {
            "continuation_view": "agentic-workspace summary --select continuation_view --format json",
            "active_intent_contract": "agentic-workspace start --target . --select active_intent_contract --format json",
        },
    }


def _apply_required_payload_target_start_gate(
    *, payload: dict[str, Any], target_root: Path, config: WorkspaceConfig, startup_template: dict[str, Any]
) -> None:
    installed_state = payload.get("installed_state_compatibility")
    if not isinstance(installed_state, dict):
        return
    action_effect = _as_dict(installed_state.get("action_effect"))
    action_state = _as_dict(installed_state.get("action_state"))
    payload_target = _as_dict(action_state.get("payload_target"))
    if action_effect.get("force") != "required_before_execution" or payload_target.get("policy") != "required-before-work":
        return
    command = str(action_effect.get("resolution_command") or action_state.get("dry_run_command") or "")
    recheck_command = str(action_state.get("recheck_command") or payload_target.get("recheck_command") or "")
    payload_repair_subflow = _as_dict(installed_state.get("payload_repair_subflow"))
    if payload_repair_subflow:
        payload["payload_repair_subflow"] = payload_repair_subflow
    payload["workflow_sufficiency"] = _workflow_sufficiency_payload(
        surface="start",
        decision="installed-payload-target-required-before-work",
        reason="Repo-declared payload target policy requires explicit sync before ordinary workspace work.",
        required_next_action="run-installed-payload-target-upgrade",
        evidence_required=["installed payload target recheck"],
        hard_gate=True,
    )
    payload["immediate_next_allowed_action"] = {
        "action": "run-installed-payload-target-upgrade",
        "summary": str(installed_state.get("reason") or action_effect.get("claim_boundary") or ""),
        "command": command,
        "run": command,
        "risk": "required-before-work payload target gate",
        "required_inputs": ["target repo"],
        "next_proof": recheck_command or f"{config.cli_invoke} start --target {target_root.as_posix()} --format json",
        "read_first": [command] if command else [],
        "open_execplan_only_when": startup_template["open_execplan_only_when"],
        **({"payload_repair_subflow": payload_repair_subflow} if payload_repair_subflow else {}),
    }


def _selector_first_start_payload(payload: dict[str, Any], *, cli_invoke: str, target_root: Path | None = None) -> dict[str, Any]:
    skill_routing = payload.get("skill_routing", {}) if isinstance(payload.get("skill_routing"), dict) else {}
    read_only_response = payload.get("read_only_response", {})
    read_only_compact_default = bool(isinstance(read_only_response, dict) and read_only_response.get("compact_default") is True)
    next_safe_action = _next_safe_action_packet(
        immediate=payload["immediate_next_allowed_action"],
        workflow_sufficiency=payload.get("workflow_sufficiency"),
        skill_routing=payload.get("skill_routing"),
        memory_consult=payload.get("memory_consult"),
    )
    next_safe_action = _compact_selector_next_safe_action(next_safe_action)
    workflow_payload = payload.get(
        "workflow_sufficiency",
        _workflow_sufficiency_payload(
            surface="start",
            decision="enough-for-first-contact-routing",
            reason="Use the next action and selectors; no raw workspace files are needed yet.",
        ),
    )
    compact_workflow = _tiny_workflow_sufficiency(workflow_payload)
    if read_only_compact_default:
        compact_workflow = {
            key: compact_workflow.get(key)
            for key in ("kind", "surface", "sufficiency_result", "required_next_action", "evidence_required")
            if compact_workflow.get(key) not in (None, "", [], {})
        }
    context: dict[str, Any] = {
        "primary_action": {
            **payload["immediate_next_allowed_action"],
            "read_first": payload["immediate_next_allowed_action"].get("read_first", []),
        },
        **({"route_decision": _compact_start_route_decision(payload.get("route_decision"))} if payload.get("route_decision") else {}),
        "active_state": _active_state_with_orientation_delta(payload.get("active_state_summary", {}), cli_invoke=cli_invoke),
        "skill_routing": {
            "status": skill_routing.get("status", "unknown") if isinstance(skill_routing, dict) else "unknown",
            "detail_selector": "skill_routing",
        },
        "planning": {
            "workflow_sufficiency": compact_workflow,
            **(
                {"planning_safety_gate": _selector_first_planning_safety_gate(payload["planning_safety_gate"])}
                if "planning_safety_gate" in payload
                else {}
            ),
        },
        "memory": {
            "status": payload.get("memory_consult", {}).get("status", "unknown")
            if isinstance(payload.get("memory_consult"), dict)
            else "unknown",
            "detail_selector": "memory_decision_packet",
        }
        if read_only_compact_default
        else payload.get("memory_consult", {}),
    }
    compact_closeout_obligations = _selector_first_closeout_obligations(payload)
    if compact_closeout_obligations:
        context["closeout_obligations"] = compact_closeout_obligations
    payload_repair_subflow = payload.get("payload_repair_subflow")
    if isinstance(payload_repair_subflow, dict) and payload_repair_subflow:
        context["payload_repair_subflow"] = {
            key: payload_repair_subflow.get(key)
            for key in (
                "kind",
                "status",
                "repair_mechanism",
                "safe_explicit_apply",
                "manual_review_required",
                "start_mutates",
                "next_action",
                "steps",
                "reportable_commands",
                "machine_commands",
                "detail_selector",
                "rule",
            )
            if payload_repair_subflow.get(key) not in (None, "", [], {})
        }
    local_checkpoint = payload.get("local_chat_checkpoint", {})
    work_threads = payload.get("work_threads", {})
    if isinstance(local_checkpoint, dict) and _local_chat_checkpoint_default_visible(local_checkpoint, payload=payload):
        context["local_chat_checkpoint"] = {
            key: local_checkpoint.get(key)
            for key in (
                "status",
                "path",
                "task",
                "durable_source_count",
                "durable_sources",
                "resume_rule",
                "next_safe_command",
                "volatile_observations",
                "local_notes",
                "proof_state",
                "resume_checklist",
                "planning_candidate_routes",
                "detail_command",
                "authority",
            )
            if key in local_checkpoint
        }
    if isinstance(work_threads, dict) and _local_work_threads_default_visible(work_threads) and not read_only_compact_default:
        context["work_threads"] = {
            key: work_threads.get(key)
            for key in (
                "status",
                "path",
                "thread_count",
                "current_match_count",
                "stale_count",
                "selected_thread",
                "current_matches",
                "stale_threads",
                "checkpoint_bridge",
                "selection_routes",
                "cleanup",
                "claim_boundary",
                "durable_promotion_rule",
                "authority",
            )
            if key in work_threads
        }
    parent_intent_packet = payload.get("parent_intent_status", {})
    if isinstance(parent_intent_packet, dict) and parent_intent_packet.get("status") not in {None, "", "not-recorded", "guidance-only"}:
        context["parent_intent_status"] = {
            key: parent_intent_packet.get(key)
            for key in (
                "status",
                "original_intent",
                "current_slice",
                "proof_boundary",
                "proof_is_slice_only",
                "residual_parent_intent",
                "parent_proof_required",
            )
            if key in parent_intent_packet
        }
    if isinstance(payload.get("applicable_intent_status"), dict):
        context["applicable_intent_status"] = {
            key: payload["applicable_intent_status"].get(key)
            for key in (
                "status",
                "conflicts",
                "missing_authority",
                "manual_verification_needed",
                "blocked_claims",
                "closeout_blocked",
            )
            if key in payload["applicable_intent_status"]
        }
    pre_test_guardrail = payload.get("pre_test_evidence_guardrail", {})
    if isinstance(pre_test_guardrail, dict) and pre_test_guardrail.get("status") == "advisory":
        context["pre_test_evidence_guardrail"] = pre_test_guardrail
    task_path_references = payload.get("task_path_references", {})
    if isinstance(task_path_references, dict) and task_path_references.get("status") == "present":
        context["task_path_references"] = task_path_references
    architecture_forecast = payload.get("architecture_principles_forecast", {})
    if (
        isinstance(architecture_forecast, dict)
        and architecture_forecast.get("status")
        in {
            "provisional-match",
            "needs-planned-scope",
        }
        and not read_only_compact_default
    ):
        context["architecture_principles_forecast"] = architecture_forecast
    pr_comment_attention = payload.get("pr_comment_attention", {})
    if isinstance(pr_comment_attention, dict) and pr_comment_attention.get("status") not in {None, "", "not_applicable"}:
        context["pr_comment_attention"] = {
            key: pr_comment_attention.get(key)
            for key in (
                "kind",
                "status",
                "repository",
                "pr_number",
                "comment_state",
                "actionable_count",
                "new_comment_count",
                "stack_member_count",
                "recommended_command",
                "cache_selector_command",
                "live_inspection",
                "pr_resolution",
                "write_safety",
                "claim_boundary",
            )
            if key in pr_comment_attention
        }
        context["pr_comment_attention"]["absence_states"] = {
            "stack_membership": "unavailable"
            if pr_comment_attention.get("status") == "stack_comment_status_unavailable"
            else "detail_omitted",
            "thread_level_comments": "hidden_behind_detail_route",
        }
        comment_addressing = pr_comment_attention.get("comment_addressing", {})
        if isinstance(comment_addressing, dict) and comment_addressing:
            closeout = comment_addressing.get("closeout", {}) if isinstance(comment_addressing.get("closeout"), dict) else {}
            context["pr_comment_attention"]["comment_addressing"] = {
                key: comment_addressing.get(key)
                for key in ("kind", "status", "bucket_counts", "changed_files")
                if comment_addressing.get(key) not in (None, "", [], {})
            }
            if closeout:
                context["pr_comment_attention"]["comment_addressing"]["closeout"] = {
                    key: closeout.get(key) for key in ("status", "rule") if closeout.get(key) not in (None, "", [], {})
                }
        review_stack_continuity = _as_dict(pr_comment_attention.get("review_stack_continuity"))
        if review_stack_continuity:
            affected_slice = _as_dict(review_stack_continuity.get("affected_slice"))
            proof_manifest = _as_dict(review_stack_continuity.get("incremental_proof_manifest"))
            next_action = _as_dict(review_stack_continuity.get("next_action"))
            closeout_route = _as_dict(review_stack_continuity.get("closeout_route"))
            planning_owner = _as_dict(review_stack_continuity.get("planning_owner"))
            workflow_trace = _as_dict(review_stack_continuity.get("workflow_trace"))
            context["pr_comment_attention"]["review_stack_continuity"] = {
                "kind": review_stack_continuity.get("kind"),
                "status": review_stack_continuity.get("status"),
                "phase": review_stack_continuity.get("phase"),
                "current_pr_number": review_stack_continuity.get("current_pr_number"),
                "dependency_order": review_stack_continuity.get("dependency_order", []),
                "affected_slice": {
                    key: affected_slice.get(key)
                    for key in ("status", "pr_number", "branch", "actionable_count", "paths", "proof_hints", "path_source")
                    if affected_slice.get(key) not in (None, "", [], {})
                },
                "review_findings": review_stack_continuity.get("review_findings", {}),
                "incremental_proof_manifest": {
                    key: proof_manifest.get(key)
                    for key in (
                        "status",
                        "changed_effect_paths",
                        "proof_hints",
                        "proof_reuse_status",
                        "reusable_groups",
                        "proof_selection_command_template",
                        "path_source",
                    )
                    if proof_manifest.get(key) not in (None, "", [], {})
                },
                "next_action": {key: next_action.get(key) for key in ("id", "phase", "command") if next_action.get(key)},
                "closeout_route": {
                    key: closeout_route.get(key) for key in ("status", "command", "parent_boundary") if closeout_route.get(key)
                },
                "planning_owner": {
                    key: planning_owner.get(key)
                    for key in ("status", "surface", "id", "phase", "phase_source", "transition_records")
                    if planning_owner.get(key)
                },
                "workflow_trace": {
                    key: workflow_trace.get(key)
                    for key in (
                        "status",
                        "member_count",
                        "phase_sequence",
                        "current_phase",
                        "commands",
                        "transition_source",
                        "executed_events",
                        "proof_reuse_status",
                        "interaction_cost",
                    )
                    if workflow_trace.get(key) not in (None, "", [], {})
                },
            }
        context["pr_comment_attention"]["detail_route"] = pr_comment_attention.get(
            "recommended_command", "agentic-workspace report --target . --section pr_comment_attention --format json"
        )
    installed_state_triage = payload.get("installed_state_drift_triage", {})
    if isinstance(installed_state_triage, dict) and installed_state_triage.get("status") in {"actionable_now", "claim_blocking"}:
        context["installed_state_drift_triage"] = _compact_installed_state_drift_triage(installed_state_triage)
    dogfooding_signal_status = payload.get("dogfooding_signal_status", {})
    if isinstance(dogfooding_signal_status, dict) and dogfooding_signal_status.get("status") not in {None, "", "not_applicable"}:
        if read_only_compact_default:
            context["dogfooding_signal_status"] = {
                "status": dogfooding_signal_status.get("status"),
                "selector": dogfooding_signal_status.get("selector", "dogfooding_signal_status"),
            }
        else:
            context["dogfooding_signal_status"] = {
                key: dogfooding_signal_status.get(key)
                for key in (
                    "kind",
                    "status",
                    "outcome",
                    "closeout_blocked",
                    "destinations",
                    "dismissal_reason",
                    "deferred_reason",
                    "signal_count",
                    "sample_signals",
                    "durability",
                    "durable_residue",
                    "canonical_repo_history",
                    "detail_command",
                    "selector",
                )
                if key in dogfooding_signal_status and dogfooding_signal_status.get(key) not in (None, "", [], {}, False, 0)
            }
    uv_guidance = payload.get("uv_cache_guidance", {})
    if not (isinstance(uv_guidance, dict) and uv_guidance.get("status") == "available"):
        cli_invocation = payload.get("cli_invocation", {})
        primary = str(cli_invocation.get("primary", "")) if isinstance(cli_invocation, dict) else ""
        uv_guidance = _uv_cache_guidance_payload(cli_invoke=primary)
    prep_only_active = "prep_only_handoff" in payload
    if "task_intent" in payload:
        task_intent = payload["task_intent"]
        context["task"] = (
            {
                "status": task_intent.get("status", "unknown") if isinstance(task_intent, dict) else "unknown",
                "requested_outcomes": task_intent.get("requested_outcomes", [])[:8] if isinstance(task_intent, dict) else [],
                "task_argument_mode": task_intent.get("task_argument_mode") if isinstance(task_intent, dict) else None,
            }
            if prep_only_active
            else {
                "status": task_intent.get("status", "unknown") if isinstance(task_intent, dict) else "unknown",
                "requested_outcomes": task_intent.get("requested_outcomes", [])[:8] if isinstance(task_intent, dict) else [],
                "task_argument_mode": task_intent.get("task_argument_mode") if isinstance(task_intent, dict) else None,
                "detail_selector": "acceptance",
            }
            if read_only_compact_default
            else {
                "status": task_intent.get("status", "unknown") if isinstance(task_intent, dict) else "unknown",
                "carry_forward_rule": task_intent.get("carry_forward_rule", "") if isinstance(task_intent, dict) else "",
                "requested_outcomes": task_intent.get("requested_outcomes", [])[:8] if isinstance(task_intent, dict) else [],
                "implement_changed_command": task_intent.get("implement_changed_command") if isinstance(task_intent, dict) else None,
                "task_argument_mode": task_intent.get("task_argument_mode") if isinstance(task_intent, dict) else None,
            }
        )
        if isinstance(task_intent, dict) and "acceptance" in task_intent and not prep_only_active and not read_only_compact_default:
            context["task"]["acceptance_item_count"] = (
                len(task_intent["acceptance"].get("items", [])) if isinstance(task_intent.get("acceptance"), dict) else 0
            )
            context["task"]["acceptance_detail_selector"] = "acceptance"
        if read_only_compact_default:
            context["read_only_response"] = {
                "status": read_only_response.get("status", "unknown") if isinstance(read_only_response, dict) else "unknown",
                "compact_default": True,
                "detail_selector": "read_only_response",
            }
        for optional_key in ("task_file", "task_file_instruction", "task_excerpt", "task_digest", "task_text_length"):
            if isinstance(task_intent, dict) and optional_key in task_intent:
                context["task"][optional_key] = task_intent[optional_key]
    if "repair_plan_profile" in payload:
        context["repair_plan_profile"] = payload["repair_plan_profile"]
    startup_changed_signals: list[str] = []
    planning_gate = payload.get("planning_safety_gate", {})
    if isinstance(planning_gate, dict) and planning_gate.get("status") not in {None, "", "clear"}:
        startup_changed_signals.append(
            f"planning_safety={planning_gate.get('status')}:{planning_gate.get('gate_result') or planning_gate.get('decision')}"
        )
    if isinstance(payload.get("cli_compatibility"), dict) and payload["cli_compatibility"].get("status") in {
        "advisory-drift",
        "blocking-drift",
        "warning-drift",
    }:
        startup_changed_signals.append(f"cli_compatibility={payload['cli_compatibility'].get('status')}")
    installed_state = payload.get("installed_state_compatibility", {})
    if isinstance(installed_state, dict) and installed_state.get("status") not in {None, "", "compatible"}:
        startup_changed_signals.append(f"installed_state_compatibility={installed_state.get('status')}")
    if isinstance(installed_state_triage, dict) and installed_state_triage.get("status") not in {None, "", "not_applicable"}:
        startup_changed_signals.append(f"installed_state_drift_triage={installed_state_triage.get('status')}")
    if isinstance(local_checkpoint, dict) and local_checkpoint.get("status") in {"present", "stale", "unreadable"}:
        startup_changed_signals.append(f"local_chat_checkpoint={local_checkpoint.get('status')}")
    if isinstance(work_threads, dict) and work_threads.get("status") in {
        "clear-match",
        "ambiguous",
        "stale",
        "selected-missing",
        "unreadable",
    }:
        startup_changed_signals.append(f"work_threads={work_threads.get('status')}")
    sibling_freshness = payload.get("sibling_repo_aw_freshness", {})
    if isinstance(sibling_freshness, dict) and sibling_freshness.get("status") == "attention":
        startup_changed_signals.append("sibling_repo_aw_freshness=attention")
    local_footprint = payload.get("local_footprint", {})
    if isinstance(local_footprint, dict) and local_footprint.get("status") == "attention":
        startup_changed_signals.append("local_footprint=attention")
    if isinstance(pre_test_guardrail, dict) and pre_test_guardrail.get("status") == "advisory":
        startup_changed_signals.append("pre_test_evidence=advisory")
    if isinstance(pr_comment_attention, dict) and pr_comment_attention.get("status") not in {None, "", "not_applicable"}:
        startup_changed_signals.append(f"pr_comment_attention={pr_comment_attention.get('status')}")
        review_stack_continuity = pr_comment_attention.get("review_stack_continuity")
        if isinstance(review_stack_continuity, dict) and review_stack_continuity.get("phase"):
            startup_changed_signals.append(f"review_stack_phase={review_stack_continuity.get('phase')}")
    if isinstance(dogfooding_signal_status, dict) and dogfooding_signal_status.get("status") not in {None, "", "not_applicable"}:
        startup_changed_signals.append(f"dogfooding_signal_status={dogfooding_signal_status.get('status')}")
    startup_proof = payload.get("proof", {})
    startup_proof_commands = _tiny_required_proof_commands(startup_proof) if isinstance(startup_proof, dict) else []
    startup_local_overlay = startup_proof.get("local_overlay", {}) if isinstance(startup_proof, dict) else {}
    if isinstance(startup_local_overlay, dict) and startup_local_overlay.get("status") == "active":
        startup_changed_signals.append(f"local_overlay={startup_local_overlay.get('active_count', 0)}")
    startup_high_risk_overlay = startup_proof.get("high_risk_overlay", {}) if isinstance(startup_proof, dict) else {}
    if isinstance(startup_high_risk_overlay, dict) and startup_high_risk_overlay.get("status") == "active":
        startup_changed_signals.append(f"high_risk_overlay={startup_high_risk_overlay.get('active_count', 0)}")
    available_selectors = _available_selectors_for_payload(payload)
    available_selectors = [selector for selector in available_selectors if not selector.startswith("workflow_participation")]
    if "routine_work_context" not in available_selectors:
        available_selectors.append("routine_work_context")
    if (
        target_root is not None
        and "local_chat_checkpoint" not in available_selectors
        and (target_root / ".agentic-workspace" / "local" / "chat-checkpoint.json").is_file()
    ):
        available_selectors.append("local_chat_checkpoint")
    if (
        target_root is not None
        and "work_threads" not in available_selectors
        and (target_root / ".agentic-workspace" / "local" / "work-threads").is_dir()
    ):
        available_selectors.append("work_threads")
    if "read_only_response" in payload and "acceptance" not in available_selectors:
        insert_at = (
            available_selectors.index("durable_intent_promotion")
            if "durable_intent_promotion" in available_selectors
            else len(available_selectors)
        )
        available_selectors.insert(insert_at, "acceptance")
    advisory_selectors = [
        "skill_routing",
        "workflow_sufficiency",
        "memory_decision_packet",
    ]
    if isinstance(installed_state, dict) and installed_state.get("status") not in {None, "", "compatible"}:
        advisory_selectors.append("installed_state_compatibility")
    if isinstance(installed_state_triage, dict) and installed_state_triage.get("status") not in {None, "", "not_applicable"}:
        advisory_selectors.append("installed_state_drift_triage")
    if isinstance(local_checkpoint, dict) and local_checkpoint.get("status") in {"present", "stale", "unreadable"}:
        advisory_selectors.append("local_chat_checkpoint")
    if isinstance(work_threads, dict) and work_threads.get("status") in {
        "clear-match",
        "ambiguous",
        "stale",
        "selected-missing",
        "unreadable",
    }:
        advisory_selectors.append("work_threads")
    if isinstance(local_footprint, dict) and local_footprint.get("status") == "attention":
        advisory_selectors.append("local_footprint")
    if isinstance(pre_test_guardrail, dict) and pre_test_guardrail.get("status") == "advisory":
        advisory_selectors.append("pre_test_evidence_guardrail")
    if isinstance(pr_comment_attention, dict) and pr_comment_attention.get("status") not in {None, "", "not_applicable"}:
        advisory_selectors.append("pr_comment_attention")
    if isinstance(dogfooding_signal_status, dict) and dogfooding_signal_status.get("status") not in {None, "", "not_applicable"}:
        advisory_selectors.append("dogfooding_signal_status")
    if isinstance(startup_local_overlay, dict) and startup_local_overlay.get("status") == "active":
        advisory_selectors.append("proof.local_overlay")
    if isinstance(startup_high_risk_overlay, dict) and startup_high_risk_overlay.get("status") == "active":
        advisory_selectors.append("proof.high_risk_overlay")
    selector_sample = list(dict.fromkeys([*advisory_selectors, *available_selectors[:4]]))[:8]
    selected: dict[str, Any] = {
        "kind": payload["kind"],
        "target": ".",
        "workflow_participation": _workflow_participation_payload(surface="start", compact=True),
        "action_signals": _compact_action_signals_payload(
            surface="start",
            allowed_next_action=str(next_safe_action.get("next_safe_action", "")),
            hard_blockers=next_safe_action.get("closure_blockers", []),
            implementation_allowed=bool(next_safe_action.get("implementation_allowed")),
            read_only_allowed=bool(next_safe_action.get("read_only_allowed")),
            proof_required=bool(next_safe_action.get("proof_required")),
            proof_commands=startup_proof_commands,
            changed_signals=startup_changed_signals,
            advisory_selectors=advisory_selectors,
            agent_judgment="Agent owns work-shape unless blocked.",
        ),
        "next_safe_action": next_safe_action,
        "decision_packet": _ordinary_decision_packet(
            surface="start",
            phase_question="Startup posture?",
            next_action=str(next_safe_action.get("next_safe_action", "")),
            blocked_actions=[str(item) for item in next_safe_action.get("forbidden_actions", []) if str(item).strip()],
            required_commands=[
                *dict.fromkeys(
                    str(item)
                    for item in [
                        next_safe_action.get("preferred_cli"),
                        payload.get("immediate_next_allowed_action", {}).get("command")
                        if isinstance(payload.get("immediate_next_allowed_action"), dict)
                        else "",
                        *startup_proof_commands,
                    ]
                    if item not in (None, "", []) and str(item).strip() and str(item).strip().lower() != "none"
                )
            ],
            claim_boundary=next_safe_action.get("claim_boundary", "completion claim requires proof"),
            residue_owner="active continuation state" if payload.get("active_state_summary", {}).get("active_execplan") else "none",
            reasons=startup_changed_signals[:6],
            detail_routes={
                "why_blocked": f"{cli_invoke} start --target . --select next_safe_action,action_signals --format json",
                "active_plan": (
                    f"{cli_invoke} start --target . --select active_state_summary,continuation_view --format json"
                    if _active_state_has_planning(payload.get("active_state_summary", {}))
                    else f"{cli_invoke} summary --target . --format json"
                ),
                "proof_detail": f"{cli_invoke} proof --target . --changed <paths> --format json",
            },
            shown_because=["command_phase=start", *startup_changed_signals[:3]],
            absence_states={
                "full_selector_inventory": "hidden_behind_detail_route",
                "verbose_planning_detail": "detail_omitted",
            },
        ),
        "communication_contract": compact_communication_contract_payload(surface="startup"),
        "skills": (
            {
                "kind": "agentic-workspace/startup-skills-projection/v1",
                "status": "selector-only",
                "rule": "Read-only compact startup omits skill packet detail; use the catalog selector only when needed.",
                "required": [],
                "recommended": [],
                "catalog": {
                    "available": True,
                    "detail_selector": "skills",
                    "command": f'{cli_invoke} skills --target "{target_root or Path(".")}" --task "<task>" --format json',
                },
            }
            if read_only_compact_default
            else _startup_skills_projection(
                payload=payload,
                next_safe_action=next_safe_action,
                target_root=target_root,
                cli_invoke=cli_invoke,
            )
        ),
        "context": context,
        "drill_down": {
            "ordinary_profile": "primary=next;skills=proj;detail=select",
            "rule": "Compact default omits selector inventory/schemas; use --select or --verbose for detail.",
            "selector_inventory": {
                "status": "omitted-from-compact-default",
                "available_count": len(available_selectors),
                "sample": selector_sample,
                "exact_select_command": f"{cli_invoke} start --target . --select <field[,field...]> --format json",
                "broad_diagnostics_command": f"{cli_invoke} start --target . --verbose --format json",
            },
        },
    }
    if isinstance(payload.get("decision_point_intent_carry"), dict):
        selected["decision_point_intent_carry"] = payload["decision_point_intent_carry"]
    if read_only_compact_default:
        decision = selected.get("decision_packet", {})
        if isinstance(decision, dict):
            selected["decision_packet"] = {
                key: decision.get(key)
                for key in (
                    "kind",
                    "surface",
                    "phase_question",
                    "next_action",
                    "blocked_actions",
                    "reasons",
                    "shown_because",
                    "absence_states",
                )
                if decision.get(key) not in (None, "", [], {})
            }
            if decision.get("claim_boundary") not in (None, "", [], {}):
                claim_boundary = str(decision.get("claim_boundary"))
                selected["decision_packet"]["claim_boundary"] = (
                    claim_boundary if len(claim_boundary) <= 180 else f"{claim_boundary[:177]}..."
                )
        selected["communication_contract"] = {
            "status": "selector-only",
            "detail_selector": "communication_contract",
            "rule": "Read-only compact startup keeps the decision visible; use the selector for full response-shape detail.",
        }
        selected["drill_down"]["omitted_detail"] = {
            "selectors": [
                "planning_safety_gate",
                "active_state_summary",
                "work_threads",
                "installed_state_compatibility",
                "installed_state_drift_triage",
                "memory_decision_packet",
                "architecture_principles_forecast",
                "drill_down.selector_inventory",
            ],
            "rule": "Reflection/reporting defaults stay decision-first; exact selectors expose omitted diagnostics.",
        }
    task_posture_packet = payload.get("task_posture_packet", {})
    if isinstance(task_posture_packet, dict) and task_posture_packet:
        selected["task_posture_packet"] = _compact_task_posture_packet_projection(task_posture_packet)
    show_state_delta_packets = (
        str(next_safe_action.get("next_safe_action", "")) not in {"choose-task-switch-route", "inspect-current-task-scope"}
        and not isinstance(payload.get("installed_state_compatibility"), dict)
        and not read_only_compact_default
    )
    if show_state_delta_packets:
        state_delta_core = state_delta_core_payload(
            surface="startup",
            decision_packet=selected["decision_packet"],
            communication_contract=compact_communication_contract_payload(surface="startup"),
            evidence_basis=[
                "next_safe_action",
                "action_signals",
                "active planning summary" if payload.get("active_state_summary", {}).get("active_execplan") else "startup routing state",
            ],
            safe_probe=str(
                next_safe_action.get("preferred_cli") or selected["decision_packet"].get("detail_routes", {}).get("active_plan") or ""
            ),
        )
        selected["message_economy"] = message_economy_payload(
            surface="startup",
            communication_contract=compact_communication_contract_payload(surface="startup"),
            state_delta_core=state_delta_core,
        )
        selected["current_decision"] = current_decision_payload(
            surface="startup",
            decision_packet=selected["decision_packet"],
            state_delta_core=state_delta_core,
        )
        continuation_answers = (
            payload.get("continuation_view", {}).get("answers", {}) if isinstance(payload.get("continuation_view"), dict) else {}
        )
        if isinstance(payload.get("continuation_view"), dict):
            selected["continuation_capsule"] = continuation_capsule_payload(
                surface="startup",
                current_decision=selected["current_decision"],
                message_economy=selected["message_economy"],
                preserved_intent=str(continuation_answers.get("preserved_intent", "")) if isinstance(continuation_answers, dict) else "",
                state_delta_core=state_delta_core,
                work_shape_study=(payload.get("planning_safety_gate", {}) or {}).get("work_shape_study", {}),
            )
        selected["evidence_bundle"] = evidence_bundle_payload(
            surface="startup", current_decision=selected["current_decision"], state_delta_core=state_delta_core
        )
    if isinstance(payload.get("continuation_view"), dict) or isinstance(payload.get("continuation_reorientation"), dict):
        drill_down: dict[str, Any] = selected["drill_down"]
        omitted_detail = drill_down.get("omitted_detail")
        if not isinstance(omitted_detail, dict):
            omitted_detail = {}
            drill_down["omitted_detail"] = omitted_detail
        omitted_detail["continuation"] = {
            "absence_state": "hidden_behind_detail_route",
            "detail_routes": {
                "continuation_view": f"{cli_invoke} summary --target . --select continuation_view --format json",
                "continuation_reorientation": f"{cli_invoke} start --target . --select continuation_reorientation --format json",
            },
        }
    if "task_intent" in payload:
        task_intent = payload["task_intent"]
        if (
            isinstance(task_intent, dict)
            and isinstance(task_intent.get("promotion_guidance"), dict)
            and (task_intent["promotion_guidance"].get("status") == "candidate")
        ):
            context["durable_intent_promotion"] = _tiny_task_intent_promotion_guidance(task_intent["promotion_guidance"])
    delegation = payload.get("delegation_decision", {})
    delegation_route = delegation.get("recommended_route") or delegation.get("decision") if isinstance(delegation, dict) else None
    delegation_config_effect = delegation.get("config_effect", {}) if isinstance(delegation, dict) else {}
    delegation_config_changes_behavior = isinstance(delegation_config_effect, dict) and (
        delegation_config_effect.get("configured_delegation_mode") != delegation_config_effect.get("delegation_mode")
        or delegation_config_effect.get("disabled_reason") not in (None, "")
        or (
            delegation_config_effect.get("configured_delegation_mode") == "auto"
            and delegation_config_effect.get("safe_to_auto_run_commands") is False
        )
    )
    if isinstance(delegation, dict) and (delegation_route not in {"", None, "stay-local"} or delegation_config_changes_behavior):
        context["delegation_decision"] = _compact_start_delegation_decision(delegation, include_manual_handoff_detail=False)
    cli_invocation = payload.get("cli_invocation", {})
    if isinstance(cli_invocation, dict) and cli_invocation.get("mismatch"):
        selected["cli_invocation"] = cli_invocation
    cli_compatibility = payload.get("cli_compatibility", {})
    if isinstance(cli_compatibility, dict) and cli_compatibility.get("status") in {
        "advisory-drift",
        "blocking-drift",
        "warning-drift",
    }:
        selected["cli_compatibility"] = cli_compatibility
    if isinstance(sibling_freshness, dict) and sibling_freshness.get("status") not in {None, "", "not-referenced"}:
        selected["sibling_repo_aw_freshness"] = sibling_freshness
    durable_intent = payload.get("durable_intent", {})
    subsystem_intent = durable_intent.get("subsystem_intent", {}) if isinstance(durable_intent, dict) else {}
    matched_count = int(subsystem_intent.get("matched_count", 0) or 0) if isinstance(subsystem_intent, dict) else 0
    if isinstance(durable_intent, dict) and durable_intent.get("status") == "present" and matched_count:
        context["durable_intent"] = _tiny_durable_intent(durable_intent)
    if "intent_evidence" in payload:
        context["intent_evidence"] = _compact_intent_evidence(payload.get("intent_evidence", {}))
    if "issue_reference_intent" in payload:
        context["issue_reference_intent"] = payload["issue_reference_intent"]
    for optional_key in (
        "proof",
        "path_boundaries",
        "startup_review",
        "prep_only_handoff",
        "routine_work_context",
        "closeout_trust_inspection",
        "closeout_report_route",
        "repo_posture",
        "intent_elicitation_protocol",
        "intent_discovery_dialogue",
        "vague_outcome_orientation",
        "intent_acknowledgement",
        "lane_shaping_gate",
        "open_issue_intake",
        "pre_test_evidence_guardrail",
    ):
        if optional_key in payload:
            if optional_key == "routine_work_context" and read_only_compact_default:
                continue
            context[optional_key] = payload[optional_key]
    maintainer_mode = payload.get("maintainer_mode", {})
    if isinstance(maintainer_mode, dict) and maintainer_mode.get("status") == "enabled":
        context["maintainer_mode"] = maintainer_mode
    return selected


def _active_state_with_orientation_delta(active_state: Any, *, cli_invoke: str) -> dict[str, Any]:
    if not isinstance(active_state, dict):
        return {}
    projected = dict(active_state)
    active_planning_present = _active_state_has_planning(projected)
    if active_planning_present and "orientation_delta" not in projected:
        projected["orientation_delta"] = {
            "status": "embedded",
            "summary_equivalent_for_first_contact": True,
            "detail_selectors": ["active_state_summary", "continuation_view", "next_safe_action", "action_signals"],
            "full_detail_command": _command_with_cli_invoke(
                command="agentic-workspace summary --target . --format json", cli_invoke=cli_invoke
            ),
            "rule": "Startup carries the compact active-planning facts needed for first-contact routing; run summary only for explicit detail or refresh.",
        }
    return projected


def _active_state_has_planning(active_state: Any) -> bool:
    if not isinstance(active_state, dict):
        return False
    return bool(
        active_state.get("todo_active_count")
        or active_state.get("active_execplan_count")
        or active_state.get("active_execplan")
        or active_state.get("planning_status") == "present"
    )


def _run_start_context_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="start", target_root=target_root)
    if prevalidation_error := _selector_prevalidation_error(select=getattr(args, "select", None), source_command="start"):
        _emit_payload(payload=prevalidation_error, format_name=args.format)
        return 0
    if args.format == "json":
        if recovery_payload := _obsolete_default_preset_start_recovery_payload(target_root=target_root):
            _emit_payload(payload=recovery_payload, format_name=args.format)
            return 0
    config = _load_workspace_config(target_root=target_root)
    if disabled_payload := _workspace_disabled_payload(target_root=target_root, command_name="start", config=config):
        _emit_payload(payload=disabled_payload, format_name=args.format)
        return 0
    start_profile = "full" if getattr(args, "verbose", False) else getattr(args, "profile", None)
    task_text = getattr(args, "task", None)
    selected_fields = getattr(args, "select", None)
    if inventory_payload := _selector_inventory_selected_payload(select=selected_fields, source_command="start"):
        _emit_payload(payload=inventory_payload, format_name=args.format)
        return 0
    payload = _start_payload(
        target_root=target_root,
        changed_paths=list(getattr(args, "changed", []) or []),
        task_text=task_text,
        profile=_start_profile_for_select(requested_profile=start_profile, select=selected_fields),
    )
    if selected_fields:
        _hydrate_selected_start_advisory_payloads(
            payload=payload,
            select=selected_fields,
            target_root=target_root,
            task_text=task_text,
            config=config,
        )
        payload = _select_payload_fields(payload, select=selected_fields, source_command="start")
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _raw_config_cli_invoke(*, target_root: Path, config_payload: dict[str, Any]) -> str:
    cli_invoke = DEFAULT_CLI_INVOKE
    raw_workspace = config_payload.get("workspace", {})
    if isinstance(raw_workspace, dict) and isinstance(raw_workspace.get("cli_invoke"), str) and raw_workspace["cli_invoke"].strip():
        cli_invoke = raw_workspace["cli_invoke"].strip()
    local_config_path = target_root / WORKSPACE_LOCAL_CONFIG_PATH
    if local_config_path.exists():
        try:
            local_payload = tomllib.loads(local_config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return cli_invoke
        local_workspace = local_payload.get("workspace", {})
        if (
            isinstance(local_workspace, dict)
            and isinstance(local_workspace.get("cli_invoke"), str)
            and local_workspace["cli_invoke"].strip()
        ):
            cli_invoke = local_workspace["cli_invoke"].strip()
    return cli_invoke


def _obsolete_default_preset_start_recovery_payload(*, target_root: Path) -> dict[str, Any] | None:
    config_path = target_root / WORKSPACE_CONFIG_PATH
    if not config_path.exists():
        return None
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    raw_workspace = payload.get("workspace", {})
    if not isinstance(raw_workspace, dict) or "default_preset" not in raw_workspace:
        return None
    preset = raw_workspace.get("default_preset")
    modules = payload.get("modules", {})
    has_replacement = isinstance(modules, dict) and isinstance(modules.get("enabled"), list)
    repair_safe = has_replacement
    cli_invoke = _raw_config_cli_invoke(target_root=target_root, config_payload=payload)
    return {
        "kind": "agentic-workspace/start-recovery/v1",
        "status": "recovery-required",
        "target": ".",
        "problem": {
            "kind": "agentic-workspace/config-migration/v1",
            "config_path": WORKSPACE_CONFIG_PATH.as_posix(),
            "obsolete_field": "workspace.default_preset",
            "observed_value": preset,
            "reason": "workspace.default_preset is no longer accepted by Agentic Workspace config loading.",
            "replacement": "[modules] enabled = [...]",
            "config_valid": False,
        },
        "automated_repair": {
            "safe": repair_safe,
            "reason": "replacement modules.enabled is already present" if repair_safe else "module selection cannot be inferred safely",
        },
        "next_safe_action": {
            "next_safe_action": "repair-config-before-work",
            "implementation_allowed": False,
            "read_only_allowed": True,
            "proof_required": False,
            "closure_blockers": ["stale workspace config blocks ordinary startup routing"],
            "recommended_action": (
                f"Edit {WORKSPACE_CONFIG_PATH.as_posix()} to remove [workspace].default_preset and declare [modules] enabled = [...]."
            ),
        },
        "recovery_packet": {
            "kind": "agentic-workspace/config-recovery-packet/v1",
            "source": WORKSPACE_CONFIG_PATH.as_posix(),
            "blocked_because": "ordinary start cannot load authoritative workspace config while obsolete fields remain",
            "next_safe_command": _command_with_cli_invoke(
                command="agentic-workspace config --target . --format json", cli_invoke=cli_invoke
            ),
            "agent_owns": ["choose the correct module list from repo context or ask the maintainer when unclear"],
            "human_owns": ["confirm module intent when the stale preset cannot be mapped safely"],
        },
    }
