from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *


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
