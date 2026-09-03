"""Derived orchestration projections over canonical Planning and assignment owners.

This module deliberately owns no queue, lifecycle state, or mutation authority.
It turns current owner records and typed operation results into bounded routing
facts that their canonical owners can consume.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from agentic_workspace.actionability import operation_invocation


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _revision(subject: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(subject), sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def assignment_bound_entry(*, launched: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    """Collapse generic startup to the current assignment-bound worker authority."""

    launch = _mapping(launched)
    canonical = _mapping(current)
    if not launch:
        return {}
    launch_assignment = _mapping(launch.get("assignment"))
    current_assignment = _mapping(canonical.get("assignment"))
    identity_fields = ("assignment_id", "assignment_revision", "run_id", "target")
    mismatches = [field for field in identity_fields if _text(launch_assignment.get(field)) != _text(current_assignment.get(field))]
    current_status = _text(canonical.get("status"))
    if mismatches or current_status != "assignment-bound":
        return {
            "kind": "agentic-workspace/assignment-bound-entry/v1",
            "status": "recovery-required",
            "broad_startup_constructed": False,
            "mismatched_identity_fields": mismatches,
            "current_assignment": {field: current_assignment.get(field) for field in identity_fields},
            "next_action": {
                "owner": "assignment-lifecycle",
                "action": "resolve-current-assignment-run",
                "reason_code": "assignment-identity-mismatch" if mismatches else "stale-or-terminal-assignment",
            },
            "claim_boundary": "Recovery may resolve current assignment identity only; it cannot retarget or widen worker authority.",
        }
    bounded = json.loads(json.dumps(canonical, default=str))
    return {
        "kind": "agentic-workspace/assignment-bound-entry/v1",
        "status": "bounded-worker-continuation",
        "broad_startup_constructed": False,
        "worker_context": bounded,
        "next_action": {
            "owner": "assignment-worker",
            "action": "execute-current-assignment",
            "assignment_id": current_assignment.get("assignment_id"),
            "assignment_revision": current_assignment.get("assignment_revision"),
            "run_id": current_assignment.get("run_id"),
        },
        "claim_boundary": "The worker may execute and return only; target selection, admission, integration, proof, and parent closeout remain unavailable.",
    }


def derive_orchestration_frontier(
    *, planning_slices: Sequence[Mapping[str, Any]], assignments: Sequence[Mapping[str, Any]] = ()
) -> dict[str, Any]:
    """Derive a versioned frontier without persisting a queue or current selection."""

    slices = [dict(item) for item in planning_slices]
    if not slices:
        return {}
    by_id = {_text(item.get("slice_id")): item for item in slices if _text(item.get("slice_id"))}
    current_assignments: dict[str, list[dict[str, Any]]] = {}
    for assignment in assignments:
        item = dict(assignment)
        if _text(item.get("status")) not in {
            "current",
            "in-flight",
            "returned",
            "awaiting-admission",
            "admitted",
            "integrated",
            "integration-pending",
        }:
            continue
        current_assignments.setdefault(_text(item.get("slice_id")), []).append(item)
    entries: list[dict[str, Any]] = []
    for item in slices:
        slice_id = _text(item.get("slice_id"))
        semantic_revision = _text(item.get("semantic_revision"))
        dependencies = [_text(value) for value in _items(item.get("dependencies")) if _text(value)]
        blocked_by = [
            dependency for dependency in dependencies if _text(by_id.get(dependency, {}).get("status")) not in {"complete", "integrated"}
        ]
        all_attempts = current_assignments.get(slice_id, [])
        attempts = [
            attempt
            for attempt in all_attempts
            if not _text(attempt.get("semantic_revision")) or _text(attempt.get("semantic_revision")) == semantic_revision
        ]
        stale_attempts = [attempt for attempt in all_attempts if attempt not in attempts]
        attempt_states = {_text(attempt.get("status")) for attempt in attempts}
        status = _text(item.get("status"))
        if status in {"complete", "integrated"}:
            frontier_status = "complete"
        elif status == "integration-pending":
            frontier_status = "integration-pending"
        elif blocked_by:
            frontier_status = "blocked"
        elif attempt_states.intersection({"returned", "awaiting-admission", "admitted", "integrated", "integration-pending"}):
            frontier_status = "integration-pending"
        elif attempts:
            frontier_status = "in-flight"
        else:
            frontier_status = "ready"
        entries.append(
            {
                "slice_id": slice_id,
                "semantic_revision": semantic_revision,
                "status": frontier_status,
                "blocked_by": blocked_by,
                "current_attempts": [
                    {
                        "assignment_id": attempt.get("assignment_id"),
                        "assignment_revision": attempt.get("assignment_revision"),
                        "run_id": attempt.get("run_id"),
                        "target": attempt.get("target"),
                    }
                    for attempt in attempts
                ],
                "stale_attempts": [
                    {
                        "assignment_id": attempt.get("assignment_id"),
                        "assignment_revision": attempt.get("assignment_revision"),
                        "run_id": attempt.get("run_id"),
                        "semantic_revision": attempt.get("semantic_revision"),
                        "reason": "planning-semantic-revision-changed",
                    }
                    for attempt in stale_attempts
                ],
                "executable_contract": _mapping(item.get("executable_contract")),
            }
        )
    subject = {"slices": entries}
    return {
        "kind": "agentic-workspace/orchestration-frontier/v1",
        "status": "derived",
        "revision": _revision(subject),
        "entries": entries,
        "ready_slice_ids": [item["slice_id"] for item in entries if item["status"] == "ready"],
        "authority": "read-only-projection-of-planning-and-assignment-owners",
        "persistence": "none",
    }


def attribute_orchestration_outcome(*, evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Conservatively route an admitted outcome to an existing responsibility owner."""

    item = _mapping(evidence)
    admitted = item.get("admitted") is True
    stage = _text(item.get("failure_stage") or item.get("stage"))
    changed_intent = item.get("changed_intent") is True
    context_sufficient = item.get("context_sufficient") is True
    transport_sufficient = item.get("transport_sufficient") is True
    target_executed = item.get("target_executed") is True
    worker_succeeded = item.get("worker_succeeded") is True
    ambiguous = item.get("mixed") is True or item.get("censored") is True
    if not admitted:
        responsibility = "censored"
    elif ambiguous:
        responsibility = "mixed-or-unknown"
    elif changed_intent:
        responsibility = "changed-human-intent"
    elif stage in {"planning", "decomposition", "task-specification"}:
        responsibility = "planning-decomposition"
    elif not context_sufficient or stage in {"context", "context-selection"}:
        responsibility = "context-selection"
    elif not transport_sufficient or stage in {"transport", "context-inflation"}:
        responsibility = "transport-context-inflation"
    elif worker_succeeded and stage in {"return", "admission", "integration"}:
        responsibility = "return-admission-integration"
    elif worker_succeeded and stage in {"proof", "validation", "review"}:
        responsibility = "proof-validation-review"
    elif stage in {"environment", "tooling"}:
        responsibility = "environment-tooling"
    elif target_executed and context_sufficient and transport_sufficient:
        responsibility = "target-execution"
    else:
        responsibility = "mixed-or-unknown"
    target_authoritative = responsibility == "target-execution"
    repo_friction = (
        responsibility in {"context-selection", "proof-validation-review", "planning-decomposition"} and item.get("repo_owned") is True
    )
    return {
        "kind": "agentic-workspace/orchestration-outcome-attribution/v1",
        "status": "attributed" if responsibility not in {"mixed-or-unknown", "censored"} else "non-authoritative",
        "responsibility": responsibility,
        "semantic_identity": {
            "slice_id": item.get("slice_id"),
            "semantic_revision": item.get("semantic_revision"),
            "task_class": item.get("task_class"),
        },
        "attempt_identity": {
            "assignment_id": item.get("assignment_id"),
            "assignment_revision": item.get("assignment_revision"),
            "run_id": item.get("run_id"),
            "target": item.get("target"),
        },
        "routing_effect": {
            "target_evidence_allowed": target_authoritative,
            "target_evidence_owner": "target-outcome-evidence" if target_authoritative else None,
            "source_owner_adaptation_pressure": repo_friction,
            "source_owner": item.get("source_owner") if repo_friction else None,
        },
        "hard_gates_remain_prior": True,
        "raw_trajectory_retained": False,
    }


