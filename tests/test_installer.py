from __future__ import annotations

from pathlib import Path

from repo_memory_bootstrap import installer


def test_detect_install_mode_is_full_without_todo_file(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (tmp_path / "memory").mkdir()

    assert installer.detect_install_mode(tmp_path) == "full"


def test_payload_entries_do_not_include_todo_stub() -> None:
    entries = installer._payload_entries(installer.payload_root())

    assert all(entry.relative_path != Path("TODO.md") for entry in entries)
    assert all(".agent-work" not in entry.relative_path.as_posix() for entry in entries)
    assert all(entry.relative_path != Path("memory/current/active-decisions.md") for entry in entries)
    assert any(entry.relative_path == Path("memory/current/task-context.md") for entry in entries)


def test_payload_current_baseline_is_project_state_and_task_context_only() -> None:
    entries = installer._payload_entries(installer.payload_root())

    current_paths = {
        entry.relative_path.as_posix()
        for entry in entries
        if entry.relative_path.as_posix().startswith("memory/current/")
    }

    assert current_paths == {
        "memory/current/project-state.md",
        "memory/current/task-context.md",
    }


def test_extract_make_targets_ignores_assignments_and_recipes() -> None:
    text = """
    .PHONY: lint test
    PYTHON ?= python

    lint test:
    \t$(PYTHON) -m pytest

    check-memory:
    \tpython scripts/check/check_memory_freshness.py
    """

    assert installer._extract_make_targets(text) == {
        ".PHONY",
        "lint",
        "test",
        "check-memory",
    }


def test_equivalent_optional_fragment_detail_detects_existing_makefile_target() -> None:
    existing = """
    check-memory:
    \t$(PYTHON) scripts/check/check_memory_freshness.py
    """
    fragment = """
    check-memory:
    \tpython scripts/check/check_memory_freshness.py
    """

    detail = installer._equivalent_optional_fragment_detail(
        target_file=Path("Makefile"),
        existing=existing,
        fragment=fragment,
    )

    assert detail == "equivalent Makefile target already present (check-memory)"


def test_equivalent_optional_fragment_detail_requires_matching_targets() -> None:
    detail = installer._equivalent_optional_fragment_detail(
        target_file=Path("Makefile"),
        existing="lint:\n\tpython -m ruff check .\n",
        fragment="check-memory:\n\tpython scripts/check/check_memory_freshness.py\n",
    )

    assert detail is None


def test_plan_optional_appends_skips_equivalent_makefile_target(tmp_path: Path) -> None:
    source_root = tmp_path / "payload"
    target_root = tmp_path / "target"
    (source_root / "optional").mkdir(parents=True)
    target_root.mkdir()

    fragment = "check-memory:\n\tpython scripts/check/check_memory_freshness.py\n"
    makefile = "check-memory:\n\t$(PYTHON) scripts/check/check_memory_freshness.py\n"

    (source_root / "optional" / "Makefile.fragment.mk").write_text(fragment, encoding="utf-8")
    (source_root / "optional" / "CONTRIBUTING.fragment.md").write_text("Contributing fragment\n", encoding="utf-8")
    (source_root / "optional" / "pull_request_template.fragment.md").write_text("PR fragment\n", encoding="utf-8")
    (target_root / "Makefile").write_text(makefile, encoding="utf-8")

    result = installer.InstallResult(target_root=target_root, dry_run=False)

    installer._plan_optional_appends(
        source_root,
        target_root,
        result,
        apply=True,
    )

    assert (target_root / "Makefile").read_text(encoding="utf-8") == makefile
    makefile_actions = [action for action in result.actions if action.path == target_root / "Makefile"]
    assert len(makefile_actions) == 1
    assert makefile_actions[0].kind == "skipped"
    assert makefile_actions[0].detail == "equivalent Makefile target already present (check-memory)"


def test_patch_agents_workflow_block_inserts_pointer_after_heading() -> None:
    existing = "# Agent Instructions\n\nRepo-local rules live here.\n"

    patched = installer._patch_agents_workflow_block(existing)

    assert installer.WORKFLOW_POINTER_BLOCK in patched
    assert patched.startswith("# Agent Instructions\n\n")
    assert patched.endswith("Repo-local rules live here.\n")


def test_doctor_flags_agents_that_embed_current_shared_workflow_sections(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "system").mkdir(parents=True)
    (target / "AGENTS.md").write_text(
        "# Agent Instructions\n\n"
        f"{installer.WORKFLOW_POINTER_BLOCK}\n\n"
        "## Overview file\n"
        "- copied shared rule\n\n"
        "## Task-context file\n"
        "- copied shared rule\n",
        encoding="utf-8",
    )
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 8\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md"
        and action.kind == "manual review"
        and "embeds shared workflow rules" in action.detail
        for action in result.actions
    )


def test_upgrade_replaces_shared_files_without_todo_manual_review(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "current").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 7\n", encoding="utf-8")
    (target / "memory" / "system" / "WORKFLOW.md").write_text("old workflow\n", encoding="utf-8")
    (target / "memory" / "current" / "task-context.md").write_text("# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert all(action.path != target / "TODO.md" for action in result.actions)
    assert any(
        action.path == target / "memory" / "system" / "WORKFLOW.md" and action.kind == "would replace"
        for action in result.actions
    )
    assert any(
        action.path == target / "memory" / "current" / "task-context.md" and action.kind == "would replace"
        for action in result.actions
    )


def test_list_payload_files_excludes_agent_work_templates_and_gitignore_append(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".git").mkdir()

    result = installer.list_payload_files(target=target)

    assert all(action.path != target / ".gitignore" for action in result.actions)
    assert all(".agent-work" not in action.path.as_posix() for action in result.actions)
    assert all(action.path != target / "memory" / "current" / "active-decisions.md" for action in result.actions)


def test_install_dry_run_includes_current_memory_baseline(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.install_bootstrap(target=target, dry_run=True)

    planned_copies = {
        action.path.relative_to(target).as_posix()
        for action in result.actions
        if action.kind == "would copy"
    }

    assert "memory/current/project-state.md" in planned_copies
    assert "memory/current/task-context.md" in planned_copies
    assert "memory/current/active-decisions.md" not in planned_copies
