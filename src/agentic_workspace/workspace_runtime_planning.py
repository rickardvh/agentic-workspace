"""Planning continuation and active-state runtime packets.

This module owns Planning runtime packet helpers while the old monolith keeps
compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import argparse
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
    _checkpoint_git_value,
    _command_with_expected_planning_revision,
    _decision_maturity_payload,
    _emit_payload,
    _ensure_external_intent_cache_if_available,
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
    _resolve_target_root,
    _rewrite_module_cli_commands,
    _validate_target_root,
    _work_shape_guidance_payload,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _command_with_cli_invoke,
)


def _run_reconcile_report_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="reconcile", target_root=target_root)
    from repo_planning_bootstrap.installer import planning_reconcile
    from repo_planning_bootstrap.runtime_projection import _print_reconcile

    _ensure_external_intent_cache_if_available(target_root=target_root)
    payload = planning_reconcile(
        target=target_root,
        apply_safe_prune=bool(getattr(args, "apply_safe_prune", False)),
        dry_run=bool(getattr(args, "dry_run", False)),
    )
    payload = _rewrite_module_cli_commands(payload)
    if args.format == "json":
        _emit_payload(payload=payload, format_name=args.format)
    else:
        _print_reconcile(payload)
    return 0


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
    for candidate in top_roadmap[:5]:
        candidate_id = str(candidate.get("id", "")).strip()
        if not candidate_id:
            continue
        source_bucket = str(candidate.get("source_bucket", "")).strip()
        owner_surface = str(candidate.get("owner_surface") or candidate.get("surface") or "").strip()
        has_existing_execplan = source_bucket.startswith("todo.") and bool(
            re.search(r"\.agentic-workspace/planning/execplans/.+", owner_surface)
        )
        is_lane_record = source_bucket == "roadmap.lanes" or owner_surface.endswith(".lane.json")
        if has_existing_execplan:
            route_command = _command_with_cli_invoke(
                command=f'agentic-workspace summary --target "{target_root.as_posix()}" --select execplans --format json',
                cli_invoke=config.cli_invoke,
            )
            canonical_operation = "none"
            next_action = "reuse-existing-execplan-owner"
            mutation_required = False
        elif is_lane_record:
            route_command = _command_with_cli_invoke(
                command=_command_with_expected_planning_revision(
                    f'agentic-workspace planning lane-activate {candidate_id} --target "{target_root.as_posix()}" --format json',
                    planning_revision=planning_revision,
                ),
                cli_invoke=config.cli_invoke,
            )
            canonical_operation = "planning.lane-activate.lifecycle"
            next_action = "activate-existing-lane-owner"
            mutation_required = True
        else:
            route_command = _candidate_promotion_command(
                candidate_id=candidate_id,
                config=config,
                planning_revision=planning_revision,
            )
            canonical_operation = "planning.promote-to-plan.lifecycle"
            next_action = "promote-roadmap-candidate-to-plan"
            mutation_required = True
        route_options.append(
            {
                "kind": "roadmap-candidate",
                "id": candidate_id,
                "title": candidate.get("title", ""),
                "refs": candidate.get("refs", ""),
                "source_bucket": source_bucket,
                "owner_surface": owner_surface,
                "canonical_operation": canonical_operation,
                "next_action": next_action,
                "mutation_required": mutation_required,
                "command": route_command,
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


def _work_shape_study_payload(
    *,
    target_root: Path,
    config: WorkspaceConfig,
    issue_refs: list[str],
    issue_scope_evidence: dict[str, Any],
    active_planning_present: bool,
    planning_revision: dict[str, Any],
    candidate_pressure: dict[str, Any],
    work_shape: str | None,
    proof_burden: str | None,
) -> dict[str, Any]:
    """Compile only the evidence needed to choose a Planning shape."""
    custody_required = active_planning_present or work_shape in {"lane", "epic"} or proof_burden == "high"
    if not issue_refs:
        return {
            "kind": "agentic-workspace/work-shape-study/v1",
            "status": "not-applicable",
            "planning_custody_required": custody_required,
            "work_shape_evidence_status": "sufficient" if work_shape in {"direct", "bounded", "lane", "epic"} else "unknown",
            "rule": "Pre-study stays absent unless concrete missing evidence could change the Planning shape.",
        }

    evidence_status = str(issue_scope_evidence.get("status") or "unknown")
    raw_evidence = [item for item in issue_scope_evidence.get("evidence", []) if isinstance(item, dict)]
    observed: list[str] = []
    inferred: list[str] = []
    unavailable = [str(item) for item in issue_scope_evidence.get("missing_issue_refs", []) if str(item).strip()]
    selected_shape = ""
    artifact_route = ""
    ambiguous_evidence = False
    broad_kinds = {"parent-lane", "lane", "epic", "roadmap", "capability-lane", "issue-batch"}
    for item in raw_evidence:
        item_id = str(item.get("id") or "").strip()
        kind = str(item.get("kind") or "").strip().lower()
        parent_id = str(item.get("parent_id") or "").strip()
        if kind:
            observed.append(f"{item_id}:kind={kind}")
        if parent_id:
            observed.append(f"{item_id}:parent_id={parent_id}")
        if kind in {"ambiguous", "unknown-shape"}:
            ambiguous_evidence = True
        elif kind in broad_kinds:
            selected_shape = "epic" if kind == "epic" else "lane"
            artifact_route = "decomposition-planning" if selected_shape == "epic" else "lane-planning"
        elif parent_id and selected_shape not in {"lane", "epic"}:
            selected_shape = "slice"
            artifact_route = "lane-slice-planning"
    if not selected_shape and evidence_status == "available" and not ambiguous_evidence:
        selected_shape = work_shape if work_shape in {"lane", "epic"} else "direct" if work_shape == "direct" else "bounded"
        artifact_route = {
            "lane": "lane-planning",
            "epic": "decomposition-planning",
            "direct": "direct-no-artifact",
            "bounded": "bounded-execplan",
        }[selected_shape]
        inferred.append(f"available referenced intent supports {selected_shape} work")

    missing_can_change_shape = evidence_status in {"unknown", "partial"}
    custody_required = custody_required or selected_shape in {"lane", "epic", "slice"} or ambiguous_evidence
    if missing_can_change_shape:
        result_status, decision_status = "information-gathering-required", "study-required"
        selected_shape, artifact_route, next_action = "unknown", "", "refresh-referenced-external-intent"
    elif ambiguous_evidence:
        result_status, decision_status = "ambiguous", "needs-human-decision"
        selected_shape, artifact_route, next_action = "unknown", "", "ask-work-shape-clarification"
    elif active_planning_present:
        result_status, decision_status, next_action = "consumed", "consumed-by-planning", "continue-from-active-plan"
    else:
        result_status = "skipped" if selected_shape in {"direct", "bounded"} else "sufficient"
        decision_status = "shape-selected"
        next_action = {
            "lane": "create-or-promote-lane-owner",
            "epic": "create-or-promote-decomposition-owner",
            "slice": "create-or-promote-parent-lane-owner",
            "direct": "continue-direct",
            "bounded": "create-bounded-execplan" if custody_required else "continue-direct",
        }.get(selected_shape, "needs-human-decision")

    route_options = [route for route in candidate_pressure.get("route_options", []) if isinstance(route, dict)]
    reusable_owner_route = next(
        (
            route
            for route in route_options
            if route.get("next_action") == "reuse-existing-execplan-owner" and str(route.get("owner_surface") or "").strip()
        ),
        None,
    )
    if reusable_owner_route is None:
        reusable_owner_route = next(
            (
                route
                for route in route_options
                if route.get("next_action") == "activate-existing-lane-owner" and str(route.get("owner_surface") or "").strip()
            ),
            None,
        )
    if reusable_owner_route and selected_shape in {"bounded", "slice", "epic"}:
        artifact_route = "existing-planning-owner"
        next_action = str(reusable_owner_route.get("next_action") or "select-existing-planning-owner")

    owner_writer: dict[str, Any]
    if reusable_owner_route and selected_shape in {"bounded", "slice", "epic"}:
        owner_surface = str(reusable_owner_route.get("owner_surface") or "").strip()
        expected_kind = "planning-lane-record" if owner_surface.endswith(".lane.json") else "planning-execplan"
        owner_writer = {
            "required_artifact_kind": expected_kind,
            "canonical_operation": str(reusable_owner_route.get("canonical_operation") or "none"),
            "selected_route": str(reusable_owner_route.get("next_action") or "select-existing-planning-owner"),
            "mutation_required": bool(reusable_owner_route.get("mutation_required")),
            "id": str(reusable_owner_route.get("id") or "").strip(),
            "source_bucket": str(reusable_owner_route.get("source_bucket") or "").strip(),
            "command": str(reusable_owner_route.get("command") or ""),
            "readiness_requirements": ["existing Planning owner remains current", "planning revision remains current"],
            "postcondition": {
                "owner_path": owner_surface,
                "selector_command": _command_with_cli_invoke(
                    command=f'agentic-workspace summary --target "{target_root.as_posix()}" --select execplans,lanes --format json',
                    cli_invoke=config.cli_invoke,
                ),
                "expected_owner_kind": expected_kind,
            },
        }
    elif selected_shape == "lane":
        source_ref = next((str(item.get("id") or "") for item in raw_evidence if str(item.get("id") or "").strip()), "lane")
        lane_id = re.sub(r"[^a-z0-9]+", "-", source_ref.lower()).strip("-") or "lane"
        owner_id = f"issue-{lane_id}"
        existing_owner_path = target_root / ".agentic-workspace" / "planning" / "lanes" / f"{owner_id}.lane.json"
        existing_owner: dict[str, Any] | None = None
        if existing_owner_path.is_file():
            try:
                loaded_owner = json.loads(existing_owner_path.read_text(encoding="utf-8-sig"))
                existing_owner = loaded_owner if isinstance(loaded_owner, dict) else None
            except (OSError, json.JSONDecodeError):
                existing_owner = None
        promotion_route = next(
            (
                route
                for route in candidate_pressure.get("route_options", [])
                if isinstance(route, dict) and route.get("kind") == "decomposition-lane" and route.get("id") == owner_id
            ),
            None,
        )
        if promotion_route is None:
            decomposition_root = target_root / ".agentic-workspace" / "planning" / "decompositions"
            for decomposition_path in sorted(decomposition_root.glob("*.decomposition.json")) if decomposition_root.exists() else []:
                try:
                    decomposition_record = json.loads(decomposition_path.read_text(encoding="utf-8-sig"))
                except (OSError, json.JSONDecodeError):
                    continue
                candidates = decomposition_record.get("candidate_lanes", []) if isinstance(decomposition_record, dict) else []
                if any(
                    isinstance(candidate, dict)
                    and str(candidate.get("id") or "").strip() == owner_id
                    and str(candidate.get("readiness") or "").strip() != "promoted"
                    for candidate in candidates
                ):
                    promotion_route = {
                        "kind": "decomposition-lane",
                        "id": owner_id,
                        "decomposition": decomposition_path.relative_to(target_root).as_posix(),
                    }
                    break
        selected_operation = (
            "" if existing_owner else "planning.lane-promote.lifecycle" if promotion_route else "planning.lane-create.lifecycle"
        )
        selected_route = (
            "reuse-existing-lane-owner"
            if existing_owner
            else "promote-existing-decomposition-candidate"
            if promotion_route
            else "create-new-lane-owner"
        )
        if existing_owner:
            command = _command_with_cli_invoke(
                command=f'agentic-workspace summary --target "{target_root.as_posix()}" --select lanes --format json',
                cli_invoke=config.cli_invoke,
            )
        else:
            command = _command_with_cli_invoke(
                command=_command_with_expected_planning_revision(
                    (
                        f'agentic-workspace planning lane-promote {owner_id} --target "{target_root.as_posix()}" --format json'
                        if promotion_route
                        else f'agentic-workspace planning lane-create --id {owner_id} --target "{target_root.as_posix()}" --format json'
                    ),
                    planning_revision=planning_revision,
                ),
                cli_invoke=config.cli_invoke,
            )
        owner_writer = {
            "required_artifact_kind": "planning-lane-record",
            "canonical_operation": selected_operation,
            "selected_route": selected_route,
            "mutation_required": existing_owner is None,
            "command": command,
            "readiness_requirements": ["referenced intent resolved to lane", "planning revision remains current"],
            "postcondition": {
                "owner_path": f".agentic-workspace/planning/lanes/{owner_id}.lane.json",
                "parent_decomposition": (
                    str(existing_owner.get("parent_decomposition_ref") or "")
                    if existing_owner
                    else str(promotion_route.get("decomposition") or "")
                    if promotion_route
                    else ""
                ),
                "selector_command": _command_with_cli_invoke(
                    command=f'agentic-workspace summary --target "{target_root.as_posix()}" --select lanes --format json',
                    cli_invoke=config.cli_invoke,
                ),
                "expected_owner_kind": "planning-lane-record",
            },
        }
    elif selected_shape == "epic":
        source_ref = next((str(item.get("id") or "") for item in raw_evidence if str(item.get("id") or "").strip()), "epic")
        epic_id = re.sub(r"[^a-z0-9]+", "-", source_ref.lower()).strip("-") or "epic"
        command = _command_with_cli_invoke(
            command=_command_with_expected_planning_revision(
                f'agentic-workspace planning decomposition-create --id issue-{epic_id} --title "Epic for {source_ref}" --outcome "Deliver the larger intended outcome for {source_ref}" --target "{target_root.as_posix()}" --format json',
                planning_revision=planning_revision,
            ),
            cli_invoke=config.cli_invoke,
        )
        owner_writer = {
            "required_artifact_kind": "planning-decomposition-record",
            "canonical_operation": "planning.decomposition-create.lifecycle",
            "command": command,
            "readiness_requirements": ["larger intended outcome is named"],
            "postcondition": {
                "owner_path": f".agentic-workspace/planning/decompositions/issue-{epic_id}.decomposition.json",
                "selector_command": _command_with_cli_invoke(
                    command=f'agentic-workspace planning report --target "{target_root.as_posix()}" --verbose --format json',
                    cli_invoke=config.cli_invoke,
                ),
                "expected_owner_kind": "planning-decomposition-record",
            },
        }
    elif selected_shape == "bounded" and custody_required:
        source_ref = next((str(item.get("id") or "") for item in raw_evidence if str(item.get("id") or "").strip()), "bounded-plan")
        plan_id = re.sub(r"[^a-z0-9]+", "-", source_ref.lower()).strip("-") or "bounded-plan"
        command = _command_with_cli_invoke(
            command=_command_with_expected_planning_revision(
                f'agentic-workspace planning new-plan --id issue-{plan_id} --title "Bounded plan for {source_ref}" --target "{target_root.as_posix()}" --activate --switch-active --format json',
                planning_revision=planning_revision,
            ),
            cli_invoke=config.cli_invoke,
        )
        owner_writer = {
            "required_artifact_kind": "planning-execplan",
            "canonical_operation": "planning.new-plan.lifecycle",
            "command": command,
            "readiness_requirements": ["bounded scope is named"],
            "postcondition": {
                "owner_path": f".agentic-workspace/planning/execplans/issue-{plan_id}.plan.json",
                "selector_command": _command_with_cli_invoke(
                    command=f'agentic-workspace summary --target "{target_root.as_posix()}" --select execplans --format json',
                    cli_invoke=config.cli_invoke,
                ),
                "expected_owner_kind": "planning-execplan",
            },
        }
    else:
        owner_writer = {
            "required_artifact_kind": "none",
            "canonical_operation": "none",
            "command": "",
            "readiness_requirements": [],
            "postcondition": {"expected_owner_kind": "none"},
        }

    refresh_command = str(issue_scope_evidence.get("refresh_command") or "")
    source_path = str(issue_scope_evidence.get("source_path") or "")
    source_mtime = ""
    if source_path:
        try:
            source_mtime = str((target_root / source_path).stat().st_mtime_ns)
        except OSError:
            source_mtime = "unavailable"
    return {
        "kind": "agentic-workspace/work-shape-study/v1",
        "status": result_status,
        "planning_custody_required": custody_required,
        "work_shape_evidence_status": "insufficient" if missing_can_change_shape else "sufficient",
        "decision": {
            "status": decision_status,
            "work_shape": selected_shape,
            "planning_artifact_route": artifact_route,
            "next_safe_action": next_action,
            "owner_writer": owner_writer,
        },
        "evidence": {
            "observed": observed,
            "inferred": inferred,
            "missing": [f"referenced intent for {item}" for item in unavailable],
            "unavailable": unavailable,
        },
        "safe_probes": (
            [{"command": refresh_command, "why": "May distinguish direct or bounded work from a lane, slice, or epic.", "read_only": True}]
            if refresh_command and missing_can_change_shape
            else []
        ),
        "blocked_mutations": (["planning shape-specific creation", "product implementation"] if missing_can_change_shape else []),
        "budget": {
            "scope": "direct references and one-hop parent/child shape evidence",
            "stop_when": "one Planning shape is sufficiently supported",
            "escalate_when": "materially different shapes remain plausible after safe probes",
        },
        "freshness": {
            "task_binding": issue_refs,
            "intent_revision": source_mtime,
            "source_head": _checkpoint_git_value(target_root=target_root, args=["rev-parse", "HEAD"]) or "unavailable",
            "planning_revision": planning_revision.get("revision_id", ""),
            "config_identity": config.cli_invoke,
            "stale_when": [
                "referenced intent changes",
                "parent/child relationships change",
                "source HEAD changes",
                "active Planning changes",
                "relevant config changes",
                "user corrects intent",
            ],
        },
        "consumption": {
            "next_owner": "Planning canonical core" if active_planning_present else artifact_route or "agent decision",
            "state": "consumed" if active_planning_present else "pending" if custody_required else "not-needed",
            "retain_after_consumption": False,
        },
        "decision_delta": {
            "before": "unknown" if missing_can_change_shape else selected_shape,
            "after": selected_shape if not missing_can_change_shape else "unknown",
            "evidence_arrived": not missing_can_change_shape,
            "newly_safe_action": next_action,
        },
        "rule": "This disposable packet selects Planning shape; Planning becomes authoritative after consumption.",
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


def _planning_route_evidence_payload(
    *,
    active_planning_present: bool,
    active_plan_reliance: dict[str, Any],
    active_summary: dict[str, Any],
    task_text: str | None,
    config: WorkspaceConfig,
    planning_revision: dict[str, Any],
) -> dict[str, Any]:
    """Collect bounded, structured Planning evidence for route resolution.

    This producer does not expose a consumer action contract.  The route
    resolver below is the only surface that converts these facts into route
    dimensions, claims, authority, and a next action.
    """
    if not active_planning_present:
        return {"kind": "agentic-workspace/task-switch-reconciliation/v1", "status": "not-applicable"}
    summary_command = _command_with_cli_invoke(command="agentic-workspace summary --target . --format json", cli_invoke=config.cli_invoke)
    closeout_command = _command_with_expected_planning_revision(
        _command_with_cli_invoke(
            command="agentic-workspace planning closeout --target . --proof-from last --format json",
            cli_invoke=config.cli_invoke,
        ),
        planning_revision=planning_revision,
    )
    text = " ".join((task_text or "").lower().split())
    maintenance_markers = ("report", "dogfood", "upgrade", "payload", "config", "doctor", "comment", "review", "status")
    matched_maintenance_markers = [marker for marker in maintenance_markers if marker in text]
    mismatch_evidence = _task_switch_mismatch_evidence(active_summary=active_summary, task_text=task_text)
    shared_refs = [str(ref) for ref in mismatch_evidence.get("shared_refs", []) if str(ref).strip()]
    if shared_refs:
        return {
            "kind": "agentic-workspace/task-switch-reconciliation/v1",
            "status": "issue-matched-continuation",
            "summary": "Current task shares explicit structured issue or PR refs with the active plan; treat it as active-plan continuation unless other gates name a concrete mismatch.",
            "active_execplan": active_summary.get("active_execplan", ""),
            "intent_conflict_state": "explicit-reference-continuation",
            "mismatch_evidence": mismatch_evidence,
            "current_task_class": "active-plan-continuation",
            "classification_basis": "shared-structured-reference",
            "matched_maintenance_markers": matched_maintenance_markers,
            "classification_inputs": [
                "active_plan_reliance.status=not-needed-for-current-task",
                f"shared_refs={','.join(str(ref) for ref in shared_refs[:8])}",
                f"shared_ref_count={len(shared_refs)}",
                f"shared_term_count={len(mismatch_evidence.get('shared_terms', []))}",
            ],
            "semantic_boundary": (
                "Only structured issue/PR reference overlap can suppress generic active-plan task-switch pressure here. "
                "This does not close the active plan or override other planning, proof, parent-closure, or delegation gates."
            ),
            "recommended_next_action": "continue-active-plan",
            "next_action_packet": {
                "action": "continue-active-plan",
                "summary": "The task and active plan share explicit refs; continue through the active plan route unless a concrete structured mismatch appears.",
                "command": summary_command,
                "run": summary_command,
                "risk": "issue-matched-continuation",
                "required_inputs": ["current task", "active plan boundary", "shared issue/PR refs"],
                "next_proof": "use implement/proof for changed paths and keep active plan closeout separate from task-switch classification",
                "read_first": [summary_command],
                "open_execplan_only_when": "the continuation needs active plan contract or proof detail",
            },
            "safe_routes": [
                {
                    "id": "continue-active-plan",
                    "command": summary_command,
                    "when": "the shared issue/PR reference is the intended active plan continuation",
                },
                {
                    "id": "reconcile-active-plan-before-implementation",
                    "command": closeout_command,
                    "when": "another structured field names a concrete mismatch despite the shared reference",
                },
            ],
            "implementation_allowed": True,
            "active_plan_protection": {
                "claim_boundary": "The task may continue the active plan but must still satisfy plan proof and closeout before completion claims.",
                "blocked_claims": ["claim-unrelated-task-complete", "silently-close-active-plan"],
            },
            "rule": "Structured issue/PR ref overlap is active-plan continuation evidence; arbitrary prose keyword overlap is not.",
        }
    configured_target_root = getattr(config, "target_root", None)
    if isinstance(configured_target_root, Path):
        completed_route_target_root = configured_target_root
    elif configured_target_root:
        completed_route_target_root = Path(configured_target_root)
    else:
        completed_route_target_root = Path.cwd()
    text = " ".join((task_text or "").lower().split())
    maintenance_markers = ("report", "dogfood", "upgrade", "payload", "config", "doctor", "comment", "review", "status")
    matched_maintenance_markers = [marker for marker in maintenance_markers if marker in text]
    bounded_reflection = _bounded_reflection_reporting_payload(task_text=task_text)
    recommended = "inspect-current-task-scope"
    mismatch_evidence = _task_switch_mismatch_evidence(active_summary=active_summary, task_text=task_text)
    shared_refs = [str(ref) for ref in mismatch_evidence.get("shared_refs", []) if str(ref).strip()]
    completed_plan_route = _completed_active_plan_route_payload(
        target_root=completed_route_target_root,
        active_summary=active_summary,
        config=config,
        planning_revision=planning_revision,
    )
    if completed_plan_route.get("status") == "archive-or-retire-recommended" and not shared_refs:
        return {
            "kind": "agentic-workspace/task-switch-reconciliation/v1",
            "status": "completed-active-plan-route",
            "summary": "The active execplan has explicit slice completion evidence; route it to archive or retire before treating it as current work.",
            "active_execplan": active_summary.get("active_execplan", ""),
            "intent_conflict_state": "completed-active-plan-residue",
            "mismatch_evidence": mismatch_evidence,
            "current_task_class": "completed-active-plan-cleanup",
            "classification_basis": "active-execplan-closeout-evidence",
            "recommended_next_action": "archive-or-retire-completed-plan",
            "completed_active_plan": completed_plan_route,
            "next_action_packet": {
                "action": "archive-or-retire-completed-plan",
                "summary": "A completed active execplan is still active; archive, retire, demote, or explicitly keep it active before relying on later startup routing.",
                "command": completed_plan_route.get("archive_command", ""),
                "run": completed_plan_route.get("archive_command", ""),
                "risk": "completed-active-plan-residue",
                "required_inputs": ["active execplan", "completion evidence"],
                "next_proof": completed_plan_route.get("recheck_command", summary_command),
                "read_first": [summary_command],
                "open_execplan_only_when": "the archive/retire route needs verification of plan-local closeout evidence",
            },
            "safe_routes": [
                {
                    "id": "archive-completed-active-plan",
                    "command": completed_plan_route.get("archive_command", ""),
                    "when": "plan-local proof and closeout evidence are accepted as current-slice completion",
                },
                {
                    "id": "record-plan-remains-active",
                    "command": summary_command,
                    "when": "completion evidence is insufficient or the plan intentionally remains active",
                },
            ],
            "implementation_allowed": False,
            "active_plan_protection": {
                "claim_boundary": "Completed-plan routing may retire the current slice only; parent/lane closure still requires separate closeout evidence.",
                "blocked_claims": ["claim-lane-complete", "claim-parent-complete", "silently-close-planning-state"],
            },
            "rule": "Completed active-plan cleanup is command-routed; startup never silently archives or closes planning state.",
        }
    if shared_refs:
        return {
            "kind": "agentic-workspace/task-switch-reconciliation/v1",
            "status": "issue-matched-continuation",
            "summary": "Current task shares explicit structured issue or PR refs with the active plan; treat it as active-plan continuation unless other gates name a concrete mismatch.",
            "active_execplan": active_summary.get("active_execplan", ""),
            "intent_conflict_state": "explicit-reference-continuation",
            "mismatch_evidence": mismatch_evidence,
            "current_task_class": "active-plan-continuation",
            "classification_basis": "shared-structured-reference",
            "matched_maintenance_markers": matched_maintenance_markers,
            "classification_inputs": [
                "active_plan_reliance.status=not-needed-for-current-task",
                f"shared_refs={','.join(str(ref) for ref in shared_refs[:8])}",
                f"shared_ref_count={len(shared_refs)}",
                f"shared_term_count={len(mismatch_evidence.get('shared_terms', []))}",
            ],
            "semantic_boundary": (
                "Only structured issue/PR reference overlap can suppress generic active-plan task-switch pressure here. "
                "This does not close the active plan or override other planning, proof, parent-closure, or delegation gates."
            ),
            "recommended_next_action": "continue-active-plan",
            "next_action_packet": {
                "action": "continue-active-plan",
                "summary": "The task and active plan share explicit refs; continue through the active plan route unless a concrete structured mismatch appears.",
                "command": summary_command,
                "run": summary_command,
                "risk": "issue-matched-continuation",
                "required_inputs": ["current task", "active plan boundary", "shared issue/PR refs"],
                "next_proof": "use implement/proof for changed paths and keep active plan closeout separate from task-switch classification",
                "read_first": [summary_command],
                "open_execplan_only_when": "the continuation needs active plan contract or proof detail",
            },
            "safe_routes": [
                {
                    "id": "continue-active-plan",
                    "command": summary_command,
                    "when": "the shared issue/PR reference is the intended active plan continuation",
                },
                {
                    "id": "reconcile-active-plan-before-implementation",
                    "command": closeout_command,
                    "when": "another structured field names a concrete mismatch despite the shared reference",
                },
            ],
            "implementation_allowed": True,
            "active_plan_protection": {
                "claim_boundary": "Shared refs allow continuation routing only; do not claim active-plan completion from this gate.",
                "blocked_claims": ["claim-active-plan-complete", "silently-abandon-active-plan"],
            },
            "rule": "Structured issue/PR ref overlap is active-plan continuation evidence; arbitrary prose keyword overlap is not.",
        }
    if bounded_reflection.get("status") == "bounded":
        return {
            "kind": "agentic-workspace/task-switch-reconciliation/v1",
            "status": "bounded-reflection-reporting",
            "summary": "Current task is bounded reflection, reporting, dogfooding, or issue-shaping; active-plan state remains protected but does not require a generic task-switch choice.",
            "active_execplan": active_summary.get("active_execplan", ""),
            "intent_conflict_state": "bounded-current-task-active-plan-protected",
            "mismatch_evidence": mismatch_evidence,
            "current_task_class": bounded_reflection.get("current_task_class", "bounded-reflection-reporting"),
            "classification_basis": bounded_reflection.get("classification_basis", "read-only-reporting-task-shape"),
            "matched_maintenance_markers": matched_maintenance_markers,
            "classification_inputs": [
                "active_plan_reliance.status=not-needed-for-current-task",
                f"shared_term_count={len(mismatch_evidence.get('shared_terms', []))}",
                f"shared_ref_count={len(mismatch_evidence.get('shared_refs', []))}",
                f"matched_reflection_signal_count={len(bounded_reflection.get('matched_reflection_signals', []))}",
                f"matched_mutation_signal_count={len(bounded_reflection.get('matched_mutation_signals', []))}",
            ],
            "semantic_boundary": bounded_reflection["claim_boundary"],
            "recommended_next_action": "produce-bounded-reflection-report",
            "next_action_packet": {
                "action": "produce-bounded-reflection-report",
                "summary": "Produce the requested bounded reflection/reporting/dogfooding output without claiming active-plan progress.",
                "command": "",
                "run": None,
                "risk": "bounded-reflection-active-plan-protected",
                "required_inputs": ["current task", "active plan claim boundary"],
                "next_proof": "no file proof unless the task later becomes an edit",
                "read_first": [],
                "open_execplan_only_when": "the task changes from reflection/reporting into active-plan mutation or implementation",
            },
            "safe_routes": [
                {
                    "id": "produce-bounded-reflection-report",
                    "command": "",
                    "when": "the current task remains read-only reflection, reporting, dogfooding, or issue shaping",
                },
                {
                    "id": "inspect-active-plan",
                    "command": summary_command,
                    "when": "the reflection needs active-plan audit detail",
                },
                {
                    "id": "reconcile-active-plan-before-implementation",
                    "command": closeout_command,
                    "when": "the task changes into implementation or active-plan mutation",
                },
            ],
            "implementation_allowed": True,
            "active_plan_protection": {
                "claim_boundary": bounded_reflection["claim_boundary"],
                "blocked_claims": ["claim-active-plan-progress", "claim-active-plan-complete", "silently-abandon-active-plan"],
            },
            "rule": "Bounded reflection/reporting may proceed while preserving active-plan claim boundaries and selector-backed audit detail.",
        }
    if active_plan_reliance.get("status") != "not-needed-for-current-task":
        return {"kind": "agentic-workspace/task-switch-reconciliation/v1", "status": "not-applicable"}
    return {
        "kind": "agentic-workspace/task-switch-reconciliation/v1",
        "status": "scope-inspection-required",
        "summary": "Current task does not explicitly continue the active plan. Preserve the selected plan and inspect the current task scope before any mutation.",
        "active_execplan": active_summary.get("active_execplan", ""),
        "intent_conflict_state": "explicit-task-differs-from-active-plan",
        "mismatch_evidence": mismatch_evidence,
        "current_task_class": "new-explicit-task",
        "classification_basis": "explicit-task-without-structured-owner-scope",
        "matched_maintenance_markers": matched_maintenance_markers,
        "classification_inputs": [
            "active_plan_reliance.status=not-needed-for-current-task",
            f"shared_term_count={len(mismatch_evidence.get('shared_terms', []))}",
            f"shared_ref_count={len(mismatch_evidence.get('shared_refs', []))}",
            f"maintenance_marker_count={len(matched_maintenance_markers)}",
        ],
        "semantic_boundary": (
            "The task has no structured continuation or owner-scope evidence. Inspect scope before mutation; maintenance markers "
            "remain non-authoritative diagnostics and cannot select or close the active plan."
        ),
        "recommended_next_action": recommended,
        "next_action_packet": {
            "action": "inspect-current-task-scope",
            "summary": "Inspect the current task's concrete scope before mutation; the selected active plan remains protected.",
            "command": summary_command,
            "run": summary_command,
            "risk": "current-task-scope-unresolved",
            "required_inputs": ["current task", "changed paths or structured owner reference", "active plan boundary"],
            "next_proof": "supply changed paths to implement/proof before a mutation claim; do not claim active-plan progress",
            "read_first": [summary_command],
            "open_execplan_only_when": "the new task mutates active-plan-owned work or needs active plan ownership changed",
        },
        "safe_routes": [
            {
                "id": "inspect-current-task-scope",
                "command": summary_command,
                "when": "the task has no structured continuation or changed-path ownership evidence",
            },
        ],
        "implementation_allowed": False,
        "active_plan_protection": {
            "claim_boundary": "Do not claim active-plan progress, completion, or abandonment from this new task.",
            "blocked_claims": ["claim-active-plan-progress", "claim-active-plan-complete", "silently-abandon-active-plan"],
        },
        "rule": "An unrelated active plan is protected state. Missing current-task scope requires bounded inspection, not a user-visible internal route choice.",
    }


def _acknowledged_current_task_switch_payload(
    task_switch: dict[str, Any], *, changed_paths: list[str], path_classification: dict[str, Any]
) -> dict[str, Any]:
    if task_switch.get("status") not in {"active", "scope-inspection-required"} or not changed_paths:
        return task_switch
    dirty_shape = str(path_classification.get("dirty_shape") or "")
    if dirty_shape in {"planning-only", "planning-plus-implementation", "implementation-with-archived-planning-residue"}:
        return task_switch
    acknowledged = dict(task_switch)
    acknowledged["status"] = "current-task-route-acknowledged"
    acknowledged["intent_conflict_state"] = "current-task-route-acknowledged-active-plan-protected"
    acknowledged["summary"] = (
        "Current task route is acknowledged from the changed-path implementation context; continue current-task proof "
        "without claiming active-plan progress."
    )
    acknowledged["recommended_next_action"] = "prove-current-task"
    acknowledged["next_action_packet"] = {
        "action": "prove-current-task",
        "summary": "Continue current-task implementation proof; active-plan progress remains out of scope.",
        "command": "",
        "run": None,
        "risk": "active-plan-protected-current-task",
        "required_inputs": ["changed paths", "current task", "active plan claim boundary"],
        "next_proof": "run implement/proof-selected commands for the changed paths; do not claim active-plan progress",
        "read_first": [],
        "open_execplan_only_when": "the task mutates active-plan-owned surfaces or needs active plan ownership changed",
    }
    acknowledged["route_acknowledgement"] = {
        "status": "acknowledged",
        "route": "current-task",
        "acknowledged_by": "changed-path implementation context",
        "changed_path_count": len(changed_paths),
        "claim_boundary": "Current task is intentionally separate; do not claim active-plan progress, completion, or abandonment.",
        "proof_rule": "Use current-task proof only.",
        "return_to_active_plan": {
            "status": "available",
            "command": "agentic-workspace summary --target . --format json",
            "rule": "Return by rereading checked-in Planning; route acknowledgement is not an active-plan mutation.",
        },
        "stale_thread_cleanup": {
            "status": "available",
            "inspect_command": "agentic-workspace start --target . --select work_threads --format json",
            "prune_command": "agentic-workspace work-thread prune --target . --all-candidates --dry-run --format json",
            "rule": "Prune only local advisory candidates; never use pruning as completion proof.",
        },
    }
    acknowledged["rule"] = (
        "Changed-path implementation context can acknowledge the current-task route when planning-owned surfaces are not being "
        "mutated; active-plan protection still blocks active-plan progress claims."
    )
    return acknowledged


def _planning_route_decision_payload(
    route_evidence: dict[str, Any],
    *,
    planning_revision: dict[str, Any] | None = None,
    reconciliation_proposal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive the consumer-neutral route contract from orthogonal facts.

    Older evidence packets carry a legacy ``status`` only.  It remains a
    compatibility input, while ordinary producers may supply the three
    decision dimensions directly.
    """
    status = str(route_evidence.get("status") or "not-applicable")
    next_packet = _as_dict(route_evidence.get("next_action_packet"))
    legacy_relation = (
        "continues-selected-owner"
        if status == "issue-matched-continuation"
        else "bounded-independent"
        if status in {"bounded-reflection-reporting", "current-task-route-acknowledged"}
        else "independent-pending-scope"
        if status == "scope-inspection-required"
        else "ambiguous"
        if status == "active"
        else "not-applicable"
    )
    legacy_posture = (
        "completed-residue"
        if status == "completed-active-plan-route"
        else "current"
        if legacy_relation != "not-applicable"
        else "not-applicable"
    )
    task_relation = str(route_evidence.get("task_relation") or legacy_relation)
    owner_posture = str(route_evidence.get("owner_posture") or legacy_posture)
    transition_by_posture = {
        "completed-residue": "closeout-or-archive",
        "external-conflict": "reconcile",
        "externally-stale": "reconcile",
        "projection-drifted": "repair-projection",
        "proof-incomplete": "complete-proof",
        "missing": "select-owner",
    }
    transition = str(
        route_evidence.get("required_transition")
        or transition_by_posture.get(owner_posture)
        or (
            "ask-for-route-decision"
            if task_relation == "ambiguous"
            else "inspect-current-task-scope"
            if task_relation == "independent-pending-scope"
            else "none"
        )
    )
    continuing = task_relation == "continues-selected-owner"
    bounded = task_relation == "bounded-independent"
    ambiguous = task_relation == "ambiguous"
    active_plan_protection = _as_dict(route_evidence.get("active_plan_protection"))
    blocked_claims = active_plan_protection.get("blocked_claims") or route_evidence.get("blocked_claims") or []
    selected_owner_ref = str(route_evidence.get("active_execplan") or "")
    decision = {
        "kind": "agentic-planning/route-decision/v1",
        "task_relation": task_relation,
        "owner_posture": owner_posture,
        "required_transition": transition,
        "selected_owner": selected_owner_ref,
        "selected_owner_identity": {
            "ref": selected_owner_ref,
            "revision": str(_as_dict(planning_revision).get("revision_id") or _as_dict(planning_revision).get("revision") or ""),
        },
        "identity_effects": [],
        "input_provenance": {
            "task_relation": "planning-route-evidence.structured-reference-and-boundary-evidence",
            "owner_posture": "active-owner-lifecycle-and-route-evidence",
            "required_transition": "route-decision-policy; detailed reconciliation remains owned by planning reconcile",
        },
        "reason_codes": [code for code in (status, str(route_evidence.get("intent_conflict_state") or "")) if code],
        "allowed_claims": ["bounded-task-progress"] if bounded else ["active-plan-progress"] if continuing else [],
        "blocked_claims": blocked_claims,
        "implementation_allowed": False if ambiguous or transition != "none" else bool(route_evidence.get("implementation_allowed")),
        "mutation_authority": "none"
        if ambiguous or transition != "none"
        else "current-task"
        if bounded
        else "selected-owner"
        if continuing
        else "none",
        "proof_expectation": str(next_packet.get("next_proof") or ""),
        "state_update_policy": "read-only" if transition == "none" else "explicit-transition-required",
        "next_safe_action": next_packet,
    }
    proposal = _as_dict(reconciliation_proposal)
    if proposal.get("status") == "current":
        decision.update(
            {
                "owner_posture": "external-reconciliation-pending",
                "required_transition": "reconcile",
                "implementation_allowed": False,
                "mutation_authority": "reconciliation-proposal",
                "proof_expectation": "apply the current reconciliation proposal and retain its mutation receipt",
                "state_update_policy": "reconciliation-apply-required",
                "next_safe_action": {
                    "action": "apply-planning-reconciliation-proposal",
                    "command": proposal.get("apply_command", ""),
                    "run": proposal.get("apply_command", ""),
                    "summary": "Apply the current Planning reconciliation proposal after its compare-and-swap check.",
                },
            }
        )
        decision["reason_codes"] = [*decision["reason_codes"], "current-reconciliation-proposal"]
        decision["reconciliation_proposal"] = proposal
    return decision


