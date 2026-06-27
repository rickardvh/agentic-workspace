"""Proof, verification, and closeout runtime packet builders.

This module owns proof and closeout runtime packet helpers while the old
monolith keeps compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from agentic_workspace import config as config_lib
from agentic_workspace._schema import ModuleDescriptor
from agentic_workspace.config import DEFAULT_ASSURANCE_LEVEL, DEFAULT_CLI_INVOKE, WorkspaceConfig
from agentic_workspace.runtime_source_review import runtime_source_edit_review_for_changed_paths
from agentic_workspace.runtime_symbol_working_set import runtime_symbol_working_set_for_changed_paths
from agentic_workspace.workspace_runtime_core import (
    _PROOF_EXECUTION_STATUSES,
    _PROOF_SELECTION_RULES,
    _active_planning_assurance_for_proof,
    _active_planning_record_for_report_section,
    _adapt_make_proof_command_for_target,
    _applicable_intent_status_payload,
    _apply_learned_route_hints_to_capabilities,
    _architecture_principles_payload,
    _assurance_item_state,
    _assurance_requirements_report_payload,
    _assurance_requirements_with_verification,
    _authority_boundary_payload,
    _cli_authority_review_for_changed_paths,
    _closeout_intent_evidence_payload,
    _closeout_report_adoption_payload,
    _closeout_report_completeness_payload,
    _closeout_report_decision_review_payload,
    _closeout_report_final_response_rendering_payload,
    _closeout_report_profile_policy_payload,
    _closeout_report_review_compression_payload,
    _closeout_report_selected_review_mode,
    _closeout_report_traceability_rows,
    _completion_gate_payload,
    _confirm_learned_route_hints,
    _dedupe,
    _defaults_payload,
    _direct_cli_edit_review_for_changed_paths,
    _docs_only_reduction_lane,
    _host_repo_learning_posture_payload,
    _intent_decision_projection,
    _intent_proof_prompt_payload,
    _issue_scope_evidence_payload,
    _lane_execution_metadata,
    _learned_route_reliance_payload,
    _load_proof_route_hints,
    _load_workspace_config,
    _make_targets_without_negative_routes,
    _makefile_targets,
    _manual_verification_templates_for_intents,
    _missing_repo_path_references_in_command,
    _ordered_module_names,
    _package_json_scripts,
    _package_scripts_without_negative_routes,
    _parent_intent_status_payload,
    _project_roots_for_changed_paths,
    _proof_adequacy_payload,
    _proof_command_for_target,
    _proof_command_is_search_sweep,
    _proof_command_tiers,
    _proof_completion_options,
    _proof_confidence_payload,
    _proof_execution_evidence_summary,
    _proof_intent_for_lane,
    _proof_kind_for_lane,
    _proof_next_decision_payload,
    _proof_route_decision_payload,
    _proof_route_explanation_payload,
    _proof_route_source_for_lane,
    _requirement_grounding_payload,
    _routine_work_context_payload,
    _run_lifecycle_command,
    _skill_behavior_impact_review_for_changed_paths,
    _split_validation_command,
    _subsystem_matches_for_changed_paths,
    _supplemental_proof_lanes_for_changed_paths,
    _surface_value_review_for_changed_paths,
    _target_proof_capabilities,
    _test_strategy_check_payload,
    _transient_validation_retry_guidance,
    _validation_plan_for_proof,
    _verification_report_payload,
    _workflow_obligation_closeout_contract_payload,
    _workflow_obligations_report_payload,
    _workflow_sufficiency_payload,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _cli_authority_classification_for_path,
    _command_with_cli_invoke,
    _generated_cli_freshness_payload,
    _list_payload,
    _tiny_surface_compatibility_review,
)


def _proof_lifecycle_command(*args: Any, **kwargs: Any) -> dict[str, Any]:
    generated_cli: Any = None
    try:
        from generated.workspace.python import cli as generated_cli
    except Exception:
        pass
    if generated_cli is not None:
        patched = getattr(generated_cli, "_run_lifecycle_command", None)
        if patched is not None and patched is not _run_lifecycle_command:
            return patched(*args, **kwargs)
    return _run_lifecycle_command(*args, **kwargs)


def _closeout_report_payload(
    *,
    active_planning_record: dict[str, Any],
    closeout_trust: dict[str, Any],
    completion_contract: dict[str, Any],
    workflow_compliance_summary: dict[str, Any],
    verification: dict[str, Any],
    architecture_principles: dict[str, Any] | None = None,
    config: WorkspaceConfig,
) -> dict[str, Any]:
    active_planning_record = active_planning_record if isinstance(active_planning_record, dict) else {}
    closeout_trust = closeout_trust if isinstance(closeout_trust, dict) else {}
    completion_contract = completion_contract if isinstance(completion_contract, dict) else {}
    verification = verification if isinstance(verification, dict) else {}
    architecture_principles = architecture_principles if isinstance(architecture_principles, dict) else {}
    execution = _as_dict(active_planning_record.get("execution_run"))
    proof_report = _as_dict(active_planning_record.get("proof_report"))
    closure_check = _as_dict(active_planning_record.get("closure_check"))
    delegated = _as_dict(active_planning_record.get("delegated_judgment"))
    evidence_source = _as_dict(active_planning_record.get("_closeout_evidence_source"))
    default_evidence_authority = "active-planning-evidence" if active_planning_record else ""
    evidence_authority = str(evidence_source.get("authority") or default_evidence_authority).strip()
    evidence_is_archived = evidence_authority == "archived-planning-evidence"
    evidence_is_retained = evidence_authority == "retained-closeout-evidence"
    evidence_state = (
        "retained" if evidence_is_retained else "archived" if evidence_is_archived else "active" if active_planning_record else "absent"
    )
    intent_check = _as_dict(closeout_trust.get("intent_satisfaction_check"))
    completion_boundary = _as_dict(completion_contract.get("completion_boundary"))
    traceability_rows = _closeout_report_traceability_rows(
        active_planning_record=active_planning_record,
        closeout_trust=closeout_trust,
        completion_contract=completion_contract,
        verification=verification,
    )
    completeness = _closeout_report_completeness_payload(
        active_planning_record=active_planning_record,
        closeout_trust=closeout_trust,
        completion_contract=completion_contract,
        traceability_rows=traceability_rows,
        verification=verification,
        assurance_requirements=_as_dict(closeout_trust.get("assurance_requirements")),
    )
    profile_policy = _closeout_report_profile_policy_payload(
        closeout_trust=closeout_trust,
        completion_contract=completion_contract,
        verification=verification,
        completeness=completeness,
        config=config,
        cli_invoke=config.cli_invoke,
    )
    trust = str(closeout_trust.get("trust", "unknown"))
    if profile_policy["selected_profile"] == "audit" and completeness["status"] != "complete":
        trust = "lower-trust"
    raw_completion_options = [item for item in _list_payload(closeout_trust.get("completion_options")) if isinstance(item, dict)]
    options = {str(item.get("id", "")): item for item in raw_completion_options}
    next_action = (
        closeout_trust.get("recommended_next_action")
        or _as_dict(closeout_trust.get("terminal_action")).get("recommended_next_action")
        or "Use the closeout report evidence before making a final completion claim."
    )
    work_completed = str(execution.get("what happened") or execution.get("summary") or "").strip()
    requested_outcome = str(
        delegated.get("requested outcome") or delegated.get("requested_outcome") or completion_contract.get("must_be_true") or ""
    ).strip()
    intent_evidence = _closeout_intent_evidence_payload(
        active_planning_record=active_planning_record,
        evidence_state=evidence_state,
        requested_outcome=requested_outcome,
        intent_check=intent_check,
    )
    parent_intent_status = _parent_intent_status_payload(
        active_planning_record=active_planning_record,
        intent_check=intent_check,
        completion_boundary=completion_boundary,
    )
    applicable_intent_status = _applicable_intent_status_payload(
        active_planning_record=active_planning_record,
        verification=verification,
        assurance_requirements=_as_dict(closeout_trust.get("assurance_requirements")),
    )
    architecture_closeout = _as_dict(architecture_principles.get("closeout"))

    def meaningful_closeout_text(value: Any) -> str:
        text = str(value or "").strip()
        return "" if text.lower() in {"", "none", "null", "unknown", "pending", "not-run-yet"} else text

    changed_surfaces = str(execution.get("changed surfaces") or "").strip()
    raw_proof_report_validation = str(proof_report.get("validation proof") or "").strip()
    raw_execution_validation = str(execution.get("validations run") or "").strip()
    proof_report_validation = meaningful_closeout_text(raw_proof_report_validation)
    validation_proof = str(
        proof_report_validation or meaningful_closeout_text(raw_execution_validation) or raw_proof_report_validation
    ).strip()
    proof_achieved_now = str(proof_report.get("proof achieved now") or "").strip()
    proof_execution_recorded = bool(proof_report_validation) or meaningful_closeout_text(proof_achieved_now).lower().startswith(
        ("yes", "passed", "satisfied", "complete")
    )
    validation_proof_blocker = "intent_satisfaction.closure_scope.validation_proof"
    proof_execution = {
        "kind": "agentic-workspace/closeout-proof-execution/v1",
        "status": "recorded" if proof_execution_recorded else "missing",
        "proof": validation_proof,
        "proof_achieved_now": proof_achieved_now,
        "source_field": (
            "planning.closeout_evidence.proof_report.validation proof"
            if evidence_is_retained
            else "planning.archive.execplan.proof_report.validation proof"
            if evidence_is_archived
            else "planning.active.planning_record.proof_report.validation proof"
        ),
        "claim_boundary": "proof execution only",
        "confidence_boundary": (
            "Recorded proof execution satisfies the validation-proof reporting blocker, but structured intent-proof "
            "confidence remains separate and must not be inferred from free-form proof text."
        ),
        "rule": "Proof execution records that validation was reported; proof_confidence reports structured claim support.",
    }
    completion_options = copy.deepcopy(raw_completion_options)
    option_blockers: dict[str, list[str]] = {}
    parent_status_value = str(parent_intent_status.get("status") or "").strip()
    if parent_status_value and parent_status_value not in {"satisfied", "guidance-only", "not-recorded"}:
        option_blockers.setdefault("claim-work-complete", []).append("parent_intent_status")
        option_blockers.setdefault("close-parent-lane", []).append("parent_intent_status")
    if applicable_intent_status.get("closeout_blocked"):
        blocked_claims = [
            str(item).strip() for item in _list_payload(applicable_intent_status.get("blocked_claims")) if str(item).strip()
        ] or ["claim-work-complete", "close-parent-lane"]
        for claim in blocked_claims:
            option_blockers.setdefault(claim, []).append("applicable_intent_status")
    if architecture_closeout.get("required_claim"):
        option_blockers.setdefault("claim-work-complete", []).append("architecture_principles_status")
    for option in completion_options:
        blockers_for_option = _dedupe([*(_list_payload(option.get("blocking_fields"))), *option_blockers.get(str(option.get("id")), [])])
        if proof_execution_recorded:
            blockers_for_option = [blocker for blocker in blockers_for_option if str(blocker) != validation_proof_blocker]
        if not blockers_for_option:
            option.pop("blocking_fields", None)
            continue
        option["blocking_fields"] = blockers_for_option
        if str(option.get("id")) in option_blockers:
            option["allowed"] = False
            option["why"] = "completion claim is blocked until parent/applicable intent evidence is reconciled"
    completion_decision = str(completion_contract.get("completion_decision", "unknown"))
    proof_confidence = _as_dict(closeout_trust.get("proof_confidence"))
    behavior_preservation = _as_dict(proof_confidence.get("behavior_preservation"))
    residual_risk = str(proof_confidence.get("residual_risk", ""))
    completion_gate = _as_dict(closeout_trust.get("completion_gate"))
    if not completion_gate:
        completion_gate = _completion_gate_payload(
            active_planning_record=active_planning_record,
            intent_check=intent_check,
            acceptance_reconciliation=_as_dict(closeout_trust.get("acceptance_criteria_reconciliation")),
            intent_proof_check=_as_dict(closeout_trust.get("intent_proof_check")),
            parent_intent_status=parent_intent_status,
            applicable_intent_status=applicable_intent_status,
            durable_residue_action=_as_dict(closeout_trust.get("durable_residue_action")),
        )
    task_posture_followthrough = _as_dict(completion_gate.get("task_posture_followthrough"))
    first_blocking_option = next((item for item in completion_options if item.get("allowed") is False and item.get("blocking_fields")), {})
    blockers = first_blocking_option.get("blocking_fields", [])
    workflow_obligation_contract = _workflow_obligation_closeout_contract_payload(
        config=config,
        active_planning_record=active_planning_record,
    )
    decision_review = _closeout_report_decision_review_payload(
        active_planning_record=active_planning_record,
        proof_report=proof_report,
    )
    selected_review_mode = _closeout_report_selected_review_mode(
        profile_policy=profile_policy,
        trust=trust,
        completeness=completeness,
        decision_review=decision_review,
        behavior_preservation=behavior_preservation,
    )
    final_response_rendering = _closeout_report_final_response_rendering_payload(
        status="present" if active_planning_record else "guidance-only",
        profile_policy=profile_policy,
        trust=trust,
        work_completed=work_completed,
        requested_outcome=requested_outcome,
        changed_surfaces=changed_surfaces,
        validation_proof=validation_proof,
        completion_decision=completion_decision,
        completion_boundary=completion_boundary,
        completion_options=completion_options,
        completeness=completeness,
        residual_risk=residual_risk,
        blockers=blockers if isinstance(blockers, list) else [],
        next_action=str(next_action),
        decision_review=decision_review,
        behavior_preservation=behavior_preservation,
        parent_intent_status=parent_intent_status,
        applicable_intent_status=applicable_intent_status,
        workflow_obligation_contract=workflow_obligation_contract,
        completion_gate=completion_gate,
        review_mode=selected_review_mode,
    )
    detail_commands = {
        "closeout_report": str(profile_policy.get("next_command", "")),
        "closeout_trust": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section closeout_trust --format json",
            cli_invoke=config.cli_invoke,
        ),
        "completion_contract": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section completion_contract --format json",
            cli_invoke=config.cli_invoke,
        ),
        "decision_pressure": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section decision_pressure --format json",
            cli_invoke=config.cli_invoke,
        ),
    }
    follow_up_owner = str(
        _as_dict(options.get("keep-parent-open")).get("owner") or completion_boundary.get("required_follow_up_owner") or ""
    ).strip()
    review_compression = _closeout_report_review_compression_payload(
        profile_policy=profile_policy,
        trust=trust,
        completeness=completeness,
        decision_review=decision_review,
        behavior_preservation=behavior_preservation,
        residual_risk=residual_risk,
        follow_up_owner=follow_up_owner,
        detail_commands=detail_commands,
    )
    closeout_adoption = _closeout_report_adoption_payload(
        profile_policy=profile_policy,
        final_response_rendering=final_response_rendering,
        decision_review=decision_review,
        review_compression=review_compression,
    )
    closeout_authority_boundary = _authority_boundary_payload(
        surface="closeout_report",
        enforced_by_aw=[str(blocker) for blocker in blockers] if isinstance(blockers, list) else [],
        observed_by_aw=[
            f"planning_evidence_state={evidence_state}",
            f"selected_profile={profile_policy['selected_profile']}",
            f"trust={trust}",
            f"completion_decision={completion_decision}",
            f"workflow_obligation_required_count={workflow_obligation_contract['required_count']}",
        ],
        recommended_by_aw=[str(next_action), profile_policy["next_command"]],
        proof_hints=[validation_proof],
        agent_owned_decisions=[
            "final user-facing wording",
            "whether proof and acceptance justify a completion claim",
            "which caveats are material enough to include in chat",
        ],
        human_owned_decisions=["acceptance of residual intent or follow-up ownership when the report names open residue"],
        rule=(
            "closeout_report renders derived evidence and gates; it must not be described as AW making the agent's "
            "semantic completion judgment."
        ),
    )
    return {
        "kind": "agentic-workspace/closeout-report/v1",
        "status": "present" if active_planning_record else "guidance-only",
        "authority": "derived-projection",
        "authority_boundary": closeout_authority_boundary,
        "planning_evidence": {
            "authority": evidence_authority or "no-planning-evidence",
            "source": evidence_source,
            "state": evidence_state,
            "rule": "Retained or archived evidence may explain the just-finished lane, but only active Planning state can govern current work.",
        },
        "profile": profile_policy["selected_profile"],
        "profile_policy": profile_policy,
        "trust": trust,
        "work_completed": work_completed,
        "interpreted_intent": {
            "requested_outcome": requested_outcome,
            "intent_evidence": intent_evidence,
            "intent_satisfaction": {
                key: intent_check.get(key)
                for key in ("status", "trust", "required_follow_on", "continuation_surface")
                if key in intent_check
            },
            "closure_decision": str(closure_check.get("closure decision") or closure_check.get("closure_decision") or "").strip(),
        },
        "intent_evidence": intent_evidence,
        "parent_intent_status": parent_intent_status,
        "applicable_intent_status": applicable_intent_status,
        "architecture_principles_status": architecture_principles,
        "changes": {
            "changed_surfaces": changed_surfaces,
            "scope_touched": str(execution.get("scope touched") or "").strip(),
            "source": "planning.closeout_evidence.execution_run"
            if evidence_is_retained
            else "planning.archive.execplan.execution_run"
            if evidence_is_archived
            else "planning.active.planning_record.execution_run",
        },
        "validation": {
            "proof": validation_proof,
            "proof_achieved_now": proof_achieved_now,
            "proof_execution": proof_execution,
            "proof_confidence": closeout_trust.get("proof_confidence", {}),
            "behavior_preservation": behavior_preservation,
        },
        "gaps_and_residual_risk": {
            "completion_blockers": blockers,
            "completion_gate": completion_gate,
            "task_posture_followthrough": task_posture_followthrough,
            "residual_risk": residual_risk,
            "durable_residue_action": closeout_trust.get("durable_residue_action", {}),
            "workflow_trust_impact": workflow_compliance_summary.get("trust_impact", "unknown")
            if isinstance(workflow_compliance_summary, dict)
            else "unknown",
        },
        "workflow_obligation_contract": workflow_obligation_contract,
        "completion_gate": completion_gate,
        "task_posture_followthrough": task_posture_followthrough,
        "closure_boundary": {
            "completion_decision": completion_contract.get("completion_decision", "unknown"),
            "decision_reasons": completion_contract.get("decision_reasons", []),
            "completion_boundary": completion_boundary,
            "terminal_action": closeout_trust.get("terminal_action", {}),
            "completion_options": completion_options,
        },
        "traceability": {
            "status": "present",
            "row_count": len(traceability_rows),
            "rows": traceability_rows,
        },
        "completeness": completeness,
        "decision_review": decision_review,
        "review_compression": review_compression,
        "closeout_adoption": closeout_adoption,
        "final_response_rendering": final_response_rendering,
        "next_action": {
            "summary": next_action,
            "command": profile_policy["next_command"],
            "run": profile_policy["next_command"],
        },
        "detail_commands": detail_commands,
        "source_fields": [
            "planning.closeout_evidence.execution_run"
            if evidence_is_retained
            else "planning.archive.execplan.execution_run"
            if evidence_is_archived
            else "planning.active.planning_record.execution_run",
            "planning.closeout_evidence.proof_report"
            if evidence_is_retained
            else "planning.archive.execplan.proof_report"
            if evidence_is_archived
            else "planning.active.planning_record.proof_report",
            "planning.closeout_evidence.closure_check"
            if evidence_is_retained
            else "planning.archive.execplan.closure_check"
            if evidence_is_archived
            else "planning.active.planning_record.closure_check",
            "report.closeout_trust",
            "report.completion_contract",
            "report.verification",
            "report.architecture_principles",
        ],
        "boundary": (
            "This report is derived operator-facing presentation. It stores no execution state, does not decide proof, "
            "and does not replace Planning, Verification, or closeout_trust as canonical owners."
        ),
    }


def _proof_payload(*, target_root: Path, descriptors: dict[str, ModuleDescriptor]) -> dict[str, Any]:
    defaults = _defaults_payload()["proof_surfaces"]
    installed_modules = [
        module_name for module_name in _ordered_module_names(descriptors) if descriptors[module_name].detector(target_root)
    ]
    current: dict[str, Any] = {
        "installed_modules": installed_modules,
        "status_health": "not-run",
        "doctor_health": "not-run",
        "warnings": [],
        "needs_review": [],
        "stale_generated_surfaces": [],
    }
    if not installed_modules:
        current["status_health"] = "not-installed"
        current["doctor_health"] = "not-installed"
    else:
        config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(descriptors))
        status_payload = _proof_lifecycle_command(
            command_name="status",
            target_root=target_root,
            local_only_repo_root=None,
            selected_modules=installed_modules,
            resolved_preset=None,
            descriptors=descriptors,
            dry_run=False,
            non_interactive=False,
            config=config,
        )
        doctor_payload = _proof_lifecycle_command(
            command_name="doctor",
            target_root=target_root,
            local_only_repo_root=None,
            selected_modules=installed_modules,
            resolved_preset=None,
            descriptors=descriptors,
            dry_run=False,
            non_interactive=False,
            config=config,
        )
        current = {
            "installed_modules": installed_modules,
            "status_health": status_payload["health"],
            "doctor_health": doctor_payload["health"],
            "warnings": _dedupe([*status_payload["warnings"], *doctor_payload["warnings"]]),
            "needs_review": _dedupe([*status_payload["needs_review"], *doctor_payload["needs_review"]]),
            "stale_generated_surfaces": _dedupe([*status_payload["stale_generated_surfaces"], *doctor_payload["stale_generated_surfaces"]]),
        }
    return {
        "target": target_root.as_posix(),
        "canonical_doc": defaults["canonical_doc"],
        "command": defaults["command"],
        "rule": defaults["rule"],
        "default_routes": defaults["default_routes"],
        "current": current,
    }


def _proof_obligations_payload(
    *,
    required_commands: list[str],
    optional_commands: list[str],
    manual_verification: dict[str, Any] | None,
    selected_commands: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manual_required = manual_verification is not None
    manual_status = manual_verification.get("status") if manual_verification is not None else "not-needed"
    authority_by_command = {str(item.get("command", "")): item for item in selected_commands or []}
    command_authority = []
    for command in required_commands:
        selected = authority_by_command.get(str(command), {})
        command_authority.append(
            {
                "command": str(command),
                "authority_source": str(selected.get("selected_from") or selected.get("lane") or "proof-route-selection"),
                "lane": str(selected.get("lane") or ""),
                "intent_type": str(selected.get("intent_type") or ""),
                "rule": "Authority describes why AW surfaced the command; the agent still owns proof sufficiency.",
            }
        )
    proof_required = bool(required_commands or manual_required)
    return {
        "kind": "agentic-workspace/proof-obligations/v1",
        "status": "required-proof-selected" if required_commands else "manual-proof-required" if manual_required else "no-required-proof",
        "required_proof": {
            "kind": "agentic-workspace/required-proof/v1",
            "status": "required" if required_commands or manual_required else "not-selected",
            "commands": required_commands,
            "command_authority": command_authority,
            "manual_verification_required": manual_required,
            "manual_verification_status": manual_status,
            "source_field": "required_commands",
            "action_effect": {
                "force": "required_before_claim" if proof_required else "advisory",
                "allowed_now": "continue-implementation-and-run-required-proof" if proof_required else "continue-implementation",
                "blocked_until_reconciled": ["claim-task-complete"] if proof_required else [],
                "claim_boundary": (
                    "completion-claims-blocked-until-required-proof-passes-or-manual-verification-is-recorded"
                    if proof_required
                    else "no-required-proof-selected"
                ),
                "resolution_selector": "proof.proof_obligations.required_proof",
                "resolution_commands": required_commands,
            },
            "rule": (
                "These commands, or required manual verification when commands are unavailable, are the proof gate for completion claims."
            ),
        },
        "recommended_confidence_checks": {
            "kind": "agentic-workspace/recommended-confidence-checks/v1",
            "status": "available" if optional_commands else "not-selected",
            "commands": optional_commands,
            "source_field": "optional_commands",
            "rule": "Recommended checks may refresh state or raise confidence, but they do not replace or relax required proof.",
        },
        "agent_selected_extra_validation": {
            "kind": "agentic-workspace/agent-selected-extra-validation/v1",
            "status": "agent-owned",
            "commands": [],
            "examples": [
                "rerun a focused failing test after the fix",
                "inspect the final diff against requested acceptance",
                "add task-specific validation when failures or risk expose an unproven behavior",
            ],
            "rule": "The agent may add validation when task intent, failures, or risk warrant it; AW does not pre-claim that extra work is mandatory.",
        },
        "completion_claim_rule": (
            "Completion claims remain blocked until required proof passes or required manual verification is recorded, "
            "then acceptance and residue are reconciled."
        ),
        "compatibility": {
            "required_commands": "unchanged hard-gate field for existing callers",
            "optional_commands": "unchanged advisory confidence-check field for existing callers",
        },
    }


def _proof_selection_for_changed_paths(
    *,
    changed_paths: list[str],
    target_root: Path | None = None,
    include_durable_intent: bool = True,
    task_text: str | None = None,
    acceptance: dict[str, Any] | None = None,
    include_assurance_requirements: bool = True,
    include_routine_work_context: bool = True,
) -> dict[str, Any]:
    defaults = _defaults_payload()
    cli_invoke = DEFAULT_CLI_INVOKE
    config: WorkspaceConfig | None = None
    if target_root is not None:
        config = _load_workspace_config(target_root=target_root)
        cli_invoke = config.cli_invoke
    validation_lanes = defaults["validation"]["lanes"]
    cli_authority_lane = _PROOF_SELECTION_RULES.get("cli_authority", {}).get("lane")

    def _lane(lane_id: str) -> dict[str, Any]:
        return next((lane for lane in validation_lanes if lane["id"] == lane_id))

    selected_ids: list[str] = []
    routing_reductions: list[dict[str, str]] = []

    def _select(lane_id: str) -> None:
        if lane_id not in selected_ids:
            selected_ids.append(lane_id)

    def generated_command_package_scope() -> str | None:
        has_python = any(
            (
                path.startswith("generated/python/")
                or path.startswith("generated/workspace/python/")
                or path.startswith("generated/planning/python/")
                or path.startswith("generated/memory/python/")
                or path.startswith("generated/verification/python/")
            )
            for path in changed_paths
        )
        has_typescript = any(
            (
                path.startswith("generated/workspace/typescript/")
                or path.startswith("generated/planning/typescript/")
                or path.startswith("generated/memory/typescript/")
                or path.startswith("generated/verification/typescript/")
            )
            for path in changed_paths
        )
        has_shared_source = any(
            (
                path in {"src/agentic_workspace/contracts/command_package_ir.json"}
                or path.startswith("scripts/generate/generate_command_packages.py")
                for path in changed_paths
            )
        )
        if has_python and (not has_typescript) and (not has_shared_source):
            return "python-only"
        if has_typescript and (not has_python):
            return "typescript-only"
        return None

    for changed_path in changed_paths:
        matched_rule = False
        for rule in _PROOF_SELECTION_RULES["rules"]:
            exact_matches = set(rule.get("exact", []))
            prefixes = tuple(rule.get("prefixes", []))
            if changed_path in exact_matches or changed_path.startswith(prefixes):
                matched_lane = str(rule["lane"])
                selected_lane = _docs_only_reduction_lane(changed_path=changed_path, matched_lane=matched_lane) or matched_lane
                if selected_lane != matched_lane:
                    routing_reductions.append(
                        {
                            "path": changed_path,
                            "from_lane": matched_lane,
                            "to_lane": selected_lane,
                            "reason": str(_PROOF_SELECTION_RULES.get("docs_only_reducer", {}).get("rule", "")),
                        }
                    )
                _select(selected_lane)
                matched_rule = True
                break
        if not matched_rule:
            _select(str(_PROOF_SELECTION_RULES["fallback_lane"]))
        cli_authority_classification = _cli_authority_classification_for_path(changed_path)
        if cli_authority_lane and cli_authority_classification:
            _select(str(cli_authority_lane))
            if cli_authority_classification.get("id") in {"root-workspace-cli-runtime", "package-cli-runtime"}:
                _select("generated_command_packages")
    selected_lanes = [copy.deepcopy(_lane(lane_id)) for lane_id in selected_ids]
    generated_scope = generated_command_package_scope()
    if generated_scope == "python-only":
        for lane in selected_lanes:
            if lane["id"] == "generated_command_packages":
                lane["enough_proof"] = [
                    "uv run python scripts/check/check_generated_command_packages.py",
                    "uv run python scripts/check/run_operation_conformance_tests.py --target python",
                    "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
                    "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
                    "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q",
                ]
                lane["ci_relationship"] = (
                    "CI may repeat generated-package proof; local Python generated-package closeout should run static, local Python conformance, and Python Docker conformance serially."
                )
                break
    subsystem_matches = _subsystem_matches_for_changed_paths(target_root=target_root, changed_paths=changed_paths)
    subsystem_lanes: list[dict[str, Any]] = []
    for subsystem in subsystem_matches["matched_subsystems"]:
        proof_commands = [str(command) for command in subsystem.get("proof", []) if str(command).strip()]
        if not proof_commands:
            continue
        subsystem_lanes.append(
            {
                "id": f"subsystem:{subsystem['id']}",
                "when": "changed path matches host-repo subsystem ownership",
                "enough_proof": proof_commands,
                "recovery_signal": "missing or failing subsystem proof should block closeout for changes in this subsystem",
                "subsystem": {
                    "id": subsystem["id"],
                    "matched_paths": subsystem.get("matched_paths", []),
                    "owns": subsystem.get("owns", []),
                    "does_not_own": subsystem.get("does_not_own", []),
                    "escalate_when": subsystem.get("escalate_when", []),
                },
            }
        )
    selected_lanes.extend(subsystem_lanes)
    selected_lanes.extend(_supplemental_proof_lanes_for_changed_paths(changed_paths=changed_paths))
    planning_assurance = _active_planning_assurance_for_proof(target_root=target_root)
    active_plan_lanes: list[dict[str, Any]] = []
    active_plan_commands = _dedupe(
        [str(command).strip() for command in _list_payload(planning_assurance.get("validation_commands")) if str(command).strip()]
    )
    if (not changed_paths) and planning_assurance.get("status") == "present" and active_plan_commands:
        active_plan_lanes.append(
            {
                "id": "planning:active_validation",
                "when": "proof --current selected active planning validation commands",
                "enough_proof": active_plan_commands,
                "recovery_signal": "missing or failing active plan validation should block closeout until resolved or explicitly routed",
                "proof_kind": "targeted-test",
                "proof_responsibility": "local-closeout",
                "execution_mode": "serial-recommended",
                "planning_source": str(_as_dict(planning_assurance.get("task")).get("surface") or ""),
            }
        )
    configured_profiles = {profile.id: profile for profile in (config.assurance.proof_profiles if config is not None else ())}
    concern_lanes: list[dict[str, Any]] = []
    missing_concern_profiles: list[str] = []
    if planning_assurance.get("status") == "present":
        for profile_id in planning_assurance.get("proof_profiles", []):
            profile = configured_profiles.get(str(profile_id))
            if profile is None:
                missing_concern_profiles.append(str(profile_id))
                continue
            concern_lanes.append(
                {
                    "id": f"concern:{profile.id}",
                    "when": "active planning assurance declares this proof concern",
                    "enough_proof": list(profile.required_commands),
                    "recovery_signal": "missing or failing concern proof should block high-assurance closeout until resolved or explicitly waived",
                    "proof_profile": profile.id,
                    "optional_commands": list(profile.optional_commands),
                    "review_aids": list(profile.review_aids),
                    "disallowed_commands": list(profile.disallowed_commands),
                }
            )
    active_assurance_requirements = (
        _assurance_requirements_report_payload(
            config=config,
            target_root=target_root,
            active_planning_record=planning_assurance if planning_assurance.get("status") == "present" else None,
            task_text=task_text,
            changed_paths=changed_paths,
        )
        if include_assurance_requirements
        else {}
    )
    requirement_lanes: list[dict[str, Any]] = []
    existing_concern_profiles = {str(lane.get("proof_profile", "")) for lane in concern_lanes}
    for requirement in active_assurance_requirements.get("active", []):
        if not isinstance(requirement, dict):
            continue
        profile_id = str(requirement.get("proof_profile") or "").strip()
        if not profile_id:
            continue
        profile = configured_profiles.get(profile_id)
        if profile is None:
            if profile_id not in missing_concern_profiles:
                missing_concern_profiles.append(profile_id)
            continue
        if profile_id in existing_concern_profiles:
            continue
        requirement_lanes.append(
            {
                "id": f"assurance-requirement:{requirement.get('id')}",
                "when": "matched repo-declared assurance requirement selects this proof profile",
                "enough_proof": list(profile.required_commands),
                "recovery_signal": "missing or failing requirement proof should block broad assurance closeout until resolved or explicitly waived",
                "proof_profile": profile.id,
                "optional_commands": list(profile.optional_commands),
                "review_aids": list(profile.review_aids),
                "disallowed_commands": list(profile.disallowed_commands),
                "requirement_id": str(requirement.get("id", "")),
                "applies_because": _list_payload(requirement.get("applies_because")),
            }
        )
        existing_concern_profiles.add(profile_id)
    verification = (
        _verification_report_payload(
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            active_planning_record=planning_assurance if planning_assurance.get("status") == "present" else None,
            assurance_requirements=active_assurance_requirements,
        )
        if target_root is not None
        else {"status": "unavailable", "active_count": 0}
    )
    active_assurance_requirements = _assurance_requirements_with_verification(active_assurance_requirements, verification)
    verification_lanes: list[dict[str, Any]] = []
    active_verification_routes = [route for route in _list_payload(verification.get("active_proof_routes")) if isinstance(route, dict)]
    for protocol in _list_payload(verification.get("active_protocols")):
        if not isinstance(protocol, dict):
            continue
        protocol_id = str(protocol.get("id", "")).strip()
        if not protocol_id:
            continue
        protocol_routes = [
            route
            for route in active_verification_routes
            if protocol_id in {str(ref).strip() for ref in _list_payload(route.get("protocol_refs"))}
            or set(_list_payload(protocol.get("scenario_refs"))).intersection(
                {str(ref).strip() for ref in _list_payload(route.get("scenario_refs"))}
            )
        ]
        route_commands = _dedupe(
            [str(command).strip() for route in protocol_routes for command in _list_payload(route.get("commands")) if str(command).strip()]
        )
        verification_lanes.append(
            {
                "id": f"verification:{protocol_id}",
                "when": "matched repo verification protocol selects soft verification proof",
                "enough_proof": _dedupe(
                    [str(command) for command in _list_payload(protocol.get("commands")) if str(command).strip()] + route_commands
                ),
                "recovery_signal": "missing verification evidence should be recorded as residual risk or evidence before broad closeout",
                "proof_kind": "diff-review" if not protocol.get("commands") and not route_commands else "targeted-test",
                "proof_responsibility": "local-closeout",
                "execution_mode": "serial-recommended",
                "verification_protocol_id": protocol_id,
                "verification_scenario_refs": _list_payload(protocol.get("scenario_refs")),
                "verification_expected_evidence": _list_payload(protocol.get("expected_evidence")),
                "verification_proof_route_ids": [str(route.get("id")) for route in protocol_routes if route.get("id")],
                "review_aids": _dedupe(
                    [str(item) for item in _list_payload(protocol.get("review_aids"))]
                    + [str(item) for route in protocol_routes for item in _list_payload(route.get("review_aids"))]
                ),
                "applies_because": _list_payload(protocol.get("applies_because")),
            }
        )
    selected_lanes.extend(active_plan_lanes)
    selected_lanes.extend(concern_lanes)
    selected_lanes.extend(requirement_lanes)
    selected_lanes.extend(verification_lanes)
    make_targets = _makefile_targets(target_root)
    package_scripts = _package_json_scripts(target_root)
    project_roots = _project_roots_for_changed_paths(target_root=target_root, changed_paths=changed_paths)
    target_capabilities = _target_proof_capabilities(target_root=target_root, make_targets=make_targets, project_roots=project_roots)
    learned_route_hints = _confirm_learned_route_hints(
        learned_hints=_load_proof_route_hints(target_root=target_root), target_capabilities=target_capabilities
    )
    target_capabilities = _apply_learned_route_hints_to_capabilities(
        target_capabilities=target_capabilities, learned_route_hints=learned_route_hints
    )
    learned_negative_commands = {
        str(hint.get("candidate_command", "")).strip()
        for hint in learned_route_hints.get("negative", [])
        if str(hint.get("candidate_command", "")).strip()
    }
    selection_make_targets = _make_targets_without_negative_routes(make_targets, learned_negative_commands)
    selection_package_scripts = _package_scripts_without_negative_routes(package_scripts, learned_negative_commands)
    selection_role_commands = target_capabilities.get("role_commands", {})
    proof_command_adjustments: list[dict[str, str]] = []
    unavailable_proof_commands: list[dict[str, str]] = []
    host_policy_disallowed_commands: dict[str, dict[str, str]] = {}
    for lane in [*concern_lanes, *requirement_lanes]:
        for raw_command in lane.get("disallowed_commands", []):
            raw_command_text = str(raw_command).strip()
            if not raw_command_text:
                continue
            candidate_commands = [raw_command_text]
            adapted_command, _adjustment = _adapt_make_proof_command_for_target(
                command=raw_command_text,
                target_root=target_root,
                make_targets=selection_make_targets,
                package_scripts=selection_package_scripts,
                role_commands=selection_role_commands,
                project_roots=project_roots,
                record_missing_makefile_as_unavailable=bool(lane.get("proof_profile") or lane.get("subsystem")),
            )
            if adapted_command is not None:
                candidate_commands.append(adapted_command)
            for candidate_command in candidate_commands:
                resolved_command = str(
                    _command_with_cli_invoke(
                        command=_proof_command_for_target(command=candidate_command, target_root=target_root), cli_invoke=cli_invoke
                    )
                )
                host_policy_disallowed_commands[resolved_command] = {
                    "lane": str(lane.get("id", "")),
                    "proof_profile": str(lane.get("proof_profile", "")),
                    "command": resolved_command,
                    "configured_command": raw_command_text,
                    "reason": "host-configured proof profile disallows this command",
                }
    host_policy_blocked_commands: list[dict[str, str]] = []
    for lane in selected_lanes:
        lane["proof_kind"] = _proof_kind_for_lane(lane)
        adapted_commands: list[str] = []
        for raw_command in lane.get("enough_proof", []):
            adapted_command, adjustment = _adapt_make_proof_command_for_target(
                command=str(raw_command),
                target_root=target_root,
                make_targets=selection_make_targets,
                package_scripts=selection_package_scripts,
                role_commands=selection_role_commands,
                project_roots=project_roots,
                record_missing_makefile_as_unavailable=bool(lane.get("proof_profile") or lane.get("subsystem")),
            )
            if adjustment is not None:
                adjustment = {"lane": str(lane.get("id", "")), **adjustment}
                if adapted_command is None:
                    unavailable_proof_commands.append(adjustment)
                else:
                    proof_command_adjustments.append(adjustment)
            if adapted_command is None:
                continue
            missing_path_refs = (
                _missing_repo_path_references_in_command(command=adapted_command, target_root=target_root)
                if lane.get("subsystem") and _proof_command_is_search_sweep(adapted_command)
                else []
            )
            if missing_path_refs:
                unavailable_proof_commands.append(
                    {
                        "lane": str(lane.get("id", "")),
                        "command": adapted_command,
                        "reason": "selected proof command references path-like arguments absent from the target repo",
                        "missing_paths": ", ".join(missing_path_refs),
                    }
                )
                continue
            resolved_command = str(
                _command_with_cli_invoke(
                    command=_proof_command_for_target(command=adapted_command, target_root=target_root), cli_invoke=cli_invoke
                )
            )
            disallowed = host_policy_disallowed_commands.get(resolved_command)
            if disallowed is not None:
                host_policy_blocked_commands.append({**disallowed, "selected_by_lane": str(lane.get("id", ""))})
                continue
            adapted_commands.append(resolved_command)
        lane["enough_proof"] = adapted_commands
    required_commands: list[str] = []
    broaden_when: list[str] = []
    escalate_when: list[str] = []
    for lane in selected_lanes:
        for command in lane.get("enough_proof", []):
            if command not in required_commands:
                required_commands.append(command)
        for condition in lane.get("broaden_when", []):
            if condition not in broaden_when:
                broaden_when.append(condition)
        for condition in lane.get("escalate_when", []):
            if condition not in escalate_when:
                escalate_when.append(condition)
    executable_lanes = [
        lane for lane in selected_lanes if lane["id"] != cli_authority_lane and lane.get("proof_kind") in {"targeted-test", "full-test"}
    ]
    if len(executable_lanes) > 1:
        escalate_when.insert(0, str(_PROOF_SELECTION_RULES["cross_lane_escalation"]))
    adjustments_by_replacement = {
        str(adjustment["replacement"]): adjustment for adjustment in proof_command_adjustments if adjustment.get("replacement")
    }
    proof_intents = [_proof_intent_for_lane(lane) for lane in selected_lanes]
    intent_by_lane_id = {intent["id"]: intent for intent in proof_intents}
    selected_commands: list[dict[str, Any]] = []
    for lane in selected_lanes:
        intent = intent_by_lane_id.get(str(lane.get("id", "")), {})
        for command in lane.get("enough_proof", []):
            command_text = str(command)
            command_cwd, run_command = _split_validation_command(command_text)
            selected_commands.append(
                {
                    "kind": "proof-command/v1",
                    "command": command_text,
                    "cwd": command_cwd,
                    "run": run_command,
                    "selected_from": _proof_route_source_for_lane(
                        lane=lane, command=command_text, adjustments_by_replacement=adjustments_by_replacement
                    ),
                    "intent_type": str(intent.get("type", "behavior-test")),
                    "lane": str(lane.get("id", "")),
                    "required": True,
                    **_lane_execution_metadata(lane),
                }
            )
    unavailable_commands = [
        {
            "kind": "proof-command-unavailable/v1",
            "command": str(command.get("command", "")),
            "lane": str(command.get("lane", "")),
            "reason": str(command.get("reason", "")),
            **({"replacement": command["replacement"]} if command.get("replacement") else {}),
            **({"missing_paths": str(command["missing_paths"])} if command.get("missing_paths") else {}),
        }
        for command in unavailable_proof_commands
    ]
    manual_verification: dict[str, Any] | None = None
    if not required_commands or unavailable_proof_commands:
        manual_verification = {
            "kind": "manual-verification/v1",
            "status": "required" if not required_commands else "required-for-unavailable-proof",
            "reason": "no live-confirmed executable route was selected"
            if not required_commands
            else "some selected proof commands are unavailable in this target repo",
            "summary": "Review changed behavior manually and record evidence because no executable proof route was selected."
            if not required_commands
            else "Review unavailable proof expectations manually and record why repo-specific proof is sufficient.",
            "instructions": [
                "Inspect the changed paths against the requested task outcome.",
                "Use target_proof_capabilities.candidate_commands only if they are relevant to this change.",
                "Record what was manually checked and why unavailable commands were not required for closeout.",
            ],
            "templates": _manual_verification_templates_for_intents(proof_intents=proof_intents),
            "candidate_commands": target_capabilities.get("candidate_commands", []),
            "unavailable_commands": unavailable_commands,
        }
    proof_execution_evidence = {
        "kind": "proof-execution-evidence/v1",
        "status": "not-run",
        "state_model": list(_PROOF_EXECUTION_STATUSES),
        "expected_commands": required_commands,
        "manual_verification_expected": manual_verification is not None,
        "rule": "Proof selection describes expected proof only; closeout must record what actually ran, failed, was skipped, or was manually verified.",
    }
    configured_policy = [
        {
            "kind": "proof-profile/v1",
            "source": "host-config",
            "id": str(lane.get("proof_profile", "")),
            "required_commands": list(lane.get("enough_proof", [])),
            "optional_commands": list(lane.get("optional_commands", [])),
            "review_aids": list(lane.get("review_aids", [])),
            "disallowed_commands": [
                str(
                    _command_with_cli_invoke(
                        command=_proof_command_for_target(command=str(command), target_root=target_root), cli_invoke=cli_invoke
                    )
                )
                for command in lane.get("disallowed_commands", [])
            ],
        }
        for lane in [*concern_lanes, *requirement_lanes]
        if lane.get("proof_profile")
    ]
    learned_route_reliance = _learned_route_reliance_payload(
        selected_commands=selected_commands,
        learned_route_hints=learned_route_hints,
    )
    proof_next_decision = _proof_next_decision_payload(
        required_commands=required_commands,
        selected_commands=selected_commands,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        manual_verification=manual_verification,
        learned_route_hints=learned_route_hints,
    )
    proof_route_decision = _proof_route_decision_payload(
        proof_next_decision=proof_next_decision,
        selected_commands=selected_commands,
        required_commands=required_commands,
        manual_verification=manual_verification,
        unavailable_commands=unavailable_commands,
        learned_route_reliance=learned_route_reliance,
    )
    host_repo_learning = _host_repo_learning_posture_payload(
        target_capabilities=target_capabilities,
        learned_route_hints=learned_route_hints,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        selected_commands=selected_commands,
    )
    proof_route_explanation = _proof_route_explanation_payload(
        proof_intents=proof_intents,
        configured_policy=configured_policy,
        learned_route_hints=learned_route_hints,
        learned_route_reliance=learned_route_reliance,
        target_capabilities=target_capabilities,
        host_repo_learning=host_repo_learning,
        selected_commands=selected_commands,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        manual_verification=manual_verification,
        proof_execution_evidence=proof_execution_evidence,
    )
    generated_cli_freshness = _generated_cli_freshness_payload(
        changed_paths=changed_paths,
        selected_lanes=selected_lanes,
        required_commands=required_commands,
    )
    architecture_principles = _architecture_principles_payload(
        target_root=target_root,
        changed_paths=changed_paths,
        cli_invoke=cli_invoke,
        compact=False,
    )
    optional_commands = ["agentic-workspace proof --target ./repo --current --format json", "agentic-workspace summary --format json"]
    for concern_lane in [*concern_lanes, *requirement_lanes, *verification_lanes]:
        for command in concern_lane.get("optional_commands", []):
            if command not in optional_commands:
                optional_commands.append(str(command))
    optional_commands = [
        str(
            _command_with_cli_invoke(
                command=_proof_command_for_target(command=str(command), target_root=target_root), cli_invoke=cli_invoke
            )
        )
        for command in optional_commands
    ]
    proof_obligations = _proof_obligations_payload(
        required_commands=required_commands,
        optional_commands=optional_commands,
        manual_verification=manual_verification,
        selected_commands=selected_commands,
    )
    intent_proof = _intent_proof_prompt_payload(task_text=task_text, acceptance=acceptance, claim_boundary="slice")
    proof_confidence = _proof_confidence_payload(
        intent_proof=intent_proof,
        proof_execution_evidence=proof_execution_evidence,
    )
    proof_adequacy = _proof_adequacy_payload(
        required_commands=required_commands,
        optional_commands=optional_commands,
        selected_lanes=selected_lanes,
        verification=verification,
        proof_obligations=proof_obligations,
        proof_confidence=proof_confidence,
        manual_verification=manual_verification,
    )
    active_planning_record_for_requirement = (
        _active_planning_record_for_report_section(target_root=target_root) if target_root is not None else {}
    )
    issue_scope_evidence_for_requirement = (
        _issue_scope_evidence_payload(
            target_root=target_root,
            config=config,
            issue_refs=sorted(set(re.findall("#\\d+", task_text or ""))),
        )
        if target_root is not None and config is not None
        else {"kind": "agentic-workspace/issue-scope-evidence/v1", "status": "not-applicable", "issue_refs": []}
    )
    requirement_grounding = _requirement_grounding_payload(
        target_root=target_root or Path("."),
        task_text=task_text,
        changed_paths=changed_paths,
        active_planning_record=active_planning_record_for_requirement,
        issue_scope_evidence=issue_scope_evidence_for_requirement,
        assurance_requirements=active_assurance_requirements,
        verification=verification,
    )
    test_strategy_check = (
        _test_strategy_check_payload(
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            verification=verification,
        )
        if target_root is not None
        else {"kind": "agentic-workspace/test-strategy-check/v1", "status": "unavailable", "changed_test_paths": []}
    )
    proof_selection = {
        "kind": "proof-selection/v1",
        "changed_paths": changed_paths,
        "proof_strategy": {
            "kind": "proof-strategy/v1",
            "proof_types": [
                {"id": "executable", "meaning": "A discovered target command can directly exercise the changed behavior or surface."},
                {
                    "id": "surface-check",
                    "meaning": "A structured checker can inspect changed declarations, manifests, or generated surfaces.",
                },
                {"id": "diff-review", "meaning": "The trust question is human/agent review of the diff against the requested outcome."},
                {
                    "id": "manual-verification",
                    "meaning": "No trustworthy executable route was discovered; closeout needs explicit manual verification evidence.",
                },
            ],
            "selection_order": [
                "match changed paths to proof intent",
                "enrich with target repo capabilities and configured assurance profiles",
                "emit executable commands only when the target exposes the required capability",
                "emit manual verification instructions when executable proof is unavailable",
            ],
            "anti_rationalization_gates": [
                {
                    "red_flag": "Tests passed, so completion is claimable.",
                    "use_instead": "Record proof execution evidence, reconcile requested intent, and use completion/closeout options before claiming done.",
                },
                {
                    "red_flag": "The local slice works, so the parent lane or epic is closed.",
                    "use_instead": "Keep parent intent open unless closeout fields and continuation owner explicitly prove it is satisfied.",
                },
                {
                    "red_flag": "A skill wording change is only prose.",
                    "use_instead": "Name the behavior the skill steers and run the CLI or contract proof that shows routing, allowed actions, or completion claims still behave correctly.",
                },
            ],
        },
        "target_proof_capabilities": target_capabilities,
        "host_repo_learning": host_repo_learning,
        "learned_route_hints": learned_route_hints,
        "learned_route_reliance": learned_route_reliance,
        "proof_intents": proof_intents,
        "configured_policy": configured_policy,
        "verification": verification,
        "selected_commands": selected_commands,
        "unavailable_commands": unavailable_commands,
        "host_policy_blocked_commands": host_policy_blocked_commands,
        "proof_execution_evidence": proof_execution_evidence,
        "intent_proof": intent_proof,
        "proof_confidence": proof_confidence,
        "proof_adequacy": proof_adequacy,
        "requirement_grounding": requirement_grounding,
        "test_strategy_check": test_strategy_check,
        "architecture_principles": architecture_principles,
        "proof_route_selection": proof_route_decision,
        "proof_route_decision": proof_route_decision,
        "proof_route_explanation": proof_route_explanation,
        "legacy_aliases": {"proof_route_decision": "proof_route_selection"},
        "proof_next_decision": proof_next_decision,
        "proof_command_tiers": _proof_command_tiers(selected_commands=selected_commands, required_commands=required_commands),
        "proof_obligations": proof_obligations,
        "transient_validation_retry": _transient_validation_retry_guidance(required_commands=required_commands),
        "tiny_surface_compatibility_review": _tiny_surface_compatibility_review(changed_paths),
        "selected_lanes": [
            {
                "id": lane["id"],
                "when": lane["when"],
                "required_commands": lane["enough_proof"],
                "proof_kind": lane.get("proof_kind", "targeted-test"),
                "proof_responsibility": lane.get("proof_responsibility", "local-closeout"),
                "execution_mode": lane.get("execution_mode", "parallel-ok"),
                "ci_relationship": lane.get("ci_relationship", ""),
                "recovery_signal": lane.get("recovery_signal", ""),
                **({"proof_profile": lane["proof_profile"]} if lane.get("proof_profile") else {}),
                **({"requirement_id": lane["requirement_id"]} if lane.get("requirement_id") else {}),
                **({"verification_protocol_id": lane["verification_protocol_id"]} if lane.get("verification_protocol_id") else {}),
                **({"verification_scenario_refs": lane["verification_scenario_refs"]} if lane.get("verification_scenario_refs") else {}),
                **(
                    {"verification_expected_evidence": lane["verification_expected_evidence"]}
                    if lane.get("verification_expected_evidence")
                    else {}
                ),
                **(
                    {"verification_proof_route_ids": lane["verification_proof_route_ids"]}
                    if lane.get("verification_proof_route_ids")
                    else {}
                ),
                **({"applies_because": lane["applies_because"]} if lane.get("applies_because") else {}),
                **({"review_aids": lane["review_aids"]} if lane.get("review_aids") else {}),
                **({"matched_paths": lane["matched_paths"]} if lane.get("matched_paths") else {}),
                **({"subsystem": lane["subsystem"]} if lane.get("subsystem") else {}),
                **({"weak_agent_safe_routing": lane["weak_agent_safe_routing"]} if lane.get("weak_agent_safe_routing") else {}),
                **({"non_local_references": lane["non_local_references"]} if lane.get("non_local_references") else {}),
            }
            for lane in selected_lanes
        ],
        "required_commands": required_commands,
        "sufficiency": _workflow_sufficiency_payload(
            surface="proof",
            decision="required-proof-selected" if required_commands else "no-required-proof-selected",
            reason="Selected commands are the minimal proof for the matched changed paths; broaden only if task intent or failures demand it."
            if required_commands
            else "No changed-path proof rule selected a required command; use current proof or a task-specific proof before closeout.",
            required_next_action="run required_commands" if required_commands else "choose task-specific proof or current proof",
            evidence_required=["proof execution evidence"] if required_commands else [],
            drill_down={"full_detail": "agentic-workspace proof --verbose --changed <paths> --format json"},
        ),
        "optional_commands": optional_commands,
        "validation_plan": _validation_plan_for_proof(
            selected_lanes=selected_lanes, optional_commands=optional_commands, target_root=target_root, cli_invoke=cli_invoke
        ),
        "broaden_when": broaden_when,
        "escalate_when": escalate_when,
        "completion_options": _proof_completion_options(
            required_commands=required_commands,
            manual_verification=manual_verification,
            test_strategy_check=test_strategy_check,
        ),
    }
    if routing_reductions:
        proof_selection["routing_reductions"] = routing_reductions
    if generated_cli_freshness is not None:
        proof_selection["generated_cli_freshness"] = generated_cli_freshness
    if proof_command_adjustments:
        proof_selection["proof_command_adjustments"] = proof_command_adjustments
    if unavailable_proof_commands:
        proof_selection["unavailable_proof_commands"] = unavailable_proof_commands
        proof_selection["escalate_when"].append(
            "Some selected proof commands are unavailable in this target repo; choose repo-specific proof before closeout."
        )
    if host_policy_blocked_commands:
        proof_selection["host_policy_blocked_commands"] = host_policy_blocked_commands
        proof_selection["escalate_when"].append(
            "Host-configured proof policy blocked one or more discovered or selected commands; choose allowed repo-specific proof before closeout."
        )
    if manual_verification is not None:
        proof_selection["manual_verification"] = manual_verification
    if config is not None and target_root is not None and include_durable_intent:
        durable_intent = _intent_decision_projection(target_root=target_root, config=config, changed_paths=changed_paths, compact=True)
        proof_selection["durable_intent"] = durable_intent
        if durable_intent.get("status") == "present":
            intent_effect = (
                "Relevant durable intent may add proof, review, or escalation expectations; inspect durable_intent before closeout."
            )
            if intent_effect not in proof_selection["escalate_when"]:
                proof_selection["escalate_when"].append(intent_effect)
    if include_routine_work_context and config is not None and target_root is not None:
        workflow_obligations = _workflow_obligations_report_payload(
            config=config,
            active_planning_record=None,
            task_text=task_text,
            changed_paths=changed_paths,
        )
        proof_routine_context = _routine_work_context_payload(
            source_payload={"proof": proof_selection, "workflow_obligations": workflow_obligations, "verification": verification},
            surface="proof",
            cli_invoke=cli_invoke,
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            compact=True,
        )
        if proof_routine_context.get("status") == "attention":
            proof_selection["routine_work_context"] = proof_routine_context
    if subsystem_matches["matched_subsystems"]:
        proof_selection["subsystem_ownership"] = subsystem_matches
    if planning_assurance.get("status") == "present":
        gate_states = [
            _assurance_item_state(
                item_id=str(gate.get("id", "")),
                declared_status=str(gate.get("status", "missing")),
                blocking=bool(gate.get("blocking", False)),
                evidence=gate.get("evidence", []) if isinstance(gate.get("evidence", []), list) else [],
                reason=str(gate.get("reason", "")).strip() or None,
            )
            for gate in planning_assurance.get("control_gates", [])
            if isinstance(gate, dict)
        ]
        ref_states = [
            _assurance_item_state(
                item_id=ref,
                declared_status="present" if ref not in planning_assurance.get("missing_required_refs", []) else "missing",
                blocking=True,
                evidence=planning_assurance.get("traceability_refs", {}).get(ref, [])
                if isinstance(planning_assurance.get("traceability_refs", {}), dict)
                else [],
            )
            for ref in planning_assurance.get("required_refs", [])
        ]
        profile_states = [
            {
                "id": str(profile_id),
                "state": "selected" if str(profile_id) not in missing_concern_profiles else "unavailable",
                "enforcement": "required",
                "trust": "satisfied" if str(profile_id) not in missing_concern_profiles else "blocking",
            }
            for profile_id in planning_assurance.get("proof_profiles", [])
        ]
        proof_evidence = _proof_execution_evidence_summary(
            declared=planning_assurance.get("proof_execution_evidence", []), required_commands=required_commands
        )
        proof_selection["planning_assurance"] = {
            **planning_assurance,
            "missing_configured_proof_profiles": missing_concern_profiles,
            "trust_state": {
                "assurance_level": planning_assurance.get("adaptive_assurance", {}).get(
                    "level", config.assurance.default_level if config is not None else DEFAULT_ASSURANCE_LEVEL
                )
                if isinstance(planning_assurance.get("adaptive_assurance", {}), dict)
                else config.assurance.default_level
                if config is not None
                else DEFAULT_ASSURANCE_LEVEL,
                "assurance_level_source": "explicit-slice-field"
                if isinstance(planning_assurance.get("adaptive_assurance", {}), dict)
                and "level" in planning_assurance.get("adaptive_assurance", {})
                else config.assurance.default_level_source
                if config is not None
                else "product-default",
                "gate_states": gate_states,
                "ref_states": ref_states,
                "proof_profile_states": profile_states,
                "proof_execution_evidence": proof_evidence,
                "overall": "blocking"
                if planning_assurance.get("closeout_status") == "blocked"
                or missing_concern_profiles
                or proof_evidence["lower_trust_required_count"]
                else "open",
            },
            "rule": "Path lanes stay package-defined; concern profiles are host-configured and activated from active planning assurance fields.",
        }
    if include_assurance_requirements:
        proof_selection["assurance_requirements"] = active_assurance_requirements
    surface_value_review = _surface_value_review_for_changed_paths(changed_paths=changed_paths, target_root=target_root)
    if surface_value_review["durable_surface_count"]:
        proof_selection["surface_value_review"] = surface_value_review
    runtime_symbol_working_set = runtime_symbol_working_set_for_changed_paths(changed_paths, target_root=target_root)
    if runtime_symbol_working_set.get("status") == "present":
        proof_selection["runtime_symbol_working_set"] = runtime_symbol_working_set
    runtime_source_review = runtime_source_edit_review_for_changed_paths(changed_paths, target_root=target_root, task_text=task_text)
    if runtime_source_review["changed_paths"]:
        proof_selection["runtime_source_edit_review"] = runtime_source_review
    direct_cli_review = _direct_cli_edit_review_for_changed_paths(changed_paths)
    if direct_cli_review["changed_paths"]:
        proof_selection["direct_cli_edit_review"] = direct_cli_review
    skill_behavior_review = _skill_behavior_impact_review_for_changed_paths(changed_paths)
    if skill_behavior_review["changed_paths"]:
        proof_selection["skill_behavior_impact_review"] = skill_behavior_review
    cli_authority_review = _cli_authority_review_for_changed_paths(changed_paths)
    if cli_authority_review["changed_paths"]:
        proof_selection["cli_authority_review"] = cli_authority_review
    return proof_selection
