from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from agentic_workspace.config import (
    WORKSPACE_DELEGATION_OUTCOMES_PATH,
    DelegationOutcomeRecord,
    DelegationTargetProfile,
)

CURRENT_ADMISSION_STATES = {"accepted", "accepted-normalized", "recovered", "compacted-summary"}
ROUTABLE_AUTHORITIES = {"aw-proof", "human-review", "local-outcome-ledger"}
ROUTABLE_CONFIDENCE = {"high", "medium"}
INACTIVE_ADMISSION_STATES = {"disputed", "superseded", "stale", "compacted-raw", "rejected"}
ROUTABLE_RECORD_MAX_AGE_DAYS = 180
ASSIGNMENT_OUTCOME_MATRIX = [
    "retain-local",
    "read-only-exploration",
    "delegated-implementation",
    "delegated-validation",
    "planning-review-escalation",
    "manual-strong-agent-handoff",
    "no-safe-route",
]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _profile_identity_keys(profile: DelegationTargetProfile) -> set[str]:
    return {key for key in (profile.target_id, profile.name, *profile.aliases) if key}


def _canonical_target_key(profile: DelegationTargetProfile | None, fallback: str) -> str:
    return profile.target_id or profile.name if profile is not None else fallback


def _delegation_signal_score(record: DelegationOutcomeRecord) -> float:
    outcome_score = {"success": 1.0, "mixed": 0.0, "failed": -1.0}[record.outcome]
    handoff_score = {"sufficient": 0.25, "borderline": 0.0, "insufficient": -0.25}[record.handoff_sufficiency]
    review_score = {"light": 0.25, "normal": 0.0, "high": -0.25}[record.review_burden]
    escalation_score = -0.5 if record.escalation_required else 0.0
    return outcome_score + handoff_score + review_score + escalation_score


def _record_scope_class(record: DelegationOutcomeRecord) -> str:
    return record.scope_class or record.task_class


def _context_key(*, task_class: str, scope_class: str | None = None) -> str:
    normalized_scope = (scope_class or task_class).strip() or task_class
    return f"{task_class.strip()}::{normalized_scope}"


def _target_record_id(*, target_name: str, record: DelegationOutcomeRecord, index: int) -> str:
    if record.record_id:
        return record.record_id
    return f"{target_name}:{record.task_class}:{_record_scope_class(record)}:{record.recorded_at}:{index}"


def _record_identity(record: DelegationOutcomeRecord, index: int) -> str:
    return record.record_id or f"{record.delegation_target}:{record.task_class}:{record.scope_class}:{record.recorded_at}:{index}"


def _record_routable(record: DelegationOutcomeRecord) -> bool:
    if record.admission_state not in CURRENT_ADMISSION_STATES:
        return False
    if record.authority not in ROUTABLE_AUTHORITIES:
        return False
    if record.confidence not in ROUTABLE_CONFIDENCE:
        return False
    if record.contradiction_state in {"contradicted", "disputed"}:
        return False
    if _record_is_stale(record):
        return False
    return True


def _record_age_days(record: DelegationOutcomeRecord) -> int | None:
    try:
        return (date.today() - date.fromisoformat(record.recorded_at[:10])).days
    except (TypeError, ValueError):
        return None


def _record_is_stale(record: DelegationOutcomeRecord) -> bool:
    age_days = _record_age_days(record)
    return age_days is None or age_days > ROUTABLE_RECORD_MAX_AGE_DAYS


def _record_uncertainty_reasons(record: DelegationOutcomeRecord) -> list[str]:
    reasons: list[str] = []
    if record.admission_state in INACTIVE_ADMISSION_STATES:
        reasons.append(f"inactive:{record.admission_state}")
    elif record.admission_state not in CURRENT_ADMISSION_STATES:
        reasons.append(f"not-current:{record.admission_state}")
    if record.authority not in ROUTABLE_AUTHORITIES:
        reasons.append(f"low-authority:{record.authority}")
    if record.confidence not in ROUTABLE_CONFIDENCE:
        reasons.append(f"low-confidence:{record.confidence}")
    if record.contradiction_state in {"contradicted", "disputed"}:
        reasons.append(f"contradiction:{record.contradiction_state}")
    if record.uncertainty_state not in {"none", ""}:
        reasons.append(f"uncertainty:{record.uncertainty_state}")
    if record.scope_drift:
        reasons.append("scope-drift")
    age_days = _record_age_days(record)
    if age_days is None:
        reasons.append("invalid-recorded-at")
    elif age_days > ROUTABLE_RECORD_MAX_AGE_DAYS:
        reasons.append(f"stale:{age_days}d")
    return reasons


