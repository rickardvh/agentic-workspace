from __future__ import annotations

from agentic_workspace.orchestration import verification_contributions
from agentic_workspace.resolved_decision_reuse import reuse_verification_semantic_contribution


def _partition(*, semantic_revision: str = "sem-1", proof_revision: str = "p1") -> dict:
    return verification_contributions(
        semantic_slice={
            "slice_id": "slice-1",
            "semantic_revision": semantic_revision,
            "acceptance": ["tests pass"],
        },
        assignment_attempt={
            "assignment_id": "assignment-1",
            "assignment_revision": "attempt-1",
            "run_id": "run-1",
            "target": "worker-a",
            "transport": "host-native",
        },
        proof_policy={"id": "proof-policy", "revision": proof_revision},
    )


def test_verification_semantic_conclusion_reuses_across_attempt_changes() -> None:
    previous = _partition()

    reused = reuse_verification_semantic_contribution(
        previous_partition=previous,
        semantic_slice={
            "slice_id": "slice-1",
            "semantic_revision": "sem-1",
            "status": "in-flight",
        },
        proof_policy={"id": "proof-policy", "revision": "p1"},
    )

    assert reused["status"] == "reused"
    assert reused["decision_revision"] == previous["semantic_contribution_revision"]
    assert reused["semantic"] == previous["semantic"]
    assert reused["invalidated_dependencies"] == []
    assert reused["attempt_identity_used"] is False
    assert reused["target_selection_authority"] is False


def test_verification_semantic_conclusion_invalidates_only_proof_policy_change() -> None:
    previous = _partition()

    stale = reuse_verification_semantic_contribution(
        previous_partition=previous,
        semantic_slice={"slice_id": "slice-1", "semantic_revision": "sem-1"},
        proof_policy={"id": "proof-policy", "revision": "p2"},
    )

    assert stale["status"] == "resolution-required"
    assert stale["semantic"] is None
    assert stale["invalidated_dependencies"] == ["proof_policy"]
    assert stale["re_resolution"] == {
        "owner": "verification",
        "action": "resolve-semantic-verification-contribution",
        "reason_code": "resolved-decision-dependency-changed",
    }


def test_verification_semantic_conclusion_invalidates_only_planning_semantic_change() -> None:
    previous = _partition()

    stale = reuse_verification_semantic_contribution(
        previous_partition=previous,
        semantic_slice={"slice_id": "slice-1", "semantic_revision": "sem-2"},
        proof_policy={"id": "proof-policy", "revision": "p1"},
    )

    assert stale["status"] == "resolution-required"
    assert stale["invalidated_dependencies"] == ["planning_slice"]


def test_unversioned_proof_policy_uses_content_digest_for_currentness() -> None:
    previous = verification_contributions(
        semantic_slice={"slice_id": "slice-1", "semantic_revision": "sem-1"},
        assignment_attempt={"assignment_id": "assignment-1", "assignment_revision": "attempt-1"},
        proof_policy={"id": "proof-policy", "independence": "required"},
    )

    current = reuse_verification_semantic_contribution(
        previous_partition=previous,
        semantic_slice={"slice_id": "slice-1", "semantic_revision": "sem-1"},
        proof_policy={"id": "proof-policy", "independence": "required"},
    )
    changed = reuse_verification_semantic_contribution(
        previous_partition=previous,
        semantic_slice={"slice_id": "slice-1", "semantic_revision": "sem-1"},
        proof_policy={"id": "proof-policy", "independence": "advisory"},
    )

    assert current["status"] == "reused"
    assert changed["status"] == "resolution-required"
    assert changed["invalidated_dependencies"] == ["proof_policy"]
