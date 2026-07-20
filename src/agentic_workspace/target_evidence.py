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


def _target_context(profile: DelegationTargetProfile | None) -> dict[str, Any]:
    if profile is None:
        return {
            "profile_status": "unprofiled",
            "capability_classes": [],
            "safe_task_classes": [],
            "forbidden_task_classes": [],
            "authority": "evidence-only",
        }
    return {
        "profile_status": "configured",
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
            normalized.append(
                {
                    "id": f"{target_name}:{record.task_class}:{record.recorded_at}:{index}",
                    "target": target_name,
                    "task_class": record.task_class,
                    "scope_class": record.task_class,
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
        target_records = records_by_target.get(target_name, [])
        scores = [_delegation_signal_score(record) for record in target_records]
        average = sum(scores) / len(scores) if scores else None
        if average is None:
            route_effect = "no-change"
            uncertainty = "sparse"
        elif average >= 0.75:
            route_effect = "preferred-for-matching-task-class"
            uncertainty = "low" if len(scores) >= 2 else "medium"
        elif average <= -0.5:
            route_effect = "strong-review-required"
            uncertainty = "medium"
        else:
            route_effect = "advisory-only"
            uncertainty = "medium"
        suitability.append(
            {
                "target": target_name,
                "profile_status": "configured" if profile is not None else "unprofiled",
                "record_count": len(target_records),
                "average_signal": round(average, 2) if average is not None else None,
                "route_effect": route_effect,
                "uncertainty": uncertainty,
                "supported_task_classes": sorted({record.task_class for record in target_records}),
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
        "admission": {
            "rejects": ["malformed records", "unscoped target", "unsupported outcome enums"],
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
    selected_target = current_target if current_target else None
    if policy_value == "local-preferred":
        decision = "keep-local"
    elif policy_value == "best-fit-advisory":
        decision = "advise-best-fit"
    elif not enforceable:
        decision = "blocked"
    elif recommendation in {"external-delegation", "manual-handoff", "stronger-reasoning"}:
        decision = "assign-or-escalate"
    else:
        decision = "assign-current-target"
    return {
        "kind": "agentic-workspace/assignment-decision/v1",
        "decision": decision,
        "assignment_policy": policy_value,
        "selected_target": selected_target,
        "runtime_recommendation": recommendation,
        "evidence_status": target_evidence.get("status", "unknown"),
        "record_count": target_evidence.get("record_count", 0),
        "claim_boundary": assignment_policy.get("binding", {}).get("claim_boundary", "assignment policy unresolved"),
        "rule": "Assignment decisions preserve policy, target evidence, and runtime suitability as separate inputs.",
    }
