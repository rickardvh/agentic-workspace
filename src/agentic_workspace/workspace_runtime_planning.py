"""Planning continuation and active-state runtime packets.

This module owns Planning runtime packet helpers while the old monolith keeps
compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from agentic_workspace.authority_envelope import mutation_baseline_payload
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
    _workflow_sufficiency_payload,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _command_with_cli_invoke,
)

PLANNING_FRONT_DOOR_OPERATION_PATH = "packages/planning/src/repo_planning_bootstrap/contracts/operations/planning.front-door.json"


def _stable_revision(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _active_owner_external_reconciliation(
    *, target_root: Path, active_summary: dict[str, Any], config: WorkspaceConfig, planning_revision: dict[str, Any]
) -> dict[str, Any]:
    """Project only external evidence that can change the selected owner's next action."""
    refs = sorted({ref for ref in _as_list(active_summary.get("active_owner_refs")) if re.fullmatch(r"#\d+", str(ref))})
    owner_ref = str(active_summary.get("active_execplan") or "")
    if not owner_ref or not refs:
        return {"status": "not-applicable"}
    evidence_path = target_root / ".agentic-workspace" / "local" / "cache" / "external-intent-evidence.json"
    if not evidence_path.is_file():
        evidence_path = target_root / ".agentic-workspace" / "planning" / "external-intent-evidence.json"
    issue_args = " ".join(f'--issue "{ref}"' for ref in refs)
    refresh_command = _command_with_cli_invoke(
        command=(
            "agentic-workspace external-intent refresh-github --target . --storage cache "
            f"{issue_args} --apply-planning-candidates --format json"
        ),
        cli_invoke=config.cli_invoke,
    )
    reconcile_command = _command_with_expected_planning_revision(
        _command_with_cli_invoke(
            command="agentic-workspace planning reconcile --target . --preview --format json",
            cli_invoke=config.cli_invoke,
        ),
        planning_revision=planning_revision,
    )
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {"status": "not-applicable"}
    items = [
        item
        for item in _as_list(_as_dict(payload).get("items"))
        if isinstance(item, dict) and str(item.get("id") or item.get("number") or "") in refs
    ]
    if not items:
        return {"status": "not-applicable"}

    def _expired(item: dict[str, Any]) -> bool:
        freshness = _as_dict(item.get("freshness"))
        if str(freshness.get("status") or "") == "stale":
            return True
        expires_at = str(freshness.get("expires_at") or "").strip()
        if not expires_at:
            refreshed_at = str(_as_dict(payload).get("refreshed_at") or "").strip()
            if not refreshed_at:
                return True
            try:
                refreshed = datetime.fromisoformat(refreshed_at.replace("Z", "+00:00"))
            except ValueError:
                return True
            if refreshed.tzinfo is None:
                refreshed = refreshed.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > refreshed.astimezone(timezone.utc) + timedelta(hours=24)
        try:
            expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires.astimezone(timezone.utc)

    stale = [item for item in items if _expired(item)]
    completed_statuses = {"closed", "complete", "completed", "done", "merged", "published", "released"}
    completed = [item for item in items if str(item.get("status_class") or item.get("status") or "").strip().lower() in completed_statuses]
    status = "refresh-required" if stale else "reconciliation-required" if completed else "current"
    return {
        "kind": "agentic-planning/active-owner-external-currentness/v1",
        "status": status,
        "owner_ref": owner_ref,
        "issue_refs": refs,
        "matched_observation_ids": [str(item.get("observation_id") or item.get("id") or "") for item in items],
        "external_revisions": [str(item.get("external_revision") or item.get("updated_at") or "") for item in items],
        "reason_code": "external-observation-stale" if stale else "external-owner-completed" if completed else "external-owner-current",
        "refresh_command": refresh_command,
        "reconcile_command": reconcile_command,
        "claim_effect": "block-owner-dependent-work-until-refresh-or-reconciliation" if status != "current" else "none",
        "authority_boundary": "External state is currentness evidence; Planning remains the authority for intent, proof, and owner transitions.",
    }


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
        lane=str(getattr(args, "lane", "") or ""),
        apply_lane_reconcile=bool(getattr(args, "apply_lane_reconcile", False)),
        apply_lane_current_slice_reconcile=bool(getattr(args, "apply_lane_current_slice_reconcile", False)),
        owner_surface=str(getattr(args, "owner_surface", "") or ""),
        relation_identity=str(getattr(args, "relation_identity", "") or ""),
        subject=str(getattr(args, "subject", "") or ""),
        expected_lane_revision=str(getattr(args, "expected_lane_revision", "") or ""),
        transition=str(getattr(args, "transition", "") or ""),
        expected_execplan=str(getattr(args, "expected_execplan", "") or ""),
        issue=str(getattr(args, "issue", "") or ""),
        external_ref=str(getattr(args, "external_ref", "") or ""),
        priority=str(getattr(args, "priority", "") or ""),
        depends_on=str(getattr(args, "depends_on", "") or ""),
        rationale=str(getattr(args, "rationale", "") or ""),
        maturity=str(getattr(args, "maturity", "") or ""),
        expected_relation_revision=str(getattr(args, "expect_relation_revision", "") or ""),
        apply_issue_relation_reconcile=bool(getattr(args, "apply_issue_relation_reconcile", False)),
        apply_issue_relation_migration=bool(getattr(args, "apply_issue_relation_migration", False)),
        apply_pending_integrations=bool(getattr(args, "apply_pending_integrations", False)),
        preview=bool(getattr(args, "preview", False)),
        apply=bool(getattr(args, "apply", False)),
        proposal=str(getattr(args, "proposal", "") or ""),
        expected_planning_revision=str(
            getattr(args, "expected_planning_revision", "") or getattr(args, "expect_planning_revision", "") or ""
        ),
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


