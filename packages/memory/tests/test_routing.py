from __future__ import annotations

import sys as _sys
import tomllib

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *


def test_route_memory_adds_routing_baseline_and_runtime_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    required = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "required"}
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}

    assert ".agentic-workspace/memory/repo/index.md" in required
    assert ".agentic-workspace/memory/repo/domains/README.md" in suggested
    assert ".agentic-workspace/memory/repo/runbooks/README.md" in suggested
    assert ".agentic-workspace/memory/repo/current/project-state.md" not in suggested
    assert ".agentic-workspace/memory/repo/current/task-context.md" not in suggested
    assert result.route_summary["routed_note_count"] == 3
    assert result.route_summary["required_count"] == 1
    assert result.route_summary["optional_count"] == 2
    assert result.route_summary["exceeded_target"] == "no"
    assert result.missing_note_hint == "If routing missed something, record which note was missing."


def test_route_memory_adds_architecture_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["src/architecture/schema.py"])
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}

    assert ".agentic-workspace/memory/repo/invariants/README.md" in suggested
    assert ".agentic-workspace/memory/repo/decisions/README.md" in suggested
    assert ".agentic-workspace/memory/repo/current/project-state.md" not in suggested
    assert ".agentic-workspace/memory/repo/current/task-context.md" not in suggested
    assert result.route_summary["exceeded_target"] == "yes"
    assert "justification" in result.route_summary


def test_route_memory_reports_low_confidence_for_index_only_fallbacks(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])

    assert result.route_summary["confidence"] == "low"
    assert result.route_summary["fallback_match_count"] >= 1
    assert "routing relied on fallback signals" in " ".join(result.route_summary["confidence_reasons"])


def test_route_memory_returns_no_payload_for_direct_task_without_memory_match(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    memory_root = target / ".agentic-workspace" / "memory" / "repo"
    (memory_root / "domains").mkdir(parents=True, exist_ok=True)
    (memory_root / "index.md").write_text("# Memory Index\n", encoding="utf-8")
    (memory_root / "domains" / "api.md").write_text("# API\n", encoding="utf-8")
    (memory_root / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
routing_only = true

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = ["src/api/**"]
stale_when = ["src/api/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["README.md"], stage="implement")

    assert result.actions == []
    assert result.route_summary["decision"] == "no-memory-required"
    assert result.route_summary["routed_note_count"] == 0
    assert result.route_summary["baseline_note_count"] == 0
    assert result.route_summary["confidence"] == "high"


def test_checked_in_memory_curation_has_bounded_routes_and_disposition_evidence() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    manifest = tomllib.loads((repo_root / ".agentic-workspace/memory/repo/manifest.toml").read_text(encoding="utf-8"))
    notes = manifest["notes"]

    assert len(notes) == 6
    assert set(notes) == {
        ".agentic-workspace/memory/repo/index.md",
        ".agentic-workspace/memory/repo/domains/example-runtime-boundary.md",
        ".agentic-workspace/memory/repo/domains/memory-package-context.md",
        ".agentic-workspace/memory/repo/domains/planning-package-context.md",
        ".agentic-workspace/memory/repo/decisions/installed-system-consolidation-2026-04-05.md",
        ".agentic-workspace/memory/repo/mistakes/recurring-failures.md",
    }
    evidence = (repo_root / "docs/maintainer/context-memory-curation.md").read_text(encoding="utf-8")
    assert "Retained manifest routes | 6" in evidence
    assert "Removed files | 19" in evidence
    assert "Proof procedures and active work state are intentionally excluded" in evidence


def test_route_memory_does_not_invent_test_remediation_for_plain_mistake_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    installer.create_memory_note(
        target=target,
        slug="local-python-invocation",
        folder="mistakes",
        note_type="mistake",
        summary="Bare python is unavailable in this local shell.",
        applies_to=["scripts/run_agentic_workspace.py"],
        routes_from=["python", "shell"],
        memory_role="durable_truth",
    )

    result = installer.route_memory(target=target, surfaces=["python", "shell"])
    pressure_actions = [action for action in result.actions if action.role == "improvement-pressure"]

    assert pressure_actions == []


def test_route_memory_falls_back_to_index_when_manifest_is_incomplete(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}

    assert ".agentic-workspace/memory/repo/domains/README.md" in suggested
    assert ".agentic-workspace/memory/repo/runbooks/README.md" in suggested


def test_route_memory_does_not_treat_routing_baseline_as_surface_coverage(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        _memory_manifest_text(),
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["docker/compose.yml"])
    required = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "required"}
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}
    manual_reviews = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "manual review"}

    assert ".agentic-workspace/memory/repo/index.md" in required
    assert ".agentic-workspace/memory/repo/domains/README.md" in suggested
    assert ".agentic-workspace/memory/repo/runbooks/README.md" in suggested
    assert ".agentic-workspace/memory/repo/index.md" not in manual_reviews


