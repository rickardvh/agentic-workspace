from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from agentic_workspace.config import (
    WORKSPACE_DELEGATION_OUTCOMES_PATH,
    DelegationOutcomeRecord,
    DelegationTargetProfile,
)


def _delegation_signal_score(record: DelegationOutcomeRecord) -> float:
    outcome_score = {"success": 1.0, "mixed": 0.0, "failed": -1.0}[record.outcome]
    handoff_score = {"sufficient": 0.25, "borderline": 0.0, "insufficient": -0.25}[record.handoff_sufficiency]
    review_score = {"light": 0.25, "normal": 0.0, "high": -0.25}[record.review_burden]
    escalation_score = -0.5 if record.escalation_required else 0.0
    return outcome_score + handoff_score + review_score + escalation_score


def _record_scope_class(record: DelegationOutcomeRecord) -> str:
    return record.task_class


def _context_key(*, task_class: str, scope_class: str | None = None) -> str:
    normalized_scope = (scope_class or task_class).strip() or task_class
    return f"{task_class.strip()}::{normalized_scope}"


def _target_record_id(*, target_name: str, record: DelegationOutcomeRecord, index: int) -> str:
    return f"{target_name}:{record.task_class}:{_record_scope_class(record)}:{record.recorded_at}:{index}"


def _target_context(profile: DelegationTargetProfile | None) -> dict[str, Any]:
    if profile is None:
        return {
            "profile_status": "unprofiled",
            "target_identity_ref": None,
            "target_revision": None,
            "revision_policy": None,
            "identity_status": "unprofiled",
            "capability_classes": [],
            "safe_task_classes": [],
            "forbidden_task_classes": [],
            "authority": "evidence-only",
        }
    return {
        "profile_status": "configured",
        "target_identity_ref": profile.target_id,
        "target_revision": profile.target_revision,
        "revision_policy": profile.revision_policy,
        "identity_status": profile.identity_status,
        "capability_classes": list(profile.capability_classes),
        "safe_task_classes": list(profile.safe_task_classes),
        "forbidden_task_classes": list(profile.forbidden_task_classes),
        "authority": "local-target-profile",
    }


