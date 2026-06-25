#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import tomllib
from pathlib import Path
from typing import Any, NamedTuple


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "packages" / "planning").exists() and (parent / ".agentic-workspace").exists():
            return parent
    return current.parents[4]


REPO_ROOT = _find_repo_root()
PLANNING_MODULE_SCRIPT = REPO_ROOT / "packages" / "planning" / "scripts" / "check" / "check_planning_surfaces.py"
if not PLANNING_MODULE_SCRIPT.exists():
    PLANNING_MODULE_SCRIPT = Path(__file__).resolve().with_name("check_planning_surfaces.py")
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


_PLANNING_MODULE = _load_module(PLANNING_MODULE_SCRIPT, "workspace_planning_checker")
_BOUNDARY_MODULE = _load_module(BOUNDARY_MODULE_SCRIPT, "workspace_boundary_checker") if BOUNDARY_MODULE_SCRIPT.exists() else None
PlanningWarning = MaintainerWarning
RUNTIME_SUBSYSTEM_ID = "workspace-cli-runtime"
RUNTIME_SOURCE_GLOB = "src/agentic_workspace/workspace_runtime*.py"
RUNTIME_ARCHITECTURE_PRINCIPLE_ID = "host-agnostic-agent-judgment"
RUNTIME_VERIFICATION_PROTOCOL_IDS = ("closeout_intent_satisfaction", "requirement_grounding_delegation")
RUNTIME_SUBSYSTEM_REF = f".agentic-workspace/OWNERSHIP.toml#subsystems.{RUNTIME_SUBSYSTEM_ID}"


def _sync_repo_root(repo_root: Path) -> None:
    _PLANNING_MODULE.REPO_ROOT = repo_root
    if _BOUNDARY_MODULE is not None and hasattr(_BOUNDARY_MODULE, "REPO_ROOT"):
        _BOUNDARY_MODULE.REPO_ROOT = repo_root


def _normalize_warning(warning: object) -> MaintainerWarning:
    return MaintainerWarning(
        warning_class=getattr(warning, "warning_class"),
        path=str(getattr(warning, "path")),
        message=getattr(warning, "message"),
    )


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8-sig"))