def _record_complexity_burden_reasons(record: DelegationOutcomeRecord) -> list[str]:
    reasons: list[str] = []
    if record.review_burden == "high":
        reasons.append("review-burden:high")
    if record.repair_burden in {"high", "required", "repeated"}:
        reasons.append(f"repair-burden:{record.repair_burden}")
    if record.retry_burden in {"required", "repeated", "high"}:
        reasons.append(f"retry-burden:{record.retry_burden}")
    if record.restart_burden in {"required", "repeated", "high"}:
        reasons.append(f"restart-burden:{record.restart_burden}")
    if record.escalation_required:
        reasons.append("escalation-required")
    if record.handoff_burden in {"insufficient", "high", "repeated"}:
        reasons.append(f"handoff-burden:{record.handoff_burden}")
    return reasons


def _context_cost_penalty(context_cost: dict[str, Any]) -> int:
    penalty = 0
    effective_input = context_cost.get("effective_input_tokens")
    if isinstance(effective_input, int) and not isinstance(effective_input, bool):
        penalty -= 30 if effective_input >= 50_000 else 20 if effective_input >= 20_000 else 10 if effective_input >= 8_000 else 0
    output_tokens = context_cost.get("output_tokens")
    if isinstance(output_tokens, int) and not isinstance(output_tokens, bool) and output_tokens >= 8_000:
        penalty -= 5
    elapsed_ms = context_cost.get("elapsed_ms")
    if isinstance(elapsed_ms, int) and not isinstance(elapsed_ms, bool) and elapsed_ms >= 600_000:
        penalty -= 5
    for field, unit, cap in (
        ("orientation_command_count", 2, 10),
        ("retry_count", 5, 15),
        ("repair_loop_count", 5, 15),
    ):
        value = context_cost.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            penalty -= min(cap, value * unit)
    return penalty


def _transport_cost_summaries(records: list[DelegationOutcomeRecord]) -> list[dict[str, Any]]:
    by_transport: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        context_cost = record.context_cost if isinstance(record.context_cost, dict) else {}
        transport = str(context_cost.get("transport") or "").strip()
        if transport:
            by_transport.setdefault(transport, []).append(context_cost)
    summaries: list[dict[str, Any]] = []
    for transport in sorted(by_transport):
        costs = by_transport[transport]
        penalties = [_context_cost_penalty(cost) for cost in costs]
        observed_context_cost = {
            field: round(
                sum(int(cost[field]) for cost in costs if isinstance(cost.get(field), int) and not isinstance(cost.get(field), bool))
                / sum(1 for cost in costs if isinstance(cost.get(field), int) and not isinstance(cost.get(field), bool))
            )
            for field in (
                "assignment_packet_bytes",
                "rendered_prompt_bytes",
                "effective_input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "elapsed_ms",
            )
            if any(isinstance(cost.get(field), int) and not isinstance(cost.get(field), bool) for cost in costs)
        }
        observable_fields = sorted(
            {
                field
                for cost in costs
                for field in (
                    "effective_input_tokens",
                    "cached_input_tokens",
                    "output_tokens",
                    "orientation_command_count",
                    "retry_count",
                    "repair_loop_count",
                )
                if cost.get(field) is not None
            }
        )
        summaries.append(
            {
                "transport": transport,
                "record_count": len(costs),
                "expected_burden_component": round(sum(penalties) / len(penalties)),
                "observed_context_cost": observed_context_cost,
                "observable_fields": observable_fields,
                "unknown_metric_state": "partial-or-unobserved" if any(cost.get("unknown_fields") for cost in costs) else "observed",
                "supporting_adapter_revisions": sorted(
                    {str(cost.get("adapter_revision") or "") for cost in costs if str(cost.get("adapter_revision") or "")}
                ),
            }
        )
    return summaries


def _complexity_reduction_signal(records_by_target: dict[str, list[DelegationOutcomeRecord]]) -> dict[str, Any]:
    repeated_contexts: list[dict[str, Any]] = []
    for target_name in sorted(records_by_target):
        records_by_context: dict[str, list[tuple[int, DelegationOutcomeRecord, list[str]]]] = {}
        for index, record in enumerate(records_by_target[target_name]):
            if record.admission_state not in CURRENT_ADMISSION_STATES:
                continue
            reasons = _record_complexity_burden_reasons(record)
            if not reasons:
                continue
            context_key = _context_key(task_class=record.task_class, scope_class=_record_scope_class(record))
            records_by_context.setdefault(context_key, []).append((index, record, reasons))
        for context_key in sorted(records_by_context):
            burdened = records_by_context[context_key]
            if len(burdened) < 2:
                continue
            repeated_contexts.append(
                {
                    "target": target_name,
                    "context_key": context_key,
                    "burden_record_count": len(burdened),
                    "supporting_record_ids": [
                        _target_record_id(target_name=target_name, record=record, index=index) for index, record, _ in burdened[:5]
                    ],
                    "burden_reasons": sorted({reason for _, _, reasons in burdened for reason in reasons}),
                    "threshold": "two-or-more-current-admitted-burden-records-for-same-context",
                }
            )
    return {
        "status": "available" if repeated_contexts else "not-observed",
        "repeated_context_count": len(repeated_contexts),
        "contexts": repeated_contexts[:10],
        "omitted_context_count": max(0, len(repeated_contexts) - 10),
        "rule": (
            "Product simplification signals require repeated admitted repair, retry, escalation, restart, "
            "handoff, or high-review burden in the same target/task/scope context; ledger compaction alone is not a complexity signal."
        ),
    }


