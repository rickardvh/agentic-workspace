#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
PLANNING_MODULE_SCRIPT = (
    REPO_ROOT / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_maintainer_surfaces.py"
)
BOUNDARY_MODULE_SCRIPT = REPO_ROOT / "scripts" / "check" / "check_source_payload_operational_install.py"


class MaintainerWarning(NamedTuple):
    warning_class: str
    path: str
    message: str


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load maintainer checker module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PLANNING_MODULE = _load_module(PLANNING_MODULE_SCRIPT, "workspace_planning_maintainer_checker")
_BOUNDARY_MODULE = (
    _load_module(BOUNDARY_MODULE_SCRIPT, "workspace_boundary_checker") if BOUNDARY_MODULE_SCRIPT.exists() else None
)
PlanningWarning = MaintainerWarning


def _sync_repo_root(repo_root: Path) -> None:
    _PLANNING_MODULE.REPO_ROOT = repo_root
    if _BOUNDARY_MODULE is not None and hasattr(_BOUNDARY_MODULE, "REPO_ROOT"):
        _BOUNDARY_MODULE.REPO_ROOT = repo_root


def _normalize_warning(warning: object) -> MaintainerWarning:
    warning_class = getattr(warning, "warning_class")
    path = str(getattr(warning, "path"))
    message = getattr(warning, "message")
    return MaintainerWarning(warning_class=warning_class, path=path, message=message)


def gather_maintainer_warnings(*, repo_root: Path | None = None) -> list[MaintainerWarning]:
    effective_root = REPO_ROOT if repo_root is None else repo_root
    _sync_repo_root(effective_root)
    warnings = [
        _normalize_warning(warning)
        for warning in _PLANNING_MODULE.gather_maintainer_warnings(repo_root=effective_root)
    ]
    if _BOUNDARY_MODULE is not None:
        warnings.extend(
            _normalize_warning(warning)
            for warning in _BOUNDARY_MODULE.gather_boundary_warnings(repo_root=effective_root)
        )
    return warnings


def gather_maintainer_summary(*, repo_root: Path | None = None) -> dict[str, Any]:
    effective_root = REPO_ROOT if repo_root is None else repo_root
    warnings = gather_maintainer_warnings(repo_root=effective_root)
    summary: dict[str, Any] = {
        "warning_count": len(warnings),
        "warnings": [warning._asdict() for warning in warnings],
        "planning": _PLANNING_MODULE.gather_maintainer_summary(repo_root=effective_root),
    }
    if _BOUNDARY_MODULE is not None:
        summary["boundary"] = _BOUNDARY_MODULE.gather_boundary_summary(repo_root=effective_root)
    else:
        summary["boundary"] = None
    return summary


def _print_warnings(warnings: list[MaintainerWarning]) -> None:
    print("Maintainer surface health report")
    if not warnings:
        print("- No maintainer-surface drift warnings detected.")
        return

    for warning in warnings:
        print(f"- [{warning.warning_class}] {warning.path}: {warning.message}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advisory maintainer-surface health checker.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero exit status when warnings are present.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = gather_maintainer_summary(repo_root=REPO_ROOT)
    warnings = [MaintainerWarning(**warning) for warning in summary["warnings"]]

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_warnings(warnings)

    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
