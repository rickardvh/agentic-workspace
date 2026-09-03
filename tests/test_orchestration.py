from __future__ import annotations

import argparse
import json

from agentic_workspace.orchestration import (
    assignment_bound_entry,
    attribute_orchestration_outcome,
    derive_orchestration_frontier,
    evaluate_external_orchestration_candidate,
    reconcile_action_result,
    verification_contributions,
)


def _kernel(*, revision: str = "rev-1", run_id: str = "run-1", target: str = "worker-a", status: str = "assignment-bound"):
    return {
        "kind": "agentic-workspace/delegated-worker-kernel/v1",
        "status": status,
        "assignment": {
            "assignment_id": "assignment-1",
            "assignment_revision": revision,
            "run_id": run_id,
            "target": target,
        },
        "scope": {
            "allowed_paths": ["src/bounded.py"],
            "allowed_effects": ["edit"],
            "proof_obligation": {"id": "proof-1"},
            "stop_conditions": ["scope-change"],
        },
        "admission": {"return_schema": "delegated-return/v1"},
    }


def test_assignment_bound_entry_preserves_current_worker_authority() -> None:
    current = _kernel()
    result = assignment_bound_entry(launched=current, current=current)

    assert result["status"] == "bounded-worker-continuation"
    assert result["broad_startup_constructed"] is False
    assert result["worker_context"] == current
    assert result["next_action"]["run_id"] == "run-1"
    assert "integration" in result["claim_boundary"]


def test_assignment_bound_entry_fails_closed_on_revision_or_target_drift() -> None:
    result = assignment_bound_entry(launched=_kernel(revision="old", target="worker-b"), current=_kernel())

    assert result["status"] == "recovery-required"
    assert result["broad_startup_constructed"] is False
    assert result["mismatched_identity_fields"] == ["assignment_revision", "target"]
    assert result["next_action"]["owner"] == "assignment-lifecycle"


def test_generic_start_collapses_to_assignment_entry(monkeypatch, tmp_path) -> None:
    from agentic_workspace import workspace_runtime_startup as startup

    emitted = []
    kernel = _kernel()
    monkeypatch.setenv("AGENTIC_WORKSPACE_DELEGATED_WORKER_KERNEL", json.dumps(kernel))
    monkeypatch.setattr(startup, "_resolve_target_root", lambda _target: tmp_path)
    monkeypatch.setattr(startup, "_validate_target_root", lambda **_kwargs: None)
    monkeypatch.setattr(startup, "_selector_prevalidation_error", lambda **_kwargs: None)
    monkeypatch.setattr(startup, "_obsolete_default_preset_start_recovery_payload", lambda **_kwargs: None)
    monkeypatch.setattr(startup, "_load_workspace_config", lambda **_kwargs: object())
    monkeypatch.setattr(startup, "_workspace_disabled_payload", lambda **_kwargs: None)
    monkeypatch.setattr(startup, "_delegated_worker_kernel_payload", lambda **_kwargs: kernel)
    monkeypatch.setattr(startup, "_emit_payload", lambda **kwargs: emitted.append(kwargs["payload"]))
    monkeypatch.setattr(startup, "_start_payload", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("broad startup ran")))
    args = argparse.Namespace(target=str(tmp_path), select=None, format="json", task="bounded work", changed=[], verbose=False)

    assert startup._run_start_context_adapter(args) == 0
    assert emitted[0]["status"] == "bounded-worker-continuation"
    assert emitted[0]["broad_startup_constructed"] is False


def test_frontier_is_derived_and_separates_semantic_slice_from_attempt() -> None:
    result = derive_orchestration_frontier(
        planning_slices=[
            {"slice_id": "a", "semantic_revision": "sem-a", "status": "complete"},
            {"slice_id": "b", "semantic_revision": "sem-b", "dependencies": ["a"], "executable_contract": {"effect": "edit"}},
            {"slice_id": "c", "semantic_revision": "sem-c", "dependencies": ["b"]},
        ],
        assignments=[
            {
                "slice_id": "b",
                "status": "current",
                "assignment_id": "assignment-b",
                "assignment_revision": "attempt-2",
                "run_id": "run-2",
                "target": "worker-a",
            }
        ],
    )

    assert result["persistence"] == "none"
    assert result["ready_slice_ids"] == []
    assert result["entries"][1]["status"] == "in-flight"
    assert result["entries"][1]["semantic_revision"] == "sem-b"
    assert result["entries"][1]["current_attempts"][0]["assignment_revision"] == "attempt-2"
    assert result["entries"][2]["blocked_by"] == ["b"]