def _currently_admitted_records(records: list[tuple[int, DelegationOutcomeRecord]]) -> list[tuple[int, DelegationOutcomeRecord]]:
    """Return records assignment may consume after lifecycle transitions are applied."""

    superseded_ids = {
        record.predecessor_id
        for _, record in records
        if record.operation in {"supersede", "correct-or-dispute", "prune-or-compact"} and record.predecessor_id
    }
    inactive_state_ids = {
        _record_identity(record, index) for index, record in records if record.admission_state in INACTIVE_ADMISSION_STATES
    }
    inactive_ids = superseded_ids | inactive_state_ids
    admitted: list[tuple[int, DelegationOutcomeRecord]] = []
    for index, record in records:
        record_id = _record_identity(record, index)
        if record_id in inactive_ids:
            continue
        if not _record_routable(record):
            continue
        admitted.append((index, record))
    return admitted


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
    profile_list = list(profiles)
    profile_by_name = {profile.name: profile for profile in profile_list}
    all_records = list(records)
    profile_by_identity: dict[str, DelegationTargetProfile | None] = {}
    ambiguous_identities: set[str] = set()
    for profile in profile_list:
        for identity in _profile_identity_keys(profile):
            if identity in profile_by_identity and profile_by_identity[identity] is not profile:
                ambiguous_identities.add(identity)
                profile_by_identity[identity] = None
            else:
                profile_by_identity[identity] = profile
    records_by_target: dict[str, list[DelegationOutcomeRecord]] = {}
    canonical_profile_by_target: dict[str, DelegationTargetProfile | None] = {}
    for record in all_records:
        profile = profile_by_identity.get(record.delegation_target)
        canonical_target = (
            record.delegation_target
            if record.delegation_target in ambiguous_identities
            else _canonical_target_key(profile, record.delegation_target)
        )
        records_by_target.setdefault(canonical_target, []).append(record)
        canonical_profile_by_target[canonical_target] = profile

    normalized: list[dict[str, Any]] = []
    for target_name in sorted(records_by_target):
        profile = canonical_profile_by_target.get(target_name) or profile_by_name.get(target_name)
        context = _target_context(profile)
        for index, record in enumerate(records_by_target[target_name]):
            scope_class = _record_scope_class(record)
            normalized.append(
                {
                    "id": _target_record_id(target_name=target_name, record=record, index=index),
                    "target": target_name,
                    "target_input_ref": record.delegation_target,
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
                    "operation": record.operation,
                    "predecessor_id": record.predecessor_id or None,
                    "authority": record.authority,
                    "confidence": record.confidence,
                    "admission_state": record.admission_state,
                    "provenance": {
                        "source_type": record.source_type,
                        "source_ref": record.source_ref or WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
                        "producer_class": record.producer_class,
                        "idempotency_key": record.idempotency_key or None,
                    },
                    "route_observations": {
                        "route_outcome": record.route_outcome or None,
                        "assignment_route": record.assignment_route or None,
                        "proof": record.proof_observation or None,
                        "review": record.review_observation or None,
                    },
                    "burden": {
                        "handoff": record.handoff_burden or None,
                        "repair": record.repair_burden or None,
                        "retry": record.retry_burden or None,
                        "restart": record.restart_burden or None,
                        "expected": record.expected_burden or None,
                        "observed": record.observed_burden or None,
                    },
                    "context_cost": record.context_cost,
                    "lifecycle_state": {
                        "scope_drift": record.scope_drift,
                        "contradiction": record.contradiction_state,
                        "uncertainty": record.uncertainty_state,
                    },
                    "admission": {
                        "routable": _record_routable(record),
                        "authority": record.authority,
                        "confidence": record.confidence,
                        "state": record.admission_state,
                    },
                    "source": {
                        "type": record.source_type or "local-json-ledger",
                        "ref": record.source_ref or WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
                        "checked_in": False,
                    },
                    "routing_relevance": "task-and-scope-bound",
                    "signal": _delegation_signal_score(record),
                    **context,
                }
            )

    uncertainty_accounts: list[dict[str, Any]] = []
    for target_name in sorted(records_by_target):
        target_records = records_by_target.get(target_name, [])
        for index, record in enumerate(target_records):
            reasons = _record_uncertainty_reasons(record)
            if not reasons:
                continue
            scope_class = _record_scope_class(record)
            uncertainty_accounts.append(
                {
                    "target": target_name,
                    "context_key": _context_key(task_class=record.task_class, scope_class=scope_class),
                    "record_id": _target_record_id(target_name=target_name, record=record, index=index),
                    "outcome": record.outcome,
                    "signal": _delegation_signal_score(record),
                    "uncertainty_reasons": reasons,
                    "routable": False,
                    "routing_effect": "visible-uncertainty-only",
                }
            )

    suitability: list[dict[str, Any]] = []
    target_names = sorted({_canonical_target_key(profile, profile.name) for profile in profile_list} | set(records_by_target))
    for target_name in target_names:
        profile = canonical_profile_by_target.get(target_name) or next(
            (candidate for candidate in profile_list if _canonical_target_key(candidate, candidate.name) == target_name),
            None,
        )
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
                    "transport_costs": [],
                }
            )
            continue
        records_by_context: dict[str, list[tuple[int, DelegationOutcomeRecord]]] = {}
        for index, record in enumerate(target_records):
            records_by_context.setdefault(_context_key(task_class=record.task_class, scope_class=_record_scope_class(record)), []).append(
                (index, record)
            )
        for context_key in sorted(records_by_context):
            indexed_scoped_records = _currently_admitted_records(records_by_context[context_key])
            if not indexed_scoped_records:
                continue
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
                    "raw_history_retention": "bounded-local-ledger-with-lifecycle-transitions",
                    "transport_costs": _transport_cost_summaries(scoped_records),
                    "retention": {
                        "status": "bounded-current-calibration",
                        "current_records": len(scoped_records),
                        "raw_history_rule": "Superseded, disputed, stale, and compacted raw records are excluded from routing; compact summaries remain routable only with lineage/provenance.",
                    },
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
            "retention_rule": "bounded by lifecycle transitions; prune-or-compact records replace raw predecessors with provenance-preserving calibration summaries",
        },
        "record_count": len(normalized),
        "normalized_records": normalized[:20],
        "omitted_record_count": max(0, len(normalized) - 20),
        "suitability": suitability,
        "uncertainty_accounts": uncertainty_accounts[:20],
        "omitted_uncertainty_account_count": max(0, len(uncertainty_accounts) - 20),
        "complexity_reduction_signal": _complexity_reduction_signal(records_by_target),
        "lifecycle": {
            "kind": "agentic-workspace/target-outcome-evidence-lifecycle/v1",
            "public_operations": [
                {
                    "operation": "submit",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --scope-class <scope> --operation submit --outcome <success|mixed|failed> --handoff-sufficiency <sufficient|borderline|insufficient> --review-burden <light|normal|high> --format json",
                    "admission": "public local submissions may not self-promote to aw-proof or human-review; high-authority evidence must come from a trusted internal producer receipt",
                },
                {
                    "operation": "query",
                    "command": "agentic-workspace config --target . --select mixed_agent.target_evidence --format json",
                    "admission": "returns bounded accepted evidence, contextual suitability, and exact supporting records",
                },
                {
                    "operation": "correct-or-dispute",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --scope-class <scope> --operation correct-or-dispute --predecessor-id <record-id> --outcome <mixed|failed> --review-burden high --escalation-required --format json",
                    "admission": "links to an existing record id and removes the disputed predecessor from current routing consumption",
                },
                {
                    "operation": "supersede",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --scope-class <scope> --operation supersede --predecessor-id <record-id> --outcome <success|mixed|failed> --format json",
                    "admission": "links to an existing predecessor and makes only the superseding record current for matching task/scope routing",
                },
                {
                    "operation": "prune-or-compact",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --scope-class <scope> --operation prune-or-compact --predecessor-id <record-id> --outcome mixed --format json",
                    "admission": "replaces bounded raw predecessors with a compact current calibration summary preserving target/task/scope ids, source lineage, uncertainty, and predecessor provenance",
                },
            ],
            "admission_rejections": [
                "malformed records",
                "duplicate target/task/scope/date evidence without a lifecycle predecessor",
                "ambiguous or unscoped target",
                "unsupported outcome enums",
                "records lacking task/scope context",
                "transition records without an existing predecessor id",
            ],
            "routing_rule": "Assignment may consume only current, admitted, non-contradicted evidence matching the requested target/task/scope context.",
        },
        "admission": {
            "rejects": [
                "malformed records",
                "duplicate target/task/scope/provenance evidence without a lifecycle predecessor",
                "low-confidence or untrusted-authority records before routing",
                "unscoped target",
                "unscoped task/scope context",
                "unsupported outcome enums",
                "unknown predecessor transition",
                "cross-context predecessor transition",
                "stale, contradicted, or already transitioned predecessor",
            ],
            "source": "config.load_delegation_outcomes",
            "producer_boundary": "AW-owned producers may record proof/review/retry/closeout observations only when those semantics come from the corresponding proof, review, or lifecycle owner; local notes remain advisory evidence.",
        },
        "authority_order": [
            "explicit human policy",
            "repo-owned proof and ownership boundaries",
            "normalized local target evidence",
            "target profile estimates",
            "model self-assessment",
        ],
        "assignment_outcome_matrix": ASSIGNMENT_OUTCOME_MATRIX,
    }