def _task_switch_reconciliation_payload(**kwargs: Any) -> dict[str, Any]:
    """Compatibility diagnostic alias; ordinary consumers must use route_decision."""
    return _planning_route_evidence_payload(**kwargs)


def _structured_route_inputs(
    *, active_summary: dict[str, Any], task_text: str | None, planning_revision: dict[str, Any], proposal: dict[str, Any]
) -> dict[str, str]:
    """Derive ordinary resolver inputs from current-work and owner facts."""
    active_owner = str(active_summary.get("active_execplan") or "")
    shared_refs = _task_switch_mismatch_evidence(active_summary=active_summary, task_text=task_text).get("shared_refs", [])
    task_relation = "continues-selected-owner" if shared_refs else "independent-pending-scope" if active_owner else "bounded-independent"
    revision_status = str(planning_revision.get("status") or "")
    owner_posture = (
        "projection-drifted"
        if revision_status in {"stale", "drifted"}
        else "external-conflict"
        if proposal.get("status") == "current"
        else "missing"
        if not active_owner
        else "current"
    )
    return {"task_relation": task_relation, "owner_posture": owner_posture}


def _current_reconciliation_proposal(*, target_root: Path, planning_revision: dict[str, Any]) -> dict[str, Any]:
    """Read only a current #2281 proposal summary; compilation remains package-owned."""
    proposal_root = target_root / ".agentic-workspace/local/planning/reconciliation-proposals"
    expected_revision = str(_as_dict(planning_revision).get("revision_id") or "")
    if not proposal_root.is_dir() or not expected_revision:
        return {"status": "absent"}
    for path in sorted(proposal_root.glob("*.json"), reverse=True)[:8]:
        try:
            proposal = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source = _as_dict(_as_dict(proposal).get("source"))
        if source.get("planning_revision") != expected_revision:
            continue
        proposal_id = str(_as_dict(proposal).get("proposal_id") or "")
        apply_command = str(_as_dict(proposal).get("apply_command") or "")
        if proposal_id and apply_command:
            return {"status": "current", "proposal_id": proposal_id, "apply_command": apply_command}
    return {"status": "stale-or-absent"}


