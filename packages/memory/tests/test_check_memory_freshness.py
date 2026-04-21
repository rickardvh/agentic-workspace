from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _checker_script_path() -> Path:
    root_checker = WORKSPACE_ROOT / "scripts" / "check" / "check_memory_freshness.py"
    if root_checker.exists():
        return root_checker
    return PACKAGE_ROOT / "scripts" / "check" / "check_memory_freshness.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _project_state_text(body: str = "- Concise summary only.") -> str:
    return f"""
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

{body}

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
"""


def test_memory_freshness_flags_current_note_authority_drift(tmp_path: Path) -> None:
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md", _project_state_text())
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
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
""",
    )

    result = subprocess.run(
        [sys.executable, str(_checker_script_path()), "--strict"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Current-note authority drift:" in result.stdout
    assert ".agentic-workspace/memory/repo/current/project-state.md" in result.stdout
    assert "Current-note durable-truth drift:" in result.stdout


def test_memory_freshness_reports_current_note_overlap_pressure(tmp_path: Path) -> None:
    shared = "service contract boundary request validation response schema compatibility migration rollback observability operator safety"
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md", _project_state_text(body=f"- {shared}"))
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md", f"# API\n\n{shared}\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/project-state.md"]
note_type = "current-overview"
canonical_home = ".agentic-workspace/memory/repo/current/project-state.md"
authority = "advisory"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""",
    )

    result = subprocess.run(
        [sys.executable, str(_checker_script_path())],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Current-note overlap pressure:" in result.stdout
    assert (
        ".agentic-workspace/memory/repo/current/project-state.md overlaps durable note .agentic-workspace/memory/repo/domains/api.md"
        in result.stdout
    )


def test_memory_freshness_skips_overlap_pressure_for_current_notes_with_explicit_durable_handoff(
    tmp_path: Path,
) -> None:
    shared = "service contract boundary request validation response schema compatibility migration rollback observability operator safety"
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "current" / "project-state.md",
        _project_state_text(
            body=(
                "- "
                + shared
                + (
                    "\n- For durable rationale, load the matching note under `.agentic-workspace/memory/repo/decisions/` "
                    "or `.agentic-workspace/memory/repo/domains/` instead of expanding this overview."
                )
            )
        ),
    )
    _write(tmp_path / ".agentic-workspace" / "memory" / "repo" / "domains" / "api.md", f"# API\n\n{shared}\n")
    _write(
        tmp_path / ".agentic-workspace" / "memory" / "repo" / "manifest.toml",
        """
version = 1

[notes.".agentic-workspace/memory/repo/current/project-state.md"]
note_type = "current-overview"
canonical_home = ".agentic-workspace/memory/repo/current/project-state.md"
authority = "advisory"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"

[notes.".agentic-workspace/memory/repo/domains/api.md"]
note_type = "domain"
canonical_home = ".agentic-workspace/memory/repo/domains/api.md"
authority = "canonical"
audience = "human+agent"
canonicality = "agent_only"
task_relevance = "optional"
""",
    )

    result = subprocess.run(
        [sys.executable, str(_checker_script_path())],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Current-note overlap pressure:" in result.stdout
    assert (
        ".agentic-workspace/memory/repo/current/project-state.md overlaps durable note .agentic-workspace/memory/repo/domains/api.md"
        not in result.stdout
    )
