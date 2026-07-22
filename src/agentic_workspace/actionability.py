"""Shared actionability and progress-making next-action derivation."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def decision_input_revision(
    *,
    operation_id: str = "",
    arguments: dict[str, Any] | None = None,
    effect_class: str = "",
    authority_class: str = "",
    preconditions: dict[str, Any] | None = None,
    owner_context_revision: dict[str, Any] | None = None,
    mutation_boundary: dict[str, Any] | None = None,
    proof_requirements: list[Any] | None = None,
    evaluation_revision: dict[str, Any] | None = None,
    executor_revision: dict[str, Any] | None = None,
) -> str:
    """Canonical revision for a typed operating action's current decision inputs."""

    canonical = {
        "operation_id": operation_id,
        "arguments": dict(arguments or {}),
        "effect_class": effect_class,
        "authority_class": authority_class or "operation-contract",
        "preconditions": dict(preconditions or {}),
        "owner_context_revision": dict(owner_context_revision or {}),
        "mutation_boundary": dict(mutation_boundary or {}),
        "proof_requirements": list(proof_requirements or []),
        "evaluation_revision": dict(evaluation_revision or {}),
        "executor_revision": dict(executor_revision or {}),
    }
    return "sha256:" + hashlib.sha256(json.dumps(canonical, sort_keys=True, default=str).encode()).hexdigest()


def invocation_decision_input_revision(invocation: dict[str, Any]) -> str:
    return decision_input_revision(
        operation_id=str(invocation.get("operation_id") or invocation.get("operation") or ""),
        arguments=invocation.get("arguments") if isinstance(invocation.get("arguments"), dict) else {},
        effect_class=str(invocation.get("effect_class") or ""),
        authority_class=str(invocation.get("authority_class") or ""),
        preconditions=invocation.get("preconditions") if isinstance(invocation.get("preconditions"), dict) else {},
        owner_context_revision=invocation.get("owner_context_revision")
        if isinstance(invocation.get("owner_context_revision"), dict)
        else {},
        mutation_boundary=invocation.get("mutation_boundary") if isinstance(invocation.get("mutation_boundary"), dict) else {},
        proof_requirements=invocation.get("proof_requirements") if isinstance(invocation.get("proof_requirements"), list) else [],
        evaluation_revision=invocation.get("evaluation_revision") if isinstance(invocation.get("evaluation_revision"), dict) else {},
        executor_revision=invocation.get("executor_revision") if isinstance(invocation.get("executor_revision"), dict) else {},
    )


