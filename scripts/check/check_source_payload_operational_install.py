#!/usr/bin/env python3
"""Advisory checks for source/payload/root-install boundaries.

Warn when package-local installed surfaces appear under packages/*
or when the root operational install is incomplete for the monorepo's
dogfooded memory/planning systems.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]

WARNING_PACKAGE_LOCAL_INSTALL_DRIFT = "package_local_install_drift"
WARNING_ROOT_OPERATIONAL_INSTALL_DRIFT = "root_operational_install_drift"
WARNING_CONTRACT_DRIFT = "contract_drift"
WARNING_DOC_INSTALLED_SURFACE_DRIFT = "doc_installed_surface_drift"


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


def _markdown_payload_claims(readme_path: Path) -> list[str]:
    if not readme_path.exists():
        return []
    lines = readme_path.read_text(encoding="utf-8").splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "The package ships these payload files:":
            start = index + 1
            break
    if start is None:
        return []
    claims: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if claims:
                break
            continue
        if not stripped.startswith("- `") or not stripped.endswith("`"):
            break
        claims.append(stripped.removeprefix("- `").removesuffix("`"))
    return claims


def _planning_required_payload_claims(repo_root: Path) -> list[str]:
    package_src = repo_root / "packages" / "planning" / "src"
    if not package_src.exists():
        return []
    sys.path.insert(0, str(package_src))
    try:
        installer = importlib.import_module("repo_planning_bootstrap.installer")
        return sorted(path.as_posix() for path in installer.REQUIRED_PAYLOAD_FILES)
    finally:
        try:
            sys.path.remove(str(package_src))
        except ValueError:
            pass


def _readme_payload_claim_warnings(*, repo_root: Path) -> list[BoundaryWarning]:
    readme_path = repo_root / "packages" / "planning" / "README.md"
    expected = _planning_required_payload_claims(repo_root)
    if not expected:
        return []
    actual = sorted(_markdown_payload_claims(readme_path))
    if actual == expected:
        return []
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    details: list[str] = []
    if missing:
        details.append("missing payload claim(s): " + ", ".join(missing))
    if extra:
        details.append("stale payload claim(s): " + ", ".join(extra))
    if not actual:
        details.append("missing `The package ships these payload files:` payload claim block")
    return [
        BoundaryWarning(
            WARNING_DOC_INSTALLED_SURFACE_DRIFT,
            _render_path(readme_path),
            "Planning README installed-surface claims drifted from REQUIRED_PAYLOAD_FILES; " + "; ".join(details),
        )
    ]


def gather_boundary_warnings(*, repo_root: Path = REPO_ROOT) -> list[BoundaryWarning]:
    warnings: list[BoundaryWarning] = []

    package_local_candidates = {
        repo_root / "packages" / "memory" / ".agentic-workspace": (
            "Package-local installed memory surfaces detected under packages/memory; remove accidental installs and refresh the root operational install instead."
        ),
        repo_root / "packages" / "planning" / ".agentic-workspace": (
            "Package-local installed planning surfaces detected under packages/planning; remove accidental installs and refresh the root operational install instead."
        ),
        repo_root / "packages" / "planning" / "bootstrap" / ".agentic-workspace" / "planning" / "state.toml": (
            "Active surface `state.toml` found in bootstrap; avoid checked-in active state in the payload."
        ),
        repo_root / "packages" / "planning" / "bootstrap" / "ROADMAP.md": (
            "Active surface `ROADMAP.md` found in bootstrap; rename to `ROADMAP.template.md` to maintain the boundary."
        ),
        repo_root / "packages" / "planning" / "bootstrap" / "AGENTS.md": (
            "Active surface `AGENTS.md` found in bootstrap; rename to `AGENTS.template.md` to maintain the boundary."
        ),
        repo_root / "packages" / "memory" / "bootstrap" / "AGENTS.md": (
            "Active surface `AGENTS.md` found in bootstrap; rename to `AGENTS.template.md` to maintain the boundary."
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

    warnings.extend(_readme_payload_claim_warnings(repo_root=repo_root))

    required_root_surfaces = {
        repo_root / ".agentic-workspace" / "memory" / "repo" / "index.md": (
            "Root operational memory install is missing `.agentic-workspace/memory/repo/index.md`."
        ),
        repo_root / ".agentic-workspace" / "memory" / "WORKFLOW.md": (
            "Root operational memory install is missing `.agentic-workspace/memory/WORKFLOW.md`."
        ),
        repo_root / ".agentic-workspace" / "memory" / "SKILLS.md": (
            "Root operational memory install is missing `.agentic-workspace/memory/SKILLS.md`."
        ),
        repo_root / ".agentic-workspace" / "planning" / "state.toml": (
            "Root operational planning install is missing `.agentic-workspace/planning/state.toml`."
        ),
        repo_root / ".agentic-workspace" / "planning" / "execplans" / "README.md": (
            "Root operational planning install is missing `.agentic-workspace/planning/execplans/README.md`."
        ),
        repo_root / ".agentic-workspace" / "planning" / "agent-manifest.json": (
            "Root operational planning install is missing `.agentic-workspace/planning/agent-manifest.json`."
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

    # Contract drift checks (Shipped Product -> Installed Product)
    for pkg_name in ("planning", "memory"):
        pkg_docs = repo_root / "packages" / pkg_name / "bootstrap" / "docs"
        root_docs = repo_root / "docs"

        if pkg_docs.exists():
            for source_path in pkg_docs.glob("*.md"):
                target_path = root_docs / source_path.name
                if target_path.exists():
                    source_content = source_path.read_text(encoding="utf-8").strip()
                    target_content = target_path.read_text(encoding="utf-8").strip()
                    if source_content != target_content:
                        warnings.append(
                            BoundaryWarning(
                                WARNING_CONTRACT_DRIFT,
                                _render_path(target_path),
                                (
                                    f"Drift detected between shipped contract `{_render_path(source_path)}` and installed surface. "
                                    f"Modify the authoritative file in `packages/{pkg_name}/bootstrap/`, then run `uv run agentic-{pkg_name}-bootstrap upgrade` to apply it to the root."
                                ),
                            )
                        )

    return warnings


def gather_boundary_summary(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    package_local_paths = [
        repo_root / "packages" / "memory" / ".agentic-workspace",
        repo_root / "packages" / "planning" / ".agentic-workspace",
    ]
    required_root_surfaces = [
        repo_root / ".agentic-workspace" / "memory" / "repo" / "index.md",
        repo_root / ".agentic-workspace" / "memory" / "WORKFLOW.md",
        repo_root / ".agentic-workspace" / "memory" / "SKILLS.md",
        repo_root / ".agentic-workspace" / "planning" / "state.toml",
        repo_root / ".agentic-workspace" / "planning" / "execplans" / "README.md",
        repo_root / ".agentic-workspace" / "planning" / "agent-manifest.json",
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
    parser.add_argument(
        "--quiet-success",
        action="store_true",
        help="Emit a compact one-line success message when no warnings are present.",
    )
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
        if args.quiet_success and not warnings:
            print("[ok] source-payload boundary")
        else:
            _print_warnings(warnings)

    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
