from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *


def test_promotion_report_remediation_mode_filters_low_confidence_candidates(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo").mkdir(parents=True, exist_ok=True)
    (target / ".agentic-workspace" / "memory" / "repo" / "index.md").write_text("# Memory Index\n\n" + ("line\n" * 140), encoding="utf-8")

    result = installer.promotion_report(target=target, notes=[".agentic-workspace/memory/repo/index.md"], mode="remediation")

    assert any(
        action.kind == "manual review" and "no promotion or elimination candidates found" in action.detail for action in result.actions
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