def test_frontier_exposes_parallel_ready_slices_and_stales_changed_semantic_attempt() -> None:
    result = derive_orchestration_frontier(
        planning_slices=[
            {"slice_id": "a", "semantic_revision": "sem-a", "status": "complete"},
            {"slice_id": "b", "semantic_revision": "sem-b2", "dependencies": ["a"]},
            {"slice_id": "c", "semantic_revision": "sem-c", "dependencies": ["a"]},
            {"slice_id": "d", "semantic_revision": "sem-d", "dependencies": ["b"]},
        ],
        assignments=[
            {
                "slice_id": "b",
                "semantic_revision": "sem-b1",
                "status": "current",
                "assignment_id": "old-b",
                "assignment_revision": "attempt-1",
                "run_id": "run-old",
            }
        ],
    )

    assert result["ready_slice_ids"] == ["b", "c"]
    assert result["entries"][1]["stale_attempts"][0]["reason"] == "planning-semantic-revision-changed"
    assert result["entries"][3]["blocked_by"] == ["b"]


def test_attribution_only_routes_equivalent_target_execution_to_target_evidence() -> None:
    target = attribute_orchestration_outcome(
        evidence={
            "admitted": True,
            "target_executed": True,
            "context_sufficient": True,
            "transport_sufficient": True,
            "slice_id": "slice-1",
            "semantic_revision": "sem-1",
            "assignment_revision": "attempt-2",
            "target": "worker-a",
        }
    )
    omitted_context = attribute_orchestration_outcome(
        evidence={"admitted": True, "target_executed": True, "context_sufficient": False, "transport_sufficient": True}
    )
    integration = attribute_orchestration_outcome(
        evidence={
            "admitted": True,
            "worker_succeeded": True,
            "failure_stage": "integration",
            "context_sufficient": True,
            "transport_sufficient": True,
        }
    )
    proof = attribute_orchestration_outcome(
        evidence={
            "admitted": True,
            "worker_succeeded": True,
            "failure_stage": "proof",
            "context_sufficient": True,
            "transport_sufficient": True,
            "repo_owned": True,
            "source_owner": "proof-routing",
        }
    )

    assert target["routing_effect"]["target_evidence_allowed"] is True
    assert target["semantic_identity"]["semantic_revision"] == "sem-1"
    assert target["attempt_identity"]["assignment_revision"] == "attempt-2"
    assert omitted_context["responsibility"] == "context-selection"
    assert integration["responsibility"] == "return-admission-integration"
    assert not integration["routing_effect"]["target_evidence_allowed"]
    assert proof["routing_effect"] == {
        "target_evidence_allowed": False,
        "target_evidence_owner": None,
        "source_owner_adaptation_pressure": True,
        "source_owner": "proof-routing",
    }


def test_ordinary_calibration_path_does_not_penalize_target_for_transport_failure(monkeypatch, tmp_path) -> None:
    from agentic_workspace import workspace_runtime_core as runtime

    monkeypatch.setattr(
        runtime,
        "_trusted_producer_assignment_context",
        lambda **_kwargs: {
            "target_context": {
                "assignment_id": "assignment-1",
                "assignment_revision": "attempt-1",
                "run_id": "run-1",
                "delegation_target": "worker-a",
                "task_class": "implementation",
                "scope_class": "bounded-code",
            }
        },
    )
    monkeypatch.setattr(
        runtime,
        "_write_trusted_producer_receipt",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("target evidence receipt must not be written")),
    )

    result = runtime._record_trusted_assignment_outcome_from_ordinary_boundary(
        target_root=tmp_path,
        producer_class="handoff-outcome",
        outcome="failed",
        source_payload={"status": "transport-failed"},
        idempotency_key="transport-failure",
        responsibility_evidence={"failure_stage": "transport", "target_executed": False},
    )

    assert result["status"] == "routed-to-responsible-owner"
    assert result["attribution"]["responsibility"] == "transport-context-inflation"
    assert result["recorded_target_evidence"] is False