def _bounded_external_issue_effect_payload(
    *, task_text: str | None, changed_paths: list[str], active_planning_present: bool
) -> dict[str, Any]:
    """Classify a bounded tracker write without granting repository custody.

    This is deliberately provider-neutral and requires positive scope and safety
    facts.  Merely mentioning issues, a count, or "preliminary" is insufficient.
    """

    text = " ".join(str(task_text or "").lower().split())
    tracker_subject = bool(re.search(r"\b(issue|issues|ticket|tickets|tracker item|tracker items)\b", text))
    external_write = bool(re.search(r"\b(file|create|open|submit|refine|update)\b", text)) and tracker_subject
    bounded_scope = any(
        (
            bool(re.search(r"\bexactly\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", text)),
            bool(
                re.search(
                    r"\bthese\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)?\s*(?:already[- ]identified\s+)?(?:issues|tickets|tracker items)\b",
                    text,
                )
            ),
            "already-identified" in text,
            "already identified" in text,
        )
    )
    duplicate_guard = any(term in text for term in ("duplicate-safe", "duplicate safe", "check for duplicates", "duplicate search"))
    constraint_marker = bool(re.search(r"\b(do not|don't|without|no)\b", text))
    no_repository_effect = constraint_marker and bool(
        re.search(
            r"\b(implement(?:ing|ation)?|edit(?:ing)? product source|source changes?|repo(?:sitory)? changes?|changing repository files)\b",
            text,
        )
    )
    no_terminal_tracker_effect = (
        constraint_marker and bool(re.search(r"\b(merge|merging|merged)\b", text)) and bool(re.search(r"\b(close|closing|closed)\b", text))
    )
    durable_shape = any(
        term in text
        for term in (
            "parent issue",
            "parent ticket",
            "implementation lane",
            "create a lane",
            "multi-session",
            "decompose",
            "unresolved decomposition",
            "implement and",
            "then implement",
            "also implement",
            "plus implementation",
        )
    )
    admitted = all(
        (
            external_write,
            bounded_scope,
            duplicate_guard,
            no_repository_effect,
            no_terminal_tracker_effect,
            not durable_shape,
            not changed_paths,
            not active_planning_present,
        )
    )
    observed = {
        "external_tracker_write": external_write,
        "bounded_candidate_set": bounded_scope,
        "duplicate_check_required": duplicate_guard,
        "repository_effects_explicitly_excluded": no_repository_effect,
        "merge_and_close_effects_explicitly_excluded": no_terminal_tracker_effect,
        "durable_execution_shape_detected": durable_shape,
        "changed_path_count": len(changed_paths),
        "active_planning_present": active_planning_present,
    }
    if admitted:
        required_safety_checks = [
            "duplicate-search",
            "issue-shaping-and-template-compliance",
            "explicit-external-write-authority",
            "truthful-post-create-reconciliation",
        ]
        route: dict[str, Any] = {
            "kind": "agentic-workspace/bounded-external-effect-route/v1",
            "status": "direct-route-admitted",
            "effect_class": "external-issue-filing",
            "planning_custody_required": False,
            "observed_facts": observed,
            "required_safety_checks": required_safety_checks,
            "residue_policy": "External tracker receipts remain coordination evidence; create no checked-in Planning owner solely for permission.",
            "provider_boundary": "The effect class is a bounded external tracker write; no GitHub-specific planning bypass is granted.",
            "rule": "A positively bounded external tracker effect may use its existing intake/write owner without checked-in Planning custody.",
        }
        route["start_projection"] = {
            "bounded_external_effect": {**route},
            "workflow_sufficiency": _workflow_sufficiency_payload(
                surface="start",
                decision="bounded-external-effect-direct",
                reason="Bounded external tracker effect is ready for its write owner.",
                required_next_action="perform-bounded-external-issue-filing",
                evidence_required=required_safety_checks,
            ),
            "immediate_next_allowed_action": {
                "action": "perform-bounded-external-issue-filing",
                "summary": "Use the existing external issue intake/write owner without creating checked-in Planning custody.",
                "command": "",
                "run": None,
                "risk": "bounded-external-write",
                "required_inputs": required_safety_checks,
                "next_proof": "Reconcile created tracker identities, duplicate decisions, and failed writes against the requested bounded set.",
                "read_first": [],
                "open_execplan_only_when": (
                    "The task expands into repository implementation, unresolved decomposition, multi-session continuation, "
                    "or an active-owner conflict."
                ),
            },
        }
        return route
    reason_codes = [key for key, value in observed.items() if value is False]
    if durable_shape:
        reason_codes.append("durable-execution-shape-detected")
    if changed_paths:
        reason_codes.append("repository-changes-present")
    if active_planning_present:
        reason_codes.append("active-owner-conflict-or-continuation")
    return {
        "kind": "agentic-workspace/bounded-external-effect-route/v1",
        "status": "not-admitted",
        "effect_class": "repo-implementation-or-unbounded-work" if durable_shape or changed_paths else "unclassified",
        "planning_custody_required": bool(durable_shape or changed_paths or active_planning_present),
        "observed_facts": observed,
        "reason_codes": sorted(set(reason_codes)),
        "rule": "Counts or tracker wording alone never exempt work from Planning custody.",
    }


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
                "agentic-workspace planning owner-select --owner <existing-owner-id> --owner-ref <existing-owner-ref> "
                '--mode local --reason "reconcile current diff retrofit" --target . --dry-run --format json'
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
    exact_task_identity_match = mismatch_evidence.get("exact_task_identity_match") is True
    if shared_refs or exact_task_identity_match:
        continuation_basis = "exact-current-task-owner-intent" if exact_task_identity_match else "shared-structured-reference"
        return {
            "kind": "agentic-workspace/task-switch-reconciliation/v1",
            "status": "issue-matched-continuation",
            "summary": "Current task matches the selected plan's intent identity; treat it as active-plan continuation unless another gate names a concrete mismatch.",
            "active_execplan": active_summary.get("active_execplan", ""),
            "intent_conflict_state": "explicit-reference-continuation",
            "mismatch_evidence": mismatch_evidence,
            "current_task_class": "active-plan-continuation",
            "classification_basis": continuation_basis,
            "matched_maintenance_markers": matched_maintenance_markers,
            "classification_inputs": [
                "active_plan_reliance.status=not-needed-for-current-task",
                f"shared_refs={','.join(str(ref) for ref in shared_refs[:8])}",
                f"shared_ref_count={len(shared_refs)}",
                f"shared_term_count={len(mismatch_evidence.get('shared_terms', []))}",
                f"exact_task_identity_match={str(exact_task_identity_match).lower()}",
            ],
            "semantic_boundary": (
                "Exact task/owner-intent identity or structured issue/PR reference overlap can suppress generic active-plan task-switch pressure here. "
                "This does not close the active plan or override other planning, proof, parent-closure, or delegation gates."
            ),
            "recommended_next_action": "continue-active-plan",
            "next_action_packet": {
                "action": "continue-active-plan",
                "summary": "The task matches the selected plan identity; continue through that plan unless a concrete structured mismatch appears.",
                "command": summary_command,
                "run": summary_command,
                "risk": "issue-matched-continuation",
                "required_inputs": ["current task", "active plan intent or structured owner refs", "active plan boundary"],
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
            "rule": "Exact task/owner-intent identity or structured ref overlap is continuation evidence; arbitrary prose keyword overlap is not.",
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
    acknowledged["implementation_allowed"] = True
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
    if _as_dict(path_classification.get("effect_scope")).get("status") == "proven-local-transient":
        acknowledged["summary"] = (
            "Current-task cleanup is mechanically bounded to ignored transient residue; the selected Planning owner and its claims remain unchanged."
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
        "owner-promotion-required": "promote-or-create-owner",
        "reconciliation-stale": "reconcile",
    }
    transition = str(
        route_evidence.get("required_transition")
        or (
            "promote-or-create-owner"
            if task_relation == "owner-promotion-required"
            else transition_by_posture.get(owner_posture)
            or (
                "ask-for-route-decision"
                if task_relation == "ambiguous"
                else "inspect-current-task-scope"
                if task_relation == "independent-pending-scope"
                else "none"
            )
        )
    )
    continuing = task_relation == "continues-selected-owner"
    bounded = task_relation == "bounded-independent"
    ambiguous = task_relation == "ambiguous"
    owner_admission = _as_dict(route_evidence.get("owner_admission"))
    route_inputs = _as_dict(route_evidence.get("route_inputs"))
    task_binding = _as_dict(route_inputs.get("task_binding"))
    if (
        bounded
        and str(task_binding.get("basis") or "") == "structured-intent-non-overlap"
        and transition in {"closeout-or-archive", "complete-proof"}
    ):
        transition = "none"
    owner_facts = _as_dict(route_inputs.get("owner"))
    selected_owner_ref = str(route_evidence.get("active_execplan") or owner_facts.get("ref") or "")
    task_mode = str(task_binding.get("mode") or "")
    mutation_baseline = _as_dict(route_inputs.get("mutation_baseline"))
    mutation_paths = [str(path) for path in task_binding.get("allowed_paths", []) if isinstance(task_binding.get("allowed_paths"), list)]
    bounded_mutation = bounded and task_mode == "mutation"
    mutation_baseline_current = not bounded_mutation or _mutation_baseline_route_current(mutation_baseline, changed_paths=mutation_paths)
    mutation_baseline_admission = {
        "status": "not-required",
        "source": "canonical-route-decision",
        "reason": "The resolved route does not require bounded mutation authority.",
    }
    if bounded_mutation:
        mutation_baseline_admission = {
            "status": "current" if mutation_baseline_current else "blocked",
            "source": "canonical-route-decision",
            "baseline_id": str(mutation_baseline.get("baseline_id") or ""),
            "head": str(mutation_baseline.get("head") or ""),
            "mutation_revision": str(
                _as_dict(mutation_baseline.get("observed_state")).get("enforcement_fingerprint")
                or mutation_baseline.get("mutation_revision")
                or mutation_baseline.get("revision")
                or ""
            ),
            "scope": _as_dict(mutation_baseline.get("scope")),
            "requested_paths": mutation_paths,
            "reason": "current live mutation baseline admitted into the canonical route decision"
            if mutation_baseline_current
            else _mutation_baseline_repair_reason(mutation_baseline, changed_paths=mutation_paths),
            "rule": "Bounded mutation permission is derived exactly once by the canonical route decision; downstream consumers only project this admission.",
        }
        if not mutation_baseline_current and transition == "none":
            transition = "refresh-mutation-baseline"
    route_proposal = _as_dict(reconciliation_proposal) or _as_dict(route_evidence.get("reconciliation_proposal"))
    next_packet = _route_decision_next_action_packet(
        route_evidence={**route_evidence, "reconciliation_proposal": route_proposal},
        task_relation=task_relation,
        owner_posture=owner_posture,
        required_transition=transition,
        planning_revision=planning_revision,
    )
    action_identity = _as_dict(next_packet.get("operation_invocation")).get("input_identity", {})
    claim_effect_boundary = copy.deepcopy(_as_dict(_as_dict(action_identity).get("claim_effect_boundary")))
    allowed_claims = (
        ["bounded-task-progress"]
        if transition == "none" and bounded
        else ["active-plan-progress"]
        if transition == "none" and continuing
        else []
    )
    blocked_claims = _route_decision_blocked_claims(task_relation=task_relation, owner_posture=owner_posture, transition=transition)
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
        "identity_effects": [
            {
                "inputs": ["branch", "worktree", "repository", "target", "selected_owner_revision"],
                "effect": "invalidate-and-rebind-before-action",
                "residue_policy": "do-not-persist-orienting-read-state",
            }
        ],
        "input_provenance": {
            "task_relation": "current-work binding, explicit structured references, and scoped current-task evidence",
            "owner_posture": "selected-owner lifecycle, projection, proof, and admitted external-observation facts",
            "required_transition": "route-decision policy; detailed reconciliation remains owned by planning reconcile",
        },
        "structured_inputs": route_inputs,
        **(
            {"non_interference_boundary": copy.deepcopy(_as_dict(route_inputs.get("non_interference_boundary")))}
            if _as_dict(route_inputs.get("non_interference_boundary")).get("status") in {"protected", "overlap-blocked"}
            else {}
        ),
        "claim_effect_boundary": claim_effect_boundary,
        "mutation_baseline_admission": mutation_baseline_admission,
        "reason_codes": [
            code
            for code in (
                status,
                str(route_evidence.get("intent_conflict_state") or ""),
                str(task_binding.get("basis") or ""),
                str(owner_facts.get("lifecycle") or ""),
                "mutation-baseline-required" if bounded_mutation and not mutation_baseline_current else "",
            )
            if code
        ],
        "allowed_claims": allowed_claims,
        "blocked_claims": blocked_claims,
        "implementation_allowed": False if ambiguous or transition != "none" else bool(continuing or bounded),
        "mutation_authority": "none"
        if ambiguous or transition != "none"
        else "current-task"
        if bounded and task_mode != "read-only"
        else "none"
        if bounded
        else "selected-owner"
        if continuing
        else "none",
        "proof_expectation": str(next_packet.get("next_proof") or ""),
        "state_update_policy": "pre-write-revalidation-required"
        if transition == "none" and bounded and task_mode == "mutation"
        else "read-only"
        if transition == "none"
        else "explicit-transition-required",
        "action_identity": action_identity,
        "legacy_consumer_replacement_map": {
            "task_switch_reconciliation.status": "route_decision.task_relation + route_decision.owner_posture + route_decision.required_transition",
            "task_switch_reconciliation.recommended_next_action": "route_decision.next_safe_action.action",
            "task_switch_reconciliation.blocked_claims": "route_decision.blocked_claims",
            "task_switch_reconciliation.route_acknowledgement": "route_decision.next_safe_action.operation_invocation.input_identity",
            "task_switch_reconciliation.permission": "route_decision.implementation_allowed + route_decision.mutation_authority",
        },
        "consumer_contract": {
            "authority": "planning_safety_gate.route_decision",
            "ordinary_consumers": [
                "startup",
                "implement",
                "preflight",
                "summary",
                "actionability",
                "skills",
                "SkillSpec",
                "Planning handoff",
                "proof",
                "closeout",
                "generated targets",
                "external consumers",
                "no-CLI fallback",
            ],
            "inventory_ref": "docs/maintainer/planning-route-consumer-inventory.json",
            "profiles": ["tiny", "compact", "full"],
            "dimensions": ["task_relation", "owner_posture", "required_transition"],
            "freshness_inputs": [
                "planning_revision",
                "selected_owner_revision",
                "selected_owner_lifecycle",
                "selected_owner_projection_status",
                "external_observation_revision",
                "task_binding_identity",
                "mutation_baseline_id",
                "reconciliation_proposal_revision",
            ],
            "parallel_classification": "backgrounded-diagnostic-only",
            "degraded_recovery": {
                "status": "typed",
                "missing_owner": "select-owner",
                "stale_binding": "refresh-planning-route-decision",
                "projection_drift": "repair-projection",
                "external_conflict": "reconcile",
            },
            "rule": "Every ordinary consumer projects this decision; no consumer may derive route permission from legacy task-switch labels.",
        },
        "next_safe_action": next_packet,
    }
    owner_admission_source = str(_as_dict(owner_admission.get("selected_owner")).get("source") or "")
    if (
        owner_admission.get("status") == "rejected"
        or owner_admission.get("rejected_candidates")
        or owner_admission_source.endswith("owner-selection.json")
        or owner_admission_source.endswith(":active.execplans")
    ):
        decision["owner_admission"] = owner_admission
    proposal = _as_dict(reconciliation_proposal)
    if proposal.get("status") == "current":
        proposal_posture = str(proposal.get("owner_posture") or "reconciliation-pending")
        proposal_transition = str(proposal.get("required_transition") or "reconcile")
        proposal_blocked_claims = _route_decision_blocked_claims(
            task_relation=task_relation, owner_posture=proposal_posture, transition=proposal_transition
        )
        proposal_next_packet = _route_decision_next_action_packet(
            route_evidence={**route_evidence, "reconciliation_proposal": proposal},
            task_relation=task_relation,
            owner_posture=proposal_posture,
            required_transition=proposal_transition,
            planning_revision=planning_revision,
        )
        decision.update(
            {
                "owner_posture": proposal_posture,
                "required_transition": proposal_transition,
                "implementation_allowed": False,
                "mutation_authority": "reconciliation-proposal",
                "allowed_claims": [],
                "blocked_claims": proposal_blocked_claims,
                "proof_expectation": "apply the current reconciliation proposal and retain its mutation receipt",
                "state_update_policy": "reconciliation-apply-required",
                "next_safe_action": proposal_next_packet,
                "action_identity": _as_dict(_as_dict(proposal_next_packet.get("operation_invocation")).get("input_identity")),
            }
        )
        decision["reason_codes"] = [*decision["reason_codes"], "current-reconciliation-proposal"]
        decision["reconciliation_proposal"] = proposal
    elif proposal.get("status") == "stale":
        stale_next_packet = _route_decision_next_action_packet(
            route_evidence={**route_evidence, "reconciliation_proposal": proposal},
            task_relation=task_relation,
            owner_posture="reconciliation-stale",
            required_transition="reconcile",
            planning_revision=planning_revision,
        )
        decision.update(
            {
                "owner_posture": "reconciliation-stale",
                "required_transition": "reconcile",
                "implementation_allowed": False,
                "mutation_authority": "none",
                "state_update_policy": "fresh-reconciliation-proposal-required",
                "next_safe_action": stale_next_packet,
                "action_identity": _as_dict(_as_dict(stale_next_packet.get("operation_invocation")).get("input_identity")),
            }
        )
        decision["reason_codes"] = [*decision["reason_codes"], "stale-reconciliation-proposal"]
        decision["reconciliation_proposal"] = proposal
    reconciliation_transaction = _as_dict(route_evidence.get("reconciliation_transaction"))
    if reconciliation_transaction.get("status") not in {"", "absent"}:
        decision["reconciliation_transaction"] = reconciliation_transaction
    identity_basis = {
        key: decision.get(key)
        for key in (
            "task_relation",
            "owner_posture",
            "required_transition",
            "selected_owner_identity",
            "structured_inputs",
            "mutation_baseline_admission",
            "reconciliation_proposal",
            "reconciliation_transaction",
            "action_identity",
            "blocked_claims",
            "state_update_policy",
        )
    }
    decision["input_revision"] = "sha256:" + _stable_revision(identity_basis)
    decision["decision_id"] = (
        "planning-route:"
        + _stable_revision({"input_revision": decision["input_revision"], "action_identity": decision.get("action_identity", {})})[:20]
    )
    decision["consumer_projections"] = {
        consumer: planning_route_consumer_projection(route_decision=decision, consumer=consumer)
        for consumer in decision["consumer_contract"]["ordinary_consumers"]
    }
    return decision


def _route_decision_blocked_claims(*, task_relation: str, owner_posture: str, transition: str) -> list[str]:
    if task_relation == "independent-pending-scope":
        return ["claim-active-plan-progress", "claim-active-plan-complete", "silently-abandon-active-plan"]
    if task_relation == "continues-selected-owner" and transition == "none":
        return ["claim-unrelated-task-complete", "silently-close-active-plan"]
    if owner_posture == "completed-residue" and transition != "none":
        return ["claim-lane-complete", "claim-parent-complete", "silently-close-planning-state"]
    if task_relation == "bounded-independent":
        claims = ["claim-active-plan-progress", "claim-active-plan-complete", "silently-abandon-active-plan"]
        if transition != "none":
            claims.append("claim-route-transition-complete-without-receipt")
        return claims
    if task_relation == "ambiguous" or transition == "ask-for-route-decision":
        return ["claim-active-plan-progress", "claim-active-plan-complete", "silently-abandon-active-plan"]
    return ["claim-route-transition-complete-without-receipt"]


def planning_route_consumer_projection(*, route_decision: dict[str, Any], consumer: str) -> dict[str, Any]:
    """Project the one route/action identity without granting consumer-local authority."""

    admitted = {
        "startup",
        "implement",
        "preflight",
        "summary",
        "actionability",
        "skills",
        "SkillSpec",
        "Planning handoff",
        "proof",
        "closeout",
        "generated targets",
        "external consumers",
        "no-CLI fallback",
    }
    if consumer not in admitted:
        raise ValueError(f"unsupported Planning route consumer: {consumer}")
    return {
        "kind": "agentic-planning/route-consumer-projection/v1",
        "consumer": consumer,
        "decision_id": str(route_decision.get("decision_id") or ""),
        "input_revision": str(route_decision.get("input_revision") or ""),
        "action_identity": copy.deepcopy(_as_dict(route_decision.get("action_identity"))),
        "claim_effect_boundary": copy.deepcopy(_as_dict(route_decision.get("claim_effect_boundary"))),
        "required_transition": str(route_decision.get("required_transition") or ""),
        "implementation_allowed": bool(route_decision.get("implementation_allowed")),
        "mutation_authority": str(route_decision.get("mutation_authority") or "none"),
        "proof_expectation": str(route_decision.get("proof_expectation") or ""),
        "blocked_claims": [str(item) for item in _as_list(route_decision.get("blocked_claims"))],
        "state_update_policy": str(route_decision.get("state_update_policy") or "read-only"),
        "next_safe_action": copy.deepcopy(_as_dict(route_decision.get("next_safe_action"))),
        "authority": "planning_safety_gate.route_decision",
        "extension_rule": "Consumer detail may narrow this projection but cannot widen effects, claims, mutation, or terminal authority.",
    }


def _route_decision_next_action_packet(
    *,
    route_evidence: dict[str, Any],
    task_relation: str,
    owner_posture: str,
    required_transition: str,
    planning_revision: dict[str, Any] | None,
) -> dict[str, Any]:
    """Project the one route decision into a typed next action.

    The legacy task-switch evidence is intentionally not trusted for action,
    permission, command, or claim fields.  This packet is derived from the
    compositional route dimensions and is the only ordinary route authority.
    """
    revision = str(_as_dict(planning_revision).get("revision_id") or _as_dict(planning_revision).get("revision") or "")
    action = "refresh-planning-route-decision"
    summary = "Refresh the Planning route decision before action."
    command = ""
    proof = "refresh the Planning route decision and consume its typed action contract"
    required_inputs = ["route decision", "selected owner identity", "Planning revision"]
    risk = "route-authority-incomplete"
    route_inputs = _as_dict(route_evidence.get("route_inputs"))
    task_binding = _as_dict(route_inputs.get("task_binding"))
    claim_effect_boundary = copy.deepcopy(_as_dict(route_inputs.get("claim_effect_boundary")))
    owner_facts = _as_dict(route_inputs.get("owner"))
    external_observation = _as_dict(route_inputs.get("admitted_external_observation"))
    owner_admission = _as_dict(route_evidence.get("owner_admission"))
    selected_owner = _as_dict(owner_admission.get("selected_owner"))
    selected_owner_ref = str(route_evidence.get("active_execplan") or owner_facts.get("ref") or selected_owner.get("ref") or "")
    selected_owner_revision = str(
        owner_facts.get("revision")
        or selected_owner.get("revision")
        or _as_dict(owner_admission.get("selected_owner_identity")).get("revision")
        or revision
        or ""
    )
    selected_owner_lifecycle = str(owner_facts.get("lifecycle") or selected_owner.get("lifecycle") or "")
    selected_owner_projection_status = str(owner_facts.get("projection_status") or selected_owner.get("projection_status") or "")
    mutation_baseline = _as_dict(route_inputs.get("mutation_baseline"))
    mutation_scope = _as_dict(mutation_baseline.get("scope"))
    allowed_paths = [str(path) for path in task_binding.get("allowed_paths", []) if isinstance(task_binding.get("allowed_paths"), list)]
    allowed_effects = [
        str(effect) for effect in mutation_baseline.get("allowed_effects", []) if isinstance(mutation_baseline.get("allowed_effects"), list)
    ]
    route_proposal = _as_dict(route_evidence.get("reconciliation_proposal")) or _as_dict(route_inputs.get("reconciliation_proposal"))
    if task_relation == "independent-pending-scope":
        action = "inspect-current-task-scope"
        summary = "Inspect current-task scope before mutation; the selected active plan remains protected."
        proof = "supply changed paths to implement/proof before a mutation claim; do not claim active-plan progress"
        required_inputs = ["current task", "changed paths or structured owner reference", "active plan boundary"]
        risk = "current-task-scope-unresolved"
    elif owner_posture == "completed-residue" and required_transition != "none":
        completed_plan = _as_dict(route_evidence.get("completed_active_plan"))
        action = "archive-or-retire-completed-plan"
        summary = "Archive or retire completed active-plan residue through the Planning transition route."
        command = str(completed_plan.get("archive_command") or "")
        proof = str(completed_plan.get("recheck_command") or "rerun startup after the archive/retire transition")
        required_inputs = ["active execplan", "completion evidence", "Planning revision"]
        risk = "completed-active-plan-residue"
    elif task_relation == "continues-selected-owner" and required_transition == "none":
        action = "continue-active-plan"
        summary = "Continue through the selected-owner Planning route."
        proof = "use implement/proof for changed paths and keep active plan closeout separate from task-switch classification"
        required_inputs = ["current task", "selected owner", "shared issue/PR refs"]
        risk = "selected-owner-continuation"
    elif task_relation == "bounded-independent" and required_transition == "none":
        if str(route_evidence.get("status") or "") == "bounded-reflection-reporting":
            action = "produce-bounded-reflection-report"
            summary = "Produce the bounded reflection or report while preserving the selected owner's claim boundary."
            proof = "no file proof unless the task later becomes an edit"
            required_inputs = ["current task", "active plan claim boundary"]
            risk = "bounded-reflection-active-plan-protected"
        elif str(task_binding.get("mode") or "") == "read-only" and str(task_binding.get("basis") or "") == "structured-intent-non-overlap":
            action = "inspect-current-task"
            summary = "Inspect the independent current task under the selected owner's non-interference boundary."
            proof = "no file proof unless the task later requests mutation"
            required_inputs = ["current task", "selected owner identity", "non-interference boundary"]
            risk = "read-only-independent-active-plan-protected"
        else:
            action = "prove-current-task"
            summary = "Continue current-task proof without claiming active-plan progress."
            proof = "run implement/proof-selected commands for the changed paths; do not claim active-plan progress"
            required_inputs = ["changed paths or read-only task binding", "current task", "active plan claim boundary"]
            risk = "active-plan-protected-current-task"
    elif task_relation == "bounded-independent" and required_transition == "refresh-mutation-baseline":
        action = "refresh-mutation-baseline"
        summary = "Refresh the live mutation baseline before bounded repository mutation."
        proof = "rerun implement with changed paths so the authority-envelope mutation baseline is admitted before action"
        required_inputs = ["changed paths", "live mutation baseline", "Planning route decision"]
        risk = "mutation-baseline-required"
    elif task_relation == "ambiguous" or required_transition == "ask-for-route-decision":
        action = "choose-task-switch-route"
        summary = "Resolve the ambiguous Planning route before continuing."
        proof = "record the explicit task-route decision before implementation or active-plan claims"
        required_inputs = ["current task", "selected owner", "explicit route decision"]
        risk = "ambiguous-active-plan-route"
    elif required_transition == "repair-projection":
        action = "repair-planning-projection"
        summary = "Repair the selected Planning projection before ordinary action."
        proof = "refresh the selected-owner projection and retain its repair receipt"
        required_inputs = ["selected owner", "projection revision", "Planning revision"]
        risk = "projection-repair-required"
    elif required_transition == "complete-proof":
        action = "complete-selected-proof"
        summary = "Complete the selected proof route before advancing route claims."
        proof = "run or record the selected proof and re-resolve the route decision"
        required_inputs = ["selected proof route", "proof subject revision", "Planning revision"]
        risk = "proof-incomplete"
    elif required_transition == "promote-or-create-owner":
        action = "promote-or-create-planning-owner"
        summary = "Promote or create the Planning owner before claiming active-plan progress."
        proof = "create or promote the owner through Planning and re-resolve the route decision"
        required_inputs = ["current task", "owner candidate", "Planning revision"]
        risk = "owner-promotion-required"
    elif required_transition == "select-owner":
        action = "select-planning-owner"
        summary = "Select the Planning owner before ordinary action."
        proof = "record selected-owner evidence and re-resolve the route decision"
        required_inputs = ["owner candidates", "selection basis", "Planning revision"]
        risk = "owner-selection-required"
    elif required_transition == "reconcile" and owner_posture == "externally-stale" and route_evidence.get("external_refresh_command"):
        action = "refresh-external-evidence"
        summary = "Refresh the selected owner's external evidence before relying on its next action or completion state."
        command = str(route_evidence.get("external_refresh_command") or "")
        proof = str(route_evidence.get("reconciliation_preview_command") or "compile a current Planning reconciliation proposal")
        required_inputs = ["selected owner", "related external references", "fresh external observation"]
        risk = "external-owner-evidence-stale"
    elif (
        required_transition == "reconcile" and owner_posture == "external-conflict" and route_evidence.get("reconciliation_preview_command")
    ):
        action = "compile-planning-reconciliation-proposal"
        summary = "Compile the smallest honest Planning transition from current external completion evidence and local proof."
        command = str(route_evidence.get("reconciliation_preview_command") or "")
        proof = "review and apply the revision-bound reconciliation proposal; external completion alone cannot close intent"
        required_inputs = ["selected owner", "current external completion evidence", "local proof posture", "Planning revision"]
        risk = "external-owner-state-changed"
    elif (
        required_transition == "reconcile"
        and _as_dict(route_evidence.get("reconciliation_transaction")).get("status") == "preview-available"
    ):
        transaction = _as_dict(route_evidence.get("reconciliation_transaction"))
        action = "compile-planning-reconciliation-proposal"
        summary = "Compile the exact bounded target-authority reconciliation transaction before applying stale integration proposals."
        command = str(transaction.get("preview_command") or "")
        proof = "review and apply the revision-bound transaction; preserve unrelated owners, relations, local selection, and human intent"
        required_inputs = [
            *[f"affected owner: {item}" for item in _as_list(transaction.get("affected_owner_refs"))],
            f"target authority revision: {transaction.get('current_target_authority_revision')}",
            "Planning revision",
        ]
        risk = "target-authority-reconciliation-stale"
    elif required_transition == "reconcile":
        action = "refresh-planning-reconciliation-proposal"
        summary = "Refresh the Planning reconciliation proposal before applying a transition."
        command = str(route_evidence.get("reconciliation_preview_command") or "")
        proof = "produce a current reconciliation proposal and re-enter the Planning front door"
        required_inputs = ["selected owner", "conflict evidence", "Planning revision"]
        risk = "fresh-reconciliation-proposal-required"
    if required_transition == "reconcile" and route_proposal.get("status") == "current":
        action = "apply-planning-reconciliation-proposal"
        summary = "Apply the current Planning reconciliation proposal after its compare-and-swap check."
        command = str(_as_dict(route_evidence.get("reconciliation_proposal")).get("apply_command") or "")
        proof = "apply the current reconciliation proposal and retain its mutation receipt"
        required_inputs = ["current proposal identity", "Planning revision", "compare-and-swap receipt"]
        risk = "planning-reconciliation-required"
    continuing = task_relation == "continues-selected-owner"
    bounded = task_relation == "bounded-independent"
    ambiguous = task_relation == "ambiguous"
    task_mode = str(task_binding.get("mode") or "")
    proposal_current = required_transition == "reconcile" and route_proposal.get("status") == "current"
    implementation_allowed = False if ambiguous or required_transition != "none" else bool(continuing or bounded)
    mutation_authority = (
        "reconciliation-proposal"
        if proposal_current
        else "none"
        if ambiguous or required_transition != "none"
        else "current-task"
        if bounded and task_mode != "read-only"
        else "none"
        if bounded
        else "selected-owner"
        if continuing
        else "none"
    )
    state_update_policy = (
        "reconciliation-apply-required"
        if proposal_current
        else "pre-write-revalidation-required"
        if required_transition == "none" and bounded and task_mode == "mutation"
        else "read-only"
        if required_transition == "none"
        else "explicit-transition-required"
    )
    allowed_claims = (
        ["bounded-task-progress"]
        if required_transition == "none" and bounded
        else ["active-plan-progress"]
        if required_transition == "none" and continuing
        else []
    )
    blocked_claims = _route_decision_blocked_claims(
        task_relation=task_relation, owner_posture=owner_posture, transition=required_transition
    )
    action_contract = {
        "kind": "agentic-planning/route-action-input/v1",
        "route_action": action,
        "task_relation": task_relation,
        "owner_posture": owner_posture,
        "expected_transition": required_transition,
        "planning_revision": revision,
        "selected_owner_ref": selected_owner_ref,
        "selected_owner_revision": selected_owner_revision,
        "selected_owner_lifecycle": selected_owner_lifecycle,
        "selected_owner_projection_status": selected_owner_projection_status,
        "external_observation_revision": _stable_revision(
            {
                "status": external_observation.get("status"),
                "observation_ids": external_observation.get("matched_observation_ids", []),
                "external_revisions": external_observation.get("external_revisions", []),
            }
        )
        if external_observation and external_observation.get("status") != "not-applicable"
        else "",
        "task_binding_identity": str(task_binding.get("identity") or task_binding.get("task_digest") or ""),
        "task_binding_mode": str(task_binding.get("mode") or ""),
        "mutation_baseline_id": str(mutation_baseline.get("baseline_id") or ""),
        "mutation_scope_digest": _stable_revision(mutation_scope) if mutation_scope else "",
        "mutation_allowed_paths_digest": _stable_revision(sorted(allowed_paths)) if allowed_paths else "",
        "allowed_effects_digest": _stable_revision(sorted(allowed_effects)) if allowed_effects else "",
        "overlap_claim_digest": _stable_revision(_as_dict(mutation_baseline.get("overlap_claim")))
        if mutation_baseline.get("overlap_claim")
        else "",
        "implementation_allowed": implementation_allowed,
        "mutation_authority": mutation_authority,
        "state_update_policy": state_update_policy,
        "allowed_claims": allowed_claims,
        "blocked_claims": blocked_claims,
        "claim_effect_boundary": claim_effect_boundary,
        "reconciliation_proposal_id": str(route_proposal.get("proposal_id") or route_proposal.get("identity") or ""),
        "reconciliation_proposal_revision": str(route_proposal.get("revision") or route_proposal.get("proposal_revision") or ""),
        "expected_claim_effect": {
            "proof": proof,
            "risk": risk,
            "required_inputs": required_inputs,
        },
    }
    action_contract["idempotency_key"] = "planning-route:" + _stable_revision(action_contract)[:24]
    input_revision = "sha256:" + _stable_revision(action_contract)
    return {
        "action": action,
        "summary": summary,
        "command": command,
        "run": command or None,
        "risk": risk,
        "required_inputs": required_inputs,
        "next_proof": proof,
        "read_first": [],
        "operation_invocation": {
            "operation_id": "planning.front-door",
            "operation_action": "route-decision-next-action",
            "operation_path": PLANNING_FRONT_DOOR_OPERATION_PATH,
            "adapter_id": "planning.front-door.cli",
            "authority": "agentic-planning/route-decision/v1",
            "input_revision": input_revision,
            "input_identity": action_contract,
            "stale_action_rejection": {
                "status": "reject-on-input-revision-mismatch",
                "reject_when_changed": [
                    "planning_revision",
                    "selected_owner_revision",
                    "selected_owner_lifecycle",
                    "selected_owner_projection_status",
                    "external_observation_revision",
                    "task_binding_identity",
                    "task_binding_mode",
                    "mutation_baseline_id",
                    "mutation_scope_digest",
                    "mutation_allowed_paths_digest",
                    "allowed_effects_digest",
                    "overlap_claim_digest",
                    "implementation_allowed",
                    "mutation_authority",
                    "state_update_policy",
                    "allowed_claims",
                    "blocked_claims",
                    "claim_effect_boundary",
                    "reconciliation_proposal_id",
                    "reconciliation_proposal_revision",
                ],
            },
            "preconditions": required_inputs,
            "expected_transition": required_transition,
        },
    }


def validate_planning_route_action_invocation(
    *,
    invocation: dict[str, Any],
    live_route_decision: dict[str, Any],
) -> dict[str, Any]:
    """Admit a Planning route action only while its live authority inputs match.

    The route decision advertises ``planning.front-door`` as the executable
    operation, but execution cannot trust the caller's serialized packet.  This
    admission boundary compares the caller-supplied invocation with the current
    route decision's own operation identity before any mutation or claim
    advancement may use the action.
    """

    live_invocation = _as_dict(_as_dict(live_route_decision.get("next_safe_action")).get("operation_invocation"))
    required = {
        "operation_id": "planning.front-door",
        "operation_action": "route-decision-next-action",
        "operation_path": PLANNING_FRONT_DOOR_OPERATION_PATH,
        "authority": "agentic-planning/route-decision/v1",
    }
    static_failures = [
        field
        for field, expected in required.items()
        if str(invocation.get(field) or "") != expected or str(live_invocation.get(field) or "") != expected
    ]
    caller_identity = _as_dict(invocation.get("input_identity"))
    live_identity = _as_dict(live_invocation.get("input_identity"))
    live_revision = "sha256:" + _stable_revision(live_identity) if live_identity else ""
    revision_failures = [
        field
        for field, caller, live in [
            ("input_identity", caller_identity, live_identity),
            ("input_revision", str(invocation.get("input_revision") or ""), live_revision),
        ]
        if caller != live
    ]
    changed_authority_fields = [
        field
        for field in [
            "planning_revision",
            "selected_owner_revision",
            "selected_owner_lifecycle",
            "selected_owner_projection_status",
            "task_binding_identity",
            "task_binding_mode",
            "mutation_baseline_id",
            "mutation_scope_digest",
            "mutation_allowed_paths_digest",
            "allowed_effects_digest",
            "overlap_claim_digest",
            "implementation_allowed",
            "mutation_authority",
            "state_update_policy",
            "allowed_claims",
            "blocked_claims",
            "reconciliation_proposal_id",
            "reconciliation_proposal_revision",
            "external_observation_revision",
        ]
        if str(caller_identity.get(field) or "") != str(live_identity.get(field) or "")
    ]
    status = "admitted" if not static_failures and not revision_failures else "rejected"
    return {
        "kind": "agentic-planning/route-action-admission/v1",
        "status": status,
        "operation_id": str(invocation.get("operation_id") or ""),
        "operation_path": str(invocation.get("operation_path") or ""),
        "live_operation_path": str(live_invocation.get("operation_path") or ""),
        "input_revision": str(invocation.get("input_revision") or ""),
        "live_input_revision": live_revision,
        "static_failures": static_failures,
        "revision_failures": revision_failures,
        "changed_authority_fields": changed_authority_fields,
        "rejection": {
            "status": "reject-on-input-revision-mismatch",
            "reason": "caller route-action identity is stale or not bound to the Planning front-door operation",
        }
        if status == "rejected"
        else {},
    }


def _apply_planning_front_door_reconciliation_proposal(
    *,
    target_root: Path,
    live_route_decision: Mapping[str, Any],
    action_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply a live route reconciliation only through the Planning CAS transaction."""

    proposal = _as_dict(_as_dict(live_route_decision).get("reconciliation_proposal"))
    proposal_id = str(proposal.get("proposal_id") or proposal.get("identity") or "")
    expected_planning_revision = str(_as_dict(action_identity).get("planning_revision") or "")
    if proposal.get("status") != "current":
        return {
            "mutation_outcome": "blocked",
            "claim_outcome": "blocked",
            "reconciliation_apply": {
                "kind": "agentic-planning/reconciliation-front-door-apply/v1",
                "status": "blocked",
                "reason": "current-proposal-required",
            },
        }
    if not proposal_id or not expected_planning_revision:
        return {
            "mutation_outcome": "blocked",
            "claim_outcome": "blocked",
            "reconciliation_apply": {
                "kind": "agentic-planning/reconciliation-front-door-apply/v1",
                "status": "blocked",
                "reason": "proposal-identity-and-planning-revision-required",
                "proposal_id": proposal_id,
                "expected_planning_revision": expected_planning_revision,
            },
        }
    try:
        from repo_planning_bootstrap.installer import planning_reconcile

        transaction = planning_reconcile(
            target=target_root,
            apply=True,
            proposal=proposal_id,
            expected_planning_revision=expected_planning_revision,
        )
    except Exception as exc:  # pragma: no cover - defensive runtime boundary.
        transaction = {
            "kind": "agentic-planning/reconciliation-transaction/v1",
            "status": "rolled-back",
            "reason": str(exc),
        }
    transaction = _as_dict(transaction)
    transaction_status = str(transaction.get("status") or "")
    receipt = _as_dict(transaction.get("receipt"))
    applied = transaction_status in {"applied", "already-applied"} and bool(receipt)
    return {
        "mutation_outcome": "applied" if applied else "blocked",
        "claim_outcome": "available-after-proof" if applied else "blocked",
        "mutation_receipt": receipt,
        "reconciliation_apply": transaction,
    }


def _planning_front_door_host_action_invocation(
    *,
    target_root: Path,
    route_action: str,
    action_identity: Mapping[str, Any],
    task_text: str,
    changed_paths: list[str],
) -> dict[str, Any]:
    """Compile one host invocation from the versioned front-door operation IR."""

    front_door_path = target_root / PLANNING_FRONT_DOOR_OPERATION_PATH
    try:
        front_door = json.loads(front_door_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "kind": "agentic-planning/front-door-host-action-invocation/v1",
            "status": "unavailable",
            "reason": "front-door-operation-contract-unavailable",
            "error": str(exc),
        }
    binding = _as_dict(_as_dict(front_door.get("route_action_bindings")).get(route_action))
    if not binding:
        return {}
    operation_path = str(binding.get("operation_path") or "")
    destination_path = target_root / operation_path
    try:
        destination = json.loads(destination_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "kind": "agentic-planning/front-door-host-action-invocation/v1",
            "status": "unavailable",
            "reason": "destination-operation-contract-unavailable",
            "operation_path": operation_path,
            "error": str(exc),
        }
    route_values = dict(action_identity)
    runtime_values: dict[str, Any] = {
        "target": target_root.as_posix(),
        "task": task_text,
        "changed_paths": changed_paths,
    }
    arguments: dict[str, Any] = {}
    missing_sources: list[str] = []
    for name, raw_source in _as_dict(binding.get("arguments")).items():
        source = _as_dict(raw_source)
        if "literal" in source:
            arguments[str(name)] = source.get("literal")
            continue
        source_ref = str(source.get("from") or "")
        namespace, _, field = source_ref.partition(".")
        values = route_values if namespace == "route" else runtime_values if namespace == "runtime" else {}
        value = values.get(field)
        if field not in values or value is None or value == "" or value == []:
            missing_sources.append(source_ref)
            continue
        arguments[str(name)] = value
    declared_inputs = {
        str(item.get("name") or "")
        for item in _as_list(destination.get("inputs"))
        if isinstance(item, dict) and str(item.get("name") or "")
    }
    undeclared_arguments = sorted(set(arguments) - declared_inputs)
    identity = {
        "route_action": route_action,
        "front_door_operation_id": str(front_door.get("id") or ""),
        "front_door_contract_revision": "sha256:" + _stable_revision(front_door),
        "operation_id": str(destination.get("id") or ""),
        "operation_path": operation_path,
        "operation_contract_revision": "sha256:" + _stable_revision(destination),
        "operation_schema_version": str(destination.get("schema_version") or ""),
        "arguments": arguments,
        "route_input_revision": "sha256:" + _stable_revision(dict(action_identity)),
        "planning_revision": str(action_identity.get("planning_revision") or ""),
        "selected_owner_revision": str(action_identity.get("selected_owner_revision") or ""),
        "idempotency_key": str(action_identity.get("idempotency_key") or ""),
        "result_admission": _as_dict(binding.get("result_admission")),
    }
    return {
        "kind": "agentic-planning/front-door-host-action-invocation/v1",
        "status": "ready" if binding and not missing_sources and not undeclared_arguments else "blocked",
        **identity,
        "invocation_revision": "sha256:" + _stable_revision(identity),
        "missing_argument_sources": missing_sources,
        "undeclared_arguments": undeclared_arguments,
        "revalidate_before_execution": [
            "front_door_contract_revision",
            "operation_contract_revision",
            "route_input_revision",
            "planning_revision",
            "selected_owner_revision",
            "mutation_baseline_id",
        ],
        "rule": "Execute exactly this versioned operation contract through a supported host adapter, then re-admit its bound result through planning.front-door.",
    }


_HOST_ACTION_EXECUTION_SEAL = object()


@dataclass(frozen=True)
class _ExecutedPlanningHostActionResult:
    payload: dict[str, Any]
    seal: object


def _host_action_result_status(*, payload: Mapping[str, Any], accepted_statuses: set[str]) -> str:
    candidates = [
        str(payload.get("status") or ""),
        str(payload.get("outcome") or ""),
        str(_as_dict(payload.get("mutation_outcome")).get("reason_code") or ""),
        str(_as_dict(payload.get("mutation_outcome")).get("outcome") or ""),
    ]
    aliases = {
        "already-current": "already-applied",
        "already-selected": "already-applied",
        "unchanged": "no-op",
        "blocked-noop": "no-op",
        "created": "applied",
        "updated": "applied",
        "archived": "applied",
        "selected": "applied",
        "written": "applied",
        "success": "passed",
    }
    for candidate in candidates:
        normalized = aliases.get(candidate, candidate)
        if normalized in accepted_statuses:
            return normalized
    for fallback in ("reported", "current", "passed"):
        if fallback in accepted_statuses:
            return fallback
    return "unclassified"


def _execute_planning_front_door_host_action(*, invocation: Mapping[str, Any]) -> _ExecutedPlanningHostActionResult:
    """Execute the exact destination contract through the configured AW front door."""

    target_root = Path(str(_as_dict(invocation.get("arguments")).get("target") or ".")).resolve()
    operation_path = str(invocation.get("operation_path") or "")
    destination_path = target_root / operation_path
    try:
        destination = json.loads(destination_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _ExecutedPlanningHostActionResult(
            payload={"status": "failed", "reason": "destination-operation-contract-unavailable", "error": str(exc)},
            seal=_HOST_ACTION_EXECUTION_SEAL,
        )
    current_contract_revision = "sha256:" + _stable_revision(destination)
    if current_contract_revision != invocation.get("operation_contract_revision"):
        return _ExecutedPlanningHostActionResult(
            payload={"status": "failed", "reason": "destination-operation-contract-stale"},
            seal=_HOST_ACTION_EXECUTION_SEAL,
        )
    command_surface = _as_dict(destination.get("command_surface"))
    command_name = str(command_surface.get("command") or "")
    if not command_name:
        return _ExecutedPlanningHostActionResult(
            payload={"status": "failed", "reason": "destination-command-surface-unavailable"},
            seal=_HOST_ACTION_EXECUTION_SEAL,
        )
    from agentic_workspace.client import resolve_invocation

    command = [*resolve_invocation(target_root)]
    if str(command_surface.get("program") or "") == "agentic-planning":
        command.append("planning")
    command.append(command_name)
    arguments = _as_dict(invocation.get("arguments"))
    for name, value in arguments.items():
        flag = f"--{str(name).replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                command.append(flag)
        elif isinstance(value, list):
            for item in value:
                command.extend([flag, str(item)])
        elif value is not None and value != "":
            command.extend([flag, str(value)])
    before_revision = str(_as_dict(invocation).get("planning_revision") or "")
    try:
        completed = subprocess.run(command, cwd=target_root, capture_output=True, text=True, check=False)
    except OSError as exc:
        return _ExecutedPlanningHostActionResult(
            payload={"status": "failed", "reason": "destination-operation-executor-unavailable", "error": str(exc)},
            seal=_HOST_ACTION_EXECUTION_SEAL,
        )
    raw_output = completed.stdout or completed.stderr
    try:
        result_payload = json.loads(raw_output)
    except json.JSONDecodeError:
        result_payload = {"status": "failed", "reason": "destination-result-malformed", "exit_code": completed.returncode}
    if not isinstance(result_payload, dict):
        result_payload = {"status": "failed", "reason": "destination-result-not-object", "exit_code": completed.returncode}
    accepted_statuses = {str(item) for item in _as_list(_as_dict(invocation.get("result_admission")).get("accepted_statuses"))}
    result_status = (
        "failed" if completed.returncode else _host_action_result_status(payload=result_payload, accepted_statuses=accepted_statuses)
    )
    after_revision_payload = _planning_revision_payload(target_root=target_root)
    after_revision = str(after_revision_payload.get("revision_id") or after_revision_payload.get("revision") or "")
    postcondition_status = "verified"
    if result_status == "applied" and before_revision and after_revision == before_revision:
        postcondition_status = "failed"
    result_revision = "sha256:" + _stable_revision(result_payload)
    executor_revision = "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    receipt_identity = {
        "producer": "agentic-workspace.configured-operation-executor",
        "operation_id": str(invocation.get("operation_id") or ""),
        "invocation_revision": str(invocation.get("invocation_revision") or ""),
        "operation_contract_revision": current_contract_revision,
        "executor_revision": executor_revision,
        "idempotency_key": str(invocation.get("idempotency_key") or ""),
        "result_status": result_status,
        "result_revision": result_revision,
        "planning_revision_before": before_revision,
        "planning_revision_after": after_revision,
        "postcondition_status": postcondition_status,
    }
    receipt = {
        "kind": "agentic-planning/front-door-host-action-execution-receipt/v1",
        **receipt_identity,
        "receipt_id": "sha256:" + _stable_revision(receipt_identity),
    }
    return _ExecutedPlanningHostActionResult(
        payload={
            "kind": str(_as_dict(invocation.get("result_admission")).get("kind") or ""),
            "status": result_status,
            "operation_id": str(invocation.get("operation_id") or ""),
            "invocation_revision": str(invocation.get("invocation_revision") or ""),
            "operation_contract_revision": current_contract_revision,
            "result": result_payload,
            "receipt": receipt,
        },
        seal=_HOST_ACTION_EXECUTION_SEAL,
    )


def admit_planning_front_door_host_action_result(
    *, invocation: Mapping[str, Any], result: _ExecutedPlanningHostActionResult | Mapping[str, Any]
) -> dict[str, Any]:
    """Re-admit only a result returned by this destination-operation executor."""

    if not isinstance(result, _ExecutedPlanningHostActionResult) or result.seal is not _HOST_ACTION_EXECUTION_SEAL:
        return {
            "kind": "agentic-planning/front-door-host-action-admission/v1",
            "status": "rejected",
            "operation_id": str(invocation.get("operation_id") or ""),
            "invocation_revision": str(invocation.get("invocation_revision") or ""),
            "result_status": "",
            "failures": ["producer-owned-result"],
            "receipt": {},
        }
    payload = result.payload

    expected = _as_dict(invocation.get("result_admission"))
    accepted_statuses = {str(item) for item in _as_list(expected.get("accepted_statuses"))}
    failures: list[str] = []
    expectations = {
        "kind": str(expected.get("kind") or ""),
        "operation_id": str(invocation.get("operation_id") or ""),
        "invocation_revision": str(invocation.get("invocation_revision") or ""),
        "operation_contract_revision": str(invocation.get("operation_contract_revision") or ""),
    }
    for field, value in expectations.items():
        if str(payload.get(field) or "") != value:
            failures.append(field)
    if str(payload.get("status") or "") not in accepted_statuses:
        failures.append("status")
    receipt = _as_dict(payload.get("receipt"))
    receipt_identity = {key: value for key, value in receipt.items() if key not in {"kind", "receipt_id"}}
    current_executor_revision = "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if (
        receipt.get("kind") != "agentic-planning/front-door-host-action-execution-receipt/v1"
        or receipt.get("producer") != "agentic-workspace.configured-operation-executor"
        or receipt.get("operation_id") != expectations["operation_id"]
        or receipt.get("invocation_revision") != expectations["invocation_revision"]
        or receipt.get("operation_contract_revision") != expectations["operation_contract_revision"]
        or receipt.get("executor_revision") != current_executor_revision
        or receipt.get("idempotency_key") != invocation.get("idempotency_key")
        or receipt.get("planning_revision_before") != invocation.get("planning_revision")
        or receipt.get("result_status") != payload.get("status")
        or receipt.get("result_revision") != "sha256:" + _stable_revision(_as_dict(payload.get("result")))
        or receipt.get("postcondition_status") != "verified"
        or receipt.get("receipt_id") != "sha256:" + _stable_revision(receipt_identity)
    ):
        failures.append("receipt")
    return {
        "kind": "agentic-planning/front-door-host-action-admission/v1",
        "status": "admitted" if not failures else "rejected",
        "operation_id": expectations["operation_id"],
        "invocation_revision": expectations["invocation_revision"],
        "result_status": str(payload.get("status") or ""),
        "failures": failures,
        "receipt": receipt if not failures else {},
    }


def _planning_front_door_projection_outcome(
    route_action: str,
    action_identity: Mapping[str, Any],
    *,
    target_root: Path,
    task_text: str,
    changed_paths: list[str],
) -> dict[str, Any]:
    """Return the finite non-mutating outcome for an admitted Planning route action."""
    projection_outcomes = {
        "refresh-planning-route-decision": ("no-op", "blocked", "refresh-route-decision", "route-authority-incomplete"),
        "continue-active-plan": ("no-op", "available-after-proof", "continue-selected-owner", "selected-owner-continuation"),
        "prove-current-task": ("no-op", "available-after-proof", "prove-current-task", "active-plan-protected-current-task"),
        "inspect-current-task-scope": ("no-op", "blocked", "inspect-current-task-scope", "current-task-scope-unresolved"),
        "choose-task-switch-route": ("blocked", "blocked", "explicit-route-choice-required", "ambiguous-active-plan-route"),
        "archive-or-retire-completed-plan": (
            "host-action-required",
            "blocked",
            "archive-or-retire-through-planning",
            "completed-active-plan-residue",
        ),
        "refresh-mutation-baseline": (
            "host-action-required",
            "blocked",
            "refresh-mutation-baseline",
            "mutation-baseline-required",
        ),
        "repair-planning-projection": (
            "host-action-required",
            "blocked",
            "repair-selected-owner-projection",
            "projection-repair-required",
        ),
        "complete-selected-proof": ("host-action-required", "blocked", "complete-selected-proof", "proof-incomplete"),
        "promote-or-create-planning-owner": (
            "host-action-required",
            "blocked",
            "promote-or-create-owner",
            "owner-promotion-required",
        ),
        "select-planning-owner": ("host-action-required", "blocked", "select-owner", "owner-selection-required"),
        "refresh-planning-reconciliation-proposal": (
            "host-action-required",
            "blocked",
            "refresh-reconciliation-proposal",
            "fresh-reconciliation-proposal-required",
        ),
    }
    mutation_outcome, claim_outcome, transition_outcome, reason = projection_outcomes.get(
        route_action, ("rejected", "blocked", "unsupported-route-action", "unsupported-route-action")
    )
    host_action_invocation = _planning_front_door_host_action_invocation(
        target_root=target_root,
        route_action=route_action,
        action_identity=action_identity,
        task_text=task_text,
        changed_paths=changed_paths,
    )
    if mutation_outcome == "host-action-required" and host_action_invocation.get("status") != "ready":
        mutation_outcome = "blocked"
    return {
        "mutation_outcome": mutation_outcome,
        "claim_outcome": claim_outcome,
        "typed_owner_operation": host_action_invocation,
        "host_action_invocation": host_action_invocation,
        "route_transition": {
            "kind": "agentic-planning/front-door-route-transition/v1",
            "status": transition_outcome,
            "route_action": route_action,
            "dispatch_status": str(host_action_invocation.get("status") or "not-required"),
            "expected_transition": str(_as_dict(action_identity).get("expected_transition") or ""),
            "state_update_policy": str(_as_dict(action_identity).get("state_update_policy") or ""),
            "implementation_allowed": bool(_as_dict(action_identity).get("implementation_allowed") is True),
            "mutation_authority": str(_as_dict(action_identity).get("mutation_authority") or "none"),
            "reason": reason,
            "rule": "Every admitted route action returns an explicit front-door transition outcome; consumers must not reinterpret legacy route fields.",
        },
    }


def execute_planning_front_door_route_action(values: Mapping[str, Any]) -> dict[str, Any]:
    """Runtime admission boundary for the generated ``planning.front-door`` operation.

    Generated clients and command adapters may carry a serialized route-action
    packet, but this front door must not execute, claim, or mutate from that
    packet directly.  It re-resolves the live Planning gate for the requested
    target/task/scope, admits only the exact current invocation identity, then
    dispatches the finite route action as an explicit no-op/applied/rejected
    outcome.
    """

    from agentic_workspace import config as config_lib

    target_root = Path(str(values.get("target") or ".")).resolve()
    task_text = str(values.get("task") or values.get("task_text") or "")
    raw_changed = values.get("changed_paths", values.get("changed", values.get("paths", [])))
    if isinstance(raw_changed, str):
        changed_paths = [raw_changed]
    elif isinstance(raw_changed, list):
        changed_paths = [str(path) for path in raw_changed if str(path)]
    else:
        changed_paths = []
    invocation = _as_dict(values.get("operation_invocation") or values.get("invocation"))
    config = config_lib.load_workspace_config(target_root=target_root)
    gate = _planning_safety_gate_payload(
        target_root=target_root,
        config=config,
        changed_paths=changed_paths,
        task_text=task_text,
        execution_posture=_as_dict(values.get("execution_posture")),
    )
    live_route_decision = _as_dict(gate.get("route_decision"))
    admission = validate_planning_route_action_invocation(invocation=invocation, live_route_decision=live_route_decision)
    live_action = _as_dict(live_route_decision.get("next_safe_action"))
    action_identity = _as_dict(_as_dict(live_action.get("operation_invocation")).get("input_identity"))
    route_action = str(action_identity.get("route_action") or live_action.get("action") or "")
    admitted = admission["status"] == "admitted"
    action_result: dict[str, Any] = {}
    if admitted and route_action == "apply-planning-reconciliation-proposal":
        action_result = _apply_planning_front_door_reconciliation_proposal(
            target_root=target_root,
            live_route_decision=live_route_decision,
            action_identity=action_identity,
        )
        outcome = str(action_result.get("mutation_outcome") or "blocked")
    elif admitted:
        action_result = _planning_front_door_projection_outcome(
            route_action,
            action_identity,
            target_root=target_root,
            task_text=task_text,
            changed_paths=changed_paths,
        )
        host_invocation = _as_dict(action_result.get("host_action_invocation"))
        if host_invocation.get("status") == "ready":
            host_result = _execute_planning_front_door_host_action(invocation=host_invocation)
            host_admission = admit_planning_front_door_host_action_result(
                invocation=host_invocation,
                result=host_result,
            )
            action_result["host_action_admission"] = host_admission
            if values.get("host_action_result") is not None:
                action_result["caller_host_action_result"] = {
                    "status": "ignored-untrusted",
                    "reason": "destination results are issued only by the configured operation executor",
                }
            if host_admission.get("status") == "admitted":
                admitted_status = str(host_admission.get("result_status") or "")
                action_result["mutation_outcome"] = (
                    "applied"
                    if admitted_status == "applied"
                    else "no-op"
                    if admitted_status in {"already-applied", "no-op"}
                    else "reported"
                )
                action_result["claim_outcome"] = "available-after-proof"
                action_result["mutation_receipt"] = _as_dict(host_admission.get("receipt"))
                action_result["route_transition"] = {
                    **_as_dict(action_result.get("route_transition")),
                    "dispatch_status": "result-admitted",
                    "status": "owner-operation-result-admitted",
                }
            else:
                action_result["mutation_outcome"] = "rejected"
                action_result["claim_outcome"] = "blocked"
        outcome = str(action_result.get("mutation_outcome") or "blocked")
    else:
        outcome = "rejected"
    claim_outcome = str(
        action_result.get("claim_outcome") or ("available-after-proof" if admitted and outcome in {"no-op", "applied"} else "blocked")
    )
    return {
        "kind": "agentic-planning/front-door-route-action-result/v1",
        "status": "admitted" if admitted else "rejected",
        "operation_id": "planning.front-door",
        "operation_action": "route-decision-next-action",
        "target": target_root.as_posix(),
        "task_digest": _stable_revision(task_text)[:16],
        "changed_path_count": len(changed_paths),
        "route_action": route_action,
        "mutation_outcome": outcome,
        "claim_outcome": claim_outcome,
        "admission": admission,
        "live_route_decision": live_route_decision,
        "next_safe_action": live_action,
        **({"mutation_receipt": action_result["mutation_receipt"]} if "mutation_receipt" in action_result else {}),
        **({"reconciliation_apply": action_result["reconciliation_apply"]} if "reconciliation_apply" in action_result else {}),
        **({"route_transition": action_result["route_transition"]} if "route_transition" in action_result else {}),
        **({"host_action_invocation": action_result["host_action_invocation"]} if "host_action_invocation" in action_result else {}),
        **({"host_action_admission": action_result["host_action_admission"]} if "host_action_admission" in action_result else {}),
        "rule": "planning.front-door recomputes and admits the live route decision before any Planning transition, mutation, proof, or claim effect.",
    }


def _route_safety_outcome(route_decision: dict[str, Any]) -> dict[str, Any]:
    """Project the canonical route contract into the planning-gate outcome.

    ``task_switch_reconciliation`` remains evidence for compatibility and
    diagnosis only.  Consumers must not reclassify that legacy packet: they
    consume this projection of the already-resolved route decision.
    """
    relation = str(route_decision.get("task_relation") or "not-applicable")
    posture = str(route_decision.get("owner_posture") or "not-applicable")
    transition = str(route_decision.get("required_transition") or "none")
    action = _as_dict(route_decision.get("next_safe_action"))
    operation_invocation = _as_dict(action.get("operation_invocation"))
    structured_inputs = _as_dict(route_decision.get("structured_inputs"))
    binding = _as_dict(structured_inputs.get("task_binding"))
    baseline = _as_dict(structured_inputs.get("mutation_baseline"))
    proposal = _as_dict(route_decision.get("reconciliation_proposal"))
    mode = str(binding.get("mode") or "")
    mutation_admission = _as_dict(route_decision.get("mutation_baseline_admission"))
    baseline_identity = str(baseline.get("baseline_id") or baseline.get("head") or baseline.get("revision") or "")
    default_action = (
        "prove-current-task"
        if relation == "bounded-independent" and transition == "none"
        else "continue-active-plan"
        if relation == "continues-selected-owner" and transition == "none"
        else "inspect-current-task-scope"
        if relation == "independent-pending-scope"
        else "choose-task-switch-route"
        if relation == "ambiguous" or transition == "ask-for-route-decision"
        else "archive-or-retire-completed-plan"
        if posture == "completed-residue"
        else ""
    )
    action_safety = {
        "owner": _as_dict(route_decision.get("selected_owner_identity")),
        "relation": relation,
        "posture": posture,
        "transition": transition,
        "typed_action": operation_invocation
        or {
            "operation_id": str(action.get("operation_id") or action.get("action") or default_action),
            "authority": "planning-route-decision",
            "identity_source": "route-next-safe-action",
        },
        "rendered_action": str(action.get("action") or default_action),
        "allowed_claims": [
            str(item) for item in route_decision.get("allowed_claims", []) if isinstance(route_decision.get("allowed_claims"), list)
        ],
        "blocked_claims": [
            str(item) for item in route_decision.get("blocked_claims", []) if isinstance(route_decision.get("blocked_claims"), list)
        ],
        "effect_scope": [str(item) for item in binding.get("allowed_paths", []) if isinstance(binding.get("allowed_paths"), list)],
        "mutation_baseline": baseline,
        "mutation_baseline_identity": baseline_identity,
        "proposal_identity": str(proposal.get("proposal_id") or proposal.get("identity") or ""),
        "proposal_freshness": str(proposal.get("status") or "not-applicable"),
        "proof_expectation": str(route_decision.get("proof_expectation") or ""),
        "state_update_policy": str(route_decision.get("state_update_policy") or ""),
        "repair_owner": str(route_decision.get("repair_owner") or "planning-route-decision"),
    }
    route_applicable = any(
        (
            relation != "not-applicable",
            posture != "not-applicable",
            bool(action_safety["owner"].get("ref")),
            mode in {"read-only", "mutation"},
            action_safety["proposal_freshness"] not in {"", "not-applicable", "absent"},
        )
    )
    if not route_applicable:
        return {}
    route_identity_missing = (
        not action_safety["owner"].get("ref")
        or not _as_dict(action_safety["typed_action"]).get("operation_id")
        or not action_safety["state_update_policy"]
    )
    if route_identity_missing:
        return {
            "status": "attention",
            "decision": "route-authority-incomplete",
            "reason": "The route decision is missing owner, typed action, or state-update authority.",
            "required_next_action": "refresh-planning-route-decision",
            "workflow_sufficient": True,
            "action_safety": action_safety,
        }
    if relation == "independent-pending-scope":
        return {
            "status": "attention",
            "decision": "current-task-scope-inspection-required",
            "reason": "The resolved current task still needs scope inspection; completed owner residue remains a separate closeout obligation.",
            "required_next_action": str(action.get("action") or "inspect-current-task-scope"),
            "workflow_sufficient": True,
            "action_safety": action_safety,
        }
    if posture == "completed-residue":
        return {
            "status": "attention",
            "decision": "archive-or-retire-completed-plan",
            "reason": "The selected owner is complete and requires closeout or archive.",
            "required_next_action": "archive-or-retire-completed-plan",
            "workflow_sufficient": True,
        }
    if relation == "bounded-independent" and transition == "refresh-mutation-baseline":
        return {
            "status": "blocked",
            "decision": "mutation-baseline-required",
            "reason": str(mutation_admission.get("reason") or "The bounded route requires a refreshed mutation baseline before mutation."),
            "required_next_action": "refresh-mutation-baseline",
            "workflow_sufficient": False,
            "action_safety": action_safety,
        }
    if relation == "bounded-independent" and transition == "none":
        if mode == "mutation" and mutation_admission.get("status") != "current":
            return {
                "status": "blocked",
                "decision": "route-authority-inconsistent",
                "reason": str(
                    mutation_admission.get("reason")
                    or "The route decision is internally inconsistent: bounded mutation has no current baseline admission."
                ),
                "required_next_action": "refresh-planning-route-decision",
                "workflow_sufficient": False,
                "action_safety": action_safety,
            }
        return {
            "status": "satisfied",
            "decision": "bounded-read-only-work" if mode == "read-only" else "current-task-route-acknowledged",
            "reason": "The resolved route admits bounded work without an active-plan progress claim.",
            "required_next_action": str(action.get("action") or "prove-current-task"),
            "workflow_sufficient": True,
            "action_safety": action_safety,
        }
    if relation == "ambiguous" or transition == "ask-for-route-decision":
        return {
            "status": "attention",
            "decision": "active-plan-task-switch",
            "reason": "The resolved route is ambiguous and requires an explicit task-route decision.",
            "required_next_action": str(action.get("action") or "choose-task-switch-route"),
            "workflow_sufficient": True,
        }
    if relation == "continues-selected-owner" and transition == "none":
        return {
            "status": "satisfied",
            "decision": "planning-backed",
            "reason": "The resolved route continues the selected owner.",
            "required_next_action": str(action.get("action") or "continue-active-plan"),
            "workflow_sufficient": True,
        }
    return {
        "status": "attention",
        "decision": "route-transition-required",
        "reason": "The resolved route relation, posture, or transition is unsupported for direct action.",
        "required_next_action": str(action.get("action") or "refresh-planning-route-decision"),
        "workflow_sufficient": True,
        "action_safety": action_safety,
    }


def _mutation_baseline_route_current(baseline: dict[str, Any], *, changed_paths: list[str]) -> bool:
    scope = _as_dict(baseline.get("scope"))
    observed = _as_dict(baseline.get("observed_state"))
    observation = _as_dict(baseline.get("observation"))
    boundary = _as_dict(baseline.get("boundary_enforcement"))
    stale_revalidation = _as_dict(baseline.get("stale_revalidation"))
    ownership = _as_dict(baseline.get("ownership"))
    allowed_paths = [str(path) for path in scope.get("allowed_paths", []) if isinstance(scope.get("allowed_paths"), list)]
    requested = [path for path in changed_paths if path]
    revalidation_status = str(baseline.get("revalidation_status") or "").strip()
    return all(
        (
            baseline.get("kind") == "agentic-workspace/mutation-baseline/v1",
            revalidation_status in {"current", "fresh"},
            bool(baseline.get("baseline_id")),
            bool(baseline.get("head")),
            observation.get("ok") is True,
            bool(observed.get("enforcement_fingerprint")),
            boundary.get("status") == "fail-closed-contract",
            stale_revalidation.get("status") == "required",
            bool(ownership.get("owner")),
            bool(requested),
            set(requested).issubset(set(allowed_paths)),
        )
    )


def _mutation_baseline_repair_reason(baseline: dict[str, Any], *, changed_paths: list[str]) -> str:
    if not baseline:
        return "Bounded mutation requires a live authority-envelope mutation baseline."
    if baseline.get("kind") != "agentic-workspace/mutation-baseline/v1":
        return "Bounded mutation baseline must come from the authority-envelope mutation owner."
    if str(baseline.get("revalidation_status") or "") not in {"current", "fresh"}:
        return "Bounded mutation baseline must carry a current live revalidation status."
    scope = _as_dict(baseline.get("scope"))
    allowed_paths = [str(path) for path in scope.get("allowed_paths", []) if isinstance(scope.get("allowed_paths"), list)]
    requested = [path for path in changed_paths if path]
    if not requested or not set(requested).issubset(set(allowed_paths)):
        return "Bounded mutation baseline must cover the requested changed-path scope."
    return "Bounded mutation baseline must include head, observed state, boundary enforcement, and ownership."


def _task_switch_reconciliation_payload(**kwargs: Any) -> dict[str, Any]:
    """Compatibility diagnostic alias; ordinary consumers must use route_decision."""
    return _planning_route_evidence_payload(**kwargs)


def _task_switch_fact_payload(route_evidence: dict[str, Any]) -> dict[str, Any]:
    """Strip legacy route evidence to non-authoritative facts for consumers."""
    fact_keys = (
        "kind",
        "status",
        "summary",
        "active_execplan",
        "intent_conflict_state",
        "mismatch_evidence",
        "current_task_class",
        "classification_basis",
        "matched_maintenance_markers",
        "classification_inputs",
        "semantic_boundary",
        "rule",
    )
    facts = {key: route_evidence.get(key) for key in fact_keys if route_evidence.get(key) not in (None, "", [], {})}
    completed_plan = _as_dict(route_evidence.get("completed_active_plan"))
    if completed_plan:
        facts["completed_active_plan"] = {
            key: completed_plan.get(key)
            for key in (
                "kind",
                "status",
                "active_execplan",
                "plan_id",
                "evidence_fields",
                "missing_fields",
                "parent_lane_boundary",
                "rule",
            )
            if completed_plan.get(key) not in (None, "", [], {})
        }
    acknowledgement = _as_dict(route_evidence.get("route_acknowledgement"))
    if acknowledgement:
        facts["route_acknowledgement"] = {
            key: acknowledgement.get(key)
            for key in ("status", "route", "acknowledged_by", "changed_path_count", "proof_rule", "rule")
            if acknowledgement.get(key) not in (None, "", [], {})
        }
    if route_evidence.get("route_inputs"):
        facts["route_input_summary"] = {
            "available": True,
            "detail_source": "route_decision.structured_inputs",
            "rule": "Structured route inputs are consumed by route_decision before this compatibility packet is exposed.",
        }
    facts["authority"] = "diagnostic-facts-only"
    facts["decision_fields_removed"] = [
        "recommended_next_action",
        "next_action_packet",
        "safe_routes",
        "implementation_allowed",
        "active_plan_protection",
        "blocked_claims",
        "command",
    ]
    facts["derive_action_from"] = "planning_safety_gate.route_decision"
    return facts


def _is_bounded_current_task_route(route_decision: Any) -> bool:
    """Return whether the canonical route admits ordinary bounded current-task work.

    This predicate is intentionally expressed only in the compositional route
    dimensions.  Compatibility task-switch facts must never participate in an
    action, permission, claim, or closeout decision.
    """
    route = _as_dict(route_decision)
    return (
        route.get("kind") == "agentic-planning/route-decision/v1"
        and route.get("task_relation") == "bounded-independent"
        and route.get("owner_posture") == "current"
        and route.get("required_transition") == "none"
        and route.get("implementation_allowed") is True
        and route.get("mutation_authority") in {"current-task", "none"}
    )


def _route_claim_effect_boundary(*, task_text: str | None, changed_paths: list[str]) -> dict[str, Any]:
    """Compile the installed-payload claim boundary as a canonical route fact."""

    normalized_task = " ".join(str(task_text or "").lower().split())
    paths = [str(path).replace("\\", "/") for path in changed_paths if str(path).strip()]
    tokens = set(normalized_task.replace("/", " ").replace("-", " ").split())
    installed_subjects = {
        "install",
        "installed",
        "installation",
        "payload",
        "runtime",
        "wheel",
        "package",
        "packaged",
        "distribution",
        "executable",
    }
    drift_actions = {"drift", "upgrade", "sync", "freshness", "compatibility"}
    public_behavior_subjects = {"command", "cli", "entrypoint", "behavior", "behaviour"}
    proof_actions = {"prove", "proof", "verify", "verification", "validate", "validation"}
    mutation_actions = {"add", "change", "edit", "fix", "implement", "remove", "update", "write"}
    installed_subject_match = bool(tokens & installed_subjects)
    explicit_drift_match = bool(tokens & drift_actions) and bool(tokens & (installed_subjects | {"generated"}))
    public_behavior_match = "public" in tokens and bool(tokens & public_behavior_subjects)
    payload_proof_match = bool(tokens & proof_actions) and bool(tokens & (installed_subjects | public_behavior_subjects))
    payload_path_match = any(
        path
        in {
            ".agentic-workspace/config.toml",
            ".agentic-workspace/payload-provenance.json",
            "pyproject.toml",
            "uv.lock",
            "src/agentic_workspace/workspace_runtime_core.py",
            "src/agentic_workspace/workspace_runtime_primitives.py",
            "src/agentic_workspace/workspace_runtime_startup.py",
        }
        or path.startswith(("generated/", "scripts/generate/", "scripts/release/", "src/agentic_workspace/contracts/"))
        or path.endswith(("/pyproject.toml", "/package.json", "/package-lock.json", "/pnpm-lock.yaml"))
        for path in paths
    )
    dependency = (
        "dependent"
        if payload_path_match or installed_subject_match or explicit_drift_match or public_behavior_match or payload_proof_match
        else "independent"
        if normalized_task
        else "unknown"
    )
    effect_class = (
        "repo-mutation"
        if paths
        else "planned-repo-mutation"
        if tokens & mutation_actions
        else "read-only-inspection"
        if normalized_task
        else "unresolved"
    )
    matched_facts = [
        fact
        for fact, matched in (
            ("changed-path-effect", bool(paths)),
            ("installed-payload-path", payload_path_match),
            ("installed-artifact-subject", installed_subject_match),
            ("installed-drift-operation", explicit_drift_match),
            ("public-command-behavior", public_behavior_match),
            ("payload-dependent-proof", payload_proof_match),
        )
        if matched
    ]
    return {
        "effect_class": effect_class,
        "installed_payload_dependency": dependency,
        "claim_classes": (
            ["installed-payload-behavior", "installed-payload-freshness"]
            if dependency == "dependent"
            else ["checked-in-source-evidence"]
            if dependency == "independent"
            else []
        ),
        "matched_facts": matched_facts,
        "changed_path_count": len(paths),
    }


def _structured_route_inputs(
    *,
    target_root: Path,
    active_summary: dict[str, Any],
    task_text: str | None,
    changed_paths: list[str],
    route_evidence: dict[str, Any],
    planning_revision: dict[str, Any],
    proposal: dict[str, Any],
    path_classification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive resolver dimensions from current-work and owner facts, not status aliases."""
    active_owner, owner_record = _active_execplan_record_payload(target_root=target_root)
    active_owner = active_owner or str(active_summary.get("active_execplan") or "")
    mismatch = _task_switch_mismatch_evidence(active_summary=active_summary, task_text=task_text)
    shared_refs = [str(ref) for ref in mismatch.get("shared_refs", []) if str(ref).strip()]
    current_task_class = str(route_evidence.get("current_task_class") or "")
    acknowledged = route_evidence.get("status") == "current-task-route-acknowledged"
    bounded_read_only = current_task_class.startswith("bounded-") and not acknowledged
    bounded_mutation = acknowledged and bool(changed_paths)
    owner_scope_values: list[str] = []
    owner_scope = _as_dict(owner_record.get("scope"))
    canonical_core = _as_dict(owner_record.get("canonical_core"))
    for raw_values in (
        owner_scope.get("owned"),
        owner_record.get("touched_scope"),
        canonical_core.get("touched_scope"),
    ):
        owner_scope_values.extend(str(value).strip() for value in _as_list(raw_values) if str(value).strip())
    owner_scope_values = list(dict.fromkeys(owner_scope_values))
    concrete_owner_paths = [
        value.replace("\\", "/").strip("/") for value in owner_scope_values if " " not in value and ("/" in value or Path(value).suffix)
    ]
    normalized_changed = [path.replace("\\", "/").strip("/") for path in changed_paths]
    owner_scope_overlap = sorted(
        {
            changed
            for changed in normalized_changed
            for protected in concrete_owner_paths
            if changed == protected or changed.startswith(f"{protected}/") or protected.startswith(f"{changed}/")
        }
    )
    established_independent = bool(str(task_text or "").strip()) and mismatch.get("overlap_signal") == "low-overlap-explicit-task"
    effect_scope = _as_dict(_as_dict(path_classification).get("effect_scope"))
    local_transient_cleanup = effect_scope.get("status") == "proven-local-transient"
    mutation_baseline = _as_dict(route_evidence.get("mutation_baseline"))
    if bounded_mutation and not local_transient_cleanup:
        live_baseline = mutation_baseline_payload(target_root=target_root, changed_paths=changed_paths)
        mutation_baseline = {
            **live_baseline,
            "source": "authority-envelope-live-observation",
            "revalidation_status": "current" if _as_dict(live_baseline.get("observation")).get("ok") is True else "failed",
            "overlap_claim": {
                "status": "scoped-to-requested-paths",
                "allowed_paths": list(changed_paths),
                "unexpected_overlap_policy": "fail-closed-at-boundary-enforcement",
            },
            "allowed_effects": ["repo-mutation"],
            "changed_path_count": len(changed_paths),
        }
    exact_task_identity_match = mismatch.get("exact_task_identity_match") is True
    owner_title = str(owner_record.get("title") or "").strip().casefold()
    task_title_match = bool(owner_title and str(task_text or "").strip().casefold() == owner_title)
    if shared_refs or exact_task_identity_match or task_title_match:
        task_relation, task_basis = "continues-selected-owner", "shared-structured-reference"
        if exact_task_identity_match or task_title_match:
            task_basis = "exact-current-task-owner-intent"
    elif changed_paths and owner_scope_overlap:
        task_relation, task_basis = "ambiguous", "active-owner-scope-overlap"
    elif bounded_read_only:
        task_relation, task_basis = "bounded-independent", "bounded-read-only-current-work-binding"
    elif bounded_mutation:
        task_relation, task_basis = "bounded-independent", "bounded-mutation-current-work-binding"
    elif not active_owner:
        task_relation, task_basis = "not-applicable", "no-selected-owner"
    elif established_independent:
        task_relation, task_basis = "bounded-independent", "structured-intent-non-overlap"
    elif route_evidence.get("status") == "not-applicable":
        task_relation, task_basis = "continues-selected-owner", "selected-owner-current-task-reliance"
    else:
        task_relation, task_basis = "independent-pending-scope", "selected-owner-without-current-work-binding"

    revision_status = str(planning_revision.get("status") or "")
    closure = _as_dict(owner_record.get("closure_check"))
    proof = _as_dict(owner_record.get("proof_report"))
    lifecycle = str(owner_record.get("status") or owner_record.get("lifecycle") or "active") if active_owner else "missing"
    completed = "complete" in str(closure.get("slice status") or "").lower()
    if revision_status in {"stale", "drifted"}:
        owner_posture = "projection-drifted"
    elif not active_owner:
        owner_posture = "not-applicable"
    elif completed:
        owner_posture = "completed-residue"
    elif lifecycle in {"completed", "closed", "archived"}:
        owner_posture = "completed-residue"
    elif lifecycle in {"proof-incomplete", "awaiting-proof"} or (closure and not proof):
        owner_posture = "proof-incomplete"
    else:
        owner_posture = "current"
    adopted_child = bool(active_owner and shared_refs)
    task_binding_identity = (
        f"bounded-child:{_stable_revision({'parent_owner_ref': active_owner, 'task': str(task_text or '').strip()})[7:27]}"
        if adopted_child
        else ""
    )
    return {
        "task_relation": task_relation,
        "owner_posture": owner_posture,
        "route_inputs": {
            "claim_effect_boundary": _route_claim_effect_boundary(task_text=task_text, changed_paths=changed_paths),
            "task_binding": {
                "identity": task_binding_identity,
                "basis": task_basis,
                "relation_source": "explicit-structured-child-adoption" if adopted_child else task_basis,
                "parent_owner_ref": active_owner if adopted_child else "",
                "shared_refs": shared_refs,
                "current_task_class": current_task_class,
                "changed_path_count": len(changed_paths),
                "allowed_paths": list(changed_paths) if bounded_mutation else [],
                "mutation_scope_acknowledged": bounded_mutation,
                "mode": (
                    "local-transient-cleanup"
                    if local_transient_cleanup
                    else "read-only"
                    if bounded_read_only or (active_owner and established_independent and not changed_paths)
                    else "mutation"
                    if bounded_mutation
                    else "unresolved"
                ),
                "effect_scope": effect_scope,
            },
            "mutation_baseline": mutation_baseline,
            "owner": {
                "ref": active_owner,
                "lifecycle": lifecycle,
                "projection_status": revision_status or "unknown",
                "proof_present": bool(proof),
                "closure_status": str(closure.get("slice status") or ""),
            },
            "non_interference_boundary": {
                "status": "selected-owner"
                if active_owner and task_relation == "continues-selected-owner"
                else "protected"
                if active_owner and task_relation == "bounded-independent"
                else "overlap-blocked"
                if owner_scope_overlap
                else "not-applicable",
                "owner_ref": active_owner,
                "owner_revision": str(planning_revision.get("revision_id") or ""),
                "protected_scope": {
                    "digest": _stable_revision(owner_scope_values) if owner_scope_values else "",
                    "declared_item_count": len(owner_scope_values),
                    "concrete_path_count": len(concrete_owner_paths),
                },
                "overlap_paths": owner_scope_overlap,
                "restriction": (
                    ""
                    if task_relation == "continues-selected-owner"
                    else "Do not mutate or claim the selected owner's protected scope from this independent task."
                    if task_relation == "bounded-independent"
                    else "Resolve the active-owner overlap before mutation."
                    if owner_scope_overlap
                    else ""
                ),
            },
            "admitted_external_observation": _as_dict(route_evidence.get("admitted_external_observation")),
            "reconciliation_proposal": {
                key: proposal.get(key)
                for key in ("status", "proposal_id", "freshness", "required_transition", "owner_posture")
                if proposal.get(key) not in (None, "", [], {})
            },
        },
    }


def _current_reconciliation_proposal(*, target_root: Path, planning_revision: dict[str, Any]) -> dict[str, Any]:
    """Read only a current #2281 proposal summary; compilation remains package-owned."""
    proposal_root = target_root / ".agentic-workspace/local/planning/reconciliation-proposals"
    expected_revision = str(_as_dict(planning_revision).get("revision_id") or "")
    if not proposal_root.is_dir() or not expected_revision:
        return {"status": "absent"}
    stale_proposal_id = ""
    for path in sorted(proposal_root.glob("*.json"), reverse=True)[:8]:
        try:
            proposal = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(_as_dict(proposal).get("transaction_class") or "") == "target-authority-integration":
            continue
        source = _as_dict(_as_dict(proposal).get("source"))
        proposal_id = str(_as_dict(proposal).get("proposal_id") or "")
        apply_command = str(_as_dict(proposal).get("apply_command") or "")
        operations = [item for item in _as_list(proposal.get("operations")) if isinstance(item, dict)]
        owner_transitions = [item for item in _as_list(proposal.get("owner_transitions")) if isinstance(item, dict)]
        actionable_transitions = [
            item for item in owner_transitions if str(item.get("transition") or "") not in {"", "none", "not-applicable", "remain-live"}
        ]
        if not operations and not actionable_transitions:
            continue
        if source.get("planning_revision") != expected_revision:
            stale_proposal_id = stale_proposal_id or proposal_id
            continue
        if proposal_id and apply_command:
            return {
                "status": "current",
                "freshness": "current",
                "proposal_id": proposal_id,
                "apply_command": apply_command,
                "required_transition": str(proposal.get("required_transition") or proposal.get("transition") or "reconcile"),
                "owner_posture": str(proposal.get("owner_posture") or proposal.get("posture") or "reconciliation-pending"),
            }
    return {"status": "stale", "freshness": "stale", "proposal_id": stale_proposal_id} if stale_proposal_id else {"status": "absent"}


def _compiled_target_authority_reconciliation(*, target_root: Path, cli_invoke: str) -> dict[str, Any]:
    """Project a bounded stale-target transaction without persisting it."""
    proposal_root = target_root / ".agentic-workspace/planning/integration-proposals"
    if not proposal_root.is_dir() or not any(proposal_root.glob("*.integration-proposal.json")):
        return {"status": "absent"}
    try:
        from repo_planning_bootstrap.installer import planning_reconcile

        transaction = _as_dict(planning_reconcile(target=target_root, preview=True, dry_run=True))
    except Exception as exc:  # pragma: no cover - defensive package boundary.
        return {
            "status": "unavailable",
            "reason": "target-authority-reconciliation-preview-unavailable",
            "error": str(exc),
        }
    if transaction.get("transaction_class") != "target-authority-integration":
        return {"status": "absent"}
    if transaction.get("status") != "preview":
        semantic_conflicts = [copy.deepcopy(item) for item in _as_list(transaction.get("semantic_conflicts")) if isinstance(item, dict)]
        current_target_revision = str(transaction.get("current_target_authority_revision") or "")
        refresh_command = ""
        stale_conflict = next(
            (item for item in semantic_conflicts if str(item.get("reason_code") or "") == "stale-integration-subject-revision"),
            None,
        )
        if stale_conflict is not None:
            proposal_id = str(stale_conflict.get("proposal_id") or "")
            proposal_revision = str(stale_conflict.get("proposal_revision") or "")
            subject_revision = str(stale_conflict.get("current_subject_revision") or "")
            target_revision = str(stale_conflict.get("current_target_authority_revision") or current_target_revision)
            if proposal_id and proposal_revision and subject_revision and target_revision:
                refresh_command = _command_with_cli_invoke(
                    command=(
                        "agentic-workspace planning integration-propose "
                        f"--proposal-id {proposal_id} --refresh-existing "
                        f"--expect-proposal-revision {proposal_revision} "
                        f"--expect-subject-revision {subject_revision} "
                        f"--expect-planning-revision {target_revision} --target . --format json"
                    ),
                    cli_invoke=cli_invoke,
                )
        return {
            "status": str(transaction.get("status") or "blocked"),
            "reason": str(transaction.get("reason") or "target-authority-reconciliation-blocked"),
            "affected_owner_refs": [str(item) for item in _as_list(transaction.get("affected_owner_refs"))],
            "target_prerequisite": str(transaction.get("target_prerequisite") or ""),
            "semantic_conflicts": semantic_conflicts,
            "current_target_authority_revision": current_target_revision,
            "refresh_command": refresh_command,
        }
    proposal = _as_dict(transaction.get("proposal"))
    source = _as_dict(proposal.get("source"))
    operations = [copy.deepcopy(item) for item in _as_list(proposal.get("operations")) if isinstance(item, dict)]
    eligible_proposals = [str(item) for item in _as_list(proposal.get("eligible_proposals"))]
    refreshed_proposals = [str(item) for item in _as_list(proposal.get("refreshed_proposals"))]
    if not operations and not eligible_proposals and not refreshed_proposals:
        return {"status": "absent", "reason": "no-target-authority-reconciliation-work"}
    return {
        "status": "preview-available",
        "transaction_class": "target-authority-integration",
        "proposal_id": str(proposal.get("proposal_id") or ""),
        "preview_command": str(proposal.get("preview_command") or ""),
        "apply_command": str(proposal.get("apply_command") or ""),
        "planning_revision": str(source.get("planning_revision") or ""),
        "current_target_authority_revision": str(proposal.get("current_target_authority_revision") or ""),
        "affected_owner_refs": [str(item) for item in _as_list(proposal.get("affected_owner_refs"))],
        "eligible_proposals": eligible_proposals,
        "refreshed_proposals": refreshed_proposals,
        "operations": operations,
    }


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
    active_owner_intent = " ".join(str(active_summary.get("active_owner_intent_outcome") or "").split())
    exact_task_identity_match = bool(task and active_owner_intent and task.casefold() == active_owner_intent.casefold())
    task_terms = _task_switch_terms(task)
    active_terms = _task_switch_terms(active_text)
    task_refs = _task_switch_refs(task)
    active_refs = sorted(
        set(_task_switch_refs(active_text))
        | {str(ref) for ref in active_summary.get("active_owner_refs", []) if isinstance(active_summary.get("active_owner_refs"), list)}
    )
    shared_terms = [term for term in task_terms if term in set(active_terms)]
    shared_refs = [ref for ref in task_refs if ref in set(active_refs)]
    overlap_signal = (
        "exact-task-continuation"
        if exact_task_identity_match
        else "possible-continuation"
        if shared_refs or len(shared_terms) >= 2
        else "low-overlap-explicit-task"
    )
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
        "exact_task_identity_match": exact_task_identity_match,
        "overlap_signal": overlap_signal,
        "rule": "An exact current-task/owner-intent identity or structured refs are bounded continuation evidence; neither closes active planning.",
    }


def _planning_safety_gate_payload(
    *, target_root: Path, config: WorkspaceConfig, changed_paths: list[str], task_text: str | None, execution_posture: dict[str, Any]
) -> dict[str, Any]:
    active_summary = _fast_planning_active_summary(target_root=target_root)
    owner_admission = _as_dict(active_summary.get("owner_admission"))
    active_planning_present = bool(active_summary.get("todo_active_count") or active_summary.get("active_execplan"))
    capability = execution_posture.get("capability_posture", {}) if isinstance(execution_posture, dict) else {}
    work_shape, proof_burden = _capability_structural_hints(capability)
    decomposition_delegation = execution_posture.get("decomposition_delegation", {}) if isinstance(execution_posture, dict) else {}
    decomposition_status = str(decomposition_delegation.get("status", "")) if isinstance(decomposition_delegation, dict) else ""
    path_classification = _planning_safety_path_classification(changed_paths, target_root=target_root, task_text=task_text)
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
    bounded_external_effect = _bounded_external_issue_effect_payload(
        task_text=task_text,
        changed_paths=changed_paths,
        active_planning_present=active_planning_present,
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
    route_evidence["owner_admission"] = owner_admission
    route_evidence = _acknowledged_current_task_switch_payload(
        route_evidence,
        changed_paths=changed_paths,
        path_classification=path_classification,
    )
    reconciliation_proposal = _current_reconciliation_proposal(target_root=target_root, planning_revision=planning_revision)
    reconciliation_transaction = _compiled_target_authority_reconciliation(
        target_root=target_root,
        cli_invoke=config.cli_invoke,
    )
    external_reconciliation = _active_owner_external_reconciliation(
        target_root=target_root,
        active_summary=active_summary,
        config=config,
        planning_revision=planning_revision,
    )
    route_evidence = {
        **route_evidence,
        "admitted_external_observation": external_reconciliation,
        "external_refresh_command": str(external_reconciliation.get("refresh_command") or ""),
        "reconciliation_preview_command": str(
            reconciliation_transaction.get("preview_command")
            or reconciliation_transaction.get("refresh_command")
            or external_reconciliation.get("reconcile_command")
            or ""
        ),
        "reconciliation_transaction": reconciliation_transaction,
        **_structured_route_inputs(
            target_root=target_root,
            active_summary=active_summary,
            task_text=task_text,
            changed_paths=changed_paths,
            route_evidence={**route_evidence, "admitted_external_observation": external_reconciliation},
            planning_revision=planning_revision,
            proposal=reconciliation_proposal,
            path_classification=path_classification,
        ),
    }
    if external_reconciliation.get("status") in {"refresh-required", "reconciliation-required"}:
        route_evidence["status"] = str(external_reconciliation.get("reason_code") or "external-owner-currentness-required")
        route_evidence["owner_posture"] = (
            "externally-stale" if external_reconciliation.get("status") == "refresh-required" else "external-conflict"
        )
        route_evidence["required_transition"] = "reconcile"
    if reconciliation_transaction.get("status") == "preview-available":
        route_evidence["status"] = "target-authority-reconciliation-stale"
        route_evidence["owner_posture"] = "reconciliation-stale"
        route_evidence["required_transition"] = "reconcile"
    route_decision = _planning_route_decision_payload(
        route_evidence,
        planning_revision=planning_revision,
        reconciliation_proposal=reconciliation_proposal,
    )
    route_safety = _route_safety_outcome(route_decision)
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
    elif route_safety:
        status = str(route_safety["status"])
        decision = str(route_safety["decision"])
        reason = str(route_safety["reason"])
        required_next_action = str(route_safety["required_next_action"])
        workflow_sufficient = bool(route_safety["workflow_sufficient"])
    elif active_planning_present:
        status = "attention"
        decision = "planning-route-transition-required"
        reason = "The structured Planning route requires an explicit transition before ordinary work can continue."
        required_next_action = str(_as_dict(route_decision.get("next_safe_action")).get("action") or "inspect-current-task-scope")
        workflow_sufficient = False
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
    elif bounded_external_effect.get("status") == "direct-route-admitted":
        status = "clear"
        decision = "bounded-external-effect-direct"
        reason = (
            "The requested effect is a bounded external issue filing with repository, implementation, merge, and close "
            "effects excluded; its existing intake/write owner supplies duplicate, template, authority, and reconciliation safety."
        )
        required_next_action = "perform-bounded-external-issue-filing"
        workflow_sufficient = True
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
        "mutation-baseline-required",
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
                f"effect_class={bounded_external_effect.get('effect_class')}",
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
        "owner_admission": owner_admission,
        "active_plan_reliance": active_plan_reliance,
        "task_switch_reconciliation": _task_switch_fact_payload(route_evidence),
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
        "bounded_external_effect": bounded_external_effect,
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
                "an existing intended Planning owner can be selected or explicitly superseded without creating a new owner",
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
                    "stage": "preview-owner-reconciliation",
                    "command": retrofit_commands["claim"],
                    "purpose": "Identify and compare the existing intended owner without creating a new execution owner.",
                },
                {
                    "stage": "confirm-owner-selection",
                    "command": retrofit_commands["summary"],
                    "purpose": "Re-read Planning after explicit owner selection or supersession confirmation.",
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
            "safety_rule": "Mixed planning plus implementation changes still need an existing or explicitly superseded owner before broad completion claims.",
            "rule": "Use the reconciliation preview for already-started bounded work; do not create a new owner from inferred lane or slice text.",
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
