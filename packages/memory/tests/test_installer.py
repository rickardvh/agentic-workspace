from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from repo_memory_bootstrap import cli, installer
from repo_memory_bootstrap._installer_output import _infer_action_category
from repo_memory_bootstrap._installer_shared import (
    MEMORY_COMPATIBILITY_CONTRACT_FILES,
    MEMORY_LOWER_STABILITY_HELPER_FILES,
    PAYLOAD_REQUIRED_FILES,
    WORKSPACE_POINTER_BLOCK,
)
from repo_memory_bootstrap._ownership import module_root as memory_module_root

FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures" / "routing"
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
MEMORY_INDEX_TEMPLATE = FIXTURES_ROOT / "memory-index-template.md"
MEMORY_MANIFEST_TEMPLATE = FIXTURES_ROOT / "memory-manifest-template.toml"
MEMORY_GIT_SOURCE_REF = "git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory"


@pytest.fixture(autouse=True)
def _mkdir_before_write_text(monkeypatch: pytest.MonkeyPatch) -> None:
    original_write_text = Path.write_text

    def _write(self: Path, data: str, encoding: str | None = None, errors: str | None = None, newline: str | None = None) -> int:
        self.parent.mkdir(parents=True, exist_ok=True)
        return original_write_text(self, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", _write)


def test_ownership_module_root_matches_workspace_ledger() -> None:
    assert memory_module_root("memory") == Path(".agentic-workspace/memory")


def test_memory_contract_file_shortlist_is_explicit() -> None:
    assert Path("AGENTS.md") in MEMORY_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/memory/repo/index.md") in MEMORY_COMPATIBILITY_CONTRACT_FILES
    assert Path(".agentic-workspace/memory/repo/manifest.toml") in MEMORY_COMPATIBILITY_CONTRACT_FILES
    assert Path("scripts/check/check_memory_freshness.py") in MEMORY_LOWER_STABILITY_HELPER_FILES
    assert Path(".agentic-workspace/memory/bootstrap/README.md") in MEMORY_LOWER_STABILITY_HELPER_FILES
    assert set(MEMORY_COMPATIBILITY_CONTRACT_FILES).isdisjoint(MEMORY_LOWER_STABILITY_HELPER_FILES)
    assert set(MEMORY_COMPATIBILITY_CONTRACT_FILES) | set(MEMORY_LOWER_STABILITY_HELPER_FILES) == set(PAYLOAD_REQUIRED_FILES)


def _memory_index_text() -> str:
    if MEMORY_INDEX_TEMPLATE.exists():
        return MEMORY_INDEX_TEMPLATE.read_text(encoding="utf-8")
    root_index = WORKSPACE_ROOT / ".agentic-workspace" / "memory" / "repo" / "index.md"
    if root_index.exists():
        return root_index.read_text(encoding="utf-8")
    payload_index = installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "index.md"
    if payload_index.exists():
        return payload_index.read_text(encoding="utf-8")
    return (PACKAGE_ROOT / "memory" / "index.md").read_text(encoding="utf-8")


def _memory_manifest_text() -> str:
    if MEMORY_MANIFEST_TEMPLATE.exists():
        return MEMORY_MANIFEST_TEMPLATE.read_text(encoding="utf-8")
    root_manifest = WORKSPACE_ROOT / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    if root_manifest.exists():
        return root_manifest.read_text(encoding="utf-8")
    payload_manifest = installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    if payload_manifest.exists():
        return payload_manifest.read_text(encoding="utf-8")
    return (PACKAGE_ROOT / "memory" / "manifest.toml").read_text(encoding="utf-8")


def _project_state_text() -> str:
    root_note = WORKSPACE_ROOT / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    if root_note.exists():
        return root_note.read_text(encoding="utf-8")
    payload_note = installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    if payload_note.exists():
        return payload_note.read_text(encoding="utf-8")
    return (PACKAGE_ROOT / "memory" / "current" / "project-state.md").read_text(encoding="utf-8")


def _task_context_text() -> str:
    root_note = WORKSPACE_ROOT / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md"
    if root_note.exists():
        return root_note.read_text(encoding="utf-8")
    payload_note = installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md"
    if payload_note.exists():
        return payload_note.read_text(encoding="utf-8")
    return (PACKAGE_ROOT / "memory" / "current" / "task-context.md").read_text(encoding="utf-8")


def _load_routing_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def _write_repo_file(target: Path, relative_path: str, text: str) -> None:
    path = target / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_routing_fixture_file(
    target: Path, fixture_name: str, payload: dict[str, object] | None = None, raw_text: str | None = None
) -> None:
    fixture_path = target / "tests" / "fixtures" / "routing" / fixture_name
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_text is not None:
        fixture_path.write_text(raw_text, encoding="utf-8")
        return
    content = payload if payload is not None else _load_routing_fixture(fixture_name)
    fixture_path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def _setup_routing_fixture_repo(target: Path, fixture_name: str) -> dict[str, object]:
    fixture = _load_routing_fixture(fixture_name)
    (target / ".git").mkdir(parents=True, exist_ok=True)
    _write_repo_file(target, ".agentic-workspace/memory/repo/index.md", _memory_index_text())
    _write_repo_file(target, ".agentic-workspace/memory/repo/domains/README.md", "# Domains\n")
    _write_repo_file(target, ".agentic-workspace/memory/repo/invariants/README.md", "# Invariants\n")
    _write_repo_file(target, ".agentic-workspace/memory/repo/runbooks/README.md", "# Runbooks\n")
    _write_repo_file(target, ".agentic-workspace/memory/repo/decisions/README.md", "# Decisions\n")
    _write_repo_file(target, ".agentic-workspace/memory/repo/mistakes/recurring-failures.md", "# Recurring failures\n")

    if fixture_name == "canonical-doc-precedence.json":
        _write_repo_file(
            target,
            ".agentic-workspace/memory/repo/manifest.toml",
            (
                "version = 1\n\n"
                '[notes.".agentic-workspace/memory/repo/index.md"]\n'
                'note_type = "routing"\n'
                'canonical_home = ".agentic-workspace/memory/repo/index.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "required"\n'
                "routing_only = true\n"
                "high_level = true\n\n"
                '[notes.".agentic-workspace/memory/repo/domains/README.md"]\n'
                'note_type = "domain"\n'
                'canonical_home = ".agentic-workspace/memory/repo/domains/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["api"]\n'
                "routes_from = []\n"
                "stale_when = []\n\n"
                '[notes.".agentic-workspace/memory/repo/invariants/README.md"]\n'
                'note_type = "invariant"\n'
                'canonical_home = ".agentic-workspace/memory/repo/invariants/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["api"]\n'
                "routes_from = []\n"
                "stale_when = []\n"
            ),
        )
    elif fixture_name == "optional-pressure.json":
        _write_repo_file(
            target,
            ".agentic-workspace/memory/repo/manifest.toml",
            (
                "version = 1\n\n"
                '[notes.".agentic-workspace/memory/repo/index.md"]\n'
                'note_type = "routing"\n'
                'canonical_home = ".agentic-workspace/memory/repo/index.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "required"\n'
                "routing_only = true\n"
                "high_level = true\n\n"
                '[notes.".agentic-workspace/memory/repo/invariants/README.md"]\n'
                'note_type = "invariant"\n'
                'canonical_home = ".agentic-workspace/memory/repo/invariants/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["api"]\n'
                "routes_from = []\n"
                "stale_when = []\n\n"
                '[notes.".agentic-workspace/memory/repo/domains/README.md"]\n'
                'note_type = "domain"\n'
                'canonical_home = ".agentic-workspace/memory/repo/domains/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["api"]\n'
                "routes_from = []\n"
                "stale_when = []\n"
            ),
        )
    elif fixture_name == "missed-note-regression.json":
        _write_repo_file(
            target,
            ".agentic-workspace/memory/repo/manifest.toml",
            (
                "version = 1\n\n"
                '[notes.".agentic-workspace/memory/repo/index.md"]\n'
                'note_type = "routing"\n'
                'canonical_home = ".agentic-workspace/memory/repo/index.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "required"\n'
                "routing_only = true\n"
                "high_level = true\n\n"
                '[notes.".agentic-workspace/memory/repo/domains/README.md"]\n'
                'note_type = "domain"\n'
                'canonical_home = ".agentic-workspace/memory/repo/domains/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["tests"]\n'
                "routes_from = []\n"
                "stale_when = []\n\n"
                '[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]\n'
                'note_type = "recurring-failures"\n'
                'canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["tests"]\n'
                'routes_from = ["scripts/check/**/*.py"]\n'
                'stale_when = ["scripts/check/**/*.py"]\n'
            ),
        )
    elif fixture_name == "over-routing-regression.json":
        _write_repo_file(
            target,
            ".agentic-workspace/memory/repo/manifest.toml",
            (
                "version = 1\n\n"
                '[notes.".agentic-workspace/memory/repo/index.md"]\n'
                'note_type = "routing"\n'
                'canonical_home = ".agentic-workspace/memory/repo/index.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "required"\n'
                "routing_only = true\n"
                "high_level = true\n\n"
                '[notes.".agentic-workspace/memory/repo/domains/README.md"]\n'
                'note_type = "domain"\n'
                'canonical_home = ".agentic-workspace/memory/repo/domains/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["api"]\n'
                "routes_from = []\n"
                "stale_when = []\n\n"
                '[notes.".agentic-workspace/memory/repo/invariants/README.md"]\n'
                'note_type = "invariant"\n'
                'canonical_home = ".agentic-workspace/memory/repo/invariants/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["api"]\n'
                "routes_from = []\n"
                "stale_when = []\n"
            ),
        )
    elif fixture_name in {"runtime-basic.json", "architecture-basic.json"}:
        _write_repo_file(
            target,
            ".agentic-workspace/memory/repo/manifest.toml",
            (
                "version = 1\n\n"
                '[notes.".agentic-workspace/memory/repo/index.md"]\n'
                'note_type = "routing"\n'
                'canonical_home = ".agentic-workspace/memory/repo/index.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "required"\n'
                "routing_only = true\n"
                "high_level = true\n\n"
                '[notes.".agentic-workspace/memory/repo/domains/README.md"]\n'
                'note_type = "domain"\n'
                'canonical_home = ".agentic-workspace/memory/repo/domains/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["runtime", "architecture"]\n'
                "routes_from = []\n"
                "stale_when = []\n\n"
                '[notes.".agentic-workspace/memory/repo/runbooks/README.md"]\n'
                'note_type = "runbook"\n'
                'canonical_home = ".agentic-workspace/memory/repo/runbooks/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["runtime"]\n'
                "routes_from = []\n"
                "stale_when = []\n\n"
                '[notes.".agentic-workspace/memory/repo/invariants/README.md"]\n'
                'note_type = "invariant"\n'
                'canonical_home = ".agentic-workspace/memory/repo/invariants/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["architecture"]\n'
                "routes_from = []\n"
                "stale_when = []\n\n"
                '[notes.".agentic-workspace/memory/repo/decisions/README.md"]\n'
                'note_type = "decision"\n'
                'canonical_home = ".agentic-workspace/memory/repo/decisions/README.md"\n'
                'authority = "canonical"\n'
                'audience = "human+agent"\n'
                'canonicality = "agent_only"\n'
                'task_relevance = "optional"\n'
                'surfaces = ["architecture"]\n'
                "routes_from = []\n"
                "stale_when = []\n"
            ),
        )

    return fixture


def _routed_note_sets(result: installer.InstallResult, target: Path) -> tuple[set[str], set[str]]:
    required = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "required"}
    optional = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "optional"}
    return required, optional