def _bounded_reflection_reporting_payload(*, task_text: str | None) -> dict[str, Any]:
    text = " ".join((task_text or "").lower().split())
    if not text:
        return {"kind": "agentic-workspace/bounded-reflection-reporting/v1", "status": "not-detected"}
    reflection_signals = (
        "estimate",
        "net effect",
        "reflection",
        "reflect",
        "retrospective",
        "report",
        "status",
        "summarize",
        "summary",
        "dogfood",
        "dogfooding",
        "feedback",
        "issue-shaping",
        "shape follow-up",
        "concrete feedback",
    )
    issue_shaping_signals = (
        "create concrete",
        "feedback issues",
        "dogfooding feedback issues",
        "new issues",
        "follow-up issues",
    )
    mutation_signals = (
        "implement",
        "fix",
        "edit",
        "change",
        "modify",
        "delete",
        "write code",
        "refactor",
        "make new pull request",
    )
    matched_reflection = [signal for signal in reflection_signals if signal in text]
    matched_issue_shaping = [signal for signal in issue_shaping_signals if signal in text]
    matched_mutation = [signal for signal in mutation_signals if signal in text]
    if not matched_reflection and not matched_issue_shaping:
        return {
            "kind": "agentic-workspace/bounded-reflection-reporting/v1",
            "status": "not-detected",
            "matched_reflection_signals": [],
            "matched_mutation_signals": matched_mutation,
        }
    if matched_mutation:
        return {
            "kind": "agentic-workspace/bounded-reflection-reporting/v1",
            "status": "implementation-like",
            "matched_reflection_signals": matched_reflection,
            "matched_issue_shaping_signals": matched_issue_shaping,
            "matched_mutation_signals": matched_mutation,
            "rule": "Implementation-like signals win over issue-shaping signals; mixed tasks keep active-plan task-switch protection.",
        }
    current_task_class = "bounded-dogfooding-issue-shaping" if matched_issue_shaping else "bounded-reflection-reporting"
    return {
        "kind": "agentic-workspace/bounded-reflection-reporting/v1",
        "status": "bounded",
        "current_task_class": current_task_class,
        "classification_basis": "explicit-read-only-or-issue-shaping-task-shape",
        "matched_reflection_signals": matched_reflection,
        "matched_issue_shaping_signals": matched_issue_shaping,
        "matched_mutation_signals": matched_mutation,
        "claim_boundary": (
            "This task may produce reflection, reporting, dogfooding, or issue-shaping output, but it does not authorize "
            "active-plan progress, completion, abandonment, or unrelated implementation claims."
        ),
        "rule": "This classifier only permits bounded reporting/issue-shaping; implementation-like tasks keep active-plan protection.",
    }


