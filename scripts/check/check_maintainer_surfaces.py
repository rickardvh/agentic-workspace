#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

MODULE_SCRIPT = Path(__file__).resolve().parents[2] / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_maintainer_surfaces.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("workspace_maintainer_checker", MODULE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load maintainer checker module from {MODULE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MODULE = _load_module()
REPO_ROOT = _MODULE.REPO_ROOT
PlanningWarning = _MODULE.PlanningWarning

WARNING_DOCS_SURFACE_ROLE_DRIFT = "docs_surface_role_drift"

ROLE_GUIDANCE_RULES = {
    Path("README.md"): (
        "docs/contributor-playbook.md` - choose the right ownership surface and validation lane before editing.",
        "docs/maintainer-commands.md` - canonical command index for routine maintenance.",
        "docs/collaboration-safety.md` - concurrent-edit and git hygiene rules.",
        "docs/installed-contract-design-checklist.md` - review bar for new or changed shipped surfaces.",
        "docs/dogfooding-feedback.md` - classify internal friction before routing it onward.",
        "docs/workflow-contract-changes.md` - compact record of recent workflow-surface changes.",
    ),
    Path("docs/contributor-playbook.md"): (
        "use `docs/maintainer-commands.md` when you need the literal command to run; use this playbook when you need routing, ownership, or validation guidance.",
    ),
    Path("docs/maintainer-commands.md"): (
        "use this page when you need the canonical command to run, not the broader routing, ownership, or workflow-history context.",
    ),
    Path("docs/collaboration-safety.md"): (
        "use `docs/maintainer-commands.md` for command lookup and `docs/workflow-contract-changes.md` for compact workflow history; this page is only for concurrent-edit and merge-safety rules.",
    ),
    Path("docs/installed-contract-design-checklist.md"): (
        "use `docs/maintainer-commands.md` for commands and `docs/contributor-playbook.md` for routing; this page is only the review bar for collaboration-sensitive installed surfaces.",
    ),
    Path("docs/dogfooding-feedback.md"): (
        "use planning surfaces when the signal changes active execution; this page is only for classifying and routing the signal, not for keeping a backlog.",
    ),
    Path("docs/workflow-contract-changes.md"): (
        "keep this page short and decision-shaped; it is not the full changelog, release notes, or command index.",
    ),
}


def _sync_repo_root() -> None:
    _MODULE.REPO_ROOT = REPO_ROOT


def _render_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _gather_docs_surface_warnings(*, repo_root: Path) -> list[PlanningWarning]:
    warnings: list[PlanningWarning] = []
    for relative_path, fragments in ROLE_GUIDANCE_RULES.items():
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").lower()
        missing = [fragment for fragment in fragments if fragment.lower() not in text]
        if missing:
            warnings.append(
                PlanningWarning(
                    WARNING_DOCS_SURFACE_ROLE_DRIFT,
                    _render_path(path, repo_root=repo_root),
                    "Maintainer docs role guidance drifted; keep each page scoped to one clear purpose.",
                )
            )
    return warnings


def gather_maintainer_warnings(*, repo_root: Path | None = None):
    _sync_repo_root()
    effective_root = REPO_ROOT if repo_root is None else repo_root
    warnings = list(_MODULE.gather_maintainer_warnings(repo_root=effective_root))
    warnings.extend(_gather_docs_surface_warnings(repo_root=effective_root))
    return warnings


def gather_maintainer_summary(*, repo_root: Path | None = None) -> dict[str, Any]:
    _sync_repo_root()
    effective_root = REPO_ROOT if repo_root is None else repo_root
    summary = _MODULE.gather_maintainer_summary(repo_root=effective_root)
    warnings = gather_maintainer_warnings(repo_root=effective_root)
    summary["warnings"] = [warning._asdict() for warning in warnings]
    summary["warning_count"] = len(warnings)
    return summary


def main(argv: list[str] | None = None) -> int:
    _sync_repo_root()
    return _MODULE.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())