from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *


def test_build_substitutions_supports_explicit_placeholder_flags(
    tmp_path: Path,
) -> None:
    substitutions = installer.build_substitutions(
        target_root=tmp_path,
        project_name="demo",
        project_purpose="Bootstrap demo",
        key_repo_docs="README.md, docs/ARCHITECTURE.md",
        key_subsystems="cli, installer",
        primary_build_command="uv run build",
        primary_test_command="uv run pytest",
        other_key_commands="uv run ty check src tests",
    )

    assert substitutions["<PROJECT_NAME>"] == "demo"
    assert substitutions["<PROJECT_PURPOSE>"] == "Bootstrap demo"
    assert substitutions["<PRIMARY_TEST_COMMAND>"] == "uv run pytest"


def test_current_show_reports_missing_notes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.show_current_memory(target=target)

    assert [note.path.as_posix() for note in result.notes] == [
        ".agentic-workspace/memory/repo/current/project-state.md",
        ".agentic-workspace/memory/repo/current/task-context.md",
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
    ]
    assert all(not note.exists for note in result.notes)


def test_current_check_flags_placeholder_and_stale_task_context(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        "# Project State\n\nok\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n\n## Last confirmed\n\n2026-01-01\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert any(action.category == "placeholder-review" for action in result.actions)
    assert any("not been confirmed" in action.detail and "active goal" in action.detail for action in result.actions)


def test_current_check_flags_stale_project_state(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        "# Project State\n\n## Last confirmed\n\n2026-01-01\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        "# Task Context\n\nok\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
        and action.kind == "manual review"
        and "project-state note has not been confirmed" in action.detail
        and "authority boundaries" in action.detail
        for action in result.actions
    )


def test_current_check_flags_task_context_structure_drift_and_planner_signals(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        _project_state_text(),
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        "# Task Context\n\n"
        "## Status\n\nActive\n\n"
        "## Scope\n\n- Optional continuation context.\n\n"
        "## Next steps\n\n- 2026-04-01 do this\n- 2026-04-02 do that\n- 2026-04-03 do more\n\n"
        "## Last confirmed\n\n2026-04-04\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert any("missing expected sections" in action.detail for action in result.actions)
    assert any("planner-like headings" in action.detail for action in result.actions)
    assert any("task-log style bullets" in action.detail for action in result.actions)


def test_current_check_flags_project_state_planning_state_residue(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        "# Project State\n\n"
        "## Status\n\n"
        "- Active execplan: `.agentic-workspace/planning/execplans/example.md`.\n\n"
        "## Scope\n\n- Shared overview only.\n\n"
        "## Applies to\n\n- Root monorepo operation.\n\n"
        "## Load when\n\n- Starting work.\n\n"
        "## Review when\n\n- Current focus changes.\n\n"
        "## Current focus\n\n- Ordinary work.\n\n"
        "## Recent meaningful progress\n\n- One thing changed.\n\n"
        "## Blockers\n\n- None.\n\n"
        "## High-level notes\n\n- Keep this note short.\n\n"
        "## Failure signals\n\n- It becomes a planner.\n\n"
        "## Verify\n\n- Confirm overview still matches repo reality.\n\n"
        "## Verified against\n\n- `TODO.md`\n\n"
        "## Last confirmed\n\n2026-04-13\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(_task_context_text(), encoding="utf-8")

    result = installer.check_current_memory(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
        and "explicit planning-state residue" in action.detail
        for action in result.actions
    )


def test_current_check_flags_current_memory_that_contradicts_idle_planning_state(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\nactive_items = []\nqueued_items = []\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md"
    note_path.write_text(
        "# Task Context\n\n"
        "## Status\n\nActive\n\n"
        "## Scope\n\n- Optional continuation context.\n\n"
        "## Active goal\n\nFinish the April proof pass.\n\n"
        "## Touched surfaces\n\n- src/example.py\n\n"
        "## Blocking assumptions\n\n- None.\n\n"
        "## Next validation\n\n- pytest\n\n"
        "## Resume cues\n\n- Continue the old active execplan.\n\n"
        "## Last confirmed\n\n2026-04-28\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert any(
        action.path == note_path
        and action.role == "current-memory"
        and action.remediation_kind == "shrink-or-remove"
        and action.memory_action == "update, shrink, clear, or delete/disable the stale current-memory note"
        and "planning state has no active item" in action.detail
        for action in result.actions
    )


def test_current_check_allows_inactive_current_memory_when_planning_state_is_idle(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "planning" / "state.toml").write_text(
        "[todo]\nactive_items = []\nqueued_items = []\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md"
    note_path.write_text(
        "# Task Context\n\n"
        "## Status\n\nIdle\n\n"
        "## Scope\n\n- Optional continuation context.\n\n"
        "## Active goal\n\nNo active work; use planning state.\n\n"
        "## Touched surfaces\n\n- None.\n\n"
        "## Blocking assumptions\n\n- None.\n\n"
        "## Next validation\n\n- None.\n\n"
        "## Resume cues\n\n- Use summary.\n\n"
        "## Last confirmed\n\n2026-04-28\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert not any(action.path == note_path and "planning state has no active item" in action.detail for action in result.actions)


def test_current_check_allows_next_validation_heading(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        _project_state_text(),
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        _task_context_text(),
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert not any("planner-like headings" in action.detail for action in result.actions)


def test_build_substitutions_include_last_confirmed_date(tmp_path: Path) -> None:
    substitutions = installer.build_substitutions(target_root=tmp_path, project_name="demo")

    assert substitutions["<LAST_CONFIRMED_DATE>"].count("-") == 2


def test_current_task_staleness_reason_mentions_planner_spillover() -> None:
    text = "\n".join(["line"] * (installer.CURRENT_TASK_MAX_LINES + 1))

    reason = installer._current_task_staleness_reason(text)

    assert reason is not None
    assert "planner, backlog, or execution-log spillover" in reason


def test_install_summary_mentions_populate_next_step_when_current_notes_created(capsys, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    result = installer.install_bootstrap(target=target, dry_run=True)

    cli._print_install_summary(result)

    output = capsys.readouterr().out
    assert "install or adopt lifecycle work" in output
    assert "bootstrap-cleanup" in output
    assert "install or upgrade review" not in output
    assert "`populate` skill" not in output
    assert "memory-router" in output
    assert "memory-refresh" in output
    assert "bootstrap-managed" in output


def test_install_summary_skips_populate_next_step_when_no_current_notes_created(capsys, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text("# Project State\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text("# Task Context\n", encoding="utf-8")
    result = installer.adopt_bootstrap(target=target, dry_run=True)

    cli._print_install_summary(result)

    output = capsys.readouterr().out
    assert "`populate` skill" not in output


def test_current_view_json_shape(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    payload = installer.show_current_memory(target=target)

    data = json.loads(installer.format_result_json(payload))

    assert data["notes"][0]["path"] == ".agentic-workspace/memory/repo/current/project-state.md"


def test_current_note_size_pressure_is_classified_as_current_memory_review() -> None:
    assert (
        _infer_action_category(
            kind="consider",
            path=Path(".agentic-workspace/memory/repo/current/task-context.md"),
            detail="task-context note is oversized (92 lines, expected <= 80); remove planner/log spillover",
            role="memory-size-audit",
            safety="manual",
        )
        == "current-memory-review"
    )