def _completed_active_plan_route_payload(
    *,
    target_root: Path,
    active_summary: dict[str, Any],
    config: WorkspaceConfig,
    planning_revision: dict[str, Any],
) -> dict[str, Any]:
    active_surface, record = _active_execplan_record_payload(target_root=target_root)
    active_surface = active_surface or str(active_summary.get("active_execplan") or "")
    if not active_surface or not record:
        return {"kind": "agentic-workspace/completed-active-plan-route/v1", "status": "not-detected"}
    closure_check = _as_dict(record.get("closure_check"))
    proof_report = _as_dict(record.get("proof_report"))
    intent_satisfaction = _as_dict(record.get("intent_satisfaction"))
    intent_continuity = _as_dict(record.get("intent_continuity"))
    required_continuation = _as_dict(record.get("required_continuation"))
    closure_values = " ".join(
        str(value).lower()
        for value in (
            closure_check.get("slice status"),
            closure_check.get("larger-intent status"),
            closure_check.get("closure decision"),
            intent_satisfaction.get("was original intent fully satisfied?"),
            intent_continuity.get("this slice completes the larger intended outcome"),
            required_continuation.get("required follow-on for the larger intended outcome"),
        )
        if value
    )
    evidence_fields: list[str] = []
    if "complete" in str(closure_check.get("slice status", "")).lower():
        evidence_fields.append("closure_check.slice status")
    if proof_report and any(str(value).strip() for value in proof_report.values()):
        evidence_fields.append("proof_report")
    if str(intent_satisfaction.get("was original intent fully satisfied?", "")).strip().lower() in {"yes", "true", "satisfied"}:
        evidence_fields.append("intent_satisfaction.was original intent fully satisfied?")
    if str(required_continuation.get("required follow-on for the larger intended outcome", "")).strip().lower() in {"no", "none"}:
        evidence_fields.append("required_continuation.required follow-on for the larger intended outcome")
    completed = (
        "closure_check.slice status" in evidence_fields
        and "proof_report" in evidence_fields
        and "intent_satisfaction.was original intent fully satisfied?" in evidence_fields
    )
    if not completed:
        return {
            "kind": "agentic-workspace/completed-active-plan-route/v1",
            "status": "insufficient-evidence",
            "active_execplan": active_surface,
            "evidence_fields": evidence_fields,
            "missing_fields": [
                field
                for field in (
                    "closure_check.slice status",
                    "proof_report",
                    "intent_satisfaction.was original intent fully satisfied?",
                )
                if field not in evidence_fields
            ],
            "rule": "Incomplete active plans keep ordinary active-plan protection.",
        }
    plan_id = str(record.get("id") or Path(active_surface).name.removesuffix(".plan.json").removesuffix(".json")).strip()
    archive_command = _command_with_expected_planning_revision(
        _command_with_cli_invoke(
            command=(
                f"agentic-workspace planning archive-plan --plan {plan_id} --target . "
                "--prepare-closeout --retain-archive --apply-cleanup --format json"
            ),
            cli_invoke=config.cli_invoke,
        ),
        planning_revision=planning_revision,
    )
    recheck_command = _command_with_cli_invoke(command="agentic-workspace start --target . --format json", cli_invoke=config.cli_invoke)
    parent_boundary = (
        "current-slice-complete-only"
        if "closed" not in closure_values and "complete" not in str(closure_check.get("larger-intent status", "")).lower()
        else "parent-or-lane-closure-still-requires-explicit-closeout-authorization"
    )
    return {
        "kind": "agentic-workspace/completed-active-plan-route/v1",
        "status": "archive-or-retire-recommended",
        "active_execplan": active_surface,
        "plan_id": plan_id,
        "evidence_fields": evidence_fields,
        "archive_command": archive_command,
        "recheck_command": recheck_command,
        "parent_lane_boundary": parent_boundary,
        "claim_boundary": "Archive/retire removes stale active-plan pressure; it does not silently close parent or lane intent.",
        "rule": "Completed active plans require an explicit command-owned archive/retire route; startup reports but does not mutate.",
    }