def _routing_feedback_note(
    *, missed_cases: list[str] | None = None, over_cases: list[str] | None = None, last_confirmed: str = "2026-04-04"
) -> str:
    missed_block = "\n\n".join(missed_cases or [])
    over_block = "\n\n".join(over_cases or [])
    return (
        "# Routing Feedback\n\n"
        "## Status\n\n"
        "Active\n\n"
        "## Scope\n\n"
        "- Compact routing calibration cases only.\n\n"
        "## Load when\n\n"
        "- Reviewing whether a recorded routing case still reproduces.\n\n"
        "## Review when\n\n"
        "- A recorded routing case is tuned, rejected, or no longer useful.\n\n"
        "## Missed-note entries\n\n"
        f"{missed_block}\n\n"
        "## Over-routing entries\n\n"
        f"{over_block}\n\n"
        "## Synthesis\n\n"
        "- Keep only concrete calibration cases.\n\n"
        "## Last confirmed\n\n"
        f"{last_confirmed}\n"
    )


def test_detect_install_mode_is_full_without_todo_file(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)

    assert installer.detect_install_mode(tmp_path) == "full"


def test_payload_entries_do_not_include_todo_stub() -> None:
    entries = installer._payload_entries(installer.payload_root())

    assert all(entry.relative_path != Path("TODO.md") for entry in entries)
    assert all(".agent-work" not in entry.relative_path.as_posix() for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/repo/current/active-decisions.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/repo/current/task-context.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/repo/manifest.toml") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/SKILLS.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/UPGRADE-SOURCE.toml") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/bootstrap/README.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/bootstrap/skills/install/SKILL.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/skills/memory-router/SKILL.md") for entry in entries)
    assert any(entry.relative_path == Path(".agentic-workspace/memory/skills/memory-upgrade/SKILL.md") for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/bootstrap/skills/upgrade/SKILL.md") for entry in entries)
    assert all(entry.relative_path != Path(".agentic-workspace/memory/bootstrap/skills/upgrade/agents/openai.yaml") for entry in entries)


def test_payload_current_files_include_optional_routing_feedback() -> None:
    entries = installer._payload_entries(installer.payload_root())

    current_paths = {
        entry.relative_path.as_posix()
        for entry in entries
        if entry.relative_path.as_posix().startswith(".agentic-workspace/memory/repo/current/")
    }

    assert current_paths == {
        ".agentic-workspace/memory/repo/current/project-state.md",
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        ".agentic-workspace/memory/repo/current/task-context.md",
    }


def test_list_bundled_skills_only_includes_bootstrap_skills() -> None:
    result = installer.list_bundled_skills()

    bundled = {action.path.name for action in result.actions if action.kind == "bundled skill"}

    assert bundled == {
        "bootstrap-adoption",
        "bootstrap-populate",
        "bootstrap-upgrade",
        "bootstrap-uninstall",
    }
    assert all(action.detail == "registered packaged product skill" for action in result.actions if action.kind == "bundled skill")


def test_dev_bundled_skills_tree_only_contains_bootstrap_skill_directories() -> None:
    skills_dir = installer.skills_root()

    skill_dirs = {path.name for path in skills_dir.iterdir() if path.is_dir() and (path / "SKILL.md").exists()}

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

    assert detail == "equivalent optional Makefile convenience target already present (check-memory)"


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
    (source_root / "optional").mkdir(parents=True, exist_ok=True)
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
    assert makefile_actions[0].detail == "equivalent optional Makefile convenience target already present (check-memory)"


def test_install_does_not_duplicate_existing_optional_fragment(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
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

    assert patched == (f"# Agent Instructions\n\n{installer.WORKFLOW_POINTER_BLOCK}\n\nRepo-local rules live here.\n")


def test_doctor_flags_agents_that_embed_current_shared_workflow_sections(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text(
        "# Agent Instructions\n\n"
        f"{installer.WORKFLOW_POINTER_BLOCK}\n\n"
        "## Overview file\n"
        "- copied shared rule\n\n"
        "## Task-context file\n"
        "- copied shared rule\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 8\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md" and action.kind == "manual review" and "embeds shared workflow rules" in action.detail
        for action in result.actions
    )


def test_upgrade_replaces_shared_files_without_todo_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 7\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").write_text("old workflow\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert all(action.path != target / "TODO.md" for action in result.actions)
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "WORKFLOW.md"
        and action.kind == "would replace"
        and "planned change" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "UPGRADE-SOURCE.toml" and action.kind in {"current", "would create"}
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md" and action.kind == "would replace"
        for action in result.actions
    )


def test_doctor_reports_customised_seed_notes_as_expected_customisation(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\nlocalised\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == note_path and action.kind == "customised" and action.category == "customisation-present" for action in result.actions
    )


def test_memory_status_does_not_flag_absent_optional_append_targets_in_clean_repo(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.collect_status(target=target)

    assert any(
        action.path == target / "CONTRIBUTING.md" and action.kind == "current" and action.detail == "optional target absent"
        for action in result.actions
    )
    assert not any(action.path == target / "CONTRIBUTING.md" and action.kind == "missing" for action in result.actions)


def test_memory_doctor_does_not_flag_absent_optional_append_targets_in_clean_repo(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".github" / "pull_request_template.md"
        and action.kind == "current"
        and action.detail == "optional target absent"
        for action in result.actions
    )
    assert not any(action.path == target / ".github" / "pull_request_template.md" and action.kind == "missing" for action in result.actions)


def test_doctor_overlap_audit_ignores_generic_ownership_terms(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    domain_path = target / ".agentic-workspace" / "memory" / "repo" / "domains" / "ownership-domain.md"
    decision_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "ownership-decision.md"
    domain_path.write_text(
        (
            "# Ownership Domain\n\n"
            "ownership boundaries install installed root package packages workflow managed explicit contract "
            "consolidation lifecycle files read durable memory-only adapter\n"
        ),
        encoding="utf-8",
    )
    decision_path.write_text(
        (
            "# Ownership Decision\n\n"
            "ownership boundaries install installed root package packages workflow managed explicit contract "
            "consolidation lifecycle files read durable decision-specific ledger\n"
        ),
        encoding="utf-8",
    )

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/domains/ownership-domain.md"]\n'
        'note_type = "domain"\n'
        'canonical_home = ".agentic-workspace/memory/repo/domains/ownership-domain.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["ownership"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
        '\n[notes.".agentic-workspace/memory/repo/decisions/ownership-decision.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/ownership-decision.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["ownership"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit" and action.path in {domain_path, decision_path} and "ownership-decision.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_skips_explicit_primary_home_references(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    domain_path = target / ".agentic-workspace" / "memory" / "repo" / "domains" / "package-context.md"
    decision_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "package-context-decision.md"
    domain_path.write_text(
        (
            "# Package Context\n\n"
            "Package boundary context lives here.\n\n"
            "For the owning rationale, load `.agentic-workspace/memory/repo/decisions/package-context-decision.md` instead of expanding this note.\n"
        ),
        encoding="utf-8",
    )
    decision_path.write_text(
        ("# Package Context Decision\n\nThis note keeps the durable decision about the package boundary.\n"),
        encoding="utf-8",
    )

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/domains/package-context.md"]\n'
        'note_type = "domain"\n'
        'canonical_home = ".agentic-workspace/memory/repo/domains/package-context.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["packages"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["packages/**"]\n'
        'stale_when = ["packages/**"]\n'
        '\n[notes.".agentic-workspace/memory/repo/decisions/package-context-decision.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/package-context-decision.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["packages"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["packages/**"]\n'
        'stale_when = ["packages/**"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path in {domain_path, decision_path}
        and "package-context-decision.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_requires_shared_title_terms_for_decision_family_pairs(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    installed_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "installed-system.md"
    foundation_path = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "foundation-stability.md"
    shared_text = (
        "operational orchestration planning root-owned installs validation lifecycle boundaries adopted packages "
        "managed workspace authority consolidation checks\n"
    )
    installed_path.write_text("# Root-Owned Installed Systems\n\n" + shared_text, encoding="utf-8")
    foundation_path.write_text("# Repository Foundation Stability\n\n" + shared_text, encoding="utf-8")

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/decisions/installed-system.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/installed-system.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["orchestration"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
        '\n[notes.".agentic-workspace/memory/repo/decisions/foundation-stability.md"]\n'
        'note_type = "decision"\n'
        'canonical_home = ".agentic-workspace/memory/repo/decisions/foundation-stability.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'subsystems = ["orchestration"]\n'
        'surfaces = ["architecture"]\n'
        'routes_from = ["AGENTS.md"]\n'
        'stale_when = ["AGENTS.md"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path in {installed_path, foundation_path}
        and "foundation-stability.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_skips_distinct_package_context_notes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md").write_text(
        "# Memory Package Context\n\nMemory package authority lives in packages/memory/src and packages/memory/tests.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "planning-package-context.md").write_text(
        "# Planning Package Context\n\nPlanning package authority lives in packages/planning/src and packages/planning/tests.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/memory-package-context.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/memory-package-context.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["architecture"]
routes_from = ["packages/memory/**"]

[notes.".agentic-workspace/memory/repo/domains/planning-package-context.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/planning-package-context.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["architecture"]
routes_from = ["packages/planning/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md"
        and "planning-package-context.md" in action.detail
        for action in result.actions
    )


def test_doctor_overlap_audit_skips_package_context_companion_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md").write_text(
        "# Memory Package Context\n\nUse the companion skill for the checklist.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "package-context-inspection.md").write_text(
        "# Package Context Inspection\n\nUse the skill for execution.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/memory-package-context.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/memory-package-context.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["architecture"]
routes_from = ["packages/memory/**"]

[notes.".agentic-workspace/memory/repo/runbooks/package-context-inspection.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/package-context-inspection.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["runtime"]
routes_from = ["packages/memory/**", "packages/planning/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "memory-package-context.md"
        and "package-context-inspection.md" in action.detail
        for action in result.actions
    )


def test_upgrade_reports_customised_seed_notes_as_expected_customisation(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\nlocalised\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target)

    assert any(
        action.path == note_path
        and action.kind == "customised"
        and action.category == "customisation-present"
        and "preserving repo-local customisation during upgrade" in action.detail
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
        action.path != target / ".agentic-workspace" / "memory" / "repo" / "current" / "active-decisions.md" for action in result.actions
    )


def test_install_dry_run_includes_current_memory_baseline(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.install_bootstrap(target=target, dry_run=True)

    planned_copies = {action.path.relative_to(target).as_posix() for action in result.actions if action.kind == "would copy"}

    assert ".agentic-workspace/memory/repo/current/project-state.md" in planned_copies
    assert ".agentic-workspace/memory/repo/current/routing-feedback.md" in planned_copies
    assert ".agentic-workspace/memory/repo/current/task-context.md" in planned_copies
    assert ".agentic-workspace/memory/bootstrap/README.md" in planned_copies
    assert ".agentic-workspace/memory/repo/current/active-decisions.md" not in planned_copies


def test_install_writes_audit_clean_current_memory_seed_dates(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    for relative in (
        ".agentic-workspace/memory/repo/current/project-state.md",
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        ".agentic-workspace/memory/repo/current/task-context.md",
    ):
        text = (target / relative).read_text(encoding="utf-8")
        assert "<LAST_CONFIRMED_DATE>" not in text
        assert "## Last confirmed\n\n20" in text


def test_install_writes_audit_clean_recurring_failures_seed_date(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    text = (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").read_text(encoding="utf-8")
    assert "<LAST_CONFIRMED_DATE>" not in text
    assert "## Last confirmed\n\n20" in text


def test_bootstrap_recurring_failures_note_clarifies_anti_trap_contract() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").read_text(
        encoding="utf-8"
    )

    assert "anti-trap memory, not a bug tracker, issue mirror, or backlog" in text
    assert "one verified incident that clearly exposes a trap likely to recur" in text
    assert (
        "Move one-off bugs, active debugging, and status tracking into tests, canonical docs, issues, or the planning surface instead."
        in text
    )


def test_bootstrap_recurring_friction_ledger_clarifies_pre_backlog_evidence_contract() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md").read_text(
        encoding="utf-8"
    )

    assert "without opening a new issue yet" in text
    assert "This note is pre-backlog evidence, not a backlog, issue mirror, or execution log." in text
    assert "A later promotion decision can cite concrete recurrence bullets instead of chat memory." in text


def test_install_writes_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    text = (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8")
    assert 'source_type = "git"' in text
    assert MEMORY_GIT_SOURCE_REF in text
    assert 'source_label = "agentic-memory-bootstrap monorepo master"' in text
    assert 'recorded_at = "2026-04-05"' in text


def test_adopt_writes_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)

    installer.adopt_bootstrap(target=target)

    text = (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8")
    assert 'source_type = "git"' in text
    assert MEMORY_GIT_SOURCE_REF in text


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


def test_resolve_upgrade_source_defaults_to_git_when_metadata_missing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)

    resolved = installer.resolve_upgrade_source(target=target)

    assert resolved["source_type"] == "git"
    assert resolved["source_ref"] == MEMORY_GIT_SOURCE_REF
    assert resolved["source_label"] == "agentic-memory-bootstrap monorepo master"
    assert resolved["recorded_at"] == "2026-04-05"
    assert resolved["recommended_upgrade_after_days"] == 30


def test_upgrade_reports_resolved_source(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert any(
        action.path == target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and "upgrade source resolved to git" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and "recorded_at=2026-04-05" in action.detail
        for action in result.actions
    )


def test_doctor_reports_stale_upgrade_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").write_text(
        (
            'source_type = "git"\n'
            f'source_ref = "{MEMORY_GIT_SOURCE_REF}"\n'
            'source_label = "agentic-memory-bootstrap main"\n'
            'recorded_at = "2025-01-01"\n'
            "recommended_upgrade_after_days = 30\n"
        ),
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "warning"
        and "consider refreshing `.agentic-workspace/memory/UPGRADE-SOURCE.toml`" in action.detail
        for action in result.actions
    )


def test_upgrade_preserves_existing_local_source_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    source_path = target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml"
    source_path.write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert source_path.read_text(encoding="utf-8") == ('source_type = "local"\nsource_ref = "./local/agentic-memory"\n')
    assert any(
        action.path == source_path and action.kind == "current" and "preserving repo-local source selection" in action.detail
        for action in result.actions
    )


def test_upgrade_dry_run_does_not_include_bootstrap_workspace_files(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = installer.upgrade_bootstrap(target=target, dry_run=True)
    planned = {action.path.relative_to(target).as_posix() for action in result.actions}

    assert all(not path.startswith(".agentic-workspace/memory/bootstrap/") for path in planned)


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


def test_route_memory_reports_high_confidence_for_direct_manifest_matches(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(_memory_index_text(), encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
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
task_relevance = "required"
routes_from = ["src/api.py"]
surfaces = ["api"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/api.py"])

    assert result.route_summary["confidence"] == "high"
    assert result.route_summary["direct_match_count"] == 1
    assert result.route_summary["weak_signal_note_count"] == 0


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


def test_route_memory_uses_manifest_file_globs(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/repo_memory_bootstrap/cli.py"])

    assert any(
        action.kind == "optional"
        and action.path.relative_to(target).as_posix() == ".agentic-workspace/memory/repo/domains/cli.md"
        and "manifest path match" in action.detail
        and action.match_source == "file-path"
        for action in result.actions
    )


def test_route_memory_emits_improvement_pressure_for_matched_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md").write_text(
        ("# Deploy\n\n" + "boundary detail\n") * 80, encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/deploy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/deploy.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["deploy/**/*.yaml"]
stale_when = ["deploy/**/*.yaml"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["deploy/prod/service.yaml"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md"
        and action.kind == "consider"
        and "clearer canonical docs or refactor review" in action.detail
        for action in result.actions
    )


def test_route_memory_emits_strong_warning_for_six_plus_direct_matches(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
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

[notes.".agentic-workspace/memory/repo/domains/a.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/a.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/b.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/b.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/c.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/c.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/d.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/d.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/e.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/e.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/domains/f.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/f.md"
authority = "canonical"
audience = "human+agent"
task_relevance = "optional"
routes_from = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=["src/service.py"])

    assert result.route_summary["routed_note_count"] == 7
    assert result.route_summary["exceeded_target"] == "yes"
    warning = str(result.route_summary["warning"])
    assert "more than five notes" in warning


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


def test_sync_memory_emits_compact_primary_note_summary(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "cli.md").write_text("# CLI\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**"]
stale_when = ["src/**"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["src/service/api.py"])

    assert result.sync_summary["status"] == "actionable"
    assert result.sync_summary["primary_note"]["path"] == ".agentic-workspace/memory/repo/domains/cli.md"
    assert "Start with .agentic-workspace/memory/repo/domains/cli.md" in result.sync_summary["summary"]


def test_sync_memory_uses_manifest_staleness_triggers(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "cli.md").write_text("# CLI\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/cli.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/cli.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
related_validations = ["uv run pytest"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["src/repo_memory_bootstrap/installer.py"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "cli.md"
        and action.kind == "review"
        and "manifest staleness trigger matched" in action.detail
        for action in result.actions
    )


def test_sync_memory_emits_improvement_pressure_for_stale_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md").write_text(
        ("# Deploy\n\n" + "boundary detail\n") * 80, encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/deploy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/deploy.md"
authority = "canonical"
audience = "human+agent"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.sync_memory(target=target, files=["src/repo_memory_bootstrap/installer.py"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md"
        and action.kind == "consider"
        and "clearer canonical docs or refactor review" in action.detail
        for action in result.actions
    )


def test_verify_payload_passes_for_current_payload(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.verify_payload(target=target)

    assert not any(action.category == "contract-drift" for action in result.actions)


def test_verify_payload_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.verify_payload(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "compatibility contract files:" in action.detail
        and ".agentic-workspace/memory/repo/index.md" in action.detail
        and ".agentic-workspace/memory/repo/current/project-state.md" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "lower-stability helper files:" in action.detail
        and "scripts/check/check_memory_freshness.py" in action.detail
        and ".agentic-workspace/memory/bootstrap/README.md" in action.detail
        for action in result.actions
    )


def test_doctor_reports_contract_surface_shortlists(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "compatibility contract files:" in action.detail
        and ".agentic-workspace/memory/repo/runbooks/README.md" in action.detail
        and ".agentic-workspace/memory/repo/decisions/README.md" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "UPGRADE-SOURCE.toml"
        and action.kind == "current"
        and action.role == "payload-contract"
        and "lower-stability helper files:" in action.detail
        and ".agentic-workspace/memory/skills/README.md" in action.detail
        and "scripts/check/check_memory_freshness.py" in action.detail
        for action in result.actions
    )


def test_memory_freshness_audit_ignores_bootstrap_workspace(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    completed = subprocess.run(
        [
            sys.executable,
            str(installer.payload_root() / "scripts" / "check" / "check_memory_freshness.py"),
        ],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    )

    assert ".agentic-workspace/memory/bootstrap/" not in completed.stdout


def test_verify_payload_flags_forbidden_current_note(monkeypatch, tmp_path: Path) -> None:
    payload = tmp_path / "payload"
    (payload / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions").mkdir(parents=True, exist_ok=True)
    (payload / "scripts" / "check").mkdir(parents=True, exist_ok=True)
    (payload / "AGENTS.md").write_text("# Agent Instructions\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text("# Memory Index\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "WORKFLOW.md").write_text("# Workflow Rules\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text("# Project State\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text("# Task Context\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "active-decisions.md").write_text(
        "# Active Decisions\n", encoding="utf-8"
    )
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains" / "README.md").write_text("# Domains\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants" / "README.md").write_text("# Invariants\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "README.md").write_text("# Runbooks\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions" / "README.md").write_text("# Decisions\n", encoding="utf-8")
    (payload / "scripts" / "check" / "check_memory_freshness.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(installer, "payload_root", lambda: payload)
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.verify_payload(target=target)

    assert any(
        action.path.relative_to(target).as_posix() == ".agentic-workspace/memory/repo/current/active-decisions.md"
        and action.category == "contract-drift"
        for action in result.actions
    )


def test_doctor_reports_placeholder_review_category(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 8\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").write_text("old workflow\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text(
        "# Task Context\n\n<CURRENT_FOCUS>\n", encoding="utf-8"
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(action.category == "placeholder-review" for action in result.actions)


def test_doctor_agents_guidance_mentions_apply_local_entrypoint(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 10\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(action.path == target / "AGENTS.md" and "--apply-local-entrypoint" in action.detail for action in result.actions)


def test_doctor_flags_legacy_bootstrap_agents_prose_outside_managed_block(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        f"{installer.WORKFLOW_POINTER_BLOCK}\n\n"
        "Check `.agentic-workspace/memory/repo/skills/README.md` and the skill directories under `.agentic-workspace/memory/repo/skills/` "
        "for a checked-in memory skill whose name or description matches the task.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 39\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "AGENTS.md"
        and action.kind == "manual review"
        and "older bootstrap prose outside the managed workflow pointer block" in action.detail
        for action in result.actions
    )


def test_upgrade_keeps_agents_current_when_workflow_pointer_is_current(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "WORKFLOW.md").write_text("# Workspace workflow\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        f"# Agent instructions\n\n{WORKSPACE_POINTER_BLOCK}\n\nLocal repo instructions.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert any(action.path == target / "AGENTS.md" and action.kind == "current" for action in result.actions)
    assert not any(action.path == target / "AGENTS.md" and action.kind == "manual review" for action in result.actions)


def test_upgrade_can_remove_redundant_memory_pointer_when_workspace_pointer_is_present(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "WORKFLOW.md").write_text("# Workspace workflow\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        f"{WORKSPACE_POINTER_BLOCK}\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n\n"
        "Local repo instructions.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target, apply_local_entrypoint=True)
    agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")

    assert "<!-- agentic-memory:workflow:start -->" not in agents_text
    assert WORKSPACE_POINTER_BLOCK in agents_text
    assert any(action.path == target / "AGENTS.md" and action.kind == "patched" for action in result.actions)


def test_upgrade_migrates_legacy_layout_by_default(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "bootstrap").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "skills" / "memory-router").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system" / "WORKFLOW.md").write_text("legacy workflow\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")
    (target / "memory" / "system" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )
    (target / "memory" / "bootstrap" / "README.md").write_text("legacy bootstrap\n", encoding="utf-8")
    (target / "memory" / "skills" / "memory-router" / "SKILL.md").write_text("legacy router\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n",
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target)

    assert (target / ".agentic-workspace/memory" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8").startswith('source_type = "local"')
    assert not (target / "memory" / "system").exists()
    assert not (target / "memory" / "skills").exists()
    assert "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules." in (target / "AGENTS.md").read_text(encoding="utf-8")
    assert any(action.kind == "moved" for action in result.actions)
    assert not any(action.kind == "manual review" and "legacy managed layout detected" in action.detail for action in result.actions)


def test_upgrade_dry_run_simulates_default_migration_for_legacy_layout(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system" / "WORKFLOW.md").write_text("legacy workflow\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")
    (target / "memory" / "system" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n",
        encoding="utf-8",
    )

    result = installer.upgrade_bootstrap(target=target, dry_run=True)

    assert not (target / ".agentic-workspace/memory" / "WORKFLOW.md").exists()
    assert any(
        action.kind == "would move" and action.path == target / ".agentic-workspace/memory" / "WORKFLOW.md" for action in result.actions
    )
    assert any(action.kind == "would patch" and action.path == target / "AGENTS.md" for action in result.actions)


def test_migrate_layout_moves_legacy_managed_files_into_agentic_memory_root(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "bootstrap").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "skills" / "memory-router").mkdir(parents=True, exist_ok=True)
    (target / "memory" / "system" / "WORKFLOW.md").write_text("workflow\n", encoding="utf-8")
    (target / "memory" / "system" / "VERSION.md").write_text("Version: 38\n", encoding="utf-8")
    (target / "memory" / "system" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )
    (target / "memory" / "bootstrap" / "README.md").write_text("bootstrap\n", encoding="utf-8")
    (target / "memory" / "skills" / "memory-router" / "SKILL.md").write_text("router\n", encoding="utf-8")
    (target / "AGENTS.md").write_text(
        "# Agent instructions\n\n"
        "<!-- agentic-memory:workflow:start -->\n"
        "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-memory:workflow:end -->\n",
        encoding="utf-8",
    )

    result = installer.migrate_layout(target=target)

    assert (target / ".agentic-workspace/memory" / "WORKFLOW.md").read_text(encoding="utf-8") == "workflow\n"
    assert (target / ".agentic-workspace/memory" / "VERSION.md").read_text(encoding="utf-8") == "Version: 38\n"
    assert (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").read_text(encoding="utf-8").startswith('source_type = "local"')
    assert (target / ".agentic-workspace/memory" / "bootstrap" / "README.md").read_text(encoding="utf-8") == "bootstrap\n"
    assert (target / ".agentic-workspace/memory" / "skills" / "memory-router" / "SKILL.md").read_text(encoding="utf-8") == "router\n"
    assert not (target / "memory" / "system" / "WORKFLOW.md").exists()
    assert "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules." in (target / "AGENTS.md").read_text(encoding="utf-8")
    assert any(action.kind == "moved" for action in result.actions)


def test_cli_parser_accepts_new_commands_and_placeholder_flags() -> None:
    parser = cli.build_parser()

    current_args = parser.parse_args(["current", "check", "--target", "."])
    list_skills_args = parser.parse_args(["list-skills", "--format", "json"])
    cleanup_args = parser.parse_args(["bootstrap-cleanup", "--target", ".", "--format", "json"])
    migrate_args = parser.parse_args(["migrate-layout", "--target", ".", "--dry-run", "--format", "json"])
    uninstall_args = parser.parse_args(["uninstall", "--target", ".", "--dry-run", "--format", "json"])
    doctor_args = parser.parse_args(["doctor", "--target", ".", "--strict-doc-ownership"])
    prompt_install_args = parser.parse_args(["prompt", "install", "--target", "./repo"])
    prompt_args = parser.parse_args(["prompt", "adopt", "--target", "./repo"])
    prompt_populate_args = parser.parse_args(["prompt", "populate", "--target", "./repo"])
    prompt_uninstall_args = parser.parse_args(["prompt", "uninstall", "--target", "./repo"])
    route_args = parser.parse_args(["route", "--files", "src/app.py"])
    sync_args = parser.parse_args(["sync-memory", "--notes", ".agentic-workspace/memory/repo/index.md"])
    promotion_args = parser.parse_args(
        ["promotion-report", "--notes", ".agentic-workspace/memory/repo/domains/api.md", "--mode", "remediation"]
    )
    report_args = parser.parse_args(["report", "--target", ".", "--format", "json"])
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
            "--policy-profile",
            "strict-doc-ownership",
        ]
    )

    assert current_args.command == "current"
    assert list_skills_args.command == "list-skills"
    assert cleanup_args.command == "bootstrap-cleanup"
    assert migrate_args.command == "migrate-layout"
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
    assert promotion_args.mode == "remediation"
    assert report_args.command == "report"
    assert verify_args.command == "verify-payload"
    assert install_args.project_purpose == "purpose"
    assert install_args.policy_profile == "strict-doc-ownership"


def test_install_policy_profile_strict_doc_ownership_updates_manifest_rule(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target, policy_profile="strict-doc-ownership")

    manifest_text = (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").read_text(encoding="utf-8")
    assert "forbid_core_docs_depend_on_memory = true" in manifest_text


def test_install_policy_profile_strict_doc_ownership_reports_dry_run_update(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.install_bootstrap(target=target, dry_run=True, policy_profile="strict-doc-ownership")

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
        and action.kind == "would update"
        and "strict-doc-ownership" in action.detail
        for action in result.actions
    )


def test_memory_freshness_strict_default_does_not_fail_on_bootstrap_placeholders(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    result = subprocess.run(
        [sys.executable, "scripts/check/check_memory_freshness.py", "--strict"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Uncustomised routing placeholders:" not in result.stdout


def test_memory_freshness_strict_can_fail_on_bootstrap_placeholders_when_requested(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text(
        (target / ".agentic-workspace" / "memory" / "repo" / "index.md")
        .read_text(encoding="utf-8")
        .replace(
            "Treat starter examples as temporary orientation until the repository has real notes to replace them.",
            "Delete unused routing examples once the repository has concrete notes.",
        )
        + "\n- runtime or deployment change: `.agentic-workspace/memory/repo/domains/<runtime-or-deployment-note>.md`\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check/check_memory_freshness.py",
            "--strict",
            "--strict-categories",
            "uncustomised_index_placeholders",
        ],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Uncustomised routing placeholders:" in result.stdout
    assert "starter placeholder route examples" in result.stdout


def test_memory_freshness_reports_current_planning_state_residue(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
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

    result = subprocess.run(
        [sys.executable, "scripts/check/check_memory_freshness.py"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Current-context drift signals:" in result.stdout
    assert ".agentic-workspace/memory/repo/current/project-state.md" in result.stdout


def test_memory_report_derives_compact_module_state(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    report = installer.memory_report(target=target)

    assert report["kind"] == "memory-module-report/v1"
    assert report["schema"]["command"] == "agentic-memory-bootstrap report --target ./repo --format json"
    assert report["status"]["note_count"] >= 1
    assert report["status"]["current_note_count"] >= 2
    assert "current_notes" in report["active"]
    assert report["habitual_pull"]["status"] in {
        "ready-for-ordinary-work",
        "attention-needed",
        "needs-more-proof",
    }
    assert report["habitual_pull"]["ordinary_work_bundle"]["always_load"] == [".agentic-workspace/memory/repo/index.md"]
    assert "manual_review_count" in report["trust"]
    assert "state_counts" in report["trust"]
    assert "usefulness_audit" in report
    assert report["usefulness_audit"]["status"] in {"measured", "needs-more-proof", "attention-needed", "actionable"}


def test_memory_report_exposes_habitual_pull_boundary_and_evidence(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    report = installer.memory_report(target=target)

    habitual_pull = report["habitual_pull"]
    assert "repo-specific interpretive norms and recurring distinction hints" in habitual_pull["owner_boundary"]["memory_owns"]
    assert "broad repo doctrine or machine-readable policy" in habitual_pull["owner_boundary"]["memory_does_not_own"]
    assert habitual_pull["evidence"]["routing_fixture_count"] >= 0
    assert habitual_pull["ordinary_work_bundle"]["working_set_target"] == 3


def test_memory_report_classifies_trust_states_from_manifest_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)

    questionable_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "questionable-note.md"
    questionable_note.write_text("# Questionable\n", encoding="utf-8")
    stale_note = target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "stale-note.md"
    stale_note.write_text("# Stale\n", encoding="utf-8")
    improvement_note = target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "improvement-note.md"
    improvement_note.write_text("# Improvement\n", encoding="utf-8")

    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8")
        + """

[notes.".agentic-workspace/memory/repo/decisions/questionable-note.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/questionable-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["decision"]
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/decisions/stale-note.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/stale-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["decision"]
routes_from = ["missing/**/*.md"]
stale_when = ["missing/**/*.md"]
memory_role = "durable_truth"

[notes.".agentic-workspace/memory/repo/mistakes/improvement-note.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/improvement-note.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["test"]
surfaces = ["tests"]
routes_from = ["AGENTS.md"]
stale_when = ["AGENTS.md"]
memory_role = "improvement_signal"
improvement_candidate = true
preferred_remediation = "docs"
improvement_note = "Promote once docs improve."
elimination_target = "promote"
""",
        encoding="utf-8",
    )

    report = installer.memory_report(target=target)

    assert report["trust"]["state_counts"]["questionable"] >= 1
    assert report["trust"]["state_counts"]["stale"] >= 1
    assert report["trust"]["state_counts"]["elimination_candidate"] >= 1
    assert any(
        item["path"] == ".agentic-workspace/memory/repo/decisions/questionable-note.md" for item in report["trust"]["questionable_notes"]
    )
    assert any(
        item["path"] == ".agentic-workspace/memory/repo/mistakes/improvement-note.md" for item in report["trust"]["elimination_candidates"]
    )


def test_cli_version_flag_prints_package_version(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])

    assert excinfo.value.code == 0
    assert "agentic-memory-bootstrap" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "setup_installed_repo"),
    [
        (["list-files", "--target", ".", "--format", "json"], False),
        (["list-skills", "--format", "json"], False),
        (["prompt", "upgrade", "--target", "./repo"], False),
        (["install", "--target", ".", "--dry-run", "--format", "json"], False),
        (["adopt", "--target", ".", "--dry-run", "--format", "json"], False),
        (["status", "--target", ".", "--format", "json"], False),
        (["verify-payload", "--target", ".", "--format", "json"], False),
        (["doctor", "--target", ".", "--format", "json"], True),
        (["current", "show", "--target", ".", "--format", "json"], True),
        (["current", "check", "--target", ".", "--format", "json"], True),
        (["route", "--target", ".", "--files", "src/app.py", "--format", "json"], True),
        (["sync-memory", "--target", ".", "--files", "src/app.py", "--format", "json"], True),
        (
            [
                "promotion-report",
                "--target",
                ".",
                "--notes",
                ".agentic-workspace/memory/repo/index.md",
                "--mode",
                "remediation",
                "--format",
                "json",
            ],
            True,
        ),
        (["report", "--target", ".", "--format", "json"], True),
        (["upgrade", "--target", ".", "--dry-run", "--format", "json"], True),
        (["uninstall", "--target", ".", "--dry-run", "--format", "json"], True),
        (["bootstrap-cleanup", "--target", ".", "--format", "json"], True),
    ],
)
def test_cli_main_smoke_commands_return_zero(tmp_path: Path, argv: list[str], setup_installed_repo: bool) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    if setup_installed_repo:
        installer.install_bootstrap(target=target)

    completed = cli.main([arg if arg != "." else str(target) for arg in argv])

    assert completed == 0


def test_git_changed_files_times_out_with_warning(tmp_path: Path, monkeypatch, capsys) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["git", "status"], timeout=30)

    monkeypatch.setattr(installer.subprocess, "run", _raise_timeout)

    assert installer._git_changed_files(target) == []
    assert "Warning: git change detection failed" in capsys.readouterr().err


def test_verify_payload_reports_version_mismatch(tmp_path: Path, monkeypatch) -> None:
    payload = tmp_path / "payload"
    (payload / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace/memory" / "VERSION.md").write_text("Version: 21\n", encoding="utf-8")
    monkeypatch.setattr(installer, "payload_root", lambda: payload)

    result = installer.verify_payload(target=payload)

    assert any(
        action.path == payload / ".agentic-workspace/memory" / "VERSION.md"
        and action.kind == "manual review"
        and "does not match installer bootstrap version" in action.detail
        for action in result.actions
    )


def test_verify_payload_flags_missing_current_note_collaboration_guidance(tmp_path: Path, monkeypatch) -> None:
    payload = tmp_path / "payload"
    (payload / ".agentic-workspace/memory").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace/memory" / "VERSION.md").write_text(f"Version: {installer.BOOTSTRAP_VERSION}\n", encoding="utf-8")
    (payload / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "git"\nsource_ref = "example"\nsource_label = "Example"\nrecorded_at = "2026-04-06"\n',
        encoding="utf-8",
    )
    (payload / "AGENTS.md").write_text("# Agent Instructions\n", encoding="utf-8")
    (payload / "scripts" / "check").mkdir(parents=True, exist_ok=True)
    (payload / "scripts" / "check" / "check_memory_freshness.py").write_text("print('ok')\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (payload / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text("# Memory Index\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text("version = 1\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "domains" / "README.md").write_text("# Domains\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "invariants" / "README.md").write_text("# Invariants\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "README.md").write_text("# Runbooks\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (payload / ".agentic-workspace" / "memory" / "repo" / "decisions" / "README.md").write_text("# Decisions\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text("# Project State\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").write_text("# Task Context\n", encoding="utf-8")
    (payload / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md").write_text(
        "# Routing Feedback\n", encoding="utf-8"
    )

    monkeypatch.setattr(installer, "payload_root", lambda: payload)

    result = installer.verify_payload(target=payload)

    assert any(
        action.path == payload / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
        and action.kind == "manual review"
        and "collaboration-safe wording" in action.detail
        for action in result.actions
    )


def test_bootstrap_workflow_doc_includes_note_maintenance_and_skill_precedence_guidance() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "WORKFLOW.md").read_text(encoding="utf-8")

    assert "## Note maintenance rule" in text
    assert "Update a note when its primary home is still correct" in text
    assert "Checked-in repo-local skills should take precedence" in text
    assert "## Stale-note pressure" in text
    assert "## Canonical-doc boundary" in text
    assert "Treat memory as assistive residue by default" in text
    assert "## Interoperability contract" in text
    assert "active planning/status surface owns active intent and sequencing" in text
    assert "anti-trap memory for repeated or high-likelihood mistakes" in text
    assert "## Capture threshold" in text
    assert "## Anti-patterns" in text
    assert "Optimise for deletion and consolidation" in text
    assert "does not replace checking code, tests, or canonical docs" in text
    assert "user-specific preferences" in text
    assert "Memory is also a pressure layer" in text
    assert "## Improvement pressure" in text
    assert "## Improvement-targeting workflow" in text
    assert "record the intended post-remediation note shape before closing the signal" in text
    assert "## Remediation paths" in text
    assert "Treat `promotion-report` as the main elimination workflow" in text
    assert "Do not assume memory volume should trend downward across all repos or stages" in text
    assert "Judge memory by whether it justifies its cost and reduces rediscovery" in text
    assert "must not autonomously rewrite repo-owned docs, tests, scripts, or code outside the managed bootstrap surface" in text
    assert "prefer a clearer handoff into repo-owned work" in text
    assert "memory should help plans stay smaller by holding durable context that execplans can reference instead of repeating" in text
    assert "Repeated plan re-explanation or restart friction is a missing-synergy signal" in text
    assert "do not absorb plan history or milestone narration into memory" in text
    assert "## Starter templates" in text
    assert ".agentic-workspace/memory/repo/templates/memory-note-template.md" in text
    assert "## Improvement metadata quick reference" in text
    assert "`retention_justification`" in text


def test_bootstrap_index_includes_token_efficiency_and_small_routing_examples() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "index.md").read_text(encoding="utf-8")

    assert "## Common task bundles" in text
    assert "monorepo memory-package work" in text
    assert "workspace ownership or package-boundary change" in text
    assert "## Task routing" in text
    assert "If touching `packages/memory/**`, load `.agentic-workspace/memory/repo/domains/memory-package-context.md`." in text
    assert "not a task tracker, issue mirror, or broad fallback handbook" in text
    assert "## Loading rule" in text
    assert "## One-home reminder" in text
    assert "live decision review: the active planning slice plus `.agentic-workspace/memory/repo/decisions/README.md`" in text


def test_bootstrap_readme_includes_optional_patterns_and_project_state_shape() -> None:
    text = (installer.payload_root() / "README.md").read_text(encoding="utf-8")

    assert "Optional repo pattern only" in text
    assert "current focus, recent meaningful progress, blockers" in text
    assert "Memory owns durable repo knowledge" in text
    assert "anti-trap memory for repeated or high-likelihood mistakes" in text
    assert "When to write to memory" in text
    assert "When not to write to memory" in text
    assert "## Anti-patterns" in text
    assert "## Minimal Adoption Checklist" in text
    assert "the combined install should be cheaper than either one alone" in text
    assert "Combined-install leverage" in text
    assert "archived planning history" in text
    assert "Good memory systems should help an agent read less, not more." in text
    assert "Memory is a reasoning aid" in text
    assert "mixing user-specific memory with repo-specific technical truth" in text
    assert "durable truth" in text
    assert "improvement signal" in text
    assert "symptom captured -> remediation target chosen -> follow-up routed -> remediation lands" in text
    assert "## Improvement Paths" in text
    assert "live decision review: the active planning slice plus `.agentic-workspace/memory/repo/decisions/README.md`" in text
    assert "promotion-report --mode remediation" in text
    assert "Do not assume memory volume should follow one universal trend" in text
    assert "suggest upstream repo improvements instead of treating memory as the default answer to repo complexity" in text
    assert "remain advisory outside the managed bootstrap surface" in text
    assert "prefer a clearer handoff into repo-owned work" in text
    assert "`.agentic-workspace/memory/repo/templates/` as starter note templates" in text
    assert "`retention_justification`" in text


def test_bootstrap_payload_includes_starter_examples_for_primary_note_classes() -> None:
    payload_root = installer.payload_root()

    assert (payload_root / ".agentic-workspace" / "memory" / "repo" / "domains" / "example-runtime-boundary.md").exists()
    assert (payload_root / ".agentic-workspace" / "memory" / "repo" / "invariants" / "example-response-contract.md").exists()
    assert (payload_root / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "example-release-check.md").exists()
    assert (payload_root / ".agentic-workspace" / "memory" / "repo" / "decisions" / "example-cli-selection.md").exists()

    manifest_text = (payload_root / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").read_text(encoding="utf-8")
    assert '[notes.".agentic-workspace/memory/repo/domains/example-runtime-boundary.md"]' in manifest_text
    assert '[notes.".agentic-workspace/memory/repo/invariants/example-response-contract.md"]' in manifest_text
    assert '[notes.".agentic-workspace/memory/repo/runbooks/example-release-check.md"]' in manifest_text
    assert '[notes.".agentic-workspace/memory/repo/decisions/example-cli-selection.md"]' in manifest_text


def test_memory_note_template_includes_improvement_signal_metadata() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "templates" / "memory-note-template.md").read_text(
        encoding="utf-8"
    )

    assert "## Improvement signal metadata" in text
    assert "`preferred_remediation`" in text
    assert "`elimination_target`" in text
    assert "`config_treatment`" in text
    assert "`config_note`" in text


def test_bootstrap_task_context_starter_is_continuation_only() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md").read_text(encoding="utf-8")

    assert "Optional checked-in continuation compression" in text
    assert "## Blocking assumptions" in text
    assert "## Resume cues" in text
    assert "Do not turn it into a task list, backlog, execution log, roadmap, or sequencing surface." in text


def test_current_task_staleness_reason_mentions_planner_spillover() -> None:
    text = "\n".join(["line"] * (installer.CURRENT_TASK_MAX_LINES + 1))

    reason = installer._current_task_staleness_reason(text)

    assert reason is not None
    assert "planner, backlog, or execution-log spillover" in reason


def test_project_state_staleness_reason_mentions_planner_residue() -> None:
    text = "\n".join(["line"] * (installer.CURRENT_PROJECT_STATE_MAX_LINES + 1))

    reason = installer._project_state_staleness_reason(text)

    assert reason is not None
    assert "planner residue" in reason


def test_doctor_emits_improvement_pressure_suggestions_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 32\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring failures\n\n- This keeps happening.\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
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
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md"
        and action.kind == "consider"
        and "regression test" in action.detail
        and action.remediation_kind == "test"
        and action.remediation_target == "tests/test_recurring-failures.py"
        and action.memory_action == "shrink"
        for action in result.actions
    )


def test_sync_memory_appends_improvement_hint_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring failures\n\n- Guard this.\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
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
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md"
        and action.kind in {"review", "update"}
        and "consider a regression test" in action.detail
        and action.remediation_kind == "test"
        for action in result.actions
    )


def test_path_match_pattern_treats_double_star_as_zero_or_more_directories() -> None:
    assert installer._path_matches_pattern("tests/test_api.py", "tests/**/*.py")
    assert installer._path_matches_pattern("tests/unit/test_api.py", "tests/**/*.py")


def test_promotion_report_supports_improvement_candidates_without_docs_promotion(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "deploy.md").write_text(
        "# Deploy\n\n1. Run command A.\n2. Run command B.\n3. Verify status.\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/deploy.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/deploy.md"
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
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "deploy.md"
        and action.kind == "candidate"
        and "improvement candidate" in action.detail
        and "repo-owned script or command" in action.detail
        and action.remediation_kind == "script"
        and action.remediation_target == "scripts/deploy.py"
        and action.memory_action == "automate"
        for action in result.actions
    )


def test_promotion_report_groups_candidates_by_remediation_kind(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API\n\nStable guidance.\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "deploy.md").write_text(
        "# Deploy\n\n1. Run A.\n2. Run B.\n3. Run C.\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = "docs/api.md"
authority = "advisory"
audience = "human+agent"
canonicality = "candidate_for_promotion"
task_relevance = "optional"

[notes.".agentic-workspace/memory/repo/runbooks/deploy.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/deploy.md"
authority = "canonical"
audience = "human_operator"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "script"
improvement_candidate = true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.promotion_report(target=target, mode="remediation")
    remediation_kinds = [action.remediation_kind for action in result.actions if action.kind == "candidate"]

    assert remediation_kinds == ["docs", "script"]


def test_promotion_report_remediation_mode_filters_low_confidence_candidates(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text("# Memory Index\n\n" + ("line\n" * 140), encoding="utf-8")

    result = installer.promotion_report(target=target, notes=[".agentic-workspace/memory/repo/index.md"], mode="remediation")

    assert any(
        action.kind == "manual review" and "no promotion or elimination candidates found" in action.detail for action in result.actions
    )


def test_promotion_report_prefers_skill_for_prose_heavy_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "release.md").write_text(
        "# Release\n\n" + "\n".join(f"{idx}. Step {idx}" for idx in range(1, 12)),
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/release.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/release.md"
authority = "canonical"
audience = "human_operator"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
improvement_candidate = true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.promotion_report(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "release.md"
        and action.remediation_kind == "skill"
        and action.remediation_target == ".agentic-workspace/memory/repo/skills/release/SKILL.md"
        and action.memory_action == "automate"
        for action in result.actions
    )


def test_build_install_prompt_mentions_local_bootstrap_skills_and_target(
    monkeypatch,
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("install", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory-bootstrap init --target ./repo" in prompt
    assert "`install` skill at `./repo/.agentic-workspace/memory/bootstrap/skills`" in prompt
    assert "bootstrap-cleanup --target ./repo" in prompt
    assert ".agentic-workspace/memory/" in prompt
    assert "memory notes stay under `.agentic-workspace/memory/repo/`" in prompt


def test_build_adopt_prompt_mentions_local_bootstrap_skills_and_target(
    monkeypatch,
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("adopt", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory-bootstrap adopt --target ./repo" in prompt
    assert "`install` skill at `./repo/.agentic-workspace/memory/bootstrap/skills`" in prompt
    assert "`populate` from the same path" in prompt
    assert "bootstrap-cleanup --target ./repo" in prompt
    assert ".agentic-workspace/memory/" in prompt
    assert "memory notes stay under `.agentic-workspace/memory/repo/`" in prompt
    assert "./repo" in prompt


def test_build_populate_prompt_mentions_task_context_heuristic(monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("populate", target="./repo")

    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory-bootstrap current show --target ./repo" in prompt
    assert "`populate` skill at `./repo/.agentic-workspace/memory/bootstrap/skills`" in prompt
    assert "overview note only" in prompt
    assert "task-context.md" in prompt
    assert "./repo" in prompt


def test_build_upgrade_prompt_mentions_local_bootstrap_skills(monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("upgrade", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert "Use the checked-in `memory-upgrade` skill" in prompt
    assert "memory-upgrade" in prompt
    assert "./repo/.agentic-workspace/memory/skills/" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert "packaged upgrade flow for this repo" in prompt
    assert "prefer the installed `agentic-memory-bootstrap` CLI when available" in prompt
    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory-bootstrap upgrade --target <repo>" in prompt
    assert "bootstrap-cleanup --target ./repo" not in prompt
    assert not prompt.startswith("Run `")


def test_build_upgrade_prompt_uses_local_source_when_recorded(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"./tools/{name}")
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )

    prompt = cli._build_agent_prompt("upgrade", target=str(target))

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert "Use the checked-in `memory-upgrade` skill" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert "packaged upgrade flow for this repo" in prompt
    assert "uvx --from ./local/agentic-memory agentic-memory-bootstrap upgrade --target <repo>" in prompt
    assert MEMORY_GIT_SOURCE_REF not in prompt


def test_build_uninstall_prompt_mentions_bundled_skill(monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("uninstall", target="./repo")

    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory-bootstrap uninstall --target ./repo" in prompt
    assert "bootstrap-uninstall" in prompt


def test_build_prompt_falls_back_to_pipx_when_uvx_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda name: None if name == "uvx" else "./tools/pipx")

    prompt = cli._build_agent_prompt("upgrade", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert "Use the checked-in `memory-upgrade` skill" in prompt
    assert "./repo/.agentic-workspace/memory/skills/" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert f"pipx run --spec {MEMORY_GIT_SOURCE_REF} agentic-memory-bootstrap upgrade --target <repo>" in prompt
    assert "uvx --from" not in prompt


def test_memory_upgrade_skill_includes_module_fallback() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "skills" / "memory-upgrade" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "agentic-memory-bootstrap upgrade --target <repo>" in text
    assert "uvx --from <recorded-source> agentic-memory-bootstrap upgrade --target <repo>" in text
    assert "pipx run --spec <recorded-source> agentic-memory-bootstrap upgrade --target <repo>" in text
    assert "prefer a runner command from the recorded source" in text


def test_doctor_flags_legacy_upgrade_runbook_for_removal(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    legacy = target / ".agentic-workspace" / "memory" / "UPGRADE.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("# legacy\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == legacy and action.kind == "would remove" and action.category == "obsolete-managed-file" for action in result.actions
    )


def test_upgrade_removes_legacy_upgrade_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    legacy = target / ".agentic-workspace" / "memory" / "UPGRADE.md"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("# legacy\n", encoding="utf-8")

    result = installer.upgrade_bootstrap(target=target)

    assert not legacy.exists()
    assert any(
        action.path == legacy and action.kind == "removed" and action.category == "obsolete-managed-file" for action in result.actions
    )


def test_bootstrap_cleanup_removes_workspace(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    workspace = target / ".agentic-workspace/memory" / "bootstrap"
    assert workspace.exists()

    result = installer.cleanup_bootstrap_workspace(target=target)

    assert not workspace.exists()
    assert any(action.kind == "removed" for action in result.actions)


def test_bootstrap_cleanup_is_safe_when_workspace_absent(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.cleanup_bootstrap_workspace(target=target)

    assert any(action.kind == "skipped" for action in result.actions)


def test_uninstall_removes_safe_bootstrap_files(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)

    result = installer.uninstall_bootstrap(target=target)

    assert not (target / "AGENTS.md").exists()
    assert not (target / ".agentic-workspace" / "memory" / "repo" / "index.md").exists()
    assert not (target / "scripts" / "check" / "check_memory_freshness.py").exists()
    assert any(action.kind == "removed" for action in result.actions)


def test_uninstall_flags_customised_seed_notes_for_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    note_path = target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md"
    note_path.write_text("# Project State\n\ncustomised\n", encoding="utf-8")

    result = installer.uninstall_bootstrap(target=target, dry_run=True)

    assert any(action.path == note_path and action.kind == "manual review" for action in result.actions)


def test_uninstall_reports_remaining_repo_local_memory_as_safe_to_keep(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    installer.install_bootstrap(target=target)
    extra_note = target / ".agentic-workspace" / "memory" / "repo" / "domains" / "local-note.md"
    extra_note.parent.mkdir(parents=True, exist_ok=True)
    extra_note.write_text("# Local Note\n", encoding="utf-8")

    result = installer.uninstall_bootstrap(target=target, dry_run=True)

    assert any(action.path == extra_note and action.kind == "skipped" and "safe to keep" in action.detail for action in result.actions)


def test_install_summary_mentions_populate_next_step_when_current_notes_created(capsys, tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    result = installer.install_bootstrap(target=target, dry_run=True)

    cli._print_install_summary(result)

    output = capsys.readouterr().out
    assert "install or adopt lifecycle work" in output
    assert "bootstrap-cleanup" in output
    assert "install or upgrade review" not in output
    assert "`populate` skill" in output
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


@pytest.mark.parametrize(
    "fixture_name",
    [
        "runtime-basic.json",
        "architecture-basic.json",
        "canonical-doc-precedence.json",
        "optional-pressure.json",
        "missed-note-regression.json",
        "over-routing-regression.json",
    ],
)
def test_route_memory_matches_calibration_fixture_expectations(tmp_path: Path, fixture_name: str) -> None:
    target = tmp_path / fixture_name.removesuffix(".json")
    fixture = _setup_routing_fixture_repo(target, fixture_name)

    fixture_files = [str(item) for item in fixture["files"]] if isinstance(fixture.get("files"), list) else []
    fixture_surfaces = [str(item) for item in fixture["surfaces"]] if isinstance(fixture.get("surfaces"), list) else []
    expected_required = (
        set(str(item) for item in fixture["expected_required"]) if isinstance(fixture.get("expected_required"), list) else set()
    )
    expected_optional = (
        set(str(item) for item in fixture["expected_optional"]) if isinstance(fixture.get("expected_optional"), list) else set()
    )
    unexpected_notes = (
        set(str(item) for item in fixture["unexpected_notes"]) if isinstance(fixture.get("unexpected_notes"), list) else set()
    )
    missing_note_candidates = (
        set(str(item) for item in fixture["missing_note_candidates"]) if isinstance(fixture.get("missing_note_candidates"), list) else set()
    )

    result = installer.route_memory(
        target=target,
        files=fixture_files,
        surfaces=fixture_surfaces,
    )
    required, optional = _routed_note_sets(result, target)

    assert required == expected_required
    assert optional == expected_optional
    assert unexpected_notes.isdisjoint(required | optional)
    if missing_note_candidates:
        assert missing_note_candidates.issubset(required | optional)


def test_route_memory_matches_dot_managed_paths_as_direct_manifest_routes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    manifest_path = target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_text += (
        '\n[notes.".agentic-workspace/memory/repo/domains/dot-managed-route.md"]\n'
        'note_type = "domain"\n'
        'canonical_home = ".agentic-workspace/memory/repo/domains/dot-managed-route.md"\n'
        'authority = "canonical"\n'
        'audience = "human+agent"\n'
        'canonicality = "agent_only"\n'
        'task_relevance = "optional"\n'
        'surfaces = ["architecture"]\n'
        'routes_from = [".agentic-workspace/docs/reporting-contract.md"]\n'
        'stale_when = [".agentic-workspace/docs/reporting-contract.md"]\n'
    )
    manifest_path.write_text(manifest_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "dot-managed-route.md").write_text(
        "# Dot Managed Route\n",
        encoding="utf-8",
    )

    result = installer.route_memory(target=target, files=[".agentic-workspace/docs/reporting-contract.md"])
    required, optional = _routed_note_sets(result, target)

    assert required == {".agentic-workspace/memory/repo/index.md"}
    assert ".agentic-workspace/memory/repo/domains/dot-managed-route.md" in optional
    assert ".agentic-workspace/memory/repo/invariants/example-response-contract.md" not in optional


def test_route_memory_prefers_canonical_doc_when_manifest_marks_note_canonical_elsewhere(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API memory\n", encoding="utf-8")
    (target / "docs" / "api.md").write_text("# API docs\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
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
        action.path == target / "docs" / "api.md" and action.kind == "required" and "canonical doc takes precedence" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and action.kind == "optional"
        and "fallback context only" in action.detail
        for action in result.actions
    )


def test_route_review_handles_missing_feedback_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)

    result = installer.review_routes(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md"
        and action.kind == "manual review"
        and "routing feedback note is absent" in action.detail
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


def test_route_review_reports_over_routing_case_that_still_fails(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    _write_repo_file(target, ".agentic-workspace/memory/repo/index.md", _memory_index_text())
    _write_repo_file(target, ".agentic-workspace/memory/repo/domains/too-broad.md", "# Too broad\n")
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/manifest.toml",
        (
            "version = 1\n\n"
            '[notes.".agentic-workspace/memory/repo/domains/too-broad.md"]\n'
            'note_type = "domain"\n'
            'canonical_home = ".agentic-workspace/memory/repo/domains/too-broad.md"\n'
            'authority = "canonical"\n'
            'audience = "human+agent"\n'
            'canonicality = "agent_only"\n'
            'task_relevance = "optional"\n'
            'routes_from = ["src/**/*.py"]\n'
            'stale_when = ["src/**/*.py"]\n'
        ),
    )
    _write_repo_file(
        target,
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
        _routing_feedback_note(
            over_cases=[
                "### Case: too-broad-domain\n"
                "Task surface summary\n"
                "- Generic src python change.\n"
                "Files\n"
                "- src/service.py\n"
                "Surfaces\n"
                "- api\n"
                "Routed notes returned\n"
                "- .agentic-workspace/memory/repo/index.md\n"
                "- .agentic-workspace/memory/repo/domains/too-broad.md\n"
                "Unexpected notes\n"
                "- .agentic-workspace/memory/repo/domains/too-broad.md\n"
                "Why they were unnecessary\n"
                "- The note is too broad for this route.\n"
                "Status\n"
                "- open"
            ]
        ),
    )

    result = installer.review_routes(target=target)

    assert result.review_summary["still_over_routed_count"] == 1
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


def test_route_report_supports_fixtures_only(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "architecture-basic.json")

    result = installer.report_routes(target=target)

    assert result.route_report_summary["feedback"]["total_feedback_case_count"] == 0
    assert result.route_report_summary["fixtures"]["fixture_count"] == 2
    assert result.route_report_summary["fixtures"]["passing_fixture_count"] == 2


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


def test_route_report_fixture_counts_and_working_set_metrics_are_correct(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    _setup_routing_fixture_repo(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "runtime-basic.json")
    _write_routing_fixture_file(target, "architecture-basic.json")
    failing = _load_routing_fixture("runtime-basic.json")
    failing["name"] = "failing"
    failing["expected_optional"] = [".agentic-workspace/memory/repo/domains/wrong.md"]
    _write_routing_fixture_file(target, "failing.json", payload=failing)

    result = installer.report_routes(target=target)
    summary = result.route_report_summary["fixtures"]

    assert summary["fixture_count"] == 3
    assert summary["passing_fixture_count"] == 2
    assert summary["failing_fixture_count"] == 1
    assert summary["invalid_fixture_count"] == 0
    assert summary["average_routed_note_count"] == 3.0
    assert summary["average_required_note_count"] == 1.0
    assert summary["average_optional_note_count"] == 2.0
    assert summary["max_routed_note_count"] == 3
    assert summary["fixture_count_exceeding_target"] == 0
    assert summary["fixture_count_exceeding_strong_warning"] == 0
    assert summary["average_routed_line_count"] > 0
    assert summary["max_routed_line_count"] > 0
    confidence = result.route_report_summary["routing_confidence"]
    assert confidence["high_confidence_fixture_count"] >= 0
    assert confidence["medium_confidence_fixture_count"] >= 0
    assert confidence["low_confidence_fixture_count"] >= 0


def test_route_report_text_output_lists_only_failing_or_unresolved_items(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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

    cli._emit_result(installer.report_routes(target=target), output_format="text")
    output = capsys.readouterr().out

    assert "Feedback cases:" in output
    assert "Fixture coverage:" in output
    assert "Missed-note summary:" in output
    assert "Over-routing summary:" in output
    assert "Working-set pressure:" in output
    assert "Startup cost:" in output
    assert "fixture 'failing' fails" in output
    assert "case 'unresolved' is unresolved" in output
    assert "fixture 'runtime-basic' fails" not in output


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


def test_doctor_audits_routing_feedback_hygiene(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    _write_repo_file(target, ".agentic-workspace/memory/repo/index.md", _memory_index_text())
    filler = "\n".join("- filler" for _ in range(110))
    feedback_text = (
        "# Routing Feedback\n\n"
        "## Status\n\n"
        "Active\n\n"
        "## Scope\n\n"
        "- Oversized routing feedback test.\n\n"
        "## Load when\n\n"
        "- Reviewing calibration cases.\n\n"
        "## Review when\n\n"
        "- Compressing stale cases.\n\n"
        "## Missed-note entries\n\n"
        "### Case: incomplete-a\n"
        "Status\n"
        "- tuned\n\n"
        "### Case: resolved-b\n"
        "Task surface summary\n"
        "- Resolved case.\n"
        "Expected missing note\n"
        "- .agentic-workspace/memory/repo/domains/a.md\n"
        "Status\n"
        "- tuned\n\n"
        "### Case: resolved-c\n"
        "Task surface summary\n"
        "- Resolved case.\n"
        "Expected missing note\n"
        "- .agentic-workspace/memory/repo/domains/b.md\n"
        "Status\n"
        "- rejected\n\n"
        "### Case: resolved-d\n"
        "Task surface summary\n"
        "- Resolved case.\n"
        "Expected missing note\n"
        "- .agentic-workspace/memory/repo/domains/c.md\n"
        "Status\n"
        "- rejected\n\n"
        "## Over-routing entries\n\n"
        "## Synthesis\n\n"
        f"{filler}\n"
    )
    _write_repo_file(target, ".agentic-workspace/memory/repo/current/routing-feedback.md", feedback_text)

    result = installer.doctor_bootstrap(target=target)
    details = [
        action.detail for action in result.actions if action.path == target / ".agentic-workspace/memory/repo/current/routing-feedback.md"
    ]

    assert any("missing Last confirmed" in detail for detail in details)
    assert any("routing-feedback note is oversized" in detail for detail in details)
    assert any("too many resolved entries" in detail for detail in details)
    assert any("missing task surface summary" in detail for detail in details)
    assert any("missing expected missing/unexpected note entries" in detail for detail in details)


def test_doctor_audit_flags_core_docs_that_depend_on_memory_when_policy_enabled(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
forbid_core_docs_depend_on_memory = true
core_doc_globs = ["README.md", "docs/**/*.md"]
core_doc_exclude_globs = [".agentic-workspace/memory/repo/**/*.md", "AGENTS.md"]

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text(
        "See `.agentic-workspace/memory/repo/runbooks/deploy.md` for the stable deployment procedure.\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / "README.md" and action.kind == "manual review" and "core doc depends on memory" in action.detail
        for action in result.actions
    )


def test_doctor_strict_doc_ownership_forces_audit_without_manifest_opt_in(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
core_doc_globs = ["README.md"]
core_doc_exclude_globs = [".agentic-workspace/memory/repo/**/*.md", "AGENTS.md"]
forbid_core_docs_depend_on_memory = false

[notes.".agentic-workspace/memory/repo/index.md"]
note_type = "routing"
canonical_home = ".agentic-workspace/memory/repo/index.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / "README.md").write_text("See .agentic-workspace/memory/repo/runbooks/deploy.md for deployment steps.\n", encoding="utf-8")

    result = installer.doctor_bootstrap(target=target, strict_doc_ownership=True)

    assert any(action.path == target / "README.md" and "core doc depends on memory" in action.detail for action in result.actions)


def test_doctor_validates_manifest_canonicality_values(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
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
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and "manifest canonicality must be one of" in action.detail
        for action in result.actions
    )
    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and "manifest task_relevance must be required or optional" in action.detail
        for action in result.actions
    )


def test_doctor_validates_optional_improvement_manifest_values(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 33\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
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


def test_doctor_flags_incomplete_improvement_signal_lifecycle(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("preferred_remediation plus improvement_note, or retention_justification" in action.detail for action in result.actions)
    assert any("missing elimination_target" in action.detail for action in result.actions)
    assert any("should declare config_treatment" in action.detail for action in result.actions)
    assert any("should pair config_treatment with config_note" in action.detail for action in result.actions)


def test_doctor_accepts_retention_justification_for_improvement_signal(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        "# Recurring Failures\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
retention_justification = "The repo still lacks an executable replacement for this recurring operator trap."
elimination_target = "shrink"
config_treatment = "retain"
config_note = "Current config does not change the need to keep this trap visible until an executable replacement exists."
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any("retention_justification" in action.detail for action in result.actions)
    assert not any("config_treatment" in action.detail for action in result.actions)


def test_doctor_flags_invalid_config_treatment_metadata(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md").write_text(
        "# Recurring Friction Ledger\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "validation"
improvement_note = "Promote repeated friction into stronger remediation."
elimination_target = "promote"
config_treatment = "escalate"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("manifest config_treatment must be one of" in action.detail for action in result.actions)
    assert any("should pair config_treatment with config_note" in action.detail for action in result.actions)


def test_doctor_emits_recurring_friction_promotion_pressure_for_repeated_entry(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 32\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md").write_text(
        """
# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight recurring friction evidence.

## Load when

- The same friction shows up again.

## Review when

- A friction class is promoted elsewhere.

## Failure signals

- The same friction keeps recurring.

## When to use this

- The signal is real but still below issue threshold.

## Rules

- Keep one entry per friction class.

## Entry format

### Friction: missing-memory-capture

Observed recurrences
- 2026-04-20: Post-task friction was noticed but not captured.
- 2026-04-22: Another task required the same manual rescue.

Keep now
- Two recurrences are enough to preserve, but the exact fix still needs shaping.

Promote when
- The same friction recurs again or a clear package change presents itself.

Most likely remediation
- validation

Config treatment
- promote because current repo posture prefers escalating repeated workflow drift instead of letting it stay note-only evidence.

Last seen
2026-04-22 during issue #263 first slice

## Verification

- Repeated friction can be preserved without opening an issue immediately.

## Boundary reminder

- This note is pre-backlog evidence.

## Last confirmed

2026-04-22 during issue #263 first slice
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "validation"
improvement_candidate = true
improvement_note = "Promote repeated friction into stronger remediation."
elimination_target = "promote"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md"
        and action.role == "recurring-friction-audit"
        and action.kind == "consider"
        and "has 2 observed recurrences" in action.detail
        for action in result.actions
    )


def test_doctor_flags_missing_config_treatment_in_recurring_friction_entry(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 32\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "recurring-friction-ledger.md").write_text(
        """
# Recurring Friction Ledger

## Status

Active

## Scope

- Lightweight recurring friction evidence.

## Load when

- The same friction shows up again.

## Review when

- A friction class is promoted elsewhere.

## Failure signals

- The same friction keeps recurring.

## When to use this

- The signal is real but still below issue threshold.

## Rules

- Keep one entry per friction class.

## Entry format

### Friction: missing-memory-capture

Observed recurrences
- 2026-04-20: Post-task friction was noticed but not captured.

Keep now
- One recurrence is enough to preserve while the exact remediation is still forming.

Promote when
- The same friction recurs again or a clear package change presents itself.

Most likely remediation
- validation

Last seen
2026-04-22 during issue #263 second slice

## Verification

- Repeated friction can be preserved without opening an issue immediately.

## Boundary reminder

- This note is pre-backlog evidence.

## Last confirmed

2026-04-22 during issue #263 second slice
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "improvement_signal"
preferred_remediation = "validation"
improvement_candidate = true
improvement_note = "Promote repeated friction into stronger remediation."
elimination_target = "promote"
config_treatment = "promote"
config_note = "Current repo posture prefers escalating repeated workflow drift."
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("missing Config treatment" in action.detail for action in result.actions)


def test_doctor_flags_manifest_routing_drift_for_small_default_surface(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
routing_only = [".agentic-workspace/memory/repo/index.md", ".agentic-workspace/memory/WORKFLOW.md"]
high_level = [".agentic-workspace/memory/repo/index.md", ".agentic-workspace/memory/repo/current/task-context.md"]

[notes.".agentic-workspace/memory/WORKFLOW.md"]
note_type = "workflow-policy"
canonical_home = ".agentic-workspace/memory/WORKFLOW.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "required"

[notes.".agentic-workspace/memory/repo/current/task-context.md"]
note_type = "current-context"
canonical_home = ".agentic-workspace/memory/repo/current/task-context.md"
authority = "canonical"
audience = "agent"
canonicality = "agent_only"
task_relevance = "required"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)
    details = [action.detail for action in result.actions]

    assert any("rules.routing_only should contain only .agentic-workspace/memory/repo/index.md" in detail for detail in details)
    assert any("rules.high_level should not include .agentic-workspace/memory/repo/current/task-context.md" in detail for detail in details)
    assert any("WORKFLOW.md should remain reference policy" in detail for detail in details)
    assert any("task-context should stay optional continuation compression" in detail for detail in details)
    assert any("task-context should not advertise broad routing metadata" in detail for detail in details)


def test_doctor_flags_task_board_dependence_outside_current_notes(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text("# API\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
task_board_globs = ["TODO.md"]

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
routes_from = ["TODO.md"]
stale_when = ["TODO.md"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("task-board globs should not drive durable memory routing" in action.detail for action in result.actions)


def test_doctor_flags_canonical_dir_and_note_type_drift(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "misc").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "misc" / "api.md").write_text("# API\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "wrong.md").write_text("# Wrong\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
canonical_dirs = [".agentic-workspace/memory/repo/domains", ".agentic-workspace/memory/repo/invariants", ".agentic-workspace/memory/repo/runbooks", ".agentic-workspace/memory/repo/mistakes", ".agentic-workspace/memory/repo/decisions"]

[notes.".agentic-workspace/memory/repo/domains/wrong.md"]
note_type = "invariant"
canonical_home = ".agentic-workspace/memory/repo/domains/wrong.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"

[notes."memory/misc/api.md"]
note_type = "invariant"
canonical_home = "memory/misc/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any("durable memory notes should live under rules.canonical_dirs" in action.detail for action in result.actions)
    assert any(
        "notes under .agentic-workspace/memory/repo/domains/ should keep note_type = domain" in action.detail for action in result.actions
    )


def test_doctor_enforces_routing_feedback_as_calibration_only(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md").write_text(
        """# Routing Feedback

## Status

Active

## Scope

- Calibration only.

## Load when

- Reviewing routing.

## Review when

- Routes change.

## Missed-note entries

## Over-routing entries

## Synthesis

- Keep this compact.

## Last confirmed

2026-04-05
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/routing-feedback.md"]
note_type = "routing-feedback"
canonical_home = "docs/routing.md"
authority = "canonical"
audience = "agent"
canonicality = "candidate_for_promotion"
task_relevance = "required"
memory_role = "durable_truth"
routes_from = ["src/**/*.py"]
stale_when = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)
    details = [
        action.detail for action in result.actions if action.path == target / ".agentic-workspace/memory/repo/current/routing-feedback.md"
    ]

    assert any("routing-feedback should stay optional calibration context" in detail for detail in details)
    assert any("routing-feedback should stay agent_only calibration context" in detail for detail in details)
    assert any("routing-feedback should stay calibration-only" in detail for detail in details)
    assert any("should not advertise broad routing or freshness metadata" in detail for detail in details)


def test_doctor_flags_current_note_authority_and_memory_role_drift(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "current").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md").write_text(
        """
# Project State

## Status

Active

## Scope

- Overview only.

## Applies to

- README.md

## Load when

- Starting work.

## Review when

- Focus changes.

## Current focus

- Short summary.

## Recent meaningful progress

- None yet.

## Blockers

- None.

## High-level notes

- Keep brief.

## Failure signals

- Drift.

## Verify

- Check current state.

## Verified against

- README.md

## Last confirmed

2026-04-06
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/project-state.md"]
note_type = "current-overview"
canonical_home = ".agentic-workspace/memory/repo/current/project-state.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
memory_role = "durable_truth"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)
    details = [
        action.detail for action in result.actions if action.path == target / ".agentic-workspace/memory/repo/current/project-state.md"
    ]

    assert any("weak-authority context" in detail for detail in details)
    assert any("should not declare durable-truth or improvement-signal memory roles" in detail for detail in details)


def test_doctor_emits_note_type_specific_size_warning(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants" / "api.md").write_text(
        ("# API invariant\n\n" + "detail\n") * 90, encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/invariants/api.md"]
note_type = "invariant"
canonical_home = ".agentic-workspace/memory/repo/invariants/api.md"
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
        action.role == "memory-size-audit" and "invariant note is oversized" in action.detail and "expected <= 80" in action.detail
        for action in result.actions
    )


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


def test_doctor_emits_note_lifecycle_pressure_for_promotion_candidate(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(
        "# API\n\n" + ("Stable guidance.\n" * 45), encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
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

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.role == "memory-lifecycle"
        and action.path == target / ".agentic-workspace/memory/repo/domains/api.md"
        and "move canonical guidance into docs/api.md" in action.detail
        and "short stub" in action.detail
        for action in result.actions
    )


def test_doctor_emits_multi_home_pressure_for_procedural_domain_note(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(
        "# API\n\n" + "\n".join(f"{idx}. Run `cmd {idx}` and verify output." for idx in range(1, 8)),
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
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
        action.role == "memory-multi-home"
        and action.path == target / ".agentic-workspace/memory/repo/domains/api.md"
        and ".agentic-workspace/memory/repo/skills/api/SKILL.md" in action.detail
        for action in result.actions
    )


def test_doctor_ignores_standard_metadata_sections_when_counting_domain_procedure(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(
        """# API

## Purpose

Durable package boundary.

## Durable boundaries

- API package authority lives in `packages/api/src/`.
- Tests live in `packages/api/tests/`.

## Companion skill

Use `.agentic-workspace/memory/repo/skills/api/SKILL.md`.

## Verify

- `packages/api/src/`
- `packages/api/tests/`
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-multi-home" and action.path == target / ".agentic-workspace/memory/repo/domains/api.md"
        for action in result.actions
    )


def test_doctor_emits_multi_home_pressure_for_invariant_heavy_runbook(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "release.md").write_text(
        "# Release\n\n" + "\n".join("The service must remain compatible and must never skip validation." for _ in range(8)),
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/runbooks/release.md"]
note_type = "runbook"
canonical_home = ".agentic-workspace/memory/repo/runbooks/release.md"
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
        action.role == "memory-multi-home"
        and action.path == target / ".agentic-workspace/memory/repo/runbooks/release.md"
        and ".agentic-workspace/memory/repo/invariants/release.md" in action.detail
        for action in result.actions
    )


def test_doctor_rejects_canonical_elsewhere_targets_inside_memory(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/invariants/api.md"
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
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and "canonical_elsewhere notes must point canonical_home" in action.detail
        for action in doctor.actions
    )
    assert not any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "invariants" / "api.md" and action.kind == "required"
        for action in routed.actions
    )


def test_promotion_report_finds_candidate_notes_from_manifest(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(
        "# API\n\nStable policy draft.\n", encoding="utf-8"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
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
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md"
        and action.kind == "candidate"
        and "suggested canonical doc docs/api.md" in action.detail
        for action in result.actions
    )


def test_promotion_report_supports_explicit_notes_without_manifest_metadata(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "deploy.md").write_text("# Deploy\n\nProcedure.\n", encoding="utf-8")

    result = installer.promotion_report(target=target, notes=[".agentic-workspace/memory/repo/runbooks/deploy.md"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "deploy.md" and "checked-in skill" in action.detail
        for action in result.actions
    )


def test_promotion_report_marks_missing_explicit_notes_for_manual_review(
    tmp_path: Path,
) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)

    result = installer.promotion_report(target=target, notes=[".agentic-workspace/memory/repo/runbooks/deply.md"])

    assert any(
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "runbooks" / "deply.md"
        and action.kind == "manual review"
        and "file does not exist" in action.detail
        for action in result.actions
    )


def test_doctor_emits_advisory_note_overlap_warning(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    shared_text = (
        "service contract boundary request validation response schema compatibility migration rollback observability operator safety\n"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md").write_text(shared_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "invariants" / "api.md").write_text(shared_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["api"]
routes_from = ["src/**/*.py"]

[notes.".agentic-workspace/memory/repo/invariants/api.md"]
note_type = "invariant"
canonical_home = ".agentic-workspace/memory/repo/invariants/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
surfaces = ["api"]
routes_from = ["src/**/*.py"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert any(
        action.role == "memory-overlap-audit" and "possible note overlap" in action.detail and "recommend" in action.detail
        for action in result.actions
    )


def test_doctor_does_not_flag_wishlist_style_note_overlap_from_template_language(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "decisions").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "wishlist.md").write_text(
        """# Wishlist

## Status

Active

## Scope

- Product wishlist note.

## Applies to

- `AGENTS.md`

## Review when

- Changes are implemented.

## Failure signals

- Product feedback is not captured.

## Rule or lesson

- Keep this note focused on improvements and verified lessons.

## Last confirmed

2026-04-05
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "mistakes" / "recurring-failures.md").write_text(
        """# Recurring Failures

## Status

Active

## Scope

- Mistakes note.

## Applies to

- `AGENTS.md`

## Review when

- Behaviour changes.

## Failure signals

- Check current failure modes.

## Rule or lesson

- Keep this note focused on repeated failures and verified fixes.

## Last confirmed

2026-04-05
""",
        encoding="utf-8",
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[notes.".agentic-workspace/memory/repo/decisions/wishlist.md"]
note_type = "decision"
canonical_home = ".agentic-workspace/memory/repo/decisions/wishlist.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["memory-system"]

[notes.".agentic-workspace/memory/repo/mistakes/recurring-failures.md"]
note_type = "recurring-failures"
canonical_home = ".agentic-workspace/memory/repo/mistakes/recurring-failures.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
subsystems = ["memory-system"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = installer.doctor_bootstrap(target=target)

    assert not any(
        action.role == "memory-overlap-audit"
        and action.path == target / ".agentic-workspace" / "memory" / "repo" / "decisions" / "wishlist.md"
        for action in result.actions
    )


def test_doctor_shadow_doc_detection_flags_overlap(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "domains").mkdir(parents=True, exist_ok=True)
    (target / "docs").mkdir(parents=True, exist_ok=True)
    (target / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (target / ".agentic-workspace" / "memory").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "VERSION.md").write_text("Version: 30\n", encoding="utf-8")
    shared_text = (
        "deployment rollback procedure staging production release verification service health incident operator checklist observability\n"
    )
    (target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md").write_text(shared_text, encoding="utf-8")
    (target / "docs" / "deploy.md").write_text(shared_text, encoding="utf-8")
    (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").write_text(
        """
version = 1

[rules]
forbid_core_docs_depend_on_memory = true
core_doc_globs = ["docs/**/*.md"]
core_doc_exclude_globs = [".agentic-workspace/memory/repo/**/*.md", "AGENTS.md"]

[notes.".agentic-workspace/memory/repo/domains/deploy.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/deploy.md"
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
        action.path == target / ".agentic-workspace" / "memory" / "repo" / "domains" / "deploy.md"
        and action.role == "shadow-doc-audit"
        and "shadow-doc overlap" in action.detail
        for action in result.actions
    )
