#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

MODULE_SCRIPT = (
    Path(__file__).resolve().parents[2] / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_maintainer_surfaces.py"
)


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


def _sync_repo_root() -> None:
    _MODULE.REPO_ROOT = REPO_ROOT


def gather_maintainer_warnings(*, repo_root: Path | None = None):
    _sync_repo_root()
    effective_root = REPO_ROOT if repo_root is None else repo_root
    return _MODULE.gather_maintainer_warnings(repo_root=effective_root)


def gather_maintainer_summary(*, repo_root: Path | None = None) -> dict[str, Any]:
    _sync_repo_root()
    effective_root = REPO_ROOT if repo_root is None else repo_root
    return _MODULE.gather_maintainer_summary(repo_root=effective_root)


def main(argv: list[str] | None = None) -> int:
    _sync_repo_root()
    return _MODULE.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