def _pr_comment_repair_context_payload(*, task_text: str | None, changed_paths: list[str]) -> dict[str, Any]:
    text = " ".join(str(task_text or "").lower().split())
    pr_markers = ("pr", "pull request", "review", "review comment", "review feedback")
    repair_markers = ("address", "addressing", "fix", "repair", "respond", "resolve", "comment", "feedback")
    matched_pr_markers = [marker for marker in pr_markers if re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text)]
    matched_repair_markers = [marker for marker in repair_markers if marker in text]
    active = bool(changed_paths and matched_pr_markers and matched_repair_markers)
    return {
        "kind": "agentic-workspace/pr-comment-repair-context/v1",
        "status": "active" if active else "not-detected",
        "matched_pr_markers": matched_pr_markers,
        "matched_repair_markers": matched_repair_markers,
        "changed_path_count": len(changed_paths),
        "claim_class": "pr_feedback_addressed",
        "claim_boundary": (
            "Authorizes only a bounded PR-feedback-addressed claim after proof; it does not authorize lane, parent, "
            "issue, or full-intent completion."
        ),
        "rule": "PR-comment repair routing requires explicit task wording and changed paths; it remains a bounded closeout scope.",
    }


_TASK_SWITCH_STOPWORDS = {
    "about",
    "active",
    "after",
    "again",
    "agent",
    "all",
    "and",
    "are",
    "both",
    "but",
    "close",
    "current",
    "from",
    "have",
    "implement",
    "into",
    "issue",
    "issues",
    "lane",
    "master",
    "new",
    "open",
    "plan",
    "planning",
    "pr",
    "prs",
    "remaining",
    "task",
    "the",
    "this",
    "two",
    "with",
    "work",
}