def evaluate_external_orchestration_candidate(
    *, example: Mapping[str, Any], candidate: Mapping[str, Any], frozen_evaluation: Mapping[str, Any]
) -> dict[str, Any]:
    """Evaluate a bounded external candidate without granting it ordinary authority."""

    evidence = _mapping(example)
    proposal = _mapping(candidate)
    evaluation = _mapping(frozen_evaluation)
    constraints = _mapping(evidence.get("hard_constraints"))
    candidate_action = _text(proposal.get("action") or proposal.get("target"))
    eligible = {_text(value) for value in _items(constraints.get("eligible_candidates"))}
    violations = [_text(value) for value in _items(proposal.get("authority_violations")) if _text(value)]
    if not evaluation.get("frozen_before_candidate"):
        disposition = "RETAIN_RESEARCH"
        reason = "evaluation-not-frozen"
    elif _text(evidence.get("attribution_status")) != "attributed":
        disposition = "RETAIN_RESEARCH"
        reason = "causal-evidence-not-admitted"
    elif violations or (eligible and candidate_action not in eligible):
        disposition = "STOP"
        reason = "candidate-violates-deterministic-constraints"
    else:
        baseline_cost = float(evaluation.get("baseline_total_cost") or 0)
        candidate_cost = sum(
            float(proposal.get(field) or 0)
            for field in ("execution_cost", "repair_cost", "retry_cost", "proof_cost", "context_cost", "review_cost")
        )
        no_regressions = all(
            proposal.get(field) is not False
            for field in ("correct", "intent_preserved", "scope_preserved", "proof_preserved", "trust_preserved")
        )
        disposition = "PROMOTE_BOUNDED" if no_regressions and baseline_cost > 0 and candidate_cost < baseline_cost else "STOP"
        reason = "lower-total-cost-without-regression" if disposition == "PROMOTE_BOUNDED" else "no-bounded-improvement"
    return {
        "kind": "agentic-workspace/external-orchestration-candidate-evaluation/v1",
        "status": "evaluated",
        "candidate_identity": {"id": proposal.get("id"), "version": proposal.get("version")},
        "disposition": disposition,
        "reason": reason,
        "promotion_owner": evidence.get("canonical_owner") if disposition == "PROMOTE_BOUNDED" else None,
        "ordinary_authority_granted": False,
        "portable_trainer_required": False,
    }


