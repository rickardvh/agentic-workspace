from __future__ import annotations

from collections.abc import Iterable
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
    return True


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
            scope_class = _record_scope_class(record)
            normalized.append(
                {
                    "id": _target_record_id(target_name=target_name, record=record, index=index),
                    "target": target_name,
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

    suitability: list[dict[str, Any]] = []
    target_names = sorted(set(profile_by_name) | set(records_by_target))
    for target_name in target_names:
        profile = profile_by_name.get(target_name)
        target_records = records_by_target.get(target_name, [])
        if not target_records:
            suitability.append(
                {
                    "target": target_name,
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
        "lifecycle": {
            "kind": "agentic-workspace/target-outcome-evidence-lifecycle/v1",
            "public_operations": [
                {
                    "operation": "submit",
                    "command": "agentic-workspace note-delegation-outcome --target . --delegation-target <target> --task-class <class> --scope-class <scope> --operation submit --outcome <success|mixed|failed> --handoff-sufficiency <sufficient|borderline|insufficient> --review-burden <light|normal|high> --format json",
                    "admission": "resolves target, task class, independent scope class, source ref, producer class, route observations, authority, confidence, idempotency key, and duplicate-safe record id before routing uses it",
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
    }


def assignment_decision_from_policy(
    *, assignment_policy: dict[str, Any], runtime_resolution: dict[str, Any], target_evidence: dict[str, Any]
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
        score = int(profile.get("score") or 0) + recommendation_score.get(str(profile.get("recommendation") or ""), 0)
        matching_evidence = evidence_by_target.get(target, [])
        for evidence in matching_evidence:
            score += evidence_score.get(str(evidence.get("route_effect") or ""), 0)
        if target == current_target:
            score += 5
        candidate_scores.append(
            {
                "target": target,
                "eligible": eligible,
                "hard_rejection_reasons": hard_rejection_reasons,
                "score": score,
                "runtime_recommendation": profile.get("recommendation"),
                "required_action": required_action or "none",
                "continuation": "manual-handoff"
                if required_action == "manual-handoff-required"
                else "execute"
                if eligible
                else "not-executable",
                "evidence_contexts": [
                    {
                        "context_key": evidence.get("context_key"),
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
    selected_target = eligible_candidates[0]["target"] if eligible_candidates else None
    current_candidate = next((item for item in candidate_scores if item["target"] == current_target), None)
    current_is_eligible = bool(current_candidate and current_candidate["eligible"])
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
    if not eligible_candidates:
        decision = "no-safe-route"
        selected_target = None
        next_action = "shape the task, adjust transport/proof authority, or ask for a manual handoff before execution"
    elif policy_value == "local-preferred":
        if not current_target:
            decision = "keep-local"
            selected_target = None
            next_action = "continue locally without claiming a configured delegation target"
        elif current_is_eligible:
            decision = "keep-local"
            selected_target = current_target or None
            next_action = "execute with the eligible current target"
        else:
            decision = "policy-conflict"
            selected_target = None
            next_action = "resolve local-preferred current_target eligibility before execution"
    elif len(tied_candidates) > 1:
        decision = "tie"
        selected_target = None
        next_action = "choose between tied eligible targets or add disambiguating evidence"
    elif policy_value == "best-fit-advisory":
        decision = "advise-best-fit"
        next_action = (
            f"consider {selected_target} as advisory best fit" if selected_target else "retain current execution until a fit exists"
        )
    elif not enforceable:
        decision = "blocked"
        selected_target = None
        next_action = "repair assignment policy binding before execution"
    elif recommendation in {"external-delegation", "manual-handoff", "stronger-reasoning"}:
        selected = eligible_candidates[0]
        decision = "manual-handoff" if selected.get("continuation") == "manual-handoff" else "assign-or-escalate"
        next_action = "prepare manual handoff packet" if decision == "manual-handoff" else f"assign or escalate to {selected_target}"
    else:
        decision = "assign-best-fit" if selected_target != current_target else "assign-current-target"
        next_action = f"execute with {selected_target}" if selected_target else "hold execution until assignment is resolved"
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
            "tie_breaker": "ties are surfaced as a non-executable tie outcome; no lexical tie-break selects an executor",
            "current_target_eligible": current_is_eligible,
            "manual_transport_policy": manual_transport_policy,
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
