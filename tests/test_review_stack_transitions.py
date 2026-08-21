from __future__ import annotations

import json
from pathlib import Path

from agentic_workspace import review_stack_transitions as transitions


def _stack() -> dict:
    return {
        "current_pr_number": "2630",
        "stack_members": [
            {"pr_number": "2627", "branch": "codex/open-issues-lifecycle", "changed_paths": ["shared.py"]},
            {"pr_number": "2630", "branch": "codex/open-issues-product-closure", "changed_paths": ["shared.py"]},
        ],
    }


def _admitted_stack() -> dict:
    observation = {
        "kind": transitions.TOPOLOGY_OBSERVATION_KIND,
        "status": "admitted",
        "repository": "example/project",
        "current_branch": "codex/open-issues-lifecycle",
        "current_head_sha": "abc123",
        "current_pr_number": "2627",
        "observation_digest": "sha256:observation",
    }
    return {
        "repository": "example/project",
        "topology_observation": observation,
        "stack_members": [
            {
                "pr_number": "2627",
                "branch": "codex/open-issues-lifecycle",
                "base_branch": "master",
                "head_sha": "abc123",
                "changed_paths": ["shared.py"],
            }
        ],
    }


def test_branch_identity_precedes_ambiguous_changed_paths_and_stale_top_pointer() -> None:
    selected = transitions._select_member(
        _stack(),
        pr_number="",
        branch="codex/open-issues-lifecycle",
        changed_paths=["shared.py"],
    )
    assert selected["pr_number"] == "2627"


def test_explicit_pr_identity_precedes_branch_identity() -> None:
    selected = transitions._select_member(
        _stack(),
        pr_number="2630",
        branch="codex/open-issues-lifecycle",
        changed_paths=["shared.py"],
    )
    assert selected["pr_number"] == "2630"


def test_transition_record_binds_to_checked_out_branch_member(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / transitions.STACK_CACHE_PATH
    cache.parent.mkdir(parents=True)
    stack = _admitted_stack()
    cache.write_text(json.dumps(stack), encoding="utf-8")
    monkeypatch.setattr(transitions, "_current_branch", lambda _root: "codex/open-issues-lifecycle")
    monkeypatch.setattr(
        transitions,
        "validate_admitted_pr_topology",
        lambda **_kwargs: (True, "current", stack["topology_observation"]),
    )

    result = transitions.record_review_stack_transition(
        target_root=tmp_path,
        phase="review-correction",
        phase_after="review-proof",
        command="agentic-workspace implement --changed shared.py --format json",
        outcome="executed",
        next_action_id="run-focused-proof",
        changed_paths=["shared.py"],
    )

    assert result["pr_number"] == "2627"
    assert result["head_sha"] == "abc123"
    assert "review-stack-2627-lifecycle" in result["path"]

    record = json.loads((tmp_path / result["path"]).read_text(encoding="utf-8"))
    lifecycle = json.loads(record["scope"][0])
    assert lifecycle["review_owner_identity"] == {
        "repository": "example/project",
        "branch": "codex/open-issues-lifecycle",
        "pr_number": "2627",
        "pr_state": "open",
        "head_sha": "abc123",
        "topology_observation_digest": "sha256:observation",
    }
    assert lifecycle["review_owner_revision"] == result["owner_revision"]

    repeated = transitions.record_review_stack_transition(
        target_root=tmp_path,
        phase="review-correction",
        phase_after="review-proof",
        command="agentic-workspace implement --changed shared.py --format json",
        outcome="executed",
        next_action_id="run-focused-proof",
        changed_paths=["shared.py"],
    )
    assert repeated["status"] == "already-recorded"
    assert len(json.loads(json.loads((tmp_path / result["path"]).read_text(encoding="utf-8"))["scope"][0])["transitions"]) == 1


def test_transition_rejects_stale_or_mismatched_topology_without_mutating(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / transitions.STACK_CACHE_PATH
    cache.parent.mkdir(parents=True)
    stack = _admitted_stack()
    cache.write_text(json.dumps(stack), encoding="utf-8")
    monkeypatch.setattr(transitions, "_current_branch", lambda _root: "codex/open-issues-lifecycle")
    monkeypatch.setattr(
        transitions,
        "validate_admitted_pr_topology",
        lambda **_kwargs: (False, "topology-head-stale", stack["topology_observation"]),
    )

    result = transitions.record_review_stack_transition(
        target_root=tmp_path,
        phase="review-correction",
        phase_after="review-proof",
        command="agentic-workspace implement --format json",
        outcome="executed",
        next_action_id="run-focused-proof",
        changed_paths=["shared.py"],
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "topology-head-stale"
    assert not (tmp_path / ".agentic-workspace" / "planning" / "reviews").exists()


def test_transition_rejects_explicit_wrong_pr_identity(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / transitions.STACK_CACHE_PATH
    cache.parent.mkdir(parents=True)
    stack = _admitted_stack()
    cache.write_text(json.dumps(stack), encoding="utf-8")
    monkeypatch.setattr(transitions, "_current_branch", lambda _root: "codex/open-issues-lifecycle")
    monkeypatch.setattr(
        transitions,
        "validate_admitted_pr_topology",
        lambda **_kwargs: (True, "current", stack["topology_observation"]),
    )

    result = transitions.record_review_stack_transition(
        target_root=tmp_path,
        phase="review-correction",
        phase_after="review-proof",
        command="agentic-workspace implement --format json",
        outcome="executed",
        next_action_id="run-focused-proof",
        pr_number="9999",
    )

    assert result["status"] == "skipped"
    assert "does not match" in result["reason"]
