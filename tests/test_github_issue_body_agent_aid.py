import importlib.util
import json
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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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


def test_issue_body_renders_from_archived_lane_record(tmp_path: Path) -> None:
    lane_path = tmp_path / ".agentic-workspace" / "planning" / "lanes" / "archive" / "lane-example.lane.json"
    _write_json(
        lane_path,
        {
            "kind": "planning-lane/v1",
            "id": "lane-example",
            "title": "Example Lane",
            "lane_outcome": "The lane issue body is rendered from structured lane data.",
            "purpose_for_parent": "Avoid shell property extraction from lane objects.",
            "proof_strategy": "Issue-body tests prove source loading.",
            "residual_lane_work": "Remaining lane work stays routed to Planning.",
            "parent_decomposition_ref": ".agentic-workspace/planning/decompositions/example.decomposition.json",
        },
    )

    rendered = issue_body.render_issue_request(issue_body.request_from_lane(target_root=tmp_path, lane_id="lane-example"))

    assert rendered["title"] == "[Workspace]: Example Lane"
    assert rendered["source_refs"] == [
        {
            "kind": "planning-lane",
            "id": "lane-example",
            "path": ".agentic-workspace/planning/lanes/archive/lane-example.lane.json",
        },
        {
            "kind": "planning-decomposition",
            "path": ".agentic-workspace/planning/decompositions/example.decomposition.json",
        },
    ]
    assert "## Problem / intent\nAvoid shell property extraction from lane objects." in rendered["body"]
    assert "## Acceptance / success signal\nIssue-body tests prove source loading." in rendered["body"]


def test_issue_body_renders_from_decomposition_candidate_lane(tmp_path: Path) -> None:
    decomposition_path = tmp_path / ".agentic-workspace" / "planning" / "decompositions" / "example.decomposition.json"
    _write_json(
        decomposition_path,
        {
            "kind": "planning-decomposition/v1",
            "larger_intended_outcome": "Create GitHub issues from Planning decomposition data.",
            "parent_acceptance": {"parent_proof_required": "All candidate lane issue bodies render from structured fields."},
            "candidate_lanes": [
                {
                    "id": "lane-one",
                    "title": "Lane One",
                    "outcome": "Wrong lane.",
                    "owner_surface": "wrong",
                    "proof": "wrong",
                },
                {
                    "id": "lane-two",
                    "title": "Lane Two",
                    "outcome": "The selected decomposition lane renders an issue body.",
                    "owner_surface": ".agentic-workspace/planning/lanes/lane-two.lane.json",
                    "proof": "The source-loading test selects lane-two.",
                    "slice_contribution_to_parent": "Directly addresses Planning-derived issue generation.",
                    "residual_parent_intent": "Further lanes remain in the decomposition.",
                },
            ],
        },
    )

    rendered = issue_body.render_issue_request(
        issue_body.request_from_decomposition(
            target_root=tmp_path,
            decomposition=".agentic-workspace/planning/decompositions/example.decomposition.json",
            lane_id="lane-two",
        )
    )

    assert rendered["title"] == "[Workspace]: Lane Two"
    assert rendered["source_refs"] == [
        {
            "kind": "planning-decomposition",
            "id": "lane-two",
            "path": ".agentic-workspace/planning/decompositions/example.decomposition.json",
        }
    ]
    assert "## Problem / intent\nDirectly addresses Planning-derived issue generation." in rendered["body"]
    assert "## Required residual intent\nFurther lanes remain in the decomposition." in rendered["body"]


def test_issue_body_cli_rejects_mixed_structured_and_field_modes(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    _write_json(
        request_path,
        {
            "kind": "agentic-workspace/issue-body-request/v1",
            "template": "direction",
            "fields": {"problem_intent": {"kind": "markdown", "value": "Example"}},
        },
    )

    try:
        issue_body.main(["--input-json", str(request_path), "--kind", "direction"])
    except SystemExit as exc:
        assert "--input-json" in str(exc) or "structured source modes" in str(exc)
    else:
        raise AssertionError("input-json must be mutually exclusive with --kind")

    try:
        issue_body.main(["--from-decomposition", "example.json", "--field", "problem_intent=Example"])
    except SystemExit as exc:
        assert "structured source modes" in str(exc)
    else:
        raise AssertionError("source loading must be mutually exclusive with raw --field")


def test_issue_body_aid_validation_uses_structured_input_not_semantic_shell_fields() -> None:
    payload = json.loads(
        (_REPO_ROOT / ".agentic-workspace" / "agent-aids" / "scripts" / "github-issue-body" / "manifest.json").read_text(encoding="utf-8")
    )
    commands = payload["validation"]["commands"]

    assert any("--input-json" in command or "--from-lane" in command or "--from-decomposition" in command for command in commands)
    assert not any("--field" in command for command in commands)
