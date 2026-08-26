from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_start_routes_bounded_external_issue_filing_without_checked_in_planning(tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0
    capsys.readouterr()

    task = (
        "File exactly five duplicate-safe preliminary GitHub issues for already-identified functionality candidates, "
        "without editing product source, merging PRs, or closing work."
    )
    assert cli.main(["start", "--target", str(tmp_path), "--task", task, "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    decision = payload["decision_packet"]
    route = workspace_runtime_planning._bounded_external_issue_effect_payload(
        task_text=task,
        changed_paths=[],
        active_planning_present=False,
    )

    assert decision["action"]["id"] == "perform-bounded-external-issue-filing"
    assert decision["effects"]["workflow_required"] is False
    assert decision["effects"]["implementation_allowed"] is True
    assert route["status"] == "direct-route-admitted"
    assert route["effect_class"] == "external-issue-filing"
    assert route["planning_custody_required"] is False
    assert route["required_safety_checks"] == [
        "duplicate-search",
        "issue-shaping-and-template-compliance",
        "explicit-external-write-authority",
        "truthful-post-create-reconciliation",
    ]
    assert not list((tmp_path / ".agentic-workspace/planning/execplans").glob("*.plan.json"))
    assert not (tmp_path / ".agentic-workspace/planning/integration-proposals").exists()


def test_bounded_external_issue_route_is_provider_neutral_and_fails_closed_for_durable_work() -> None:
    provider_neutral = workspace_runtime_planning._bounded_external_issue_effect_payload(
        task_text=(
            "Refine these three already-identified duplicate-safe tracker tickets without implementing or changing "
            "repository files, without merging, and without closing them."
        ),
        changed_paths=[],
        active_planning_present=False,
    )
    assert provider_neutral["status"] == "direct-route-admitted"
    assert "GitHub-specific" in provider_neutral["provider_boundary"]

    counterexamples = [
        (
            "Create exactly two duplicate-safe parent issues for an unresolved decomposition; do not implement, merge, or close.",
            [],
            False,
        ),
        (
            "File exactly two duplicate-safe issues then implement and edit source; do not merge or close.",
            ["src/app.py"],
            False,
        ),
        (
            "File exactly two already-identified duplicate-safe issues; do not implement, merge, or close.",
            [],
            True,
        ),
    ]
    for task, changed_paths, active in counterexamples:
        route = workspace_runtime_planning._bounded_external_issue_effect_payload(
            task_text=task,
            changed_paths=changed_paths,
            active_planning_present=active,
        )
        assert route["status"] == "not-admitted"
        assert route["planning_custody_required"] is True