def reconcile_action_result(*, result: Mapping[str, Any]) -> dict[str, Any]:
    """Project a result-carried next continuation from current typed owner facts."""

    item = _mapping(result)
    if not item:
        return {}
    family = _text(item.get("family") or item.get("kind"))
    status = _text(item.get("status"))
    outcome = _text(item.get("outcome"))
    if outcome in {"blocked", "failed"}:
        return {
            "kind": "agentic-workspace/action-result-continuation/v1",
            "status": "blocked",
            "owner": family,
            "reason_code": item.get("reason_code"),
            "recovery": item.get("recovery_command"),
        }
    if item.get("stale") is True or status.startswith("stale-"):
        return {
            "kind": "agentic-workspace/action-result-continuation/v1",
            "status": "re-resolution-required",
            "owner": item.get("currentness_owner") or family,
            "action": item.get("replacement_action") or "resolve-current-owner-action",
            "reason": "the prior action is non-current and must not be retried",
        }
    if item.get("eligible") is False:
        return {
            "kind": "agentic-workspace/action-result-continuation/v1",
            "status": "blocked",
            "owner": item.get("eligibility_owner") or family,
            "reason_code": item.get("ineligibility_reason") or "protected-action-ineligible",
            "recovery": item.get("eligible_alternative"),
        }
    if item.get("semantic_decision_required") is True:
        return {
            "kind": "agentic-workspace/action-result-continuation/v1",
            "status": "decision-required",
            "owner": item.get("decision_owner") or "agent-or-human",
            "decision": item.get("decision"),
            "source_facts": _mapping(item.get("source_facts")),
        }
    if family == "agentic-workspace/assignment-lifecycle-result/v1":
        args = {
            "assignment_id": item.get("assignment_id"),
            "assignment_revision": item.get("assignment_revision"),
            "run_id": item.get("run_id"),
        }
        transitions = {
            "handoff-prepared": ("assignment.dispatch", "execute-current-assignment", "awaiting-host-execution"),
            "awaiting-host-execution": ("assignment.import", "await-structured-return", "awaiting-admission"),
            "awaiting-admission": ("assignment.admit", "admit-current-return", "admitted"),
            "admitted": ("assignment.integrate", "integrate-admitted-return", "integrated"),
            "integrated": ("proof.report", "run-current-proof-route", "proof-recorded"),
        }
        if status in transitions:
            operation_id, action, expected = transitions[status]
            invocation = operation_invocation(
                operation_id=operation_id,
                arguments=args,
                effect_class="assignment-lifecycle" if not operation_id.startswith("proof.") else "proof-recording",
                authority_class="canonical-assignment-and-planning-owner",
                expected_transition=expected,
                owner_context_revision={"assignment_revision": item.get("assignment_revision"), "run_id": item.get("run_id")},
            )
            return {
                "kind": "agentic-workspace/action-result-continuation/v1",
                "status": "actionable",
                "owner": "assignment-lifecycle" if not operation_id.startswith("proof.") else "proof-route",
                "action": action,
                "operation_invocation": invocation,
            }
        if status in {"closed", "archived"}:
            return {
                "kind": "agentic-workspace/action-result-continuation/v1",
                "status": "re-resolution-required",
                "owner": "operating-decision",
                "action": "derive-current-planning-frontier",
                "reason": "assignment lifecycle is terminal; the next slice must be re-derived from current Planning authority",
            }
    if family in {
        "proof-route-repair",
        "agentic-workspace/proof-route-repair-result/v1",
        "agentic-workspace/proof-route-repair-apply/v1",
    } and outcome in {"applied", "noop", ""}:
        return {
            "kind": "agentic-workspace/action-result-continuation/v1",
            "status": "re-resolution-required",
            "owner": "proof-route",
            "action": "rerun-current-proof-route",
            "reason": "repair changed or confirmed proof-route inputs; current proof authority must be resolved again",
        }
    return {
        "kind": "agentic-workspace/action-result-continuation/v1",
        "status": "terminal-or-unknown",
        "owner": family,
        "action": None,
    }