def _list_str(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _matches_pattern(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return path.startswith(pattern.removesuffix("**"))
    return fnmatch.fnmatchcase(path, pattern)


def _patterns_cover_runtime_sources(patterns: list[str], runtime_sources: list[str]) -> bool:
    return bool(runtime_sources) and all(any(_matches_pattern(path, pattern) for pattern in patterns) for path in runtime_sources)


def _runtime_source_files(repo_root: Path) -> list[str]:
    source_dir = repo_root / "src" / "agentic_workspace"
    if not source_dir.exists():
        return []
    return sorted(path.relative_to(repo_root).as_posix() for path in source_dir.glob("workspace_runtime*.py") if path.is_file())


def _runtime_subsystem_warnings(repo_root: Path, runtime_sources: list[str]) -> list[MaintainerWarning]:
    ownership = _load_toml(repo_root / ".agentic-workspace" / "OWNERSHIP.toml")
    subsystems = ownership.get("subsystems")
    if not isinstance(subsystems, list):
        subsystems = []

    warnings: list[MaintainerWarning] = []
    for source_path in runtime_sources:
        matches = [
            str(subsystem.get("id"))
            for subsystem in subsystems
            if isinstance(subsystem, dict)
            and any(_matches_pattern(source_path, pattern) for pattern in _list_str(subsystem.get("paths")))
        ]
        if matches != [RUNTIME_SUBSYSTEM_ID]:
            warnings.append(
                MaintainerWarning(
                    "RUNTIME_SOURCE_OWNERSHIP_DRIFT",
                    ".agentic-workspace/OWNERSHIP.toml",
                    f"{source_path} must match exactly {RUNTIME_SUBSYSTEM_ID}; matched {matches or 'none'}.",
                )
            )
    return warnings


def _runtime_architecture_warnings(repo_root: Path, runtime_sources: list[str]) -> list[MaintainerWarning]:
    intent = _load_toml(repo_root / ".agentic-workspace" / "system-intent" / "intent.toml")
    principles = intent.get("architecture_principles")
    if not isinstance(principles, list):
        principles = []
    principle = next(
        (
            item
            for item in principles
            if isinstance(item, dict) and item.get("id") == RUNTIME_ARCHITECTURE_PRINCIPLE_ID
        ),
        None,
    )
    if principle is None:
        return [
            MaintainerWarning(
                "RUNTIME_ARCHITECTURE_ROUTING_DRIFT",
                ".agentic-workspace/system-intent/intent.toml",
                f"Missing architecture principle {RUNTIME_ARCHITECTURE_PRINCIPLE_ID}.",
            )
        ]

    patterns = _list_str(principle.get("path_globs"))
    if _patterns_cover_runtime_sources(patterns, runtime_sources):
        return []
    return [
        MaintainerWarning(
            "RUNTIME_ARCHITECTURE_ROUTING_DRIFT",
            ".agentic-workspace/system-intent/intent.toml",
            f"{RUNTIME_ARCHITECTURE_PRINCIPLE_ID} path_globs must cover all {RUNTIME_SOURCE_GLOB} files.",
        )
    ]


def _runtime_verification_warnings(repo_root: Path, runtime_sources: list[str]) -> list[MaintainerWarning]:
    manifest = _load_toml(repo_root / ".agentic-workspace" / "verification" / "manifest.toml")
    protocols = manifest.get("protocols")
    if not isinstance(protocols, dict):
        protocols = {}

    warnings: list[MaintainerWarning] = []
    for protocol_id in RUNTIME_VERIFICATION_PROTOCOL_IDS:
        protocol = protocols.get(protocol_id)
        if not isinstance(protocol, dict):
            warnings.append(
                MaintainerWarning(
                    "RUNTIME_VERIFICATION_ROUTING_DRIFT",
                    ".agentic-workspace/verification/manifest.toml",
                    f"Missing Verification protocol {protocol_id}.",
                )
            )
            continue
        applies_to_paths = _list_str(protocol.get("applies_to_paths"))
        stale_when = _list_str(protocol.get("stale_when"))
        authority_refs = _list_str(protocol.get("authority_refs"))
        proof_profiles = _list_str(protocol.get("proof_profiles"))
        if (
            not _patterns_cover_runtime_sources(applies_to_paths, runtime_sources)
            or not _patterns_cover_runtime_sources(stale_when, runtime_sources)
            or RUNTIME_SUBSYSTEM_REF not in authority_refs
            or "workspace_behavior" not in proof_profiles
        ):
            warnings.append(
                MaintainerWarning(
                    "RUNTIME_VERIFICATION_ROUTING_DRIFT",
                    ".agentic-workspace/verification/manifest.toml",
                    f"{protocol_id} must derive runtime routing from {RUNTIME_SUBSYSTEM_REF} and cover {RUNTIME_SOURCE_GLOB}.",
                )
            )
    return warnings


def _runtime_boundary_warnings(repo_root: Path) -> list[MaintainerWarning]:
    runtime_sources = _runtime_source_files(repo_root)
    if not runtime_sources:
        return []
    warnings: list[MaintainerWarning] = []
    warnings.extend(_runtime_subsystem_warnings(repo_root, runtime_sources))
    warnings.extend(_runtime_architecture_warnings(repo_root, runtime_sources))
    warnings.extend(_runtime_verification_warnings(repo_root, runtime_sources))
    return warnings


def gather_maintainer_warnings(*, repo_root: Path | None = None) -> list[MaintainerWarning]:
    effective_root = REPO_ROOT if repo_root is None else repo_root
    _sync_repo_root(effective_root)
    warnings = [_normalize_warning(warning) for warning in _PLANNING_MODULE.gather_planning_warnings(repo_root=effective_root)]
    if _BOUNDARY_MODULE is not None:
        warnings.extend(_normalize_warning(warning) for warning in _BOUNDARY_MODULE.gather_boundary_warnings(repo_root=effective_root))
    warnings.extend(_runtime_boundary_warnings(effective_root))
    return warnings


def gather_maintainer_summary(*, repo_root: Path | None = None) -> dict[str, Any]:
    effective_root = REPO_ROOT if repo_root is None else repo_root
    warnings = gather_maintainer_warnings(repo_root=effective_root)
    summary: dict[str, Any] = {
        "warning_count": len(warnings),
        "warnings": [warning._asdict() for warning in warnings],
        "planning": _PLANNING_MODULE.gather_planning_summary(repo_root=effective_root),
        "boundary": _BOUNDARY_MODULE.gather_boundary_summary(repo_root=effective_root) if _BOUNDARY_MODULE is not None else None,
    }
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