def _task_switch_terms(text: str) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for term in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.lower()):
        normalized = term.strip("-_")
        if not normalized or normalized in _TASK_SWITCH_STOPWORDS or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(normalized)
        if len(terms) >= 12:
            break
    return terms


def _task_switch_refs(text: str) -> list[str]:
    hash_refs = re.findall(r"#(\d+)", text)
    refs = {f"#{match}" for match in hash_refs}
    refs.update(f"issue-{match}" for match in hash_refs)
    refs.update(f"issue-{match}" for match in re.findall(r"\bissue\s+#?(\d+)\b", text, flags=re.IGNORECASE))
    refs.update(f"issue-{match}" for match in re.findall(r"\bissue[-_](\d+)\b", text, flags=re.IGNORECASE))
    refs.update(f"issue-{match}" for match in re.findall(r"\bissues[-_](\d+)\b", text, flags=re.IGNORECASE))
    refs.update(f"pr-{match}" for match in re.findall(r"\bpr\s+#?(\d+)\b", text, flags=re.IGNORECASE))
    refs.update(f"pr-{match}" for match in re.findall(r"\bpr[-_](\d+)\b", text, flags=re.IGNORECASE))
    return sorted(refs)


def _task_switch_mismatch_evidence(*, active_summary: dict[str, Any], task_text: str | None) -> dict[str, Any]:
    active_execplan = str(active_summary.get("active_execplan") or "")
    active_plan_stem = Path(active_execplan).stem if active_execplan else ""
    if active_plan_stem.endswith(".plan"):
        active_plan_stem = active_plan_stem[: -len(".plan")]
    active_plan_label = active_plan_stem.replace("-", " ")
    active_text = " ".join(
        str(value)
        for value in (
            active_execplan,
            active_plan_label,
            active_summary.get("active_item_id"),
            active_summary.get("planning_status"),
        )
        if value
    )
    task = " ".join((task_text or "").split())
    task_terms = _task_switch_terms(task)
    active_terms = _task_switch_terms(active_text)
    task_refs = _task_switch_refs(task)
    active_refs = _task_switch_refs(active_text)
    shared_terms = [term for term in task_terms if term in set(active_terms)]
    shared_refs = [ref for ref in task_refs if ref in set(active_refs)]
    overlap_signal = "possible-continuation" if shared_refs or len(shared_terms) >= 2 else "low-overlap-explicit-task"
    return {
        "current_task_excerpt": task[:160],
        "active_plan_label": active_plan_label,
        "active_execplan": active_execplan,
        "task_refs": task_refs[:8],
        "active_refs": active_refs[:8],
        "shared_refs": shared_refs[:8],
        "task_terms": task_terms[:8],
        "active_plan_terms": active_terms[:8],
        "shared_terms": shared_terms[:8],
        "overlap_signal": overlap_signal,
        "rule": "Overlap evidence is bounded routing support; it does not decide user intent or close active planning.",
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
    work_shape_study = _work_shape_study_payload(
        target_root=target_root,
        config=config,
        issue_refs=issue_refs,
        issue_scope_evidence=issue_scope_evidence,
        active_planning_present=active_planning_present,
        planning_revision=planning_revision,
        candidate_pressure=candidate_pressure,
        work_shape=work_shape,
        proof_burden=proof_burden,
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
    route_evidence = _planning_route_evidence_payload(
        active_planning_present=active_planning_present,
        active_plan_reliance=active_plan_reliance,
        active_summary=active_summary,
        task_text=task_text,
        config=config,
        planning_revision=planning_revision,
    )
    route_evidence = _acknowledged_current_task_switch_payload(
        route_evidence,
        changed_paths=changed_paths,
        path_classification=path_classification,
    )
    reconciliation_proposal = _current_reconciliation_proposal(target_root=target_root, planning_revision=planning_revision)
    route_evidence = {
        **route_evidence,
        **_structured_route_inputs(
            active_summary=active_summary, task_text=task_text, planning_revision=planning_revision, proposal=reconciliation_proposal
        ),
    }
    route_decision = _planning_route_decision_payload(
        route_evidence,
        planning_revision=planning_revision,
        reconciliation_proposal=reconciliation_proposal,
    )
    closeout_publication_residue = (
        path_classification.get("dirty_shape") == "implementation-with-archived-planning-residue"
        and _as_dict(path_classification.get("archived_planning_residue")).get("status") == "completed-closeout-residue"
    )
    pr_comment_repair_context = _pr_comment_repair_context_payload(task_text=task_text, changed_paths=changed_paths)
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
    elif route_evidence.get("status") == "completed-active-plan-route":
        status = "attention"
        decision = "archive-or-retire-completed-plan"
        reason = str(route_evidence.get("summary") or "The active execplan appears complete and should be routed to archive or retire.")
        required_next_action = "archive-or-retire-completed-plan"
        workflow_sufficient = True
    elif route_evidence.get("status") == "bounded-reflection-reporting":
        status = "satisfied"
        decision = "bounded-reflection-reporting"
        reason = str(
            route_evidence.get("summary") or "Bounded reflection/reporting may proceed while preserving active-plan claim boundaries."
        )
        required_next_action = "produce-bounded-reflection-report"
        workflow_sufficient = True
    elif route_evidence.get("status") == "current-task-route-acknowledged":
        status = "satisfied"
        decision = "current-task-route-acknowledged"
        reason = str(route_evidence.get("summary") or "Current task route is acknowledged; active-plan state remains protected.")
        required_next_action = "prove-current-task"
        workflow_sufficient = True
    elif route_evidence.get("status") == "scope-inspection-required":
        status = "attention"
        decision = "current-task-scope-inspection-required"
        reason = str(route_evidence.get("summary") or "Current task differs from the active plan; inspect scope before mutation.")
        required_next_action = "inspect-current-task-scope"
        workflow_sufficient = True
    elif route_evidence.get("status") == "active":
        status = "attention"
        decision = "active-plan-task-switch"
        reason = str(route_evidence.get("summary") or "Current task differs from the active plan; choose a safe task route.")
        required_next_action = "choose-task-switch-route"
        workflow_sufficient = True
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
    elif path_classification["dirty_shape"] == "planning-plus-implementation" and pr_comment_repair_context.get("status") == "active":
        status = "attention"
        decision = "bounded-pr-comment-repair"
        reason = (
            "Implementation paths are mixed with planning residue, but the task is bounded PR-comment repair; "
            "planning-owner warnings stay visible while only a PR-feedback-addressed claim is in scope."
        )
        required_next_action = "prove-pr-feedback-addressed"
        workflow_sufficient = True
    elif path_classification["dirty_shape"] in {
        "implementation-with-archived-planning-residue",
        "archived-planning-residue-only",
    }:
        status = "satisfied"
        decision = "post-closeout-verification"
        reason = (
            "Changed Planning paths are completed archived closeout residue, so this is a post-closeout verification route "
            "rather than missing active implementation ownership."
        )
        required_next_action = "run-post-closeout-verification"
        workflow_sufficient = True
    elif path_classification["dirty_shape"] == "planning-plus-implementation":
        status = "violation"
        decision = "implementation-owner-missing"
        reason = "Implementation paths are mixed with planning recovery paths without active planning ownership."
        required_next_action = "checkpoint-planning-before-implementation"
        workflow_sufficient = False
    elif (
        (not active_planning_present)
        and (not changed_paths)
        and work_shape_study.get("status") == "information-gathering-required"
        and work_shape_study.get("planning_custody_required") is True
    ):
        status = "blocked"
        decision = "information-gathering-required"
        reason = "Referenced intent evidence is missing and could change the required Planning shape."
        required_next_action = "run-bounded-work-shape-study"
        workflow_sufficient = False
    elif (
        (not active_planning_present)
        and (not changed_paths)
        and _as_dict(work_shape_study.get("decision")).get("work_shape") in {"lane", "epic", "slice"}
    ):
        selected_study_shape = str(_as_dict(work_shape_study.get("decision")).get("work_shape") or "")
        status = "blocked"
        decision = "planning-shape-owner-required"
        reason = f"Referenced intent evidence selects {selected_study_shape} Planning before product implementation."
        required_next_action = str(_as_dict(work_shape_study.get("decision")).get("next_safe_action") or "create-or-promote-planning-owner")
        workflow_sufficient = False
    elif (not active_planning_present) and (not changed_paths) and work_shape_study.get("status") == "ambiguous":
        status = "blocked"
        decision = "planning-shape-human-decision-required"
        reason = "Cheap referenced-intent evidence was exhausted, but materially different Planning shapes remain plausible."
        required_next_action = "ask-work-shape-clarification"
        workflow_sufficient = False
    elif (not active_planning_present) and candidate_pressure.get("status") == "promotion-required" and not closeout_publication_residue:
        status = "blocked"
        decision = "candidate-lane-promotion-required"
        reason = "Checked-in Planning candidates indicate broad or lane-shaped work; promote or decompose a bounded lane first."
        required_next_action = "select-or-promote-candidate-lane"
        workflow_sufficient = False
    elif (not active_planning_present) and (not changed_paths) and (work_shape in {"lane", "epic"} or proof_burden == "high"):
        status = "blocked"
        decision = "planning-escalation-required"
        reason = "Broad, milestone-scale, or high-assurance task posture needs checked-in Planning custody before implementation."
        required_next_action = "create-or-promote-active-execplan"
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
    hard_gate = decision in {
        "delegation-decision-required",
        "parent-decomposition-decision-required",
        "lane-owner-artifact-required",
        "implementation-owner-missing",
        "candidate-lane-promotion-required",
        "planning-escalation-required",
        "information-gathering-required",
        "planning-shape-owner-required",
        "planning-shape-human-decision-required",
    }
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
            f"pr_comment_repair={pr_comment_repair_context.get('status')}",
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
        "decision_maturity": _decision_maturity_payload(
            decision=decision,
            workflow_sufficient=workflow_sufficient,
            required_next_action=required_next_action,
            evidence_basis=[
                f"active_planning_present={active_planning_present}",
                f"dirty_shape={path_classification.get('dirty_shape')}",
                f"candidate_pressure={candidate_pressure.get('status')}",
                f"issue_ref_count={len(issue_refs)}",
            ],
            missing_evidence=(
                ["external issue intent evidence"]
                if decision == "external-issue-scope-unknown"
                else ["changed-path scope decision"]
                if decision == "agent-work-shape-decision-required"
                else ["PR feedback proof"]
                if decision == "bounded-pr-comment-repair"
                else []
            ),
            hard_gate=hard_gate,
        ),
        "authority_boundary": authority_boundary,
        "required_next_action": required_next_action,
        "active_planning_present": active_planning_present,
        "planning_revision": planning_revision,
        "active_plan_reliance": active_plan_reliance,
        "task_switch_reconciliation": route_evidence,
        "route_decision": route_decision,
        "active_state_summary": active_summary,
        "issue_refs": issue_refs,
        "pr_context": {
            "status": "pr-context-detected" if pr_context_refs else "not-detected",
            "refs": pr_context_refs,
            "rule": "PR/review/merge-conflict wording is provider context, not unknown issue scope. Fetch PR/review state when needed.",
            "provider_requirement": "provider-aware; GitHub is one possible source, not assumed as the only provider.",
        },
        "pr_comment_repair_context": pr_comment_repair_context,
        "issue_scope_evidence": issue_scope_evidence,
        "candidate_pressure": candidate_pressure,
        "work_shape_study": work_shape_study,
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
        "implementation_allowed": workflow_sufficient
        and (
            bool(route_decision.get("implementation_allowed"))
            if route_decision.get("task_relation") not in {None, "", "not-applicable"}
            else True
        ),
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
