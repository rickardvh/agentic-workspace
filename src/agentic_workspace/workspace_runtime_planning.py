"""Planning continuation and active-state runtime packets.

This module owns Planning runtime packet helpers while the old monolith keeps
compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from agentic_workspace.config import WorkspaceConfig
from agentic_workspace.workspace_runtime_core import (
    _active_plan_delegation_requirement,
    _active_plan_parent_decomposition_requirement,
    _active_plan_reliance_payload,
    _allow_ancillary_memory_feedback_path,
    _allow_completed_archive_publication_residue,
    _allow_issue_scoped_planning_state_reconciliation,
    _authority_boundary_payload,
    _candidate_promotion_command,
    _candidate_refs,
    _candidate_relevance_payload,
    _candidate_route_label,
    _candidate_with_canonical_route,
    _capability_structural_hints,
    _command_with_expected_planning_revision,
    _external_intent_status_by_ref,
    _fast_planning_active_summary,
    _fast_planning_lane_records,
    _issue_scope_evidence_payload,
    _planning_hierarchy_owner_requirement,
    _planning_revision_payload,
    _planning_roadmap_candidates,
    _planning_safety_path_classification,
    _planning_safety_promotion_command,
    _pr_context_refs_from_task,
    _read_only_allowance_packet,
    _work_shape_guidance_payload,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _command_with_cli_invoke,
)


def _active_planning_record_for_report_section(*, target_root: Path) -> dict[str, Any]:
    return _raw_active_planning_record_for_closeout(planning_record={}, target_root=target_root)


def _raw_active_planning_record_for_closeout(*, planning_record: dict[str, Any], target_root: Path | None) -> dict[str, Any]:
    if target_root is None:
        return {}
    task = planning_record.get("task", {}) if isinstance(planning_record, dict) else {}
    surface = str(task.get("surface", "")).strip() if isinstance(task, dict) else ""
    if not surface:
        active_summary = _fast_planning_active_summary(target_root=target_root)
        surface = str(active_summary.get("active_execplan", "")).strip()
    if not surface:
        return {}
    try:
        target_resolved = target_root.resolve()
        record_path = (target_root / surface).resolve()
        record_path.relative_to(target_resolved)
    except (OSError, ValueError):
        return {}
    if record_path.suffix.lower() != ".json" or not record_path.is_file():
        return {}
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    payload = copy.deepcopy(payload)
    payload["_target_root"] = str(target_root)
    payload["_record_surface"] = surface
    parent_lane = _as_dict(payload.get("parent_lane"))
    lane_id = str(parent_lane.get("id") or parent_lane.get("lane_id") or "").strip()
    if lane_id:
        matching_record = next(
            (record for record in _fast_planning_lane_records(target_root=target_root) if str(record.get("id") or "").strip() == lane_id),
            None,
        )
        if isinstance(matching_record, dict):
            payload["_lane_owner_record"] = matching_record
    return payload


def _planning_candidate_pressure_payload(
    *,
    target_root: Path,
    config: WorkspaceConfig,
    issue_refs: list[str],
    task_text: str | None,
    work_shape: str | None,
    decomposition_delegation: dict[str, Any],
    planning_revision: dict[str, Any],
) -> dict[str, Any]:
    roadmap_candidates = _planning_roadmap_candidates(target_root)
    external_status_by_ref = _external_intent_status_by_ref(target_root)
    decomposition_candidates = (
        [candidate for candidate in decomposition_delegation.get("candidates", []) if isinstance(candidate, dict)]
        if isinstance(decomposition_delegation, dict)
        else []
    )
    issue_ref_set = set(issue_refs)
    roadmap_relevance: dict[str, dict[str, Any]] = {}
    matched_roadmap: list[dict[str, Any]] = []
    stale_roadmap: list[dict[str, Any]] = []
    unmatched_roadmap: list[dict[str, Any]] = []
    for candidate in roadmap_candidates:
        candidate_id = str(candidate.get("id", "")).strip()
        refs = sorted(_candidate_refs(candidate), key=lambda value: int(value.lstrip("#")) if value.lstrip("#").isdigit() else 0)
        relevance_payload = _candidate_relevance_payload(candidate, issue_refs=issue_refs, task_text=task_text)
        evidence = relevance_payload["strong_evidence"]
        weak_hints = relevance_payload["weak_hints"]
        ref_statuses = {ref: external_status_by_ref.get(ref, "unknown") for ref in refs if ref in external_status_by_ref}
        closed_refs = [ref for ref, status in ref_statuses.items() if status in {"closed", "done", "merged", "retired"}]
        stale_or_closed = bool(refs and closed_refs and not issue_ref_set.intersection(refs))
        if stale_or_closed:
            stale_roadmap.append(candidate)
        elif evidence:
            matched_roadmap.append(candidate)
        else:
            unmatched_roadmap.append(candidate)
        if candidate_id:
            roadmap_relevance[candidate_id] = {
                "id": candidate_id,
                "title": str(candidate.get("title", "")),
                "refs": refs,
                "evidence": evidence,
                "weak_lexical_hints": weak_hints,
                "external_statuses": ref_statuses,
                "relevance": "matched" if evidence and not stale_or_closed else "stale-or-closed" if stale_or_closed else "unmatched",
            }
    decomposition_relevance = {
        str(candidate.get("lane_id", "")).strip(): _candidate_relevance_payload(
            candidate,
            issue_refs=issue_refs,
            task_text=task_text,
        )
        for candidate in decomposition_candidates
    }
    matched_decomposition = [
        candidate
        for candidate in decomposition_candidates
        if decomposition_relevance.get(str(candidate.get("lane_id", "")).strip(), {}).get("strong_evidence")
    ]
    broad_shape = work_shape in {"lane", "epic"}
    promotion_required = False
    reasons: list[str] = []
    if broad_shape and matched_decomposition:
        promotion_required = True
        reasons.append("relevant open decomposition lane candidates exist for broad or lane-shaped work")
    if broad_shape and len(matched_roadmap) >= 2:
        promotion_required = True
        reasons.append("multiple relevant roadmap candidates exist while the requested work is broad or lane-shaped")
    if len(matched_roadmap) >= 2:
        promotion_required = True
        reasons.append("multiple roadmap candidates match the requested external issue refs")

    include_candidate_detail = promotion_required or bool(matched_roadmap)
    top_roadmap = matched_roadmap if include_candidate_detail else []
    route_options: list[dict[str, Any]] = []
    for candidate in top_roadmap[:3]:
        candidate_id = str(candidate.get("id", "")).strip()
        if not candidate_id:
            continue
        route_options.append(
            {
                "kind": "roadmap-candidate",
                "id": candidate_id,
                "title": candidate.get("title", ""),
                "refs": candidate.get("refs", ""),
                "command": _candidate_promotion_command(
                    candidate_id=candidate_id,
                    config=config,
                    planning_revision=planning_revision,
                ),
            }
        )
    top_decomposition = matched_decomposition if promotion_required else []
    for candidate in top_decomposition[:3]:
        lane_id = str(candidate.get("lane_id", "")).strip()
        if not lane_id:
            continue
        route_options.append(
            {
                "kind": "decomposition-lane",
                "id": lane_id,
                "title": candidate.get("title", ""),
                "decomposition": candidate.get("decomposition", ""),
                "relevance_evidence": decomposition_relevance.get(lane_id, {}).get("strong_evidence", []),
                "weak_lexical_hints": decomposition_relevance.get(lane_id, {}).get("weak_hints", []),
                "command": _candidate_promotion_command(candidate_id=lane_id, config=config, planning_revision=planning_revision),
            }
        )

    status = "promotion-required" if promotion_required else "observed" if roadmap_candidates or decomposition_candidates else "none"
    return {
        "kind": "agentic-workspace/planning-candidate-pressure/v1",
        "status": status,
        "work_shape": work_shape or "unknown",
        "roadmap_candidate_count": len(roadmap_candidates),
        "matched_roadmap_candidate_count": len(matched_roadmap),
        "unmatched_roadmap_candidate_count": len(unmatched_roadmap),
        "stale_or_closed_roadmap_candidate_count": len(stale_roadmap),
        "decomposition_candidate_count": len(decomposition_candidates),
        "matched_decomposition_candidate_count": len(matched_decomposition),
        "candidate_count": len(roadmap_candidates) + len(decomposition_candidates),
        "candidate_ids": [
            *[str(candidate.get("id", "")) for candidate in matched_roadmap[:5] if candidate.get("id")],
            *[str(candidate.get("lane_id", "")) for candidate in matched_decomposition[:5] if str(candidate.get("lane_id", "")).strip()],
        ]
        if include_candidate_detail
        else [],
        "relevance": {
            "status": "matched"
            if matched_roadmap or matched_decomposition
            else "unmatched"
            if roadmap_candidates or decomposition_candidates
            else "none",
            "rule": "Candidate pressure blocks only when candidates are relevant to task refs or task text; unrelated deferred lanes remain advisory.",
            "roadmap": [roadmap_relevance[candidate_id] for candidate_id in list(roadmap_relevance)[:8]],
            "decomposition": [
                {
                    "id": str(candidate.get("lane_id", "")).strip(),
                    "title": str(candidate.get("title", "")),
                    "evidence": decomposition_relevance.get(str(candidate.get("lane_id", "")).strip(), {}).get("strong_evidence", []),
                    "weak_lexical_hints": decomposition_relevance.get(str(candidate.get("lane_id", "")).strip(), {}).get("weak_hints", []),
                }
                for candidate in decomposition_candidates[:5]
            ],
        },
        "advisory_backlog": {
            "unmatched_candidate_ids": [
                str(candidate.get("id", "")).strip() for candidate in unmatched_roadmap[:5] if str(candidate.get("id", "")).strip()
            ],
            "stale_or_closed_candidate_ids": [
                str(candidate.get("id", "")).strip() for candidate in stale_roadmap[:5] if str(candidate.get("id", "")).strip()
            ],
            "rule": "Unmatched or closed external-intent-backed candidates remain visible but do not block current implementation.",
        },
        "reasons": reasons,
        "route_options": route_options,
        "required_before_implementation": [
            "promote a roadmap candidate or decomposition lane to an active execplan",
            "create a parent decomposition and bounded lane execplans",
            "or record an explicit bounded-slice exception that does not claim parent epic closure",
        ]
        if promotion_required
        else [],
        "rule": "Checked-in Planning candidate evidence can require promotion before broad implementation; prompt text alone must not authorize closing an epic.",
    }


def _active_execplan_record_payload(*, target_root: Path) -> tuple[str, dict[str, Any]]:
    active_summary = _fast_planning_active_summary(target_root=target_root)
    active_surface = str(active_summary.get("active_execplan") or "").strip()
    if not active_surface:
        return "", {}
    plan_path = target_root / active_surface
    if not plan_path.exists() or plan_path.suffix != ".json":
        return active_surface, {}
    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return active_surface, {}
    return active_surface, loaded if isinstance(loaded, dict) else {}


def _custody_only_planning_payload(
    *,
    active_planning_present: bool,
    candidate_pressure: dict[str, Any],
    issue_scope_evidence: dict[str, Any],
    issue_refs: list[str],
    work_shape: str | None,
    task_text: str | None,
    workflow_sufficient: bool,
    planning_revision: dict[str, Any],
    promotion_command: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    issue_kinds: list[str] = []
    normalized_task = " ".join((task_text or "").lower().split())
    closure_terms = (
        "close ",
        "closing ",
        "closes ",
        "closed ",
        "fixes ",
        "resolves ",
        "parent closure",
        "pr wording",
        "closing keyword",
    )
    title_lane_terms = ("parent", "lane", "epic", "batch", "multi-issue", "roadmap", "closure", "closeout", "broad")
    broad_issue_kinds = {
        "parent-lane",
        "lane",
        "epic",
        "roadmap",
        "capability-lane",
        "issue-batch",
        "closure-sensitive",
    }
    for item in issue_scope_evidence.get("evidence", []) if isinstance(issue_scope_evidence.get("evidence"), list) else []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "")).strip()
        title = str(item.get("title", "")).strip().lower()
        if kind:
            issue_kinds.append(kind)
        if kind in broad_issue_kinds:
            reasons.append(kind if kind != "capability-lane" else "parent-lane")
        if str(item.get("parent_id", "")).strip():
            reasons.append("parent-lane")
        if str(item.get("planning_residue_expected", "")).strip().lower() in {"required", "expected"}:
            reasons.append("closure-sensitive")
        if any(term in title for term in title_lane_terms):
            reasons.append("parent-lane" if "parent" in title or "lane" in title else "broad-roadmap")
    if len(issue_refs) > 1:
        reasons.append("multi-issue")
    if work_shape in {"lane", "epic"}:
        reasons.append("parent-lane" if work_shape == "lane" else "broad-roadmap")
    if int(candidate_pressure.get("matched_roadmap_candidate_count") or 0) > 0:
        reasons.append("broad-roadmap")
    if int(candidate_pressure.get("matched_decomposition_candidate_count") or 0) > 0:
        reasons.append("parent-lane")
    if issue_refs and any(term in f" {normalized_task} " for term in closure_terms):
        reasons.append("closure-sensitive")

    custody_reasons = sorted(set(reason for reason in reasons if reason))
    if active_planning_present or not workflow_sufficient or not custody_reasons:
        return {
            "kind": "agentic-workspace/custody-only-planning/v1",
            "status": "not-applicable",
            "planning_roles": {
                "implementation_gate": "not-required",
                "sequencing_aid": "agent-owned",
                "intent_custody": "not-needed",
            },
            "reason_codes": [],
            "rule": "Narrow direct work stays quiet unless broad lane, issue-batch, closure-sensitive, or parent-intent evidence is present.",
        }

    force = "required_before_claim" if "closure-sensitive" in custody_reasons else "advisory"
    blocked_claims = (
        ["claim-full-parent-satisfaction", "use-pr-closing-keywords", "claim-lane-complete"]
        if force == "required_before_claim"
        else ["claim-full-parent-satisfaction", "claim-lane-complete"]
    )
    return {
        "kind": "agentic-workspace/custody-only-planning/v1",
        "status": "required-reconciliation" if force == "required_before_claim" else "recommended",
        "force": force,
        "implementation_allowed": True,
        "planning_roles": {
            "implementation_gate": "not-required",
            "sequencing_aid": "not-required-for-current-slice",
            "intent_custody": "required-before-parent-closeout" if force == "required_before_claim" else "recommended",
        },
        "reason_codes": custody_reasons,
        "issue_refs": issue_refs,
        "issue_kinds": sorted(set(kind for kind in issue_kinds if kind)),
        "purpose": (
            "Preserve shared lane intent, parent/child scope, closeout trust, continuation, and review evidence; "
            "this is not necessarily a step-by-step execution plan."
        ),
        "slice_boundary": {
            "useful_slice_completion": "allowed-after-normal-proof",
            "full_parent_satisfaction": "requires-custody-or-equivalent-reconciliation",
            "rule": "A useful direct slice can finish without claiming the parent lane or issue batch is complete.",
        },
        "minimal_record_shape": [
            "parent intent",
            "current useful slice",
            "child issue or lane scope",
            "non-goals",
            "parent closure boundary",
            "proof and review state",
            "continuation owner/status",
            "equivalent checked-in custody evidence",
        ],
        "action_effect": {
            "force": force,
            "allowed_now": "continue-direct-implementation",
            "blocked_until_reconciled": blocked_claims if force == "required_before_claim" else [],
            "claim_boundary": "direct-slice-completion-is-not-parent-lane-satisfaction",
            "resolution_selector": "planning_safety_gate.custody_planning",
            "resolution_command": promotion_command if force == "required_before_claim" else "",
        },
        "follow_up_route": {
            "status": "creation-deferred",
            "refs": ["#1706"],
            "reason": "Cheap custody-record creation remains follow-up work; this packet only surfaces the route and claim boundary.",
            "planning_revision": planning_revision,
        },
        "rule": "Custody-only Planning is shared intent custody, not an implementation gate, unless parent closeout or PR closing claims are being made.",
    }


def _retrofit_active_owner_commands(*, config: WorkspaceConfig, planning_revision: dict[str, Any]) -> dict[str, str]:
    claim_command = _command_with_expected_planning_revision(
        _command_with_cli_invoke(
            command=(
                'agentic-workspace planning new-plan --id <slice-id> --title "<bounded current slice>" '
                '--source "current diff retrofit" --target . --activate --format json'
            ),
            cli_invoke=config.cli_invoke,
        ),
        planning_revision=planning_revision,
    )
    summary_command = _command_with_cli_invoke(
        command="agentic-workspace summary --target . --format json",
        cli_invoke=config.cli_invoke,
    )
    closeout_command = _command_with_expected_planning_revision(
        _command_with_cli_invoke(
            command=(
                "agentic-workspace planning closeout <slice-id> --target . --claim-level slice "
                "--intent-status satisfied --residue none --proof-from last --format json"
            ),
            cli_invoke=config.cli_invoke,
        ),
        planning_revision=planning_revision,
    )
    archive_command = _command_with_expected_planning_revision(
        _command_with_cli_invoke(
            command=(
                "agentic-workspace planning archive-plan --plan <slice-id> --target . "
                "--prepare-closeout --retain-archive --apply-cleanup --format json"
            ),
            cli_invoke=config.cli_invoke,
        ),
        planning_revision=planning_revision,
    )
    return {
        "claim": claim_command,
        "summary": summary_command,
        "closeout": closeout_command,
        "archive": archive_command,
    }


def _planning_safety_gate_payload(
    *, target_root: Path, config: WorkspaceConfig, changed_paths: list[str], task_text: str | None, execution_posture: dict[str, Any]
) -> dict[str, Any]:
    active_summary = _fast_planning_active_summary(target_root=target_root)
    active_planning_present = bool(active_summary.get("todo_active_count") or active_summary.get("active_execplan"))
    capability = execution_posture.get("capability_posture", {}) if isinstance(execution_posture, dict) else {}
    work_shape, proof_burden = _capability_structural_hints(capability)
    decomposition_delegation = execution_posture.get("decomposition_delegation", {}) if isinstance(execution_posture, dict) else {}
    decomposition_status = str(decomposition_delegation.get("status", "")) if isinstance(decomposition_delegation, dict) else ""
    path_classification = _planning_safety_path_classification(changed_paths)
    numeric_refs = sorted(set(re.findall("#\\d+", task_text or "")))
    pr_context_refs = _pr_context_refs_from_task(task_text)
    issue_refs = [ref for ref in numeric_refs if ref not in set(pr_context_refs)]
    path_classification = _allow_ancillary_memory_feedback_path(path_classification)
    path_classification = _allow_issue_scoped_planning_state_reconciliation(path_classification, issue_refs=issue_refs)
    path_classification = _allow_completed_archive_publication_residue(path_classification, target_root=target_root)
    planning_revision = _planning_revision_payload(target_root=target_root)
    issue_scope_evidence = _issue_scope_evidence_payload(target_root=target_root, config=config, issue_refs=issue_refs)
    candidate_pressure = _planning_candidate_pressure_payload(
        target_root=target_root,
        config=config,
        issue_refs=issue_refs,
        task_text=task_text,
        work_shape=work_shape,
        decomposition_delegation=decomposition_delegation if isinstance(decomposition_delegation, dict) else {},
        planning_revision=planning_revision,
    )
    promotion_command = _planning_safety_promotion_command(
        config=config,
        decomposition_delegation=decomposition_delegation if isinstance(decomposition_delegation, dict) else {},
        task_text=task_text,
        planning_revision=planning_revision,
    )
    active_delegation_requirement = _active_plan_delegation_requirement(
        target_root=target_root, active_summary=active_summary, config=config, task_text=task_text, execution_posture=execution_posture
    )
    active_parent_decomposition_requirement = _active_plan_parent_decomposition_requirement(
        target_root=target_root,
        active_summary=active_summary,
    )
    hierarchy_owner_requirement = _planning_hierarchy_owner_requirement(
        target_root=target_root,
        active_summary=active_summary,
        planning_revision=planning_revision,
        config=config,
    )
    active_plan_reliance = _active_plan_reliance_payload(
        target_root=target_root,
        active_planning_present=active_planning_present,
        active_summary=active_summary,
        active_delegation_requirement=active_delegation_requirement,
        planning_revision=planning_revision,
        cli_invoke=config.cli_invoke,
    )
    closeout_publication_residue = (
        path_classification.get("dirty_shape") == "implementation-with-archived-planning-residue"
        and _as_dict(path_classification.get("archived_planning_residue")).get("status") == "completed-closeout-residue"
    )
    if active_planning_present and active_delegation_requirement.get("required"):
        status = "blocked"
        decision = "delegation-decision-required"
        reason = "Active decomposed or high-assurance planning exists, but no delegation decision is recorded."
        required_next_action = "record-delegation-decision"
        workflow_sufficient = False
    elif (
        active_planning_present
        and active_parent_decomposition_requirement.get("required")
        and (path_classification["implementation_paths"] or work_shape in {"lane", "epic"})
    ):
        status = "blocked"
        decision = "parent-decomposition-decision-required"
        reason = (
            "Active epic-backed planning is linked to a parent decomposition lane that has not been updated, linked, or explicitly skipped."
        )
        required_next_action = "update-link-or-skip-parent-decomposition"
        workflow_sufficient = False
    elif active_planning_present and hierarchy_owner_requirement.get("required"):
        status = "blocked"
        decision = "lane-owner-artifact-required"
        reason = "The active execplan is a slice with a recorded parent lane, but no first-class lane owner artifact exists."
        required_next_action = "create-or-promote-lane-owner"
        workflow_sufficient = False
    elif active_planning_present:
        status = "satisfied"
        decision = "planning-backed"
        reason = "Active planning owns broad or high-assurance implementation."
        required_next_action = "continue-from-active-plan"
        workflow_sufficient = True
    elif path_classification["dirty_shape"] == "planning-only":
        status = "clear"
        decision = "planning-recovery-or-prep"
        reason = "Only planning surfaces are named; validate planning state before implementation."
        required_next_action = "validate-planning-state"
        workflow_sufficient = True
    elif path_classification["dirty_shape"] == "planning-plus-implementation":
        status = "violation"
        decision = "implementation-owner-missing"
        reason = "Implementation paths are mixed with planning recovery paths without active planning ownership."
        required_next_action = "checkpoint-planning-before-implementation"
        workflow_sufficient = False
    elif (not active_planning_present) and candidate_pressure.get("status") == "promotion-required" and not closeout_publication_residue:
        status = "blocked"
        decision = "candidate-lane-promotion-required"
        reason = "Checked-in Planning candidates indicate broad or lane-shaped work; promote or decompose a bounded lane first."
        required_next_action = "select-or-promote-candidate-lane"
        workflow_sufficient = False
    elif (
        (not active_planning_present)
        and issue_refs
        and (not changed_paths)
        and issue_scope_evidence.get("status") in {"unknown", "partial"}
    ):
        status = "attention"
        decision = "external-issue-scope-unknown"
        reason = "The task references external issue id(s), but AW has no complete cached intent evidence for their scope."
        required_next_action = "refresh-external-intent-or-state-bounded-slice"
        workflow_sufficient = True
    elif path_classification["implementation_paths"] and path_classification["scope_growth_detected"]:
        status = "attention"
        decision = "agent-work-shape-decision-required"
        reason = (
            "Changed paths cross implementation boundaries; AW reports the scope facts and proof factors, and the agent owns "
            "whether to continue direct or create planning."
        )
        required_next_action = "decide-work-shape-from-scope-facts"
        workflow_sufficient = True
    else:
        status = "clear"
        decision = "direct-work-allowed"
        reason = "No AW-owned hard blocker was detected; the agent owns soft work-shape judgment."
        required_next_action = "continue-direct"
        workflow_sufficient = True
    candidates = (
        [
            _candidate_with_canonical_route(candidate)
            for candidate in decomposition_delegation.get("candidates", [])
            if isinstance(candidate, dict)
        ]
        if isinstance(decomposition_delegation, dict) and isinstance(decomposition_delegation.get("candidates"), list)
        else []
    )
    custody_planning = _custody_only_planning_payload(
        active_planning_present=active_planning_present,
        candidate_pressure=candidate_pressure,
        issue_scope_evidence=issue_scope_evidence,
        issue_refs=issue_refs,
        work_shape=work_shape,
        task_text=task_text,
        workflow_sufficient=workflow_sufficient,
        planning_revision=planning_revision,
        promotion_command=promotion_command,
    )
    authority_boundary = _authority_boundary_payload(
        surface="planning_safety_gate",
        enforced_by_aw=[decision] if not workflow_sufficient else [],
        observed_by_aw=[
            f"active_planning_present={active_planning_present}",
            f"dirty_shape={path_classification.get('dirty_shape')}",
            f"hierarchy_owner_status={hierarchy_owner_requirement.get('status')}",
            *[f"issue_ref={issue_ref}" for issue_ref in issue_refs],
        ],
        recommended_by_aw=[required_next_action] if workflow_sufficient else [],
        candidate_routes=[
            str(_candidate_route_label(candidate) or "")
            for candidate in candidates
            if isinstance(candidate, dict) and _candidate_route_label(candidate)
        ],
        proof_hints=["selected proof commands", "changed path categories"],
        agent_owned_decisions=[
            "semantic work shape when workflow_sufficient is true",
            "whether direct work remains bounded when no hard blocker applies",
            "whether candidate planning pressure should become an active plan",
        ],
        human_owned_decisions=["issue intent and acceptance boundary when external issue evidence is unknown"]
        if issue_scope_evidence.get("status") in {"unknown", "partial"}
        else [],
        rule=(
            "Planning safety can enforce missing ownership or active-plan gates; path classifications and candidate routes "
            "are support signals for agent judgment."
        ),
    )
    read_only_allowance = _read_only_allowance_packet(
        implementation_allowed=workflow_sufficient,
        completion_claim_allowed=workflow_sufficient,
        gate_result=decision,
        required_next_action=required_next_action,
    )
    retrofit_commands = _retrofit_active_owner_commands(config=config, planning_revision=planning_revision)
    return {
        "kind": "agentic-workspace/planning-safety-gate/v1",
        "status": status,
        "gate_result": decision,
        "decision": decision,
        "workflow_sufficient": workflow_sufficient,
        "reason": reason,
        "authority_boundary": authority_boundary,
        "required_next_action": required_next_action,
        "active_planning_present": active_planning_present,
        "planning_revision": planning_revision,
        "active_plan_reliance": active_plan_reliance,
        "active_state_summary": active_summary,
        "issue_refs": issue_refs,
        "pr_context": {
            "status": "pr-context-detected" if pr_context_refs else "not-detected",
            "refs": pr_context_refs,
            "rule": "PR/review/merge-conflict wording is provider context, not unknown issue scope. Fetch PR/review state when needed.",
            "provider_requirement": "provider-aware; GitHub is one possible source, not assumed as the only provider.",
        },
        "issue_scope_evidence": issue_scope_evidence,
        "candidate_pressure": candidate_pressure,
        "custody_planning": custody_planning,
        "hierarchy_owner_requirement": hierarchy_owner_requirement,
        "repair_route": {
            "status": "available" if decision == "implementation-owner-missing" else "retired",
            "route": "retrofit-active-owner-then-closeout" if decision == "implementation-owner-missing" else "work-shape-guidance-only",
            "work_context": "already-started-continuation-or-review-repair"
            if decision == "implementation-owner-missing"
            else "new-or-direct-work-shape-guidance",
            "fit_criteria": [
                "mixed Planning and implementation paths already exist",
                "the slice is bounded and can be honestly described from the current diff",
                "active Planning ownership is missing but required before completion claims",
            ]
            if decision == "implementation-owner-missing"
            else [
                "use work_shape_guidance instead of prompt phrase exceptions",
                "agent decides whether a repair is small enough when hard_blockers is empty",
            ],
            "claim_current_slice_command": retrofit_commands["claim"] if decision == "implementation-owner-missing" else "",
            "after_claim_command": retrofit_commands["summary"] if decision == "implementation-owner-missing" else "",
            "closeout_command": retrofit_commands["closeout"] if decision == "implementation-owner-missing" else "",
            "archive_cleanup_command": retrofit_commands["archive"] if decision == "implementation-owner-missing" else "",
            "workflow": [
                {
                    "stage": "claim-current-slice",
                    "command": retrofit_commands["claim"],
                    "purpose": "Create an active owner for bounded WIP without treating it as prep-only planning.",
                },
                {
                    "stage": "tighten-owner",
                    "command": retrofit_commands["summary"],
                    "purpose": "Use the active plan as the current owner and replace generic scaffold text with current-diff scope.",
                },
                {
                    "stage": "record-closeout-evidence",
                    "command": retrofit_commands["closeout"],
                    "purpose": "Record proof, claim level, intent status, and residue before cleanup.",
                },
                {
                    "stage": "remove-active-residue",
                    "command": retrofit_commands["archive"],
                    "purpose": "Retain closeout evidence while removing active execplan state from a slice-closing PR.",
                },
            ]
            if decision == "implementation-owner-missing"
            else [],
            "cleanup_rule": "After proof and closeout evidence are recorded, run archive_cleanup_command before publishing a slice-closing PR."
            if decision == "implementation-owner-missing"
            else "",
            "safety_rule": "Mixed planning plus implementation changes still need an owner before broad completion claims.",
            "rule": "Use the compact retrofit path for already-started bounded work; otherwise work-shape guidance reports blockers, factors, proof, and stop conditions.",
        },
        "work_shape_guidance": _work_shape_guidance_payload(
            path_classification=path_classification,
            issue_refs=issue_refs,
            work_shape=work_shape or "unknown",
            proof_burden=proof_burden or "unknown",
            active_planning_present=active_planning_present,
            status=status,
            decision=decision,
            workflow_sufficient=workflow_sufficient,
            required_next_action=required_next_action,
            cli_invoke=config.cli_invoke,
        ),
        "decomposition": {"status": decomposition_status or "unknown", "candidate_count": len(candidates), "candidates": candidates},
        "changed_path_facts": path_classification,
        "changed_path_classification": path_classification,
        "promotion_command": promotion_command,
        "delegation_decision_command": active_delegation_requirement.get("command"),
        "active_delegation_requirement": active_delegation_requirement,
        "active_parent_decomposition_requirement": active_parent_decomposition_requirement,
        "implementation_allowed": workflow_sufficient,
        "read_only_allowed": read_only_allowance["read_only_allowed"],
        "exploration_allowed": read_only_allowance["exploration_allowed"],
        "allowed_read_only_actions": read_only_allowance["allowed_read_only_actions"],
        "claim_boundary": read_only_allowance["claim_boundary"],
        "new_plan_command": _command_with_cli_invoke(
            command=_command_with_expected_planning_revision(
                "agentic-workspace planning new-plan --id <id> --title <title> --target . --activate --format json",
                planning_revision=planning_revision,
            ),
            cli_invoke=config.cli_invoke,
        ),
        "recovery_guidance": [
            "If implementation WIP exists without active planning ownership, use repair_route.claim_current_slice_command to retrofit an active owner before continuing.",
            "For continuation or review repair, prefer retrofit-active-owner-then-closeout over hand-editing a generic prep-only scaffold.",
            "After proof, use repair_route.closeout_command and remove active residue before publishing a PR that closes the slice.",
            "If a decomposition lane already exists, promote that lane instead of reconstructing the slice by hand.",
            "If direct work has grown across boundaries, create or promote an execplan from the discovered scope before further edits.",
        ],
        "delegation_decision_required": active_delegation_requirement.get("required", False),
        "legacy_aliases": {
            "decision": "gate_result",
            "changed_path_classification": "changed_path_facts",
            "decomposition.candidates[].route_candidate": "decomposition.candidates[].candidate_route",
        },
        "rule": "Direct/no-plan mode is provisional; AW hard blockers, changed-path scope growth, or active planning obligations require checked-in ownership.",
    }


def _active_planning_record(*, module_reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    planning_report = next((report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"), None)
    if not isinstance(planning_report, dict):
        return None
    planning_record = planning_report.get("active", {}).get("planning_record", {})
    if not isinstance(planning_record, dict) or planning_record.get("status") != "present":
        return None
    return planning_record