def verification_contributions(
    *,
    semantic_slice: Mapping[str, Any],
    assignment_attempt: Mapping[str, Any],
    proof_policy: Mapping[str, Any],
    previous_partition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Partition semantic Verification identity from execution-attempt evidence.

    A caller that already holds a source-owned partition may supply it here.
    Only Planning semantic identity and proof-policy identity decide whether the
    prior semantic contribution remains current; attempt changes still produce
    a fresh attempt contribution.
    """

    semantic = {
        "slice_id": semantic_slice.get("slice_id"),
        "semantic_revision": semantic_slice.get("semantic_revision"),
        "acceptance": semantic_slice.get("acceptance"),
        "proof_policy": dict(proof_policy),
    }
    semantic_reuse: dict[str, Any] | None = None
    if previous_partition is not None:
        from agentic_workspace.resolved_decision_reuse import reuse_verification_semantic_contribution

        reuse = reuse_verification_semantic_contribution(
            previous_partition=previous_partition,
            semantic_slice=semantic_slice,
            proof_policy=proof_policy,
        )
        if reuse["status"] == "reused":
            semantic = dict(reuse["semantic"])
        semantic_reuse = {
            "status": reuse["status"],
            "decision_revision": reuse["decision_revision"],
            "dependency_revision": reuse["dependency_revision"],
            "invalidated_dependencies": list(reuse["invalidated_dependencies"]),
            "re_resolution": reuse["re_resolution"],
        }
    attempt = {
        "assignment_id": assignment_attempt.get("assignment_id"),
        "assignment_revision": assignment_attempt.get("assignment_revision"),
        "run_id": assignment_attempt.get("run_id"),
        "target": assignment_attempt.get("target"),
        "transport": assignment_attempt.get("transport"),
        "return_id": assignment_attempt.get("return_id"),
    }
    result = {
        "kind": "agentic-workspace/verification-contribution-partition/v1",
        "semantic_contribution_revision": _revision(semantic),
        "attempt_contribution_revision": _revision(attempt),
        "semantic": semantic,
        "attempt": attempt,
        "target_selection_authority": False,
    }
    if semantic_reuse is not None:
        result["semantic_reuse"] = semantic_reuse
    return result
