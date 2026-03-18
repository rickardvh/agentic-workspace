from __future__ import annotations

import json
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


def test_list_bundled_skills_includes_memory_and_bootstrap_skills() -> None:
    result = installer.list_bundled_skills()

    bundled = {action.path.name for action in result.actions if action.kind == "bundled skill"}

    assert {
        "memory-hygiene",
        "memory-capture",
        "memory-refresh",
        "memory-router",
        "bootstrap-adoption",
        "bootstrap-populate",
        "bootstrap-upgrade",
    }.issubset(bundled)


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


def test_build_substitutions_supports_explicit_placeholder_flags(tmp_path: Path) -> None:
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
    (target / "memory" / "current" / "project-state.md").write_text("# Project State\n\nok\n", encoding="utf-8")
    (target / "memory" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n\n## Last confirmed\n\n2026-01-01\n",
        encoding="utf-8",
    )

    result = installer.check_current_memory(target=target)

    assert any(action.category == "placeholder-review" for action in result.actions)
    assert any("not been confirmed" in action.detail for action in result.actions)


def test_route_memory_adds_baseline_and_runtime_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "index.md").write_text((Path("memory/index.md")).read_text(encoding="utf-8"), encoding="utf-8")

    result = installer.route_memory(target=target, files=["deploy/k8s/service.yaml"])
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "recommended"}

    assert "memory/current/project-state.md" in suggested
    assert "memory/current/task-context.md" in suggested
    assert "memory/domains/<runtime-or-deployment-note>.md" in suggested
    assert "memory/runbooks/<relevant-operator-runbook>.md" in suggested


def test_route_memory_adds_architecture_suggestions(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "index.md").write_text((Path("memory/index.md")).read_text(encoding="utf-8"), encoding="utf-8")

    result = installer.route_memory(target=target, files=["src/architecture/schema.py"])
    suggested = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "recommended"}

    assert "memory/invariants/<relevant-invariant-note>.md" in suggested
    assert "memory/decisions/README.md" in suggested


def test_sync_memory_without_input_returns_guidance(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.sync_memory(target=target)

    assert len(result.actions) == 1
    assert result.actions[0].kind == "manual review"
    assert "provide --files/--notes" in result.actions[0].detail


def test_sync_memory_with_explicit_file_produces_recommendations(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "index.md").write_text((Path("memory/index.md")).read_text(encoding="utf-8"), encoding="utf-8")

    result = installer.sync_memory(target=target, files=["tests/test_cli.py"])

    assert any(action.kind in {"review", "update", "update index"} for action in result.actions)


def test_verify_payload_passes_for_current_payload(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.verify_payload(target=target)

    assert not any(action.category == "contract-drift" for action in result.actions)


def test_verify_payload_flags_forbidden_current_note(monkeypatch, tmp_path: Path) -> None:
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
    (payload / "memory" / "system" / "WORKFLOW.md").write_text("# Workflow Rules\n", encoding="utf-8")
    (payload / "memory" / "current" / "project-state.md").write_text("# Project State\n", encoding="utf-8")
    (payload / "memory" / "current" / "task-context.md").write_text("# Task Context\n", encoding="utf-8")
    (payload / "memory" / "current" / "active-decisions.md").write_text("# Active Decisions\n", encoding="utf-8")
    (payload / "memory" / "domains" / "README.md").write_text("# Domains\n", encoding="utf-8")
    (payload / "memory" / "invariants" / "README.md").write_text("# Invariants\n", encoding="utf-8")
    (payload / "memory" / "runbooks" / "README.md").write_text("# Runbooks\n", encoding="utf-8")
    (payload / "memory" / "mistakes" / "recurring-failures.md").write_text("# Recurring Failures\n", encoding="utf-8")
    (payload / "memory" / "decisions" / "README.md").write_text("# Decisions\n", encoding="utf-8")
    (payload / "scripts" / "check" / "check_memory_freshness.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(installer, "payload_root", lambda: payload)
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    result = installer.verify_payload(target=target)

    assert any(
        action.path.relative_to(target).as_posix() == "memory/current/active-decisions.md"
        and action.category == "contract-drift"
        for action in result.actions
    )


def test_doctor_reports_placeholder_review_category(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / "memory" / "current").mkdir(parents=True)
    (target / "memory" / "system").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 8\n", encoding="utf-8")
    (target / "memory" / "system" / "WORKFLOW.md").write_text("old workflow\n", encoding="utf-8")
    (target / "memory" / "current" / "task-context.md").write_text("# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(action.category == "placeholder-review" for action in result.actions)


def test_cli_parser_accepts_new_commands_and_placeholder_flags() -> None:
    parser = cli.build_parser()

    current_args = parser.parse_args(["current", "check", "--target", "."])
    list_skills_args = parser.parse_args(["list-skills", "--format", "json"])
    prompt_args = parser.parse_args(["prompt", "adopt", "--target", "C:/repo"])
    route_args = parser.parse_args(["route", "--files", "src/app.py"])
    sync_args = parser.parse_args(["sync-memory", "--notes", "memory/index.md"])
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
    assert prompt_args.command == "prompt"
    assert prompt_args.prompt_command == "adopt"
    assert route_args.command == "route"
    assert sync_args.command == "sync-memory"
    assert verify_args.command == "verify-payload"
    assert install_args.project_purpose == "purpose"


def test_build_agent_prompt_mentions_list_skills_and_target() -> None:
    prompt = cli._build_agent_prompt("adopt", target="C:/repo")

    assert "agentic-memory-bootstrap list-skills" in prompt
    assert "bootstrap-adoption" in prompt
    assert "bootstrap-populate" in prompt
    assert "C:/repo" in prompt


def test_current_view_json_shape(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)
    payload = installer.show_current_memory(target=target)

    data = json.loads(installer.format_result_json(payload))

    assert data["notes"][0]["path"] == "memory/current/project-state.md"
