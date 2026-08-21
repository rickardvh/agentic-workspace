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
    cache.write_text(json.dumps(_stack()), encoding="utf-8")
    monkeypatch.setattr(transitions, "_current_branch", lambda _root: "codex/open-issues-lifecycle")

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
    assert "review-stack-2627-lifecycle" in result["path"]
