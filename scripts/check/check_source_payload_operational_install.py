#!/usr/bin/env python3
"""Advisory checks for source/payload/root-install boundaries.

Warn when package-local installed surfaces appear under packages/*
or when the root operational install is incomplete for the monorepo's
dogfooded memory/planning systems.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import NamedTuple


REPO_ROOT = Path(__file__).resolve().parents[2]

WARNING_PACKAGE_LOCAL_INSTALL_DRIFT = "package_local_install_drift"
WARNING_ROOT_OPERATIONAL_INSTALL_DRIFT = "root_operational_install_drift"


class BoundaryWarning(NamedTuple):
    warning_class: str
    path: str
    message: str


def _render_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _existing(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def gather_boundary_warnings(*, repo_root: Path = REPO_ROOT) -> list[BoundaryWarning]:
    warnings: list[BoundaryWarning] = []

    package_local_candidates = {
        repo_root / "packages" / "memory" / ".agentic-workspace": (
            "Package-local installed memory surfaces detected under packages/memory; remove accidental installs and refresh the root operational install instead."
        ),
        repo_root / "packages" / "planning" / ".agentic-workspace": (
            "Package-local installed planning surfaces detected under packages/planning; remove accidental installs and refresh the root operational install instead."
        ),
        repo_root / "packages" / "planning" / "tools" / "agent-manifest.json": (
            "Package-local generated planning mirrors detected under packages/planning; generated maintainer mirrors belong at repo root only."
        ),
        repo_root / "packages" / "planning" / "tools" / "AGENT_QUICKSTART.md": (
            "Package-local generated planning mirrors detected under packages/planning; generated maintainer mirrors belong at repo root only."
        ),
        repo_root / "packages" / "planning" / "tools" / "AGENT_ROUTING.md": (
            "Package-local generated planning mirrors detected under packages/planning; generated maintainer mirrors belong at repo root only."
        ),
    }

    for path, message in package_local_candidates.items():
        if path.exists():
            warnings.append(
                BoundaryWarning(
                    WARNING_PACKAGE_LOCAL_INSTALL_DRIFT,
                    _render_path(path),
                    message,
                )
            )

    required_root_surfaces = {
        repo_root / "memory" / "index.md": "Root operational memory install is missing `memory/index.md`.",
        repo_root / ".agentic-workspace" / "memory" / "WORKFLOW.md": (
            "Root operational memory install is missing `.agentic-workspace/memory/WORKFLOW.md`."
        ),
        repo_root / ".agentic-workspace" / "memory" / "SKILLS.md": (
            "Root operational memory install is missing `.agentic-workspace/memory/SKILLS.md`."
        ),
        repo_root / "TODO.md": "Root operational planning install is missing `TODO.md`.",
        repo_root / "ROADMAP.md": "Root operational planning install is missing `ROADMAP.md`.",
        repo_root / "docs" / "execplans" / "README.md": (
            "Root operational planning install is missing `docs/execplans/README.md`."
        ),
        repo_root / ".agentic-workspace" / "planning" / "agent-manifest.json": (
            "Root operational planning install is missing `.agentic-workspace/planning/agent-manifest.json`."
        ),
        repo_root / "tools" / "agent-manifest.json": (
            "Root operational planning install is missing `tools/agent-manifest.json`."
        ),
        repo_root / "tools" / "AGENT_QUICKSTART.md": (
            "Root operational planning install is missing `tools/AGENT_QUICKSTART.md`."
        ),
        repo_root / "tools" / "AGENT_ROUTING.md": (
            "Root operational planning install is missing `tools/AGENT_ROUTING.md`."
        ),
    }

    for path, message in required_root_surfaces.items():
        if not path.exists():
            warnings.append(
                BoundaryWarning(
                    WARNING_ROOT_OPERATIONAL_INSTALL_DRIFT,
                    _render_path(path),
                    message,
                )
            )

    return warnings


def gather_boundary_summary(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    package_local_paths = [
        repo_root / "packages" / "memory" / ".agentic-workspace",
        repo_root / "packages" / "planning" / ".agentic-workspace",
        repo_root / "packages" / "planning" / "tools" / "agent-manifest.json",
        repo_root / "packages" / "planning" / "tools" / "AGENT_QUICKSTART.md",
        repo_root / "packages" / "planning" / "tools" / "AGENT_ROUTING.md",
    ]
    required_root_surfaces = [
        repo_root / "memory" / "index.md",
        repo_root / ".agentic-workspace" / "memory" / "WORKFLOW.md",
        repo_root / ".agentic-workspace" / "memory" / "SKILLS.md",
        repo_root / "TODO.md",
        repo_root / "ROADMAP.md",
        repo_root / "docs" / "execplans" / "README.md",
        repo_root / ".agentic-workspace" / "planning" / "agent-manifest.json",
        repo_root / "tools" / "agent-manifest.json",
        repo_root / "tools" / "AGENT_QUICKSTART.md",
        repo_root / "tools" / "AGENT_ROUTING.md",
    ]

    return {
        "package_local_installs": [_render_path(path) for path in _existing(package_local_paths)],
        "missing_root_surfaces": [_render_path(path) for path in required_root_surfaces if not path.exists()],
    }


def _print_warnings(warnings: list[BoundaryWarning]) -> None:
    print("Source/payload/root-install boundary report")
    if not warnings:
        print("- No boundary drift warnings detected.")
        return

    for warning in warnings:
        print(f"- [{warning.warning_class}] {warning.path}: {warning.message}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advisory checker for source/payload/root-install boundaries.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero exit status when warnings are present.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    warnings = gather_boundary_warnings(repo_root=REPO_ROOT)
    summary = {
        "warning_count": len(warnings),
        "warnings": [warning._asdict() for warning in warnings],
        "boundary": gather_boundary_summary(repo_root=REPO_ROOT),
    }

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_warnings(warnings)

    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
