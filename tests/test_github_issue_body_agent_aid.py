import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / ".agentic-workspace" / "agent-aids" / "scripts" / "github-issue-body" / "new_github_issue_body.py"
)
_SPEC = importlib.util.spec_from_file_location("new_github_issue_body", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
issue_body = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = issue_body
_SPEC.loader.exec_module(issue_body)


def test_direction_issue_body_uses_repo_template_fields() -> None:
    rendered = issue_body.render_issue(
        kind="direction",
        title="Example",
        fields={
            "problem_intent": "Make the right issue shape cheap.",
            "intended_outcome": "Agents use the repo template fields.",
            "larger_picture": "Issue intake remains reviewable.",
            "scope": "In scope: body generation.",
            "acceptance": "Generated body has template headings.",
        },
    )

    assert rendered["title"] == "[Workspace]: Example"
    assert rendered["labels"] == ["planning"]
    assert "## Problem / intent\nMake the right issue shape cheap." in rendered["body"]
    assert "## Acceptance / success signal\nGenerated body has template headings." in rendered["body"]


def test_review_issue_body_defaults_dropdowns_and_labels() -> None:
    rendered = issue_body.render_issue(
        kind="review",
        title="Template friction",
        fields={
            "observed_problem": "Issue creation bypassed templates.",
            "evidence": "#822 #823 #824",
            "desired_signal": "A cheap body scaffold.",
            "outcome": "Agents preserve form fields.",
        },
    )

    assert rendered["title"] == "[Review]: Template friction"
    assert rendered["labels"] == ["review"]
    assert "## Issue kind\nReview / trust gap" in rendered["body"]
    assert "## Should the product absorb this first?\nYes" in rendered["body"]


def test_issue_body_normalizes_duplicate_template_title_prefix() -> None:
    rendered = issue_body.render_issue(kind="review", title="[Review]: Template friction", fields={})

    assert rendered["title"] == "[Review]: Template friction"
    assert rendered["title_prefix"] == "[Review]:"
    assert rendered["normalized_title"] == "Template friction"
    assert rendered["duplicate_prefix_normalized"] is True