def test_external_candidate_requires_attribution_constraints_and_total_cost() -> None:
    example = {
        "attribution_status": "attributed",
        "canonical_owner": "target-ranking",
        "hard_constraints": {"eligible_candidates": ["worker-a", "worker-b"]},
    }
    candidate = {
        "id": "candidate-1",
        "version": "v2",
        "target": "worker-b",
        "execution_cost": 4,
        "repair_cost": 1,
        "retry_cost": 0,
        "proof_cost": 1,
        "context_cost": 1,
        "review_cost": 1,
        "correct": True,
        "intent_preserved": True,
        "scope_preserved": True,
        "proof_preserved": True,
        "trust_preserved": True,
    }
    evaluation = {"frozen_before_candidate": True, "baseline_total_cost": 12}

    promoted = evaluate_external_orchestration_candidate(example=example, candidate=candidate, frozen_evaluation=evaluation)
    ineligible = evaluate_external_orchestration_candidate(
        example=example, candidate={**candidate, "target": "worker-c"}, frozen_evaluation=evaluation
    )

    assert promoted["disposition"] == "PROMOTE_BOUNDED"
    assert promoted["ordinary_authority_granted"] is False
    assert ineligible["disposition"] == "STOP"


def test_result_continuation_uses_typed_assignment_action_and_proof_reresolution() -> None:
    assignment = reconcile_action_result(
        result={
            "kind": "agentic-workspace/assignment-lifecycle-result/v1",
            "status": "awaiting-admission",
            "outcome": "applied",
            "assignment_id": "assignment-1",
            "assignment_revision": "rev-1",
            "run_id": "run-1",
        }
    )
    proof = reconcile_action_result(
        result={"kind": "agentic-workspace/proof-route-repair-result/v1", "status": "repaired", "outcome": "applied"}
    )

    assert assignment["operation_invocation"]["operation_id"] == "assignment.admit"
    assert assignment["operation_invocation"]["arguments"]["assignment_revision"] == "rev-1"
    assert proof["action"] == "rerun-current-proof-route"


def test_result_continuation_rejects_stale_replay_and_preserves_semantic_judgment() -> None:
    stale = reconcile_action_result(
        result={
            "kind": "agentic-planning/semantic-mutation-result/v1",
            "status": "stale-owner-revision",
            "stale": True,
            "currentness_owner": "planning-owner",
            "replacement_action": "resolve-current-semantic-mutation",
        }
    )
    decision = reconcile_action_result(
        result={
            "kind": "agentic-workspace/orchestration-frontier-result/v1",
            "status": "current",
            "semantic_decision_required": True,
            "decision": "revise-slice-or-stop",
            "source_facts": {"worker_reported_scope_change": True},
        }
    )

    assert stale["action"] == "resolve-current-semantic-mutation"
    assert "must not be retried" in stale["reason"]
    assert decision["status"] == "decision-required"
    assert decision["source_facts"] == {"worker_reported_scope_change": True}


def test_verification_partition_reuses_semantic_contribution_across_attempt_retry() -> None:
    semantic = {"slice_id": "slice-1", "semantic_revision": "sem-1", "acceptance": ["tests pass"]}
    policy = {"id": "proof-policy", "revision": "p1"}
    first = verification_contributions(
        semantic_slice=semantic,
        assignment_attempt={"assignment_id": "a", "assignment_revision": "r1", "run_id": "run-1", "target": "worker-a"},
        proof_policy=policy,
    )
    retry = verification_contributions(
        semantic_slice={**semantic, "acceptance": ["consumer-local text must not replace current owner truth"]},
        assignment_attempt={"assignment_id": "a", "assignment_revision": "r2", "run_id": "run-2", "target": "worker-b"},
        proof_policy=policy,
        previous_partition=first,
    )
    changed = verification_contributions(
        semantic_slice={**semantic, "semantic_revision": "sem-2"},
        assignment_attempt={"assignment_id": "a", "assignment_revision": "r2", "run_id": "run-2", "target": "worker-b"},
        proof_policy=policy,
        previous_partition=first,
    )

    assert first["semantic_contribution_revision"] == retry["semantic_contribution_revision"]
    assert retry["semantic"] == first["semantic"]
    assert retry["semantic_reuse"]["status"] == "reused"
    assert retry["semantic_reuse"]["invalidated_dependencies"] == []
    assert first["attempt_contribution_revision"] != retry["attempt_contribution_revision"]
    assert retry["semantic_contribution_revision"] != changed["semantic_contribution_revision"]
    assert changed["semantic_reuse"]["status"] == "resolution-required"
    assert changed["semantic_reuse"]["invalidated_dependencies"] == ["planning_slice"]
    assert first["target_selection_authority"] is False