def assignment_decision_from_policy(
    *,
    assignment_policy: dict[str, Any],
    runtime_resolution: dict[str, Any],
    target_evidence: dict[str, Any],
    human_intent: str = "",
) -> dict[str, Any]:
    policy_value = str(assignment_policy.get("assignment_policy", {}).get("value") or "local-preferred")
    current_target = str(assignment_policy.get("current_target", {}).get("value") or "")
    manual_transport_policy = str(assignment_policy.get("manual_transport_policy", {}).get("value") or "allowed")
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
        if not requested_context_key or context_key != requested_context_key:
            continue
        if target:
            evidence_by_target.setdefault(target, []).append(item)
    uncertainty_by_target: dict[str, list[dict[str, Any]]] = {}
    for item in target_evidence.get("uncertainty_accounts", []):
        if not isinstance(item, dict):
            continue
        target = str(item.get("target") or "")
        context_key = str(item.get("context_key") or "")
        if not requested_context_key or context_key != requested_context_key:
            continue
        if target:
            uncertainty_by_target.setdefault(target, []).append(item)

    candidate_scores: list[dict[str, Any]] = []
    hard_reject_actions = {"escalate-before-execution"}
    recommendation_score = {"recommended": 40, "acceptable": 20, "poor-fit": -30}
    target_cost_score = {"cheap": 10, "standard": 0, "premium": -10, "unknown": 0}
    target_latency_score = {"fast": 5, "standard": 0, "slow": -5, "unknown": 0}
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
        target_identity_ref = str(profile.get("target_id") or target)
        target_revision = str(profile.get("target_revision") or "")
        revision_policy = str(profile.get("revision_policy") or "")
        target_aliases = {str(alias) for alias in profile.get("aliases", [])} if isinstance(profile.get("aliases"), list) else set()
        current_target_matches_profile = current_target in ({target, target_identity_ref} | target_aliases)
        required_action = str(profile.get("required_action") or "")
        location = str(profile.get("location") or "")
        execution_methods = [str(item) for item in profile.get("execution_methods", []) if str(item).strip()]
        human_control_modes = [str(item) for item in profile.get("human_control_modes", []) if str(item).strip()]
        proof_requirements = [str(item) for item in profile.get("proof_requirements", []) if str(item).strip()]
        hard_rejection_reasons: list[str] = []
        if bool(profile.get("capability_mismatch")):
            hard_rejection_reasons.append("capability-mismatch")
        if required_action in hard_reject_actions:
            hard_rejection_reasons.append(required_action)
        if not execution_methods:
            hard_rejection_reasons.append("missing-execution-method")
        if location == "external" and not any(method in {"cli", "api", "manual"} for method in execution_methods):
            hard_rejection_reasons.append("external-transport-unavailable")
        if location == "external" and set(execution_methods) == {"manual"} and manual_transport_policy == "disabled":
            hard_rejection_reasons.append("manual-transport-disabled")
        if location == "external" and "manual" in execution_methods and manual_transport_policy == "required-when-no-automatic-method":
            if not any(method in {"cli", "api"} for method in execution_methods):
                required_action = "manual-handoff-required"
        if "off" in human_control_modes:
            hard_rejection_reasons.append("human-control-forbids-delegation")
        if "required-proof-missing" in proof_requirements:
            hard_rejection_reasons.append("required-proof-missing")
        eligible = not hard_rejection_reasons
        declared_fit_score = int(profile.get("score") or 0)
        recommendation_component = recommendation_score.get(str(profile.get("recommendation") or ""), 0)
        cost_class = str(profile.get("cost_class") or "unknown")
        latency_class = str(profile.get("latency_class") or "unknown")
        target_cost_component = target_cost_score.get(cost_class, 0)
        target_latency_component = target_latency_score.get(latency_class, 0)
        contextual_evidence_component = 0
        matching_evidence = evidence_by_target.get(target_identity_ref, []) or evidence_by_target.get(target, [])
        for evidence in matching_evidence:
            contextual_evidence_component += evidence_score.get(str(evidence.get("route_effect") or ""), 0)
        current_target_component = 5 if current_target_matches_profile else 0
        transport_options: list[dict[str, Any]] = []
        for method_index, method in enumerate(execution_methods):
            matching_transport_costs = [
                cost
                for evidence in matching_evidence
                for cost in evidence.get("transport_costs", [])
                if isinstance(cost, dict) and str(cost.get("transport") or "") == method
            ]
            transport_option: dict[str, Any] = {
                "transport": method,
                "expected_burden": round(
                    sum(int(cost.get("expected_burden_component") or 0) for cost in matching_transport_costs)
                    / len(matching_transport_costs)
                )
                if matching_transport_costs
                else 0,
                "evidence_state": "admitted-contextual" if matching_transport_costs else "unknown",
                "record_count": sum(int(cost.get("record_count") or 0) for cost in matching_transport_costs),
                "configured_order": method_index,
            }
            observed_fields = {field for cost in matching_transport_costs for field in _as_dict(cost.get("observed_context_cost"))}
            observed_context_cost = {}
            for field in sorted(observed_fields):
                weighted_values = [
                    (int(_as_dict(cost.get("observed_context_cost"))[field]), max(1, int(cost.get("record_count") or 1)))
                    for cost in matching_transport_costs
                    if isinstance(_as_dict(cost.get("observed_context_cost")).get(field), int)
                ]
                if weighted_values:
                    observed_context_cost[field] = round(
                        sum(value * weight for value, weight in weighted_values) / sum(weight for _, weight in weighted_values)
                    )
            if observed_context_cost:
                transport_option["observed_context_cost"] = observed_context_cost
            transport_options.append(transport_option)
        selected_transport_option = (
            max(transport_options, key=lambda item: (int(item["expected_burden"]), -int(item["configured_order"])))
            if transport_options
            else {}
        )
        selected_transport = str(selected_transport_option.get("transport") or "")
        transport_burden_component = int(selected_transport_option.get("expected_burden") or 0)
        burden_component = transport_burden_component + target_cost_component + target_latency_component
        for evidence in matching_evidence:
            if evidence.get("route_effect") == "strong-review-required":
                burden_component -= 10
            if evidence.get("uncertainty") == "low":
                burden_component += 2
        matching_uncertainty = uncertainty_by_target.get(target_identity_ref, []) or uncertainty_by_target.get(target, [])
        uncertainty_component = -5 * len(matching_uncertainty)
        probe_value_component = 5 if not matching_evidence and eligible else 0
        score = (
            declared_fit_score
            + recommendation_component
            + contextual_evidence_component
            + current_target_component
            + burden_component
            + uncertainty_component
            + probe_value_component
        )
        task_is_validation = requested_task_class in {"validation", "review", "proof"} or requested_scope_class in {
            "validation",
            "review",
            "proof",
        }
        continuation = (
            "manual-handoff"
            if required_action == "manual-handoff-required"
            else "delegated-validation"
            if eligible and task_is_validation
            else "delegated-implementation"
            if eligible
            else "not-executable"
        )
        candidate_scores.append(
            {
                "target": target,
                "target_identity_ref": target_identity_ref or None,
                "target_revision": target_revision or None,
                "aliases": sorted(target_aliases),
                "revision_policy": revision_policy or None,
                "eligible": eligible,
                "hard_rejection_reasons": hard_rejection_reasons,
                "eligibility": {
                    "capability": "rejected" if "capability-mismatch" in hard_rejection_reasons else "eligible",
                    "execution_transport": "rejected"
                    if any(reason in hard_rejection_reasons for reason in ["missing-execution-method", "external-transport-unavailable"])
                    else "eligible",
                    "manual_transport": "rejected" if "manual-transport-disabled" in hard_rejection_reasons else "eligible",
                    "proof": "rejected" if "required-proof-missing" in hard_rejection_reasons else "eligible",
                    "human_control": "rejected" if "human-control-forbids-delegation" in hard_rejection_reasons else "eligible",
                    "reason": hard_rejection_reasons,
                },
                "score": score,
                "ranking_components": {
                    "declared_fit": declared_fit_score,
                    "runtime_recommendation": recommendation_component,
                    "contextual_evidence": contextual_evidence_component,
                    "current_target_retention": current_target_component,
                    "target_cost_class": target_cost_component,
                    "target_latency_class": target_latency_component,
                    "transport_context_cost": transport_burden_component,
                    "expected_burden": burden_component,
                    "uncertainty": uncertainty_component,
                    "probe_value": probe_value_component,
                    "total": score,
                },
                "runtime_recommendation": profile.get("recommendation"),
                "cost_class": cost_class,
                "latency_class": latency_class,
                "selected_transport": selected_transport or None,
                "transport_options": transport_options,
                "required_action": required_action or "none",
                "continuation": continuation,
                "permitted_continuation": continuation,
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
                "uncertainty_contexts": [
                    {
                        "context_key": evidence.get("context_key"),
                        "record_id": evidence.get("record_id"),
                        "uncertainty_reasons": evidence.get("uncertainty_reasons", []),
                        "routing_effect": evidence.get("routing_effect"),
                    }
                    for evidence in matching_uncertainty[:5]
                ],
            }
        )
    current_candidate = next(
        (
            item
            for item in candidate_scores
            if current_target
            in (
                {
                    str(item.get("target") or ""),
                    str(item.get("target_identity_ref") or ""),
                }
                | {str(alias) for alias in item.get("aliases", [])}
            )
        ),
        None,
    )

    def candidate_observed_context(candidate: dict[str, Any]) -> dict[str, Any]:
        selected_transport = str(candidate.get("selected_transport") or "")
        option = next(
            (
                item
                for item in candidate.get("transport_options", [])
                if isinstance(item, dict) and str(item.get("transport") or "") == selected_transport
            ),
            {},
        )
        return _as_dict(option.get("observed_context_cost"))

    context_inflation_guard: list[dict[str, Any]] = []
    current_observed = candidate_observed_context(current_candidate or {})
    current_total_tokens = int(current_observed.get("effective_input_tokens") or 0) + int(current_observed.get("output_tokens") or 0)
    current_prompt_bytes = int(current_observed.get("rendered_prompt_bytes") or 0)
    recommendation_rank = {"poor-fit": 0, "acceptable": 1, "recommended": 2}
    if (
        current_candidate
        and current_candidate.get("eligible")
        and current_total_tokens > 0
        and current_prompt_bytes > 0
        and current_total_tokens > current_prompt_bytes * 50
        and current_candidate.get("required_action") != "delegate-down-when-safe"
    ):
        for candidate in candidate_scores:
            if candidate is current_candidate or not candidate.get("eligible"):
                continue
            candidate_observed = candidate_observed_context(candidate)
            candidate_total_tokens = int(candidate_observed.get("effective_input_tokens") or 0) + int(
                candidate_observed.get("output_tokens") or 0
            )
            candidate_prompt_bytes = int(candidate_observed.get("rendered_prompt_bytes") or 0)
            material_increase = candidate_total_tokens > current_total_tokens + max(5_000, round(current_total_tokens * 0.02))
            stronger_fit = int(_as_dict(candidate.get("ranking_components")).get("declared_fit") or 0) > int(
                _as_dict(current_candidate.get("ranking_components")).get("declared_fit") or 0
            ) or recommendation_rank.get(str(candidate.get("runtime_recommendation") or ""), 0) > recommendation_rank.get(
                str(current_candidate.get("runtime_recommendation") or ""), 0
            )
            if (
                material_increase
                and candidate_prompt_bytes > 0
                and candidate_total_tokens > candidate_prompt_bytes * 50
                and not stronger_fit
            ):
                penalty = max(1, int(candidate["score"]) - int(current_candidate["score"]) + 1)
                candidate["score"] = int(candidate["score"]) - penalty
                ranking = _as_dict(candidate.get("ranking_components"))
                ranking["context_inflation_guard"] = -penalty
                ranking["total"] = candidate["score"]
                context_inflation_guard.append(
                    {
                        "candidate": candidate["target"],
                        "retained_target": current_candidate["target"],
                        "candidate_total_tokens": candidate_total_tokens,
                        "current_total_tokens": current_total_tokens,
                        "observed_increase_tokens": candidate_total_tokens - current_total_tokens,
                        "threshold_tokens": max(5_000, round(current_total_tokens * 0.02)),
                        "ranking_adjustment": -penalty,
                        "reason": "materially-higher-observed-context-without-stronger-declared-fit",
                    }
                )
    eligible_candidates = [item for item in candidate_scores if item["eligible"]]
    eligible_candidates.sort(key=lambda item: (-int(item["score"]), str(item["target"])))
    selected_target = eligible_candidates[0]["target"] if eligible_candidates else None
    current_is_eligible = bool(current_candidate and current_candidate["eligible"])
    downroute_required = bool(current_candidate and current_candidate.get("required_action") == "delegate-down-when-safe")
    downroute_candidates = [
        item
        for item in eligible_candidates
        if current_target
        not in (
            {str(item.get("target") or ""), str(item.get("target_identity_ref") or "")} | {str(alias) for alias in item.get("aliases", [])}
        )
    ]
    if downroute_required and downroute_candidates:
        eligible_candidates = downroute_candidates
        selected_target = eligible_candidates[0]["target"]
    tied_candidates: list[dict[str, Any]] = []
    if eligible_candidates:
        top_score = int(eligible_candidates[0]["score"])
        tied_candidates = [item for item in eligible_candidates if int(item["score"]) == top_score]
    next_action = "continue locally"
    alternatives = [
        {
            "target": item["target"],
            "score": item["score"],
            "eligible": item["eligible"],
            "hard_rejection_reasons": item["hard_rejection_reasons"],
        }
        for item in candidate_scores
        if item["target"] != selected_target
    ][:5]
    if not requested_context_key:
        decision = "shape-before-assignment"
        canonical_outcome = "read-only-exploration"
        selected_target = None
        next_action = "derive a shaped task context before assignment; run read-only exploration or Planning shaping first"
    elif not eligible_candidates:
        decision = "no-safe-route"
        canonical_outcome = "no-safe-route"
        selected_target = None
        next_action = "shape the task, adjust transport/proof authority, or ask for a manual handoff before execution"
    elif policy_value == "local-preferred":
        if not current_target:
            decision = "keep-local"
            canonical_outcome = "retain-local"
            selected_target = None
            next_action = "continue locally without claiming a configured delegation target"
        elif current_is_eligible:
            decision = "keep-local"
            canonical_outcome = "retain-local"
            selected_target = current_target or None
            next_action = "execute with the eligible current target"
        else:
            decision = "policy-conflict"
            canonical_outcome = "planning-review-escalation"
            selected_target = None
            next_action = "resolve local-preferred current_target eligibility before execution"
    elif len(tied_candidates) > 1:
        decision = "tie"
        canonical_outcome = "planning-review-escalation"
        selected_target = None
        next_action = "choose between tied eligible targets or add disambiguating evidence"
    elif policy_value == "best-fit-advisory":
        decision = "advise-best-fit"
        canonical_outcome = "read-only-exploration"
        next_action = (
            f"consider {selected_target} as advisory best fit" if selected_target else "retain current execution until a fit exists"
        )
    elif not enforceable:
        decision = "blocked"
        canonical_outcome = "planning-review-escalation"
        selected_target = None
        next_action = "repair assignment policy binding before execution"
    elif recommendation in {"external-delegation", "manual-handoff", "stronger-reasoning"}:
        selected = eligible_candidates[0]
        decision = "manual-handoff" if selected.get("continuation") == "manual-handoff" else "assign-or-escalate"
        canonical_outcome = (
            "manual-strong-agent-handoff" if selected.get("continuation") == "manual-handoff" else selected.get("continuation")
        )
        next_action = "prepare manual handoff packet" if decision == "manual-handoff" else f"assign or escalate to {selected_target}"
    else:
        selected = eligible_candidates[0] if eligible_candidates else {}
        selected_target_refs = {str(selected.get("target") or ""), str(selected.get("target_identity_ref") or "")}
        decision = "assign-current-target" if current_target in selected_target_refs else "assign-best-fit"
        canonical_outcome = selected.get("continuation") or "delegated-implementation"
        next_action = f"execute with {selected_target}" if selected_target else "hold execution until assignment is resolved"
    selected_candidate = next(
        (
            item
            for item in candidate_scores
            if selected_target
            in {
                str(item.get("target") or ""),
                str(item.get("target_identity_ref") or ""),
            }
        ),
        {},
    )
    decision_revision_input = {
        "assignment_policy": policy_value,
        "current_target": current_target or None,
        "requested_context_key": requested_context_key or None,
        "decision": decision,
        "canonical_outcome": canonical_outcome,
        "selected_target": selected_target,
        "selected_target_identity_ref": selected_candidate.get("target_identity_ref"),
        "selected_target_revision": selected_candidate.get("target_revision"),
        "selected_transport": selected_candidate.get("selected_transport"),
        "candidate_scores": candidate_scores,
        "human_intent": " ".join(human_intent.split()),
    }
    assignment_decision_revision = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(decision_revision_input, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
    )
    return {
        "kind": "agentic-workspace/assignment-decision/v1",
        "decision": decision,
        "canonical_outcome": canonical_outcome,
        "outcome_matrix": ASSIGNMENT_OUTCOME_MATRIX,
        "assignment_policy": policy_value,
        "selected_target": selected_target,
        "selected_target_identity_ref": selected_candidate.get("target_identity_ref"),
        "selected_target_revision": selected_candidate.get("target_revision"),
        "selected_transport": selected_candidate.get("selected_transport"),
        "assignment_decision_revision": assignment_decision_revision,
        "task_class": requested_task_class or None,
        "scope_class": requested_scope_class or None,
        "context_key": requested_context_key or None,
        "current_target": current_target or None,
        "candidate_scores": candidate_scores,
        "selection_basis": {
            "hard_eligibility_first": True,
            "uses_runtime_candidate_comparison": bool(profile_recommendations),
            "uses_contextual_evidence": bool(suitability),
            "requested_context_key": requested_context_key or None,
            "tie_breaker": "ties are surfaced as a non-executable tie outcome; no lexical tie-break selects an executor",
            "current_target_eligible": current_is_eligible,
            "context_inflation_guard": {
                "status": "applied" if context_inflation_guard else "not-applied",
                "cases": context_inflation_guard,
                "rule": "Retain an equally capable current target when supported-host evidence shows a material token increase and declared price/latency priors lack portable normalization.",
            },
            "downroute_required": downroute_required,
            "downroute_applied": downroute_required and bool(downroute_candidates),
            "manual_transport_policy": manual_transport_policy,
            "component_order": [
                "task_requirements",
                "hard_eligibility",
                "declared_fit",
                "contextual_evidence",
                "expected_burden",
                "uncertainty",
                "probe_value",
                "policy",
            ],
            "task_requirements": {
                "task_class": requested_task_class or None,
                "scope_class": requested_scope_class or None,
                "context_key": requested_context_key or None,
                "requires_validation": bool(requested_task_class and requested_task_class in {"validation", "review", "proof"}),
            },
            "context_authority": {
                "status": "present" if requested_context_key else "missing",
                "fail_closed_without_context": True,
                "rule": "Ordinary assignment may not aggregate target evidence across all task/scope contexts when the shaped task context is absent.",
            },
        },
        "alternatives": alternatives,
        "uncertainty": "tie" if len(tied_candidates) > 1 else "sparse-evidence" if not suitability else "ranked",
        "override_authority": assignment_policy.get("human_override_policy", {}).get("value", "explicit-only"),
        "next_action": next_action,
        "runtime_recommendation": recommendation,
        "evidence_status": target_evidence.get("status", "unknown"),
        "record_count": target_evidence.get("record_count", 0),
        "claim_boundary": assignment_policy.get("binding", {}).get("claim_boundary", "assignment policy unresolved"),
        "rule": "Assignment decisions preserve policy, contextual target evidence, and runtime suitability as separate inputs; learned evidence cannot override hard policy or capability prohibitions.",
    }