def target_evidence_posture(
    *,
    target_root: Path | None,
    profiles: Iterable[DelegationTargetProfile],
    records: Iterable[DelegationOutcomeRecord],
) -> dict[str, Any]:
    profile_by_name = {profile.name: profile for profile in profiles}
    records_by_target: dict[str, list[DelegationOutcomeRecord]] = {}
    for record in records:
        records_by_target.setdefault(record.delegation_target, []).append(record)

    normalized: list[dict[str, Any]] = []
    for target_name in sorted(records_by_target):
        profile = profile_by_name.get(target_name)
        context = _target_context(profile)
        for index, record in enumerate(records_by_target[target_name]):
            scope_class = _record_scope_class(record)
            normalized.append(
                {
                    "id": _target_record_id(target_name=target_name, record=record, index=index),
                    "target": target_name,
                    "target_identity_ref": context["target_identity_ref"],
                    "target_revision": context["target_revision"],
                    "task_class": record.task_class,
                    "scope_class": scope_class,
                    "context_key": _context_key(task_class=record.task_class, scope_class=scope_class),
                    "outcome": record.outcome,
                    "handoff_sufficiency": record.handoff_sufficiency,
                    "review_burden": record.review_burden,
                    "escalation_required": record.escalation_required,
                    "recorded_at": record.recorded_at,
                    "authority": "local-outcome-ledger",
                    "confidence": "medium",
                    "admission_state": "accepted-normalized",
                    "source": {
                        "type": "local-json-ledger",
                        "ref": WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
                        "checked_in": False,
                    },
                    "routing_relevance": "task-class-bound",
                    "signal": _delegation_signal_score(record),
                    **context,
                }
            )

    suitability: list[dict[str, Any]] = []
    target_names = sorted(set(profile_by_name) | set(records_by_target))
    for target_name in target_names:
        profile = profile_by_name.get(target_name)
        context = _target_context(profile)
        target_records = records_by_target.get(target_name, [])
        if not target_records:
            suitability.append(
                {
                    "target": target_name,
                    "target_identity_ref": context["target_identity_ref"],
                    "target_revision": context["target_revision"],
                    "revision_policy": context["revision_policy"],
                    "context_key": None,
                    "task_class": None,
                    "scope_class": None,
                    "profile_status": "configured" if profile is not None else "unprofiled",
                    "record_count": 0,
                    "average_signal": None,
                    "route_effect": "no-change",
                    "uncertainty": "sparse",
                    "supporting_record_ids": [],
                    "supported_task_classes": [],
                    "irrelevance_rule": "Only records for matching task/scope classes may affect assignment for that class.",
                    "raw_history_retention": "bounded-local-ledger",
                }
            )
            continue
        records_by_context: dict[str, list[tuple[int, DelegationOutcomeRecord]]] = {}
        for index, record in enumerate(target_records):
            records_by_context.setdefault(_context_key(task_class=record.task_class, scope_class=_record_scope_class(record)), []).append(
                (index, record)
            )
        for context_key in sorted(records_by_context):
            indexed_scoped_records = records_by_context[context_key]
            scoped_records = [record for _, record in indexed_scoped_records]
            scores = [_delegation_signal_score(record) for record in scoped_records]
            average = sum(scores) / len(scores)
            if average >= 0.75:
                route_effect = "preferred-for-matching-task-class"
                uncertainty = "low" if len(scores) >= 2 else "medium"
            elif average <= -0.5:
                route_effect = "strong-review-required"
                uncertainty = "medium"
            else:
                route_effect = "advisory-only"
                uncertainty = "medium"
            first = scoped_records[0]
            suitability.append(
                {
                    "target": target_name,
                    "target_identity_ref": context["target_identity_ref"],
                    "target_revision": context["target_revision"],
                    "revision_policy": context["revision_policy"],
                    "context_key": context_key,
                    "task_class": first.task_class,
                    "scope_class": _record_scope_class(first),
                    "profile_status": "configured" if profile is not None else "unprofiled",
                    "record_count": len(scoped_records),
                    "average_signal": round(average, 2),
                    "route_effect": route_effect,
                    "uncertainty": uncertainty,
                    "supporting_record_ids": [
                        _target_record_id(target_name=target_name, record=record, index=index)
                        for index, record in indexed_scoped_records[:5]
                    ],
                    "supported_task_classes": sorted({record.task_class for record in scoped_records}),
                    "irrelevance_rule": "Only records for matching task/scope classes may affect assignment for that class.",
                    "raw_history_retention": "bounded-local-ledger",
                }
            )

    storage_path = WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix()
    return {
        "kind": "agentic-workspace/target-outcome-evidence-posture/v1",
        "status": "present" if normalized else "no-local-evidence",
        "storage": {
            "path": storage_path,
            "location": "local-only",
            "checked_in": False,
            "exists": (target_root / WORKSPACE_DELEGATION_OUTCOMES_PATH).exists() if target_root is not None else False,
            "safe_to_remove": True,
            "raw_transcripts_stored": False,
        },
        "record_count": len(normalized),
        "normalized_records": normalized[:20],
        "omitted_record_count": max(0, len(normalized) - 20),
        "suitability": suitability,
        "lifecycle": {
            "kind": "agentic-workspace/target-outcome-evidence-lifecycle/v1",
            "public_operations": [
                {
                    "operation": "submit",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --outcome <success|mixed|failed> --handoff-sufficiency <sufficient|borderline|insufficient> --review-burden <light|normal|high> --format json",
                    "admission": "normalizes scoped local outcome evidence before routing uses it",
                },
                {
                    "operation": "query",
                    "command": "agentic-workspace config --target . --select mixed_agent.target_evidence --format json",
                    "admission": "returns bounded accepted evidence, contextual suitability, and exact supporting records",
                },
                {
                    "operation": "correct-or-dispute",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --outcome <mixed|failed> --review-burden high --escalation-required --format json",
                    "admission": "records a scoped counter-signal; assignment consumes only matching task/scope records",
                },
                {
                    "operation": "supersede",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --outcome <success|mixed|failed> --format json",
                    "admission": "records newer scoped evidence without deleting older audit history; recency policy remains explicit",
                },
                {
                    "operation": "prune-or-compact",
                    "command": "agentic-workspace config --target . --select mixed_agent.target_evidence.storage --format json",
                    "admission": "raw local ledger is safe to remove; compact retained signals must preserve target/context ids",
                },
            ],
            "admission_rejections": [
                "malformed records",
                "duplicate target/task/date evidence without a distinct outcome signal",
                "ambiguous or unscoped target",
                "unsupported outcome enums",
                "records lacking task/scope context",
            ],
            "routing_rule": "Assignment may consume only accepted evidence matching the requested task/scope context.",
        },
        "admission": {
            "rejects": [
                "malformed records",
                "duplicate target/task/date evidence without a distinct outcome signal",
                "unscoped target",
                "unsupported outcome enums",
            ],
            "source": "config.load_delegation_outcomes",
        },
        "authority_order": [
            "explicit human policy",
            "repo-owned proof and ownership boundaries",
            "normalized local target evidence",
            "target profile estimates",
            "model self-assessment",
        ],
    }