def operation_invocation(
    *,
    operation_id: str,
    arguments: dict[str, Any] | None = None,
    effect_class: str = "",
    authority_class: str = "",
    expected_transition: str = "",
    input_revision: str = "",
    claim_effect: str = "",
    command_rendering: str = "",
    preconditions: dict[str, Any] | None = None,
    owner_context_revision: dict[str, Any] | None = None,
    mutation_boundary: dict[str, Any] | None = None,
    proof_requirements: list[Any] | None = None,
    evaluation_revision: dict[str, Any] | None = None,
    executor_revision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a typed operation invocation that owns action identity."""

    normalized_arguments = dict(arguments or {})
    normalized_preconditions = dict(preconditions or {})
    normalized_owner_context = dict(owner_context_revision or {})
    normalized_mutation_boundary = dict(mutation_boundary or {})
    normalized_proof_requirements = list(proof_requirements or [])
    normalized_evaluation_revision = dict(evaluation_revision or {})
    normalized_executor_revision = dict(executor_revision or {})
    caller_supplied_input_revision = str(input_revision or "").strip()
    canonical_input_revision = decision_input_revision(
        operation_id=operation_id,
        arguments=normalized_arguments,
        effect_class=effect_class,
        authority_class=authority_class,
        preconditions=normalized_preconditions,
        owner_context_revision=normalized_owner_context,
        mutation_boundary=normalized_mutation_boundary,
        proof_requirements=normalized_proof_requirements,
        evaluation_revision=normalized_evaluation_revision,
        executor_revision=normalized_executor_revision,
    )
    idempotency_input = {
        "operation_id": operation_id,
        "arguments": normalized_arguments,
        "input_revision": canonical_input_revision,
        "expected_transition": expected_transition,
        "owner_context_revision": normalized_owner_context,
        "mutation_boundary": normalized_mutation_boundary,
        "proof_requirements": normalized_proof_requirements,
        "evaluation_revision": normalized_evaluation_revision,
        "executor_revision": normalized_executor_revision,
    }
    idempotency_key = hashlib.sha256(json.dumps(idempotency_input, sort_keys=True).encode()).hexdigest()[:16]
    invocation = {
        "kind": "agentic-workspace/operation-invocation/v1",
        "operation_id": operation_id,
        "contract_version": "agentic-workspace/operation/v1",
        "arguments": normalized_arguments,
        "effect_class": effect_class,
        "authority_class": authority_class or "operation-contract",
        "required_authority": "operation-contract",
        "preconditions": normalized_preconditions,
        "owner_context_revision": normalized_owner_context,
        "mutation_boundary": normalized_mutation_boundary,
        "proof_requirements": normalized_proof_requirements,
        "evaluation_revision": normalized_evaluation_revision,
        "executor_revision": normalized_executor_revision,
        "expected_input_revision": canonical_input_revision,
        "expected_transition": expected_transition,
        "idempotency_key": idempotency_key,
        "claim_effect": claim_effect,
        "stale_action_rejection": {
            "status": "reject-on-input-revision-mismatch",
            "comparison_fields": [
                "expected_input_revision",
                "owner_context_revision",
                "mutation_boundary",
                "proof_requirements",
                "evaluation_revision",
                "executor_revision",
            ],
            "repair": "Refresh the operating decision before executing this typed action.",
            "revision_source": "live-authority-resolver",
            "caller_supplied_input_revision": caller_supplied_input_revision,
            "caller_revision_authority": "ignored",
        },
        "renderings": {"cli": command_rendering} if command_rendering else {},
        "rule": "Operation identity and progress checks use this typed invocation; rendered commands are display or manual recovery text.",
    }
    return {key: value for key, value in invocation.items() if value not in ("", {}, [], None)}


def _proposed_invocation(proposed: dict[str, Any]) -> dict[str, Any]:
    invocation = proposed.get("operation_invocation") or proposed.get("typed_invocation")
    return dict(invocation) if isinstance(invocation, dict) else {}


def _invocation_operation(invocation: dict[str, Any]) -> str:
    return str(invocation.get("operation_id") or invocation.get("operation") or "").strip()


def derive_actionability(
    *,
    command_name: str,
    health: str,
    warnings: list[Any],
    repair_actions: list[Any],
    manual_review_actions: list[Any],
    proposed_next_action: dict[str, Any] | None,
    claim_limits: list[str] | None = None,
) -> dict[str, Any]:
    """Derive one coherent action decision and reject ordinary same-operation loops."""

    def identity(item: Any) -> str:
        if isinstance(item, dict):
            return str(
                item.get("id") or item.get("finding_id") or item.get("code") or item.get("message") or json.dumps(item, sort_keys=True)
            )
        return str(item)

    findings: list[dict[str, Any]] = []
    repair_ids = {identity(item) for item in repair_actions}
    if repair_actions:
        findings.append(
            {
                "class": "required-repair",
                "count": len(repair_ids),
                "owner": "workspace-or-repo-maintainer",
                "finding_ids": sorted(repair_ids),
            }
        )
    required_reviews = [
        item
        for item in manual_review_actions
        if isinstance(item, dict) and (item.get("action_required") is True or str(item.get("severity") or "").lower() == "error")
    ]
    advisory_reviews = [item for item in manual_review_actions if item not in required_reviews]
    if required_reviews:
        findings.append({"class": "required-review", "count": len(required_reviews), "owner": "human-or-reviewer"})
    required_ids = {identity(item) for item in required_reviews} - repair_ids
    advisory_ids = ({identity(item) for item in advisory_reviews} | {identity(item) for item in warnings}) - repair_ids - required_ids
    if required_reviews:
        findings[-1]["count"] = len(required_ids)
        findings[-1]["finding_ids"] = sorted(required_ids)
        if not required_ids:
            findings.pop()
    advisory_count = len(advisory_ids)
    if advisory_count:
        findings.append(
            {
                "class": "optional-advisory",
                "count": advisory_count,
                "owner": "current-actor-or-reviewer",
                "finding_ids": sorted(advisory_ids),
            }
        )
    if not findings:
        findings.append({"class": "resolved-or-informational", "count": 1, "owner": "none"})

    action_required = bool(repair_actions or required_reviews)
    proposed = dict(proposed_next_action or {})
    next_command = str(proposed.get("command") or proposed.get("run") or "").strip()
    invocation = _proposed_invocation(proposed)
    proposed_operation = _invocation_operation(invocation)
    same_operation = bool(proposed_operation and proposed_operation == command_name)
    external_condition = str(proposed.get("external_change_condition") or "").strip()
    expected_transition = str(
        invocation.get("expected_transition") or proposed.get("expected_transition") or proposed.get("state_transition") or ""
    ).strip()
    digest_input = {
        "operation": command_name,
        "health": health,
        "finding_classes": [item["class"] for item in findings],
        "finding_ids": sorted(repair_ids | required_ids | advisory_ids),
        "action_required": action_required,
        "claim_limits": list(claim_limits or []),
    }
    input_digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True).encode()).hexdigest()[:16]
    proposed_input_digest = str(proposed.get("input_digest") or "").strip()
    same_state = proposed_input_digest == input_digest if proposed_input_digest else not expected_transition
    expected_input_revision = str(invocation.get("expected_input_revision") or "").strip()
    current_input_revision = invocation_decision_input_revision(invocation) if invocation else ""
    stale_action_rejected = bool(
        invocation.get("stale_action_rejection") and (not expected_input_revision or expected_input_revision != current_input_revision)
    )
    self_loop_rejected = same_operation and same_state and not external_condition
    if not action_required:
        next_action = {
            "action": "no-immediate-action",
            "summary": (
                "No progress-making action is currently required; advisories and claim limits remain visible."
                if warnings or claim_limits
                else "No immediate action is required."
            ),
            "commands": [],
        }
    elif stale_action_rejected:
        next_action = {
            "action": "required-action-unavailable",
            "summary": "Required work remains, but the typed action was derived from stale input state.",
            "commands": [],
            "owner": str(proposed.get("owner") or "workspace-or-repo-maintainer"),
            "missing_precondition": "fresh operating decision with matching owner, context, authority, proof, and mutation baseline revisions",
            "stale_action_rejection": invocation.get("stale_action_rejection"),
        }
    elif self_loop_rejected:
        next_action = {
            "action": "required-action-unavailable",
            "summary": "Required work remains, but the proposed action repeats the same operation against unchanged state.",
            "commands": [],
            "owner": str(proposed.get("owner") or "workspace-or-repo-maintainer"),
            "missing_precondition": str(proposed.get("missing_precondition") or "state change or a distinct transition-bearing action"),
        }
    else:
        next_action = proposed
    return {
        "kind": "agentic-workspace/actionability/v1",
        "status": "action-required" if action_required else "advisory-only" if warnings or claim_limits else "resolved",
        "health": health,
        "action_required": action_required,
        "findings": findings,
        "claim_limits": list(claim_limits or []),
        "next_action": next_action,
        "progress_check": {
            "input_digest": input_digest,
            "current_input_revision": current_input_revision,
            "proposed_operation": proposed_operation,
            "operation_invocation": invocation,
            "command_identity_authority": "typed-operation-invocation" if invocation else "absent-display-command-only",
            "same_operation": same_operation,
            "same_state": same_state,
            "expected_transition": expected_transition,
            "expected_input_revision": expected_input_revision,
            "stale_action_rejected": stale_action_rejected,
            "external_change_condition": external_condition,
            "result": "rejected-stale-action"
            if stale_action_rejected
            else "rejected-same-state-loop"
            if self_loop_rejected
            else "progress-making"
            if next_command or invocation
            else "terminal",
        },
        "rule": "Status, required action, claim limits, and next action derive from one finding classification; ordinary same-state loops are not next actions.",
    }
