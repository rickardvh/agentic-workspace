from __future__ import annotations

import pytest

import repo_planning_bootstrap.installer as installer


@pytest.mark.parametrize(
    ("claim", "decision", "blocked", "retention_skipped", "slice_allowed", "larger_allowed"),
    [
        ("slice", "archive-and-close", False, False, True, False),
        ("lane", "archive-and-close", False, False, True, True),
        ("epic", "archive-but-keep-lane-open", False, True, True, False),
        ("lane", "archive-and-close", True, False, False, False),
    ],
)
def test_closeout_completion_options_isolate_claim_policy(
    claim: str,
    decision: str,
    blocked: bool,
    retention_skipped: bool,
    slice_allowed: bool,
    larger_allowed: bool,
) -> None:
    options = installer._closeout_completion_options(
        plan="plan-alpha",
        normalized_claim=claim,
        closure_decision=decision,
        continuation_owner="ROADMAP.md",
        blocked=blocked,
        retention_skipped=retention_skipped,
    )
    by_id = {option["id"]: option for option in options}

    assert by_id["claim-slice-complete"]["allowed"] is slice_allowed
    assert by_id["close-larger-intent"]["allowed"] is larger_allowed
    assert by_id["host-side-issue-closure"]["allowed"] is False
    assert ("archive-retention-status" in by_id) is retention_skipped