def assignment_decision_from_policy(
    *, assignment_policy: dict[str, Any], runtime_resolution: dict[str, Any], target_evidence: dict[str, Any]
) -> dict[str, Any]:
    policy_value = str(assignment_policy.get("assignment_policy", {}).get("value") or "local-preferred")
    current_target = str(assignment_policy.get("current_target", {}).get("value") or "")
    recommendation = str(runtime_resolution.get("recommendation") or "stay-local")
    enforceable = bool(assignment_policy.get("binding", {}).get("enforceable", False))
    profile_recommendations = [item for item in runtime_resolution.get("profile_recommendations", []) if isinstance(item, dict)]
    suitability = [item for item in target_evidence.get("suitability", []) if isinstance(item, dict)]
    capability_context = runtime_resolution.get("capability_context", {})
    requested_task_class = str(capability_context.get("task_class") or "").strip() if isinstance(capability_context, dict) else ""
    requested_scope_class = (
        str(capability_context.get("scope_class") or requested_task_class).strip()
        if isinstance(capability_context, dict)
        else requested_task_class
    )
    requested_context_key = _context_key(task_class=requested_task_class, scope_class=requested_scope_class) if requested_task_class else ""
    evidence_by_target: dict[str, list[dict[str, Any]]] = {}
    for item in suitability:
        target = str(item.get("target") or "")
        context_key = str(item.get("context_key") or "")
        if requested_context_key and context_key != requested_context_key:
            continue
        if target:
            evidence_by_target.setdefault(target, []).append(item)

    candidate_scores: list[dict[str, Any]] = []
    hard_reject_actions = {"escalate-before-execution"}
    recommendation_score = {"recommended": 40, "acceptable": 20, "poor-fit": -30}
    evidence_score = {
        "preferred-for-matching-task-class": 15,
        "advisory-only": 3,
        "no-change": 0,
        "strong-review-required": -20,
    }
    for profile in profile_recommendations:
        target = str(profile.get("name") or "")
        if not target:
            continue
        target_identity_ref = str(profile.get("target_id") or "")
        target_revision = str(profile.get("target_revision") or "")
        revision_policy = str(profile.get("revision_policy") or "")
        required_action = str(profile.get("required_action") or "")
        eligible = not bool(profile.get("capability_mismatch")) and required_action not in hard_reject_actions
        score = int(profile.get("score") or 0) + recommendation_score.get(str(profile.get("recommendation") or ""), 0)
        matching_evidence = evidence_by_target.get(target, [])
        for evidence in matching_evidence:
            score += evidence_score.get(str(evidence.get("route_effect") or ""), 0)
        if target == current_target:
            score += 5
        candidate_scores.append(
            {
                "target": target,
                "target_identity_ref": target_identity_ref or None,
                "target_revision": target_revision or None,
                "revision_policy": revision_policy or None,
                "eligible": eligible,
                "score": score,
                "runtime_recommendation": profile.get("recommendation"),
                "required_action": required_action or "none",
                "evidence_contexts": [
                    {
                        "context_key": evidence.get("context_key"),
                        "target_identity_ref": evidence.get("target_identity_ref"),
                        "target_revision": evidence.get("target_revision"),
                        "route_effect": evidence.get("route_effect"),
                        "record_count": evidence.get("record_count"),
                        "supporting_record_ids": evidence.get("supporting_record_ids", []),
                    }
                    for evidence in matching_evidence
                ],
            }
        )
    eligible_candidates = [item for item in candidate_scores if item["eligible"]]
    eligible_candidates.sort(key=lambda item: (-int(item["score"]), str(item["target"])))
    selected_target = eligible_candidates[0]["target"] if eligible_candidates else (current_target or None)
    if policy_value == "local-preferred":
        decision = "keep-local"
    elif policy_value == "best-fit-advisory":
        decision = "advise-best-fit"
    elif not enforceable:
        decision = "blocked"
        selected_target = current_target or None
    elif not eligible_candidates:
        decision = "no-safe-route"
        selected_target = None
    elif recommendation in {"external-delegation", "manual-handoff", "stronger-reasoning"}:
        decision = "assign-or-escalate"
    else:
        decision = "assign-best-fit" if selected_target != current_target else "assign-current-target"
    return {
        "kind": "agentic-workspace/assignment-decision/v1",
        "decision": decision,
        "assignment_policy": policy_value,
        "selected_target": selected_target,
        "current_target": current_target or None,
        "candidate_scores": candidate_scores,
        "selection_basis": {
            "hard_eligibility_first": True,
            "uses_runtime_candidate_comparison": bool(profile_recommendations),
            "uses_contextual_evidence": bool(suitability),
            "requested_context_key": requested_context_key or None,
            "tie_breaker": "highest score, then stable target identity/name",
        },
        "runtime_recommendation": recommendation,
        "evidence_status": target_evidence.get("status", "unknown"),
        "record_count": target_evidence.get("record_count", 0),
        "claim_boundary": assignment_policy.get("binding", {}).get("claim_boundary", "assignment policy unresolved"),
        "rule": "Assignment decisions preserve policy, contextual target evidence, and runtime suitability as separate inputs; learned evidence cannot override hard policy or capability prohibitions.",
    }
