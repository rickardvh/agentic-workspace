from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from repo_memory_bootstrap import cli, installer


def test_detect_install_mode_is_full_without_todo_file(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (tmp_path / "memory").mkdir()

    assert installer.detect_install_mode(tmp_path) == "full"


def test_payload_entries_do_not_include_todo_stub() -> None:
    entries = installer._payload_entries(installer.payload_root())

    assert all(entry.relative_path != Path("TODO.md") for entry in entries)
    assert all(".agent-work" not in entry.relative_path.as_posix() for entry in entries)
    assert all(
        entry.relative_path != Path("memory/current/active-decisions.md")
        for entry in entries
    )
    assert any(
        entry.relative_path == Path("memory/current/task-context.md")
        for entry in entries
    )
    assert any(entry.relative_path == Path("memory/manifest.toml") for entry in entries)
    assert any(
        entry.relative_path == Path("memory/system/SKILLS.md") for entry in entries
    )
    assert any(
        entry.relative_path == Path("memory/system/UPGRADE-SOURCE.toml")
        for entry in entries
    )
    assert any(
        entry.relative_path == Path("memory/bootstrap/README.md") for entry in entries
    )
    assert any(
        entry.relative_path == Path("memory/bootstrap/skills/install/SKILL.md")
        for entry in entries
    )
    assert any(
        entry.relative_path == Path("memory/skills/memory-router/SKILL.md")
        for entry in entries
    )
    assert any(
        entry.relative_path == Path("memory/skills/memory-upgrade/SKILL.md")
        for entry in entries
    )
    assert all(
        entry.relative_path != Path("memory/bootstrap/skills/upgrade/SKILL.md")
        for entry in entries
    )
    assert all(
        entry.relative_path
        != Path("memory/bootstrap/skills/upgrade/agents/openai.yaml")
        for entry in entries
    )


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


def test_list_bundled_skills_only_includes_bootstrap_skills() -> None:
    result = installer.list_bundled_skills()

    bundled = {
        action.path.name for action in result.actions if action.kind == "bundled skill"
    }

    assert bundled == {
        "bootstrap-adoption",
        "bootstrap-populate",
        "bootstrap-upgrade",
        "bootstrap-uninstall",
    }


def test_dev_bundled_skills_tree_only_contains_bootstrap_skill_directories() -> None:
    skills_dir = installer.skills_root()

    skill_dirs = {
        path.name
        for path in skills_dir.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    }

    assert skill_dirs == {
        "bootstrap-adoption",
        "bootstrap-populate",
        "bootstrap-upgrade",
        "bootstrap-uninstall",
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

    assert (
        detail
        == "equivalent optional Makefile convenience target already present (check-memory)"
    )


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

    (source_root / "optional" / "Makefile.fragment.mk").write_text(
        fragment, encoding="utf-8"
    )
    (source_root / "optional" / "CONTRIBUTING.fragment.md").write_text(
        "Contributing fragment\n", encoding="utf-8"
    )
    (source_root / "optional" / "pull_request_template.fragment.md").write_text(
        "PR fragment\n", encoding="utf-8"
    )
    (target_root / "Makefile").write_text(makefile, encoding="utf-8")

    result = installer.InstallResult(target_root=target_root, dry_run=False)

    installer._plan_optional_appends(
        source_root,
        target_root,
        result,
        apply=True,
    )

    assert (target_root / "Makefile").read_text(encoding="utf-8") == makefile
    makefile_actions = [
        action for action in result.actions if action.path == target_root / "Makefile"
    ]
    assert len(makefile_actions) == 1
    assert makefile_actions[0].kind == "skipped"
    assert (
        makefile_actions[0].detail
        == "equivalent optional Makefile convenience target already present (check-memory)"
    )


def test_install_does_not_duplicate_existing_optional_fragment(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    makefile = target / "Makefile"
    makefile.write_text(
        "check-memory:\n\tpython scripts/check/check_memory_freshness.py\n",
        encoding="utf-8",
    )

    result = installer.install_bootstrap(target=target, dry_run=True)

    makefile_actions = [action for action in result.actions if action.path == makefile]

    assert len(makefile_actions) == 1
    assert makefile_actions[0].kind == "skipped"
    assert "already present" in makefile_actions[0].detail


def test_patch_agents_workflow_block_inserts_pointer_after_heading() -> None:
    existing = "# Agent Instructions\n\nRepo-local rules live here.\n"

    patched = installer._patch_agents_workflow_block(existing)

    assert patched == (
        "# Agent Instructions\n\n"
        f"{installer.WORKFLOW_POINTER_BLOCK}\n\n"
        "Repo-local rules live here.\n"
    )


def test_doctor_flags_agents_that_embed_current_shared_workflow_sections(
    tmp_path: Path,
) -> None:
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
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 8\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md"
        and action.kind == "manual review"
        and "embeds shared workflow rules" in action.detail
        for action in result.actions
    )


def test_upgrade_replaces_shared_files_without_todo_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "current").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 7\n", encoding="utf-8"
    )
    (target / "memory" / "system" / "WORKFLOW.md").write_text(
        "old workflow\n", encoding="utf-8"
    )
    (target / "memory" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert all(action.path != target / "TODO.md" for action in result.actions)
    assert any(
        action.path == target / "memory" / "system" / "WORKFLOW.md"
        and action.kind == "would replace"
        for action in result.actions
    )
    assert any(
        action.path == target / "memory" / "current" / "task-context.md"
        and action.kind == "would replace"
        for action in result.actions
    )


def test_doctor_reports_customised_seed_notes_as_expected_customisation(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    installer.install_bootstrap(target=target)
    note_path = target / "memory" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\nlocalised\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == note_path
        and action.kind == "customised"
        and action.category == "customisation-present"
        for action in result.actions
    )


def test_list_payload_files_excludes_agent_work_templates_and_gitignore_append(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    (target / ".git").mkdir()

    result = installer.list_payload_files(target=target)

    assert all(action.path != target / ".gitignore" for action in result.actions)
    assert all(".agent-work" not in action.path.as_posix() for action in result.actions)
    assert all(
        action.path != target / "memory" / "current" / "active-decisions.md"
        for action in result.actions
    )


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
    assert "memory/bootstrap/README.md" in planned_copies
    assert "memory/current/active-decisions.md" not in planned_copies


def test_install_writes_audit_clean_current_memory_seed_dates(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)

    for relative in (
        "memory/current/project-state.md",
        "memory/current/task-context.md",
    ):
        text = (target / relative).read_text(encoding="utf-8")
        assert "<LAST_CONFIRMED_DATE>" not in text
        assert "## Last confirmed\n\n20" in text


def test_install_writes_audit_clean_recurring_failures_seed_date(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)

    text = (target / "memory" / "mistakes" / "recurring-failures.md").read_text(
        encoding="utf-8"
    )
    assert "<LAST_CONFIRMED_DATE>" not in text
    assert "## Last confirmed\n\n20" in text


def test_install_writes_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)

    text = (target / "memory" / "system" / "UPGRADE-SOURCE.toml").read_text(
        encoding="utf-8"
    )
    assert 'source_type = "git"' in text
    assert "git+https://github.com/Tenfifty/agentic-memory" in text


def test_adopt_writes_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory").mkdir()

    installer.adopt_bootstrap(target=target)

    text = (target / "memory" / "system" / "UPGRADE-SOURCE.toml").read_text(
        encoding="utf-8"
    )
    assert 'source_type = "git"' in text


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
    (target / ".git").mkdir(parents=True)

    result = installer.show_current_memory(target=target)

    assert [note.path.as_posix() for note in result.notes] == [
        "memory/current/project-state.md",
        "memory/current/task-context.md",
    ]
    assert all(not note.exists for note in result.notes)


def test_current_check_flags_placeholder_and_stale_task_context(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "current").mkdir(parents=True)
    (target / "memory" / "current" / "project-state.md").write_text(
        "# Project State\n\nok\n", encoding="utf-8"
    )
    (target / "memory" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n\n## Last confirmed\n\n2026-01-01\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert any(action.category == "placeholder-review" for action in result.actions)
    assert any(
        "not been confirmed" in action.detail and "active goal" in action.detail
        for action in result.actions
    )


def test_current_check_flags_stale_project_state(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "current").mkdir(parents=True)
    (target / "memory" / "current" / "project-state.md").write_text(
        "# Project State\n\n## Last confirmed\n\n2026-01-01\n",
        encoding="utf-8",
    )
    (target / "memory" / "current" / "task-context.md").write_text(
        "# Task Context\n\nok\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert any(
        action.path == target / "memory" / "current" / "project-state.md"
        and action.kind == "manual review"
        and "project-state note has not been confirmed" in action.detail
        and "authority boundaries" in action.detail
        for action in result.actions
    )


def test_build_substitutions_include_last_confirmed_date(tmp_path: Path) -> None:
    substitutions = installer.build_substitutions(
        target_root=tmp_path, project_name="demo"
    )

    assert substitutions["<LAST_CONFIRMED_DATE>"].count("-") == 2


def test_resolve_upgrade_source_defaults_to_git_when_metadata_missing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "system").mkdir(parents=True)

    resolved = installer.resolve_upgrade_source(target=target)

    assert resolved["source_type"] == "git"
    assert resolved["source_ref"] == "git+https://github.com/Tenfifty/agentic-memory"


def test_upgrade_reports_resolved_source(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    installer.install_bootstrap(target=target)

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert any(
        action.path == target / "memory" / "system" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and "upgrade source resolved to git" in action.detail
        for action in result.actions
    )


def test_upgrade_preserves_existing_local_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    installer.install_bootstrap(target=target)
    source_path = target / "memory" / "system" / "UPGRADE-SOURCE.toml"
    source_path.write_text(
        'source_type = "local"\nsource_ref = "C:/src/agentic-memory"\n',
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert source_path.read_text(encoding="utf-8") == (
        'source_type = "local"\nsource_ref = "C:/src/agentic-memory"\n'
    )
    assert any(
        action.path == source_path
        and action.kind == "current"
        and "preserving repo-local source selection" in action.detail
        for action in result.actions
    )


def test_upgrade_dry_run_does_not_include_bootstrap_workspace_files(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    installer.install_bootstrap(target=target)

    result = installer.upgrade_bootstrap(target=target, dry_run=True)
    planned = {action.path.relative_to(target).as_posix() for action in result.actions}

    assert all(not path.startswith("memory/bootstrap/") for path in planned)


def test_route_memory_adds_baseline_and_runtime_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "index.md").write_text(
        (Path("memory/index.md")).read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    suggested = {
        action.path.relative_to(target).as_posix()
        for action in result.actions
        if action.kind == "recommended"
    }

    assert "memory/current/project-state.md" in suggested
    assert "memory/current/task-context.md" in suggested
    assert "memory/domains/<runtime-or-deployment-note>.md" in suggested
    assert "memory/runbooks/<relevant-operator-runbook>.md" in suggested


def test_route_memory_adds_architecture_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "index.md").write_text(
        (Path("memory/index.md")).read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = installer.route_memory(target=target, files=["src/architecture/schema.py"])
    suggested = {
        action.path.relative_to(target).as_posix()
        for action in result.actions
        if action.kind == "recommended"
    }

    assert "memory/invariants/<relevant-invariant-note>.md" in suggested
    assert "memory/decisions/README.md" in suggested


def test_route_memory_uses_manifest_file_globs(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/domains/cli.md"]
note_type = "domain"
canonical_home = "memory/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(
        target=target, files=["src/repo_memory_bootstrap/cli.py"]
    )

    assert any(
        action.kind == "recommended"
        and action.path.relative_to(target).as_posix() == "memory/domains/cli.md"
        and "manifest path match" in action.detail
        for action in result.actions
    )


def test_sync_memory_without_input_returns_guidance(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.sync_memory(target=target)

    assert len(result.actions) == 1
    assert result.actions[0].kind == "manual review"
    assert "provide --files/--notes" in result.actions[0].detail


def test_sync_memory_with_explicit_file_produces_recommendations(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "index.md").write_text(
        (Path("memory/index.md")).read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = installer.sync_memory(target=target, files=["tests/test_cli.py"])

    assert any(
        action.kind in {"review", "update", "update index"} for action in result.actions
    )


def test_sync_memory_uses_manifest_staleness_triggers(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "domains").mkdir(parents=True)
    (target / "memory" / "domains" / "cli.md").write_text("# CLI\n", encoding="utf-8")
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/domains/cli.md"]
note_type = "domain"
canonical_home = "memory/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
related_validations = ["uv run pytest"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(
        target=target, files=["src/repo_memory_bootstrap/installer.py"]
    )

    assert any(
        action.path == target / "memory" / "domains" / "cli.md"
        and action.kind == "review"
        and "manifest staleness trigger matched" in action.detail
        for action in result.actions
    )


def test_verify_payload_passes_for_current_payload(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.verify_payload(target=target)

    assert not any(action.category == "contract-drift" for action in result.actions)


def test_memory_freshness_audit_ignores_bootstrap_workspace(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)

    completed = subprocess.run(
        [
            sys.executable,
            str(
                installer.payload_root()
                / "scripts"
                / "check"
                / "check_memory_freshness.py"
            ),
        ],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "memory/bootstrap/" not in completed.stdout


def test_verify_payload_flags_forbidden_current_note(
    monkeypatch, tmp_path: Path
) -> None:
    payload = tmp_path / "payload"
    (payload / "memory" / "current").mkdir(parents=True)
    (payload / "memory" / "system").mkdir(parents=True)
    (payload / "memory" / "domains").mkdir(parents=True)
    (payload / "memory" / "invariants").mkdir(parents=True)
    (payload / "memory" / "runbooks").mkdir(parents=True)
    (payload / "memory" / "mistakes").mkdir(parents=True)
    (payload / "memory" / "decisions").mkdir(parents=True)
    (payload / "scripts" / "check").mkdir(parents=True)
    (payload / "AGENTS.md").write_text("# Agent Instructions\n", encoding="utf-8")
    (payload / "memory" / "index.md").write_text("# Memory Index\n", encoding="utf-8")
    (payload / "memory" / "system" / "WORKFLOW.md").write_text(
        "# Workflow Rules\n", encoding="utf-8"
    )
    (payload / "memory" / "current" / "project-state.md").write_text(
        "# Project State\n", encoding="utf-8"
    )
    (payload / "memory" / "current" / "task-context.md").write_text(
        "# Task Context\n", encoding="utf-8"
    )
    (payload / "memory" / "current" / "active-decisions.md").write_text(
        "# Active Decisions\n", encoding="utf-8"
    )
    (payload / "memory" / "domains" / "README.md").write_text(
        "# Domains\n", encoding="utf-8"
    )
    (payload / "memory" / "invariants" / "README.md").write_text(
        "# Invariants\n", encoding="utf-8"
    )
    (payload / "memory" / "runbooks" / "README.md").write_text(
        "# Runbooks\n", encoding="utf-8"
    )
    (payload / "memory" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (payload / "memory" / "decisions" / "README.md").write_text(
        "# Decisions\n", encoding="utf-8"
    )
    (payload / "scripts" / "check" / "check_memory_freshness.py").write_text(
        "print('ok')\n", encoding="utf-8"
    )
    monkeypatch.setattr(installer, "payload_root", lambda: payload)
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.verify_payload(target=target)

    assert any(
        action.path.relative_to(target).as_posix()
        == "memory/current/active-decisions.md"
        and action.category == "contract-drift"
        for action in result.actions
    )


def test_doctor_reports_placeholder_review_category(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / "memory" / "current").mkdir(parents=True)
    (target / "memory" / "system").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 8\n", encoding="utf-8"
    )
    (target / "memory" / "system" / "WORKFLOW.md").write_text(
        "old workflow\n", encoding="utf-8"
    )
    (target / "memory" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(action.category == "placeholder-review" for action in result.actions)


def test_doctor_agents_guidance_mentions_apply_local_entrypoint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "system").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 10\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md"
        and "--apply-local-entrypoint" in action.detail
        for action in result.actions
    )


def test_cli_parser_accepts_new_commands_and_placeholder_flags() -> None:
    parser = cli.build_parser()

    current_args = parser.parse_args(["current", "check", "--target", "."])
    list_skills_args = parser.parse_args(["list-skills", "--format", "json"])
    cleanup_args = parser.parse_args(
        ["bootstrap-cleanup", "--target", ".", "--format", "json"]
    )
    uninstall_args = parser.parse_args(
        ["uninstall", "--target", ".", "--dry-run", "--format", "json"]
    )
    doctor_args = parser.parse_args(
        ["doctor", "--target", ".", "--strict-doc-ownership"]
    )
    prompt_install_args = parser.parse_args(
        ["prompt", "install", "--target", "C:/repo"]
    )
    prompt_args = parser.parse_args(["prompt", "adopt", "--target", "C:/repo"])
    prompt_populate_args = parser.parse_args(
        ["prompt", "populate", "--target", "C:/repo"]
    )
    prompt_uninstall_args = parser.parse_args(
        ["prompt", "uninstall", "--target", "C:/repo"]
    )
    route_args = parser.parse_args(["route", "--files", "src/app.py"])
    sync_args = parser.parse_args(["sync-memory", "--notes", "memory/index.md"])
    promotion_args = parser.parse_args(
        ["promotion-report", "--notes", "memory/domains/api.md"]
    )
    verify_args = parser.parse_args(["verify-payload", "--format", "json"])
    install_args = parser.parse_args(
        [
            "install",
            "--project-name",
            "demo",
            "--project-purpose",
            "purpose",
            "--key-repo-docs",
            "README.md",
            "--primary-build-command",
            "uv run build",
        ]
    )

    assert current_args.command == "current"
    assert list_skills_args.command == "list-skills"
    assert cleanup_args.command == "bootstrap-cleanup"
    assert uninstall_args.command == "uninstall"
    assert doctor_args.strict_doc_ownership is True
    assert prompt_install_args.prompt_command == "install"
    assert prompt_args.command == "prompt"
    assert prompt_args.prompt_command == "adopt"
    assert prompt_populate_args.prompt_command == "populate"
    assert prompt_uninstall_args.prompt_command == "uninstall"
    assert route_args.command == "route"
    assert sync_args.command == "sync-memory"
    assert promotion_args.command == "promotion-report"
    assert verify_args.command == "verify-payload"
    assert install_args.project_purpose == "purpose"


def test_verify_payload_reports_version_mismatch(tmp_path: Path, monkeypatch) -> None:
    payload = tmp_path / "payload"
    (payload / "memory" / "system").mkdir(parents=True)
    (payload / "memory" / "system" / "VERSION.md").write_text(
        "Version: 21\n", encoding="utf-8"
    )
    monkeypatch.setattr(installer, "payload_root", lambda: payload)

    result = installer.verify_payload(target=payload)

    assert any(
        action.path == payload / "memory" / "system" / "VERSION.md"
        and action.kind == "manual review"
        and "does not match installer bootstrap version" in action.detail
        for action in result.actions
    )


def test_bootstrap_workflow_doc_includes_note_maintenance_and_skill_precedence_guidance() -> (
    None
):
    text = (installer.payload_root() / "memory" / "system" / "WORKFLOW.md").read_text(
        encoding="utf-8"
    )

    assert "## Note maintenance rule" in text
    assert "Update a note when its primary home is still correct" in text
    assert "Checked-in repo-local skills should take precedence" in text
    assert "## Stale-note pressure" in text
    assert "## Canonical-doc boundary" in text
    assert "Treat memory as assistive residue by default" in text
    assert "## Interoperability contract" in text
    assert "active planning/status surface owns active intent and sequencing" in text
    assert "## Capture threshold" in text
    assert "## Anti-patterns" in text
    assert "Optimise for deletion and consolidation" in text
    assert "does not replace checking code, tests, or canonical docs" in text
    assert "user-specific preferences" in text
    assert "Memory is also a pressure layer" in text
    assert "## Improvement pressure" in text
    assert "## Remediation paths" in text


def test_bootstrap_index_includes_token_efficiency_and_small_routing_examples() -> None:
    text = (installer.payload_root() / "memory" / "index.md").read_text(
        encoding="utf-8"
    )

    assert "## Token-efficiency rule" in text
    assert "Memory is a net token saver" in text
    assert "## Small routing examples" in text
    assert "Example: deployment recovery" in text
    assert "## Canonicality rule" in text
    assert "core docs should not depend on memory" in text
    assert "## Interoperability patterns" in text
    assert "## Integration checklist" in text
    assert "Planning identifies touched paths or surfaces" in text
    assert "help an agent read less, not more" in text
    assert "Prefer durable consequences, constraints, exceptions, and recurring traps" in text
    assert "optional repo-owned `memory/current/active-decisions.md`" in text


def test_bootstrap_readme_includes_optional_patterns_and_project_state_shape() -> None:
    text = (installer.payload_root() / "README.md").read_text(encoding="utf-8")

    assert "Optional repo pattern only" in text
    assert "current focus, recent meaningful progress, blockers" in text
    assert "Memory owns durable repo knowledge" in text
    assert "When to write to memory" in text
    assert "When not to write to memory" in text
    assert "## Anti-patterns" in text
    assert "## Minimal Adoption Checklist" in text
    assert "Good memory systems should help an agent read less, not more." in text
    assert "Memory is a reasoning aid" in text
    assert "mixing user-specific memory with repo-specific technical truth" in text
    assert "durable truth" in text
    assert "improvement signal" in text
    assert "## Improvement Paths" in text
    assert "optional repo-owned `memory/current/active-decisions.md`" in text


def test_bootstrap_task_context_starter_is_continuation_only() -> None:
    text = (installer.payload_root() / "memory" / "current" / "task-context.md").read_text(
        encoding="utf-8"
    )

    assert "Optional checked-in continuation compression" in text
    assert "## Active goal" in text
    assert "## Blocking assumptions" in text
    assert "## Next validation" in text
    assert "Do not turn it into a task list, backlog, execution log, or sequencing surface." in text


def test_current_task_staleness_reason_mentions_planning_spillover() -> None:
    text = "\n".join(["line"] * (installer.CURRENT_TASK_MAX_LINES + 1))

    reason = installer._current_task_staleness_reason(text)

    assert reason is not None
    assert "planning/status spillover" in reason


def test_project_state_staleness_reason_mentions_active_plan_residue() -> None:
    text = "\n".join(["line"] * (installer.CURRENT_PROJECT_STATE_MAX_LINES + 1))

    reason = installer._project_state_staleness_reason(text)

    assert reason is not None
    assert "active-plan residue" in reason


def test_doctor_emits_improvement_pressure_suggestions_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "mistakes").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 32\n", encoding="utf-8"
    )
    (target / "memory" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring failures\n\n- This keeps happening.\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = "memory/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "test"
improvement_candidate = true
elimination_target = "shrink"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "memory" / "mistakes" / "recurring-failures.md"
        and action.kind == "consider"
        and "regression test" in action.detail
        for action in result.actions
    )


def test_sync_memory_appends_improvement_hint_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "mistakes").mkdir(parents=True)
    (target / "memory" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring failures\n\n- Guard this.\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = "memory/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
stale_when = ["tests/**/*.py"]
memory_role = "improvement_signal"
preferred_remediation = "test"
improvement_candidate = true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["tests/test_api.py"])

    assert any(
        action.path == target / "memory" / "mistakes" / "recurring-failures.md"
        and action.kind in {"review", "update"}
        and "consider a regression test" in action.detail
        for action in result.actions
    )


def test_path_match_pattern_treats_double_star_as_zero_or_more_directories() -> None:
    assert installer._path_matches_pattern("tests/test_api.py", "tests/**/*.py")
    assert installer._path_matches_pattern(
        "tests/unit/test_api.py", "tests/**/*.py"
    )


def test_promotion_report_supports_improvement_candidates_without_docs_promotion(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "runbooks").mkdir(parents=True)
    (target / "memory" / "runbooks" / "deploy.md").write_text(
        "# Deploy\n\n1. Run command A.\n2. Run command B.\n3. Verify status.\n",
        encoding="utf-8",
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/runbooks/deploy.md"]
note_type = "runbook"
canonical_home = "memory/runbooks/deploy.md"
authority = "canonical"
audience = "human_operator"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "script"
improvement_candidate = true
elimination_target = "automate"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.promotion_report(target=target)

    assert any(
        action.path == target / "memory" / "runbooks" / "deploy.md"
        and action.kind == "candidate"
        and "improvement candidate" in action.detail
        and "repo-owned script or command" in action.detail
        for action in result.actions
    )


def test_build_install_prompt_mentions_local_bootstrap_skills_and_target(
    monkeypatch,
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"C:/tools/{name}.exe")
    prompt = cli._build_agent_prompt("install", target="C:/repo")

    assert (
        "uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap init --target C:/repo"
        in prompt
    )
    assert "`install` skill at `C:/repo/memory/bootstrap/skills`" in prompt
    assert "bootstrap-cleanup --target C:/repo" in prompt


def test_build_adopt_prompt_mentions_local_bootstrap_skills_and_target(
    monkeypatch,
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"C:/tools/{name}.exe")
    prompt = cli._build_agent_prompt("adopt", target="C:/repo")

    assert (
        "uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap adopt --target C:/repo"
        in prompt
    )
    assert "`install` skill at `C:/repo/memory/bootstrap/skills`" in prompt
    assert "`populate` from the same path" in prompt
    assert "bootstrap-cleanup --target C:/repo" in prompt
    assert "C:/repo" in prompt


def test_build_populate_prompt_mentions_task_context_heuristic(monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"C:/tools/{name}.exe")
    prompt = cli._build_agent_prompt("populate", target="C:/repo")

    assert (
        "uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap current show --target C:/repo"
        in prompt
    )
    assert "`populate` skill at `C:/repo/memory/bootstrap/skills`" in prompt
    assert "task-context.md" in prompt
    assert "C:/repo" in prompt


def test_build_upgrade_prompt_mentions_local_bootstrap_skills(monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"C:/tools/{name}.exe")
    prompt = cli._build_agent_prompt("upgrade", target="C:/repo")

    assert prompt.startswith("Use the checked-in `memory-upgrade` skill")
    assert "memory-upgrade" in prompt
    assert "C:/repo/memory/skills/" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert "packaged upgrade flow for this repo" in prompt
    assert "bootstrap-cleanup --target C:/repo" not in prompt
    assert not prompt.startswith("Run `")


def test_build_upgrade_prompt_uses_local_source_when_recorded(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"C:/tools/{name}.exe")
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    installer.install_bootstrap(target=target)
    (target / "memory" / "system" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "C:/src/agentic-memory"\n',
        encoding="utf-8",
    )

    prompt = cli._build_agent_prompt("upgrade", target=str(target))

    assert prompt.startswith("Use the checked-in `memory-upgrade` skill")
    assert "recorded upgrade source automatically" in prompt
    assert "packaged upgrade flow for this repo" in prompt
    assert "git+https://github.com/Tenfifty/agentic-memory" not in prompt


def test_build_uninstall_prompt_mentions_bundled_skill(monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"C:/tools/{name}.exe")
    prompt = cli._build_agent_prompt("uninstall", target="C:/repo")

    assert (
        "uvx --from git+https://github.com/Tenfifty/agentic-memory agentic-memory-bootstrap uninstall --target C:/repo"
        in prompt
    )
    assert "bootstrap-uninstall" in prompt


def test_build_prompt_falls_back_to_pipx_when_uvx_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        cli.shutil, "which", lambda name: None if name == "uvx" else "C:/tools/pipx.exe"
    )

    prompt = cli._build_agent_prompt("upgrade", target="C:/repo")

    assert prompt.startswith("Use the checked-in `memory-upgrade` skill")
    assert "C:/repo/memory/skills/" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert "uvx --from" not in prompt
    assert "pipx run --spec" not in prompt


def test_doctor_flags_legacy_upgrade_runbook_for_removal(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)
    legacy = target / "memory" / "system" / "UPGRADE.md"
    legacy.write_text("# legacy\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == legacy
        and action.kind == "would remove"
        and action.category == "obsolete-managed-file"
        for action in result.actions
    )


def test_upgrade_removes_legacy_upgrade_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)
    legacy = target / "memory" / "system" / "UPGRADE.md"
    legacy.write_text("# legacy\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target)

    assert not legacy.exists()
    assert any(
        action.path == legacy
        and action.kind == "removed"
        and action.category == "obsolete-managed-file"
        for action in result.actions
    )


def test_bootstrap_cleanup_removes_workspace(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)
    workspace = target / "memory" / "bootstrap"
    assert workspace.exists()

    result = installer.cleanup_bootstrap_workspace(target=target)

    assert not workspace.exists()
    assert any(action.kind == "removed" for action in result.actions)


def test_bootstrap_cleanup_is_safe_when_workspace_absent(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.cleanup_bootstrap_workspace(target=target)

    assert any(action.kind == "skipped" for action in result.actions)


def test_uninstall_removes_safe_bootstrap_files(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)

    result = installer.uninstall_bootstrap(target=target)

    assert not (target / "AGENTS.md").exists()
    assert not (target / "memory" / "index.md").exists()
    assert not (target / "scripts" / "check" / "check_memory_freshness.py").exists()
    assert any(action.kind == "removed" for action in result.actions)


def test_uninstall_flags_customised_seed_notes_for_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)
    note_path = target / "memory" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\ncustomised\n", encoding="utf-8")

    result = installer.uninstall_bootstrap(target=target, dry_run=True)

    assert any(
        action.path == note_path and action.kind == "manual review"
        for action in result.actions
    )


def test_uninstall_reports_remaining_repo_local_memory_as_safe_to_keep(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    installer.install_bootstrap(target=target)
    extra_note = target / "memory" / "domains" / "local-note.md"
    extra_note.parent.mkdir(parents=True, exist_ok=True)
    extra_note.write_text("# Local Note\n", encoding="utf-8")

    result = installer.uninstall_bootstrap(target=target, dry_run=True)

    assert any(
        action.path == extra_note
        and action.kind == "skipped"
        and "safe to keep" in action.detail
        for action in result.actions
    )


def test_install_summary_mentions_populate_next_step_when_current_notes_created(
    capsys, tmp_path: Path
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    result = installer.install_bootstrap(target=target, dry_run=True)

    cli._print_install_summary(result)

    output = capsys.readouterr().out
    assert "install or adopt lifecycle work" in output
    assert "bootstrap-cleanup" in output
    assert "install or upgrade review" not in output
    assert "`populate` skill" in output


def test_install_summary_skips_populate_next_step_when_no_current_notes_created(
    capsys, tmp_path: Path
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "current").mkdir(parents=True)
    (target / "memory" / "current" / "project-state.md").write_text(
        "# Project State\n", encoding="utf-8"
    )
    (target / "memory" / "current" / "task-context.md").write_text(
        "# Task Context\n", encoding="utf-8"
    )
    result = installer.adopt_bootstrap(target=target, dry_run=True)

    cli._print_install_summary(result)

    output = capsys.readouterr().out
    assert "`populate` skill" not in output


def test_current_view_json_shape(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    payload = installer.show_current_memory(target=target)

    data = json.loads(installer.format_result_json(payload))

    assert data["notes"][0]["path"] == "memory/current/project-state.md"


def test_route_memory_prefers_canonical_doc_when_manifest_marks_note_canonical_elsewhere(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "domains").mkdir(parents=True)
    (target / "docs").mkdir(parents=True)
    (target / "memory" / "domains" / "api.md").write_text("# API memory\n", encoding="utf-8")
    (target / "docs" / "api.md").write_text("# API docs\n", encoding="utf-8")
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/domains/api.md"]
note_type = "domain"
canonical_home = "docs/api.md"
authority = "advisory"
audience = "human+agent"
canonicality = "canonical_elsewhere"
task_relevance = "optional"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/service/api.py"])

    assert any(
        action.path == target / "docs" / "api.md"
        and action.kind == "required"
        and "canonical doc takes precedence" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / "memory" / "domains" / "api.md"
        and action.kind == "recommended"
        and "fallback context only" in action.detail
        for action in result.actions
    )


def test_doctor_audit_flags_core_docs_that_depend_on_memory_when_policy_enabled(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "docs").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 30\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[rules]
forbid_core_docs_depend_on_memory = true
core_doc_globs = ["README.md", "docs/**/*.md"]
core_doc_exclude_globs = ["memory/**/*.md", "AGENTS.md"]

[notes."memory/index.md"]
note_type = "routing"
canonical_home = "memory/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        "See `memory/runbooks/deploy.md` for the stable deployment procedure.\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "README.md"
        and action.kind == "manual review"
        and "core doc depends on memory" in action.detail
        for action in result.actions
    )


def test_doctor_strict_doc_ownership_forces_audit_without_manifest_opt_in(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "docs").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 30\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[rules]
core_doc_globs = ["README.md"]
core_doc_exclude_globs = ["memory/**/*.md", "AGENTS.md"]
forbid_core_docs_depend_on_memory = false

[notes."memory/index.md"]
note_type = "routing"
canonical_home = "memory/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        "See memory/runbooks/deploy.md for deployment steps.\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target, strict_doc_ownership=True)

    assert any(
        action.path == target / "README.md"
        and "core doc depends on memory" in action.detail
        for action in result.actions
    )


def test_doctor_validates_manifest_canonicality_values(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 30\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/domains/api.md"]
note_type = "domain"
canonical_home = "memory/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "wrong"
task_relevance = "sometimes"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "memory" / "domains" / "api.md"
        and "manifest canonicality must be one of" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / "memory" / "domains" / "api.md"
        and "manifest task_relevance must be required or optional" in action.detail
        for action in result.actions
    )


def test_doctor_validates_optional_improvement_manifest_values(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 33\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/domains/api.md"]
note_type = "domain"
canonical_home = "memory/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "weird"
symptom_of = "bad"
preferred_remediation = "robot"
elimination_target = "gone"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("manifest memory_role must be durable_truth or improvement_signal" in action.detail for action in result.actions)
    assert any("manifest symptom_of must be one of" in action.detail for action in result.actions)
    assert any("manifest preferred_remediation must be one of" in action.detail for action in result.actions)
    assert any("manifest elimination_target must be one of" in action.detail for action in result.actions)


def test_doctor_rejects_canonical_elsewhere_targets_inside_memory(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "domains").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 30\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/domains/api.md"]
note_type = "domain"
canonical_home = "memory/invariants/api.md"
authority = "advisory"
audience = "human+agent"
canonicality = "canonical_elsewhere"
task_relevance = "optional"
surfaces = ["api"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    doctor = installer.doctor_bootstrap(target=target)
    routed = installer.route_memory(target=target, surfaces=["api"])

    assert any(
        action.path == target / "memory" / "domains" / "api.md"
        and "canonical_elsewhere notes must point canonical_home" in action.detail
        for action in doctor.actions
    )
    assert not any(
        action.path == target / "memory" / "invariants" / "api.md"
        and action.kind == "required"
        for action in routed.actions
    )


def test_promotion_report_finds_candidate_notes_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "domains").mkdir(parents=True)
    (target / "memory" / "domains" / "api.md").write_text(
        "# API\n\nStable policy draft.\n", encoding="utf-8"
    )
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[notes."memory/domains/api.md"]
note_type = "domain"
canonical_home = "docs/api.md"
authority = "advisory"
audience = "human+agent"
canonicality = "candidate_for_promotion"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.promotion_report(target=target)

    assert any(
        action.path == target / "memory" / "domains" / "api.md"
        and action.kind == "candidate"
        and "suggested canonical doc docs/api.md" in action.detail
        for action in result.actions
    )


def test_promotion_report_supports_explicit_notes_without_manifest_metadata(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "runbooks").mkdir(parents=True)
    (target / "memory" / "runbooks" / "deploy.md").write_text(
        "# Deploy\n\nProcedure.\n", encoding="utf-8"
    )

    result = installer.promotion_report(
        target=target, notes=["memory/runbooks/deploy.md"]
    )

    assert any(
        action.path == target / "memory" / "runbooks" / "deploy.md"
        and "checked-in skill" in action.detail
        for action in result.actions
    )


def test_promotion_report_marks_missing_explicit_notes_for_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)

    result = installer.promotion_report(
        target=target, notes=["memory/runbooks/deply.md"]
    )

    assert any(
        action.path == target / "memory" / "runbooks" / "deply.md"
        and action.kind == "manual review"
        and "file does not exist" in action.detail
        for action in result.actions
    )


def test_doctor_shadow_doc_detection_flags_overlap(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory" / "domains").mkdir(parents=True)
    (target / "docs").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system").mkdir(parents=True)
    (target / "memory" / "system" / "VERSION.md").write_text(
        "Version: 30\n", encoding="utf-8"
    )
    shared_text = (
        "deployment rollback procedure staging production release verification "
        "service health incident operator checklist observability\n"
    )
    (target / "memory" / "domains" / "deploy.md").write_text(
        shared_text, encoding="utf-8"
    )
    (target / "docs" / "deploy.md").write_text(shared_text, encoding="utf-8")
    (target / "memory" / "manifest.toml").write_text(
        """
version = 1

[rules]
forbid_core_docs_depend_on_memory = true
core_doc_globs = ["docs/**/*.md"]
core_doc_exclude_globs = ["memory/**/*.md", "AGENTS.md"]

[notes."memory/domains/deploy.md"]
note_type = "domain"
canonical_home = "memory/domains/deploy.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "memory" / "domains" / "deploy.md"
        and action.role == "shadow-doc-audit"
        and "shadow-doc overlap" in action.detail
        for action in result.actions
    )
