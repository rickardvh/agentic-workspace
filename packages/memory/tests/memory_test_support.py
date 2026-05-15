from __future__ import annotations

# ruff: noqa: F401
import json
import subprocess
import sys
from pathlib import Path

import pytest
from command_generation.generated_package_loader import load_generated_cli_module_for_entrypoint

from repo_memory_bootstrap import installer
from repo_memory_bootstrap._installer_output import _infer_action_category
from repo_memory_bootstrap._installer_shared import (
    MEMORY_COMPATIBILITY_CONTRACT_FILES,
    MEMORY_LOWER_STABILITY_HELPER_FILES,
    PAYLOAD_REQUIRED_FILES,
    WORKSPACE_POINTER_BLOCK,
)
from repo_memory_bootstrap._ownership import module_root as memory_module_root

cli = load_generated_cli_module_for_entrypoint("agentic-memory", "cli.py")

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


def _memory_freshness_script_path() -> Path:
    root_checker = WORKSPACE_ROOT / "scripts" / "check" / "check_memory_freshness.py"
    if root_checker.exists():
        return root_checker
    return PACKAGE_ROOT / "scripts" / "check" / "check_memory_freshness.py"


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
    package_note = PACKAGE_ROOT / "memory" / "current" / "project-state.md"
    if package_note.exists():
        return package_note.read_text(encoding="utf-8")
    return "# Project State\n\n## Last confirmed\n\n2026-04-13\n"


def _task_context_text() -> str:
    root_note = WORKSPACE_ROOT / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md"
    if root_note.exists():
        return root_note.read_text(encoding="utf-8")
    payload_note = installer.payload_root() / ".agentic-workspace" / "memory" / "repo" / "current" / "task-context.md"
    if payload_note.exists():
        return payload_note.read_text(encoding="utf-8")
    package_note = PACKAGE_ROOT / "memory" / "current" / "task-context.md"
    if package_note.exists():
        return package_note.read_text(encoding="utf-8")
    return (
        "# Task Context\n\n## Active goal\n\n- Legacy fixture.\n\n## Next validation\n\n- Run tests.\n\n## Last confirmed\n\n2026-04-13\n"
    )


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


__all__ = [name for name in globals() if not name.startswith("__")]