def test_route_memory_only_suggests_task_context_on_explicit_input(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=[".agentic-workspace/memory/repo/current/task-context.md"])

    assert any(
        action.kind == "optional"
        and action.path.relative_to(target).as_posix() == ".agentic-workspace/memory/repo/current/task-context.md"
        and "explicit current-context input" in action.detail
        for action in result.actions
    )


def test_sync_memory_without_input_returns_guidance(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.sync_memory(target=target)

    assert len(result.actions) == 1
    assert result.actions[0].kind == "manual review"
    assert "provide --files/--notes" in result.actions[0].detail


def test_sync_memory_with_explicit_file_produces_recommendations(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.sync_memory(target=target, files=["tests/test_cli.py"])

    assert any(action.kind in {"review", "update", "update index"} for action in result.actions)


def test_path_match_pattern_treats_double_star_as_zero_or_more_directories() -> None:
    assert installer._path_matches_pattern("tests/test_api.py", "tests/**/*.py")
    assert installer._path_matches_pattern("tests/unit/test_api.py", "tests/**/*.py")


def test_route_memory_json_includes_summary_and_missing_note_hint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    data = json.loads(installer.format_result_json(result))

    assert data["route_summary"]["routed_note_count"] == 3
    assert data["route_summary"]["required_count"] == 1
    assert data["route_summary"]["optional_count"] == 2
    assert data["missing_note_hint"] == "If routing missed something, record which note was missing."


def test_route_review_handles_missing_feedback_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.review_routes(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md"
        and action.kind == "current"
        and "absent by default" in action.detail
        for action in result.actions
    )


def test_route_review_reports_missed_note_case_that_now_passes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary == {
        "reviewed_case_count": 1,
        "still_missed_count": 0,
        "still_over_routed_count": 0,
        "unresolved_case_count": 0,
    }
    assert result.review_cases[0]["matched"] is True


def test_route_review_reports_missed_note_case_that_still_fails(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: wrong-expected-note\n"
                "Task surface summary\n"
                "- Validation work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/runbooks/runtime.md\n"
                "Why it was needed\n"
                "- Pretend this note should have been routed.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary["still_missed_count"] == 1
    assert result.review_cases[0]["matched"] is False


def test_route_review_marks_incomplete_case_unresolved(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=["### Case: incomplete\nTask surface summary\n- Missing explicit files and expected note.\nStatus\n- open"]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary["unresolved_case_count"] == 1
    assert result.review_cases[0]["unresolved"] is True


def test_route_review_json_includes_summary_and_cases(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    data = json.loads(installer.format_result_json(installer.review_routes(target=target)))

    assert data["review_summary"]["reviewed_case_count"] == 1
    assert data["review_cases"][0]["case_type"] == "missed_note"


def test_route_report_handles_missing_feedback_and_fixture_inputs(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 0
    assert result.route_report_summary["fixtures"]["fixture_count"] == 0
    assert "No parseable routing-feedback cases yet" in result.route_report_summary["feedback_guidance"]
    assert "No routing fixtures found" in result.route_report_summary["fixture_guidance"]


def test_route_report_supports_feedback_cases_only(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Validation work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 1
    assert result.route_report_summary["fixtures"]["fixture_count"] == 0
    assert result.route_report_feedback_cases[0]["matched"] is True


def test_route_report_supports_feedback_cases_and_fixtures(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_routing_fixture_file(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: runtime-domain\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why it was needed\n"
                "- Validation guidance should be routed for this surface.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- tuned"
            ]
        ),
    )

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["tuned_case_count"] == 1
    assert result.route_report_summary["fixtures"]["fixture_count"] == 1
    assert result.route_report_summary["working_set"]["average_routed_note_count"] == 3.0


def test_route_report_json_includes_summary_feedback_cases_and_fixture_results(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")

    data = json.loads(installer.format_result_json(installer.report_routes(target=target)))

    assert "route_report_summary" in data
    assert "route_report_feedback_cases" in data
    assert "route_report_fixture_results" in data
    assert "missed_note" in data["route_report_summary"]
    assert "over_routing" in data["route_report_summary"]
    assert "routing_confidence" in data["route_report_summary"]
    assert "startup_cost" in data["route_report_summary"]


def test_route_report_keeps_missed_and_over_routing_counts_separate(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "missed-note-regression.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: missed\n"
                "Task surface summary\n"
                "- Runtime service work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- .agentic-workspace/memory/repo/runbooks/runtime.md\n"
                "Why it was needed\n"
                "- Missing note case.\n"
                "Expected routing signal\n"
                "- routes_from: scripts/check/check_memory_freshness.py\n"
                "Status\n"
                "- open"
            ],
            over_cases=[
                "### Case: over\n"
                "Task surface summary\n"
                "- Validation work.\n"
                "Files\n"
                "- scripts/check/check_memory_freshness.py\n"
                "Surfaces\n"
                "- tests\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Unexpected notes\n"
                "- .agentic-workspace/memory/repo/mistakes/recurring-failures.md\n"
                "Why they were unnecessary\n"
                "- Over-routing case.\n"
                "Status\n"
                "- open"
            ],
        ),
    )

    result = installer.report_routes(target=target)
    feedback = result.route_report_summary["feedback"]

    assert feedback["missed_note_case_count"] == 1
    assert feedback["over_routing_case_count"] == 1
    assert feedback["still_missed_count"] == 1
    assert feedback["still_over_routed_count"] == 1


def test_route_report_handles_invalid_fixture_without_crashing(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    _write_routing_fixture_file(target, "invalid.json", raw_text="{ not json }\n")

    result = installer.report_routes(target=target)

    assert result.route_report_summary["fixtures"]["invalid_fixture_count"] == 1
    assert result.route_report_fixture_results[0]["valid"] is False
    assert "invalid JSON" in result.route_report_fixture_results[0]["error"]


def test_route_report_generated_outputs_preserve_failure_detail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")
    failing = _load_routing_fixture("runtime-basic.json")
    failing["name"] = "failing"
    failing["expected_optional"] = [".agentic-workspace/memory/repo/domains/wrong.md"]
    _write_routing_fixture_file(target, "failing.json", payload=failing)
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=["### Case: unresolved\nTask surface summary\n- Missing explicit routing data.\nStatus\n- open"]
        ),
    )

    assert cli.main(["route-report", "--target", str(target), "--verbose", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    serialized = json.dumps(payload)

    assert "fixture 'failing' fails" in serialized
    assert "case 'unresolved' is unresolved" in serialized
    assert "fixture 'runtime-basic' fails" not in serialized

    assert cli.main(["route-report", "--target", str(target), "--verbose"]) == 0
    output = capsys.readouterr().out

    assert "Routing report" in output
    assert "Feedback:" in output
    assert "Fixtures:" in output


def test_route_report_excludes_externalized_feedback_cases_from_live_counts(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            missed_cases=[
                "### Case: externalized\n"
                "Task surface summary\n"
                "- Skill recommendation moved elsewhere.\n"
                "Files\n"
                "- AGENTS.md\n"
                "Surfaces\n"
                "- review\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "Expected missing note\n"
                "- tools/skills/review/SKILL.md\n"
                "Why it was needed\n"
                "- Not a Memory routing issue anymore.\n"
                "Expected routing signal\n"
                "- handled by another product surface\n"
                "Status\n"
                "- externalized on 2026-04-17 via another checked-in skill-discovery surface"
            ]
        ),
    )

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 0
    assert result.route_report_summary["feedback"]["externalized_case_count"] == 1
    assert result.route_report_feedback_cases[0]["externalized"] is True
    assert not any(action.kind == "manual review" and "externalized" in action.detail for action in result.actions)


def test_route_report_does_not_emit_combined_routing_score(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")

    data = json.loads(installer.format_result_json(installer.report_routes(target=target)))

    assert "routing_score" not in data
    assert "routing_score" not in data["route_report_summary"]
