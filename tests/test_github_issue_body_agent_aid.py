import importlib.util
import sys
from pathlib import Path

import yaml

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / ".agentic-workspace" / "agent-aids" / "scripts" / "github-issue-body" / "new_github_issue_body.py"
)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("new_github_issue_body", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
issue_body = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = issue_body
_SPEC.loader.exec_module(issue_body)


def test_issue_templates_include_completion_boundary_fields() -> None:
    required_fields = {
        "final_satisfaction",
        "bounded_slice_success",
        "partial_pr_may_close",
        "required_follow_up_owner",
        "required_residual_intent",
        "evidence_required_for_final_completion",
    }

    for template_path in sorted((_REPO_ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml")):
        if template_path.name == "config.yml":
            continue
        payload = yaml.safe_load(template_path.read_text(encoding="utf-8"))
        field_ids = {
            str(item.get("id", "")) for item in payload.get("body", []) if isinstance(item, dict) and item.get("type") != "markdown"
        }
        assert required_fields.issubset(field_ids), template_path


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
    assert "## Partial PR may close\nno" in rendered["body"]
    assert "## Final satisfaction\nFinal completion requires satisfying: Agents use the repo template fields." in rendered["body"]
    assert "## Evidence required for final completion\nFinal completion evidence must prove the final intended state" in rendered["body"]


def test_direction_issue_body_preserves_completion_boundary_fields() -> None:
    rendered = issue_body.render_issue(
        kind="direction",
        title="Completion boundary",
        fields={
            "problem_intent": "Partial progress was confused with final closure.",
            "intended_outcome": "Issues preserve final satisfaction separately from useful slices.",
            "larger_picture": "Closeout remains honest across PR slices.",
            "scope": "In scope: issue authoring.",
            "acceptance": "Generated body has final and partial closure fields.",
            "final_satisfaction": "The parent issue closes only when closeout and issue authoring both preserve the boundary.",
            "bounded_slice_success": "A first slice can add fields and leave the parent open.",
            "partial_pr_may_close": "no",
            "required_follow_up_owner": "#1187",
            "required_residual_intent": "Closeout examples still need proof.",
            "evidence_required_for_final_completion": "Issue body helper output and closeout_trust example.",
        },
    )

    assert (
        "## Final satisfaction\nThe parent issue closes only when closeout and issue authoring both preserve the boundary."
        in rendered["body"]
    )
    assert "## Bounded slice success\nA first slice can add fields and leave the parent open." in rendered["body"]
    assert "## Partial PR may close\nno" in rendered["body"]
    assert "## Required follow-up owner\n#1187" in rendered["body"]
    assert "## Required residual intent\nCloseout examples still need proof." in rendered["body"]
    assert "## Evidence required for final completion\nIssue body helper output and closeout_trust example." in rendered["body"]


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
    assert "## Partial PR may close\nno" in rendered["body"]
    assert "## Final satisfaction\nFinal completion requires satisfying: Agents preserve form fields." in rendered["body"]


def test_bug_issue_body_defaults_completion_boundary_fields() -> None:
    rendered = issue_body.render_issue(
        kind="bug",
        title="Regression",
        fields={
            "current_behavior": "The command claims final closure after a partial fix.",
            "expected_behavior": "The command preserves the remaining bug-fix intent.",
            "reproduction": "1. Run the closeout command.",
            "product_reasoning": "The package owns this guidance.",
        },
    )

    assert rendered["title"] == "[Bug]: Regression"
    assert rendered["labels"] == ["bug"]
    assert (
        "## Final satisfaction\nFinal completion requires satisfying: The command preserves the remaining bug-fix intent."
        in rendered["body"]
    )
    assert "## Bounded slice success\nA partial slice may land" in rendered["body"]
    assert "## Partial PR may close\nno" in rendered["body"]


def test_issue_body_normalizes_duplicate_template_title_prefix() -> None:
    rendered = issue_body.render_issue(kind="review", title="[Review]: Template friction", fields={})

    assert rendered["title"] == "[Review]: Template friction"
    assert rendered["title_prefix"] == "[Review]:"
    assert rendered["normalized_title"] == "Template friction"
    assert rendered["duplicate_prefix_normalized"] is True


def test_issue_body_renders_typed_structured_request() -> None:
    rendered = issue_body.render_issue_request(
        {
            "kind": "agentic-workspace/issue-body-request/v1",
            "template": "direction",
            "title": "Structured lane body",
            "fields": {
                "problem_intent": {
                    "kind": "markdown",
                    "value": "Create issue bodies from typed request data instead of shell-composed strings.",
                },
                "intended_outcome": {
                    "kind": "markdown",
                    "value": "Planning-derived issue bodies render from structured data.",
                },
                "acceptance": {
                    "kind": "markdown",
                    "value": "The generated body carries template headings and source refs.",
                },
            },
            "source_refs": [
                {
                    "kind": "planning-lane",
                    "id": "lane-example",
                    "path": ".agentic-workspace/planning/lanes/lane-example.lane.json",
                }
            ],
        }
    )

    assert rendered["request_kind"] == "agentic-workspace/issue-body-request/v1"
    assert rendered["title"] == "[Workspace]: Structured lane body"
    assert rendered["source_refs"][0]["id"] == "lane-example"
    assert "## Problem / intent\nCreate issue bodies from typed request data" in rendered["body"]
    assert "## Final satisfaction\nFinal completion requires satisfying: Planning-derived issue bodies" in rendered["body"]


def test_issue_body_request_rejects_untyped_fields() -> None:
    try:
        issue_body.render_issue_request(
            {
                "kind": "agentic-workspace/issue-body-request/v1",
                "template": "direction",
                "title": "Untyped body",
                "fields": {"problem_intent": "shell-composed scalar"},
            }
        )
    except ValueError as exc:
        assert "schema error" in str(exc)
        assert "problem_intent" in str(exc)
    else:
        raise AssertionError("render_issue_request should require typed field objects")
