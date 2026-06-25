"""Startup runtime packet builders for Agentic Workspace.

This module owns start/startup payload construction while the old monolith keeps
compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from agentic_workspace.config import WorkspaceConfig
from agentic_workspace.workspace_runtime_core import (
    _CONTEXT_TEMPLATES,
    _active_intent_contract_payload,
    _active_planning_record_for_report_section,
    _applicable_intent_status_payload,
    _apply_lane_shaping_gate_to_start_payload,
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
    _compact_intent_evidence,
    _compact_repair_plan_profile,
    _compact_repo_posture_projection,
    _compact_selector_next_safe_action,
    _compact_start_closeout_obligations,
    _compact_start_delegation_decision,
    _compact_start_prep_only_handoff,
    _compact_start_proof_payload,
    _compact_start_workflow_obligations,
    _compact_startup_installed_state_signal,
    _compact_task_posture_packet_projection,
    _completion_boundary_payload,
    _completion_closeout_inspection_payload,
    _context_router_family_payload,
    _continuation_reorientation_payload,
    _execution_posture_payload,
    _fast_installed_modules,
    _feature_tier_payload,
    _guidance_with_cli_invoke,
    _installed_state_compatibility_payload,
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
    _maintainer_mode_payload,
    _memory_consult_from_payload,
    _memory_consult_payload,
    _memory_decision_packet_payload,
    _module_operations,
    _module_registry,
    _next_safe_action_packet,
    _operating_posture_payload,
    _package_boundary_payload,
    _parent_intent_status_payload,
    _prep_only_handoff_payload,
    _raw_active_planning_record_for_closeout,
    _read_only_response_posture_payload,
    _repo_posture_payload,
    _routine_work_context_payload,
    _run_preflight_command,
    _selector_first_planning_safety_gate,
    _selector_requests,
    _sibling_repo_aw_freshness_payload,
    _start_tiny_payload_fast,
    _startup_closeout_report_route,
    _startup_continuation_view_payload,
    _startup_skill_routing_payload,
    _startup_skills_projection,
    _task_intent_carry_forward_payload,
    _task_intent_evidence_payload,
    _task_mentioned_existing_paths,
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
    _workflow_sufficiency_payload,
    _workspace_absence_startup_review,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _command_with_cli_invoke,
    _list_payload,
    _normalize_changed_paths,
)
from agentic_workspace.workspace_runtime_planning import (
    _planning_safety_gate_payload,
)
from agentic_workspace.workspace_runtime_proof import (
    _proof_selection_for_changed_paths,
)


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
        "feature_tier": {
            "active": compact_active_tier,
            "detail_command": feature_tier.get("detail_command", "agentic-workspace modules --target ./repo --format json")
            if isinstance(feature_tier, dict)
            else "agentic-workspace modules --target ./repo --format json",
        },
        "active_state_summary": payload["active_state_summary"],
        "planning_revision": payload.get("planning_revision", {}),
        "active_plan_reliance": payload.get("active_plan_reliance", {}),
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
        },
        "memory_consult": {
            "status": payload.get("memory_consult", {}).get("status", "unknown"),
            "read_first": payload.get("memory_consult", {}).get("read_first", []),
            "do_not_bulk_read": payload.get("memory_consult", {}).get("do_not_bulk_read", True),
        },
        **(
            {"local_chat_checkpoint": payload["local_chat_checkpoint"]}
            if isinstance(payload.get("local_chat_checkpoint"), dict)
            and payload["local_chat_checkpoint"].get("status") in {"present", "stale", "unreadable"}
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
        "routine_work_context": payload.get("routine_work_context", {}),
        "operating_posture": {
            "status": payload.get("operating_posture", {}).get("status", "unknown"),
            "required_behavior_summary": payload.get("operating_posture", {}).get("required_behavior_summary", ""),
        },
        "repo_posture": _compact_repo_posture_projection(payload.get("repo_posture", {})),
        "delegation_decision": _compact_start_delegation_decision(payload.get("delegation_decision", {})),
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
    projected["action_signals"] = _compact_action_signals_payload(
        surface="start",
        allowed_next_action=str(projected["next_safe_action"].get("next_safe_action", "")),
        hard_blockers=projected["next_safe_action"].get("closure_blockers", []),
        implementation_allowed=bool(projected["next_safe_action"].get("implementation_allowed")),
        read_only_allowed=bool(projected["next_safe_action"].get("read_only_allowed")),
        proof_required=bool(projected["next_safe_action"].get("proof_required")),
        proof_commands=_tiny_required_proof_commands(payload.get("proof", {})) if isinstance(payload.get("proof"), dict) else [],
        advisory_selectors=["skill_routing", "workflow_sufficiency"],
        agent_judgment="Agent owns work-shape choice unless hard_blockers names a gate.",
    )
    return projected


def _start_payload(
    *, target_root: Path, changed_paths: list[str], task_text: str | None = None, profile: str | None = None
) -> dict[str, Any]:
    startup_template = _CONTEXT_TEMPLATES["startup_context"]
    config = _load_workspace_config(target_root=target_root)
    if profile in {None, "tiny"}:
        payload = _start_tiny_payload_fast(
            target_root=target_root, changed_paths=changed_paths, task_text=task_text, config=config, startup_template=startup_template
        )
        normalized_paths = _normalize_changed_paths(changed_paths)
        task_posture_packet = _task_posture_packet_payload(
            config=config,
            surface="start",
            task_text=task_text,
            changed_paths=normalized_paths,
            workflow_obligations=payload.get("workflow_obligations", {}),
            skill_routing=payload.get("skill_routing", {}),
            planning_safety_gate=payload.get("planning_safety_gate", {}),
            proof=payload.get("proof", {}),
            compact=True,
        )
        if _task_posture_packet_relevant(
            task_text=task_text, changed_paths=normalized_paths, surface="start"
        ) and _task_posture_packet_changes_routing(task_posture_packet):
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
            "todo_active_count": active_state.get("todo", {}).get("active_count", 0),
            "active_execplan": active_execplan,
            "planning_status": planning_record.get("status", "unavailable") if isinstance(planning_record, dict) else "unavailable",
        },
        "workflow_sufficiency": _workflow_sufficiency_payload(
            surface="start",
            decision="active-planning-summary-needed" if active_planning_present else "enough-for-first-contact-routing",
            reason="Active planning exists; compact summary is next."
            if active_planning_present
            else "No active planning detected; choose the smallest shape and wait for changed paths before proof.",
            required_next_action="run summary" if active_planning_present else "choose-smallest-workflow-shape",
            evidence_required=["compact active planning summary"] if active_planning_present else [],
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
            "read_first": [_command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke)]
            if active_planning_present
            else [],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        },
        "workflow_obligations": compact_workflow_obligations,
        "closeout_obligations": _compact_start_closeout_obligations(
            preflight.get("closeout_obligations", {}),
            cli_invoke=config.cli_invoke,
            target_root=target_root,
        ),
        "memory_consult": _memory_consult_payload(
            target_root=target_root, changed_paths=changed_paths, compact=True, cli_invoke=config.cli_invoke
        ),
        "local_chat_checkpoint": _local_chat_checkpoint_projection(target_root=target_root, cli_invoke=config.cli_invoke),
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
    payload["memory_decision_packet"] = _memory_decision_packet_payload(
        stage="startup",
        cli_invoke=config.cli_invoke,
        memory_consult=_memory_consult_from_payload(payload),
        changed_paths=changed_paths,
        task_text=task_text,
    )
    if installed_state_compatibility["status"] != "compatible":
        payload["installed_state_compatibility"] = installed_state_compatibility
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
    if planning_safety_gate["status"] not in {"satisfied", "clear"}:
        payload["planning_safety_gate"] = planning_safety_gate
    if not planning_safety_gate["workflow_sufficient"] and (not _is_config_posture_task(task_text)):
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
            "command": planning_safety_gate["promotion_command"],
            "run": planning_safety_gate["promotion_command"],
            "risk": "planning-required-before-implementation",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "run summary after creating or promoting the active execplan",
            "read_first": [planning_safety_gate["promotion_command"]],
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
    if not active_planning_present and task_mentioned_paths and (not changed_paths) and (not _is_config_posture_task(task_text)):
        implement_command = str(task_intent.get("implement_changed_command", "")) if isinstance(task_intent, dict) else ""
        if implement_command:
            implement_command = implement_command.replace("<paths>", " ".join(task_mentioned_paths))
        else:
            implement_command = _command_with_cli_invoke(
                command=f"agentic-workspace implement --changed {' '.join(task_mentioned_paths)} --format json",
                cli_invoke=config.cli_invoke,
            )
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-known-task-paths",
            "summary": "The task text names existing repo paths. Run the implement surface for those paths before broader startup or raw workspace reads.",
            "command": implement_command,
            "run": implement_command,
            "risk": "read-only changed-path routing",
            "required_inputs": ["target repo", "named path(s)"],
            "next_proof": "use the proof.required_commands from implement output",
            "read_first": [implement_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
            "detected_paths": task_mentioned_paths,
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
            "command": planning_safety_gate["promotion_command"],
            "run": planning_safety_gate["promotion_command"],
            "risk": "planning-required-before-implementation",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "run summary after creating or promoting the active execplan",
            "read_first": [planning_safety_gate["promotion_command"]],
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
            changed_paths=normalized_paths, target_root=target_root, include_durable_intent=False
        )
        proof_command = str(
            _command_with_cli_invoke(
                command=f"agentic-workspace proof --changed {' '.join(normalized_paths)} --format json",
                cli_invoke=config.cli_invoke,
            )
        )
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
        repair_profile = _compact_repair_plan_profile(changed_paths=normalized_paths, task_text=task_text, proof_command=proof_command)
        if repair_profile["status"] == "direct-no-plan":
            payload["repair_plan_profile"] = repair_profile
        payload["path_boundaries"] = [
            _boundary_warning_for_path(path, agent_instructions_file=config.agent_instructions_file) for path in normalized_paths
        ]
    elif normalized_paths:
        proof_payload = _proof_selection_for_changed_paths(
            changed_paths=normalized_paths, target_root=target_root, include_durable_intent=False
        )
        payload["proof"] = _compact_start_proof_payload(proof_payload)
        repair_profile = _compact_repair_plan_profile(
            changed_paths=normalized_paths,
            task_text=task_text,
            proof_command=str(
                _command_with_cli_invoke(
                    command=f"agentic-workspace proof --changed {' '.join(normalized_paths)} --format json",
                    cli_invoke=config.cli_invoke,
                )
            ),
        )
        if repair_profile["status"] == "direct-no-plan":
            payload["repair_plan_profile"] = repair_profile
        payload["path_boundaries"] = [
            _boundary_warning_for_path(path, agent_instructions_file=config.agent_instructions_file) for path in normalized_paths
        ]
    task_posture_packet = _task_posture_packet_payload(
        config=config,
        surface="start",
        task_text=task_text,
        changed_paths=normalized_paths,
        workflow_obligations=workflow_obligations,
        skill_routing=payload.get("skill_routing", {}),
        planning_safety_gate=planning_safety_gate,
        proof=payload.get("proof", {}),
        compact=(profile == "tiny"),
    )
    if _task_posture_packet_relevant(
        task_text=task_text, changed_paths=normalized_paths, surface="start"
    ) and _task_posture_packet_changes_routing(task_posture_packet):
        payload["task_posture_packet"] = task_posture_packet
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
    if _selector_requests(select, "next_safe_action") or _selector_requests(select, "action_signals"):
        _attach_start_router_fields(payload)
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
        payload["planning_safety_gate"] = _planning_safety_gate_payload(
            target_root=target_root,
            config=config,
            changed_paths=[],
            task_text=task_text,
            execution_posture=execution_posture,
        )
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
    if _selector_requests(select, "local_chat_checkpoint"):
        payload["local_chat_checkpoint"] = _local_chat_checkpoint_projection(target_root=target_root, cli_invoke=config.cli_invoke)
    if _selector_requests(select, "installed_state_compatibility"):
        installed_modules = _fast_installed_modules(target_root=target_root)
        selected_modules = list(config.enabled_modules)
        payload["installed_state_compatibility"] = _installed_state_compatibility_payload(
            config=config,
            selected_modules=selected_modules,
            installed_modules=installed_modules,
            cli_compatibility=_cli_compatibility_payload(config=config, compact=True),
            compact=True,
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


def _selector_first_start_payload(payload: dict[str, Any], *, cli_invoke: str, target_root: Path | None = None) -> dict[str, Any]:
    skill_routing = payload.get("skill_routing", {}) if isinstance(payload.get("skill_routing"), dict) else {}
    next_safe_action = _next_safe_action_packet(
        immediate=payload["immediate_next_allowed_action"],
        workflow_sufficiency=payload.get("workflow_sufficiency"),
        skill_routing=payload.get("skill_routing"),
        memory_consult=payload.get("memory_consult"),
    )
    next_safe_action = _compact_selector_next_safe_action(next_safe_action)
    context: dict[str, Any] = {
        "primary_action": payload["immediate_next_allowed_action"],
        "active_state": payload["active_state_summary"],
        "skill_routing": {
            "status": skill_routing.get("status", "unknown") if isinstance(skill_routing, dict) else "unknown",
            "query": skill_routing.get("query", "") if isinstance(skill_routing, dict) else "",
            "preferred_routes": list(skill_routing.get("preferred_routes", [])[:2]) if isinstance(skill_routing, dict) else [],
        },
        "planning": {
            "workflow_sufficiency": _tiny_workflow_sufficiency(
                payload.get(
                    "workflow_sufficiency",
                    _workflow_sufficiency_payload(
                        surface="start",
                        decision="enough-for-first-contact-routing",
                        reason="Use the next action and selectors; no raw workspace files are needed yet.",
                    ),
                )
            ),
            **(
                {"planning_safety_gate": _selector_first_planning_safety_gate(payload["planning_safety_gate"])}
                if "planning_safety_gate" in payload
                else {}
            ),
        },
        "memory": payload.get("memory_consult", {}),
    }
    local_checkpoint = payload.get("local_chat_checkpoint", {})
    if isinstance(local_checkpoint, dict) and local_checkpoint.get("status") in {"present", "stale", "unreadable"}:
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
                "detail_command",
                "authority",
            )
            if key in local_checkpoint
        }
    if isinstance(payload.get("parent_intent_status"), dict):
        context["parent_intent_status"] = {
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
    uv_guidance = payload.get("uv_cache_guidance", {})
    if not (isinstance(uv_guidance, dict) and uv_guidance.get("status") == "available"):
        cli_invocation = payload.get("cli_invocation", {})
        primary = str(cli_invocation.get("primary", "")) if isinstance(cli_invocation, dict) else ""
        uv_guidance = _uv_cache_guidance_payload(cli_invoke=primary)
    if isinstance(uv_guidance, dict) and uv_guidance.get("status") == "available":
        context["uv_cache_guidance"] = uv_guidance
    prep_only_active = "prep_only_handoff" in payload
    if "task_intent" in payload:
        task_intent = payload["task_intent"]
        read_only_response = payload.get("read_only_response", {})
        read_only_compact_default = bool(isinstance(read_only_response, dict) and read_only_response.get("compact_default") is True)
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
                "response_posture": read_only_response,
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
            context["acceptance"] = _tiny_acceptance_payload(task_intent["acceptance"])
            if context["task"].get("task_argument_mode") == "task-file":
                context["acceptance"].pop("items", None)
                context["acceptance"].pop("proof_rule", None)
        if read_only_compact_default:
            context["read_only_response"] = read_only_response
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
    if isinstance(local_checkpoint, dict) and local_checkpoint.get("status") in {"present", "stale", "unreadable"}:
        startup_changed_signals.append(f"local_chat_checkpoint={local_checkpoint.get('status')}")
    sibling_freshness = payload.get("sibling_repo_aw_freshness", {})
    if isinstance(sibling_freshness, dict) and sibling_freshness.get("status") == "attention":
        startup_changed_signals.append("sibling_repo_aw_freshness=attention")
    startup_proof = payload.get("proof", {})
    startup_proof_commands = _tiny_required_proof_commands(startup_proof) if isinstance(startup_proof, dict) else []
    available_selectors = _available_selectors_for_payload(payload)
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
    if isinstance(local_checkpoint, dict) and local_checkpoint.get("status") in {"present", "stale", "unreadable"}:
        advisory_selectors.append("local_chat_checkpoint")
    selected: dict[str, Any] = {
        "kind": payload["kind"],
        "target": ".",
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
            agent_judgment="Agent owns work-shape choice unless hard_blockers names a gate.",
        ),
        "next_safe_action": next_safe_action,
        "skills": _startup_skills_projection(
            payload=payload,
            next_safe_action=next_safe_action,
            target_root=target_root,
            cli_invoke=cli_invoke,
        ),
        "context": context,
        "drill_down": {
            "ordinary_profile": "primary=next_safe_action;skills=proj;legacy=select/context",
            "rule": "Use --select <field[,field...]> for exact fields; use --verbose only for broad diagnostics.",
            "available_selectors": available_selectors,
        },
    }
    task_posture_packet = payload.get("task_posture_packet", {})
    if isinstance(task_posture_packet, dict) and task_posture_packet:
        selected["task_posture_packet"] = _compact_task_posture_packet_projection(task_posture_packet)
    if isinstance(payload.get("continuation_view"), dict):
        selected["continuation_view"] = payload["continuation_view"]
    if isinstance(payload.get("continuation_reorientation"), dict) and payload["continuation_reorientation"].get("status") == "required":
        selected["continuation_reorientation"] = payload["continuation_reorientation"]
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
    ):
        if optional_key in payload:
            context[optional_key] = payload[optional_key]
    maintainer_mode = payload.get("maintainer_mode", {})
    if isinstance(maintainer_mode, dict) and maintainer_mode.get("status") == "enabled":
        context["maintainer_mode"] = maintainer_mode
    return selected
