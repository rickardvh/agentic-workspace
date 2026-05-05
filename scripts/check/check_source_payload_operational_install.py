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
import tomllib
from pathlib import Path
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]

WARNING_PACKAGE_LOCAL_INSTALL_DRIFT = "package_local_install_drift"
WARNING_ROOT_OPERATIONAL_INSTALL_DRIFT = "root_operational_install_drift"
WARNING_CONTRACT_DRIFT = "contract_drift"
WARNING_DOC_INSTALLED_SURFACE_DRIFT = "doc_installed_surface_drift"
WARNING_PAYLOAD_INVENTORY_DRIFT = "payload_inventory_drift"
WARNING_PACKAGING_MANIFEST_DRIFT = "packaging_manifest_drift"
WARNING_DUPLICATE_PLANNING_CHECKER_DRIFT = "duplicate_planning_checker_drift"
WARNING_EXECUTABLE_PAYLOAD_DRIFT = "executable_payload_drift"

EXECUTABLE_PAYLOAD_SUFFIXES = {
    ".bat",
    ".bash",
    ".cmd",
    ".cjs",
    ".class",
    ".cs",
    ".dll",
    ".dylib",
    ".exe",
    ".fs",
    ".go",
    ".jar",
    ".java",
    ".js",
    ".jsx",
    ".lua",
    ".mjs",
    ".php",
    ".pl",
    ".ps1",
    ".psm1",
    ".py",
    ".pyc",
    ".pyo",
    ".pyw",
    ".rb",
    ".rs",
    ".sh",
    ".so",
    ".ts",
    ".tsx",
    ".vb",
    ".zsh",
}


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


def _planning_expected_payload_files(repo_root: Path) -> list[str]:
    package_src = repo_root / "packages" / "planning" / "src"
    if not package_src.exists():
        return []
    sys.path.insert(0, str(package_src))
    try:
        installer = importlib.import_module("repo_planning_bootstrap.installer")
        package_payload = getattr(installer, "PACKAGE_PAYLOAD_FILES", installer.REQUIRED_PAYLOAD_FILES)
        return sorted(path.as_posix() for path in package_payload)
    finally:
        try:
            sys.path.remove(str(package_src))
        except ValueError:
            pass


def _memory_expected_payload_files(repo_root: Path) -> list[str]:
    package_src = repo_root / "packages" / "memory" / "src"
    if not package_src.exists():
        return []
    sys.path.insert(0, str(package_src))
    try:
        shared = importlib.import_module("repo_memory_bootstrap._installer_shared")
        return sorted(path.as_posix() for path in shared.PAYLOAD_REQUIRED_FILES)
    finally:
        try:
            sys.path.remove(str(package_src))
        except ValueError:
            pass


def _package_payload_files(repo_root: Path, package_name: str) -> list[str]:
    payload_root = repo_root / "packages" / package_name / "bootstrap"
    if not payload_root.exists():
        return []
    return sorted(path.relative_to(payload_root).as_posix() for path in payload_root.rglob("*") if _should_count_bootstrap_file(path))


def _should_count_bootstrap_file(path: Path) -> bool:
    return path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"


def _looks_like_executable_payload(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in EXECUTABLE_PAYLOAD_SUFFIXES:
        return True
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"#!"
    except OSError:
        return False


def _executable_payload_files(repo_root: Path, package_name: str) -> list[str]:
    payload_root = repo_root / "packages" / package_name / "bootstrap"
    if not payload_root.exists():
        return []
    return sorted(path.relative_to(payload_root).as_posix() for path in payload_root.rglob("*") if _looks_like_executable_payload(path))


def _executable_payload_warnings(*, repo_root: Path, package_name: str) -> list[BoundaryWarning]:
    executable_files = _executable_payload_files(repo_root, package_name)
    if not executable_files:
        return []
    return [
        BoundaryWarning(
            WARNING_EXECUTABLE_PAYLOAD_DRIFT,
            f"packages/{package_name}/bootstrap",
            (
                f"{package_name} bootstrap payload contains executable code; CLI/package source owns executable behavior, "
                "and checked-in bootstrap payload must stay declarative: "
                + ", ".join(executable_files[:8])
                + (" ..." if len(executable_files) > 8 else "")
            ),
        )
    ]


def _force_include_entries(repo_root: Path, package_name: str) -> dict[str, str]:
    pyproject = repo_root / "packages" / package_name / "pyproject.toml"
    if not pyproject.exists():
        return {}
    payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    current: Any = payload
    for key in ("tool", "hatch", "build", "targets", "wheel", "force-include"):
        if not isinstance(current, dict):
            return {}
        current = current.get(key, {})
    if not isinstance(current, dict):
        return {}
    return {str(source): str(destination) for source, destination in current.items()}


def _force_include_covers_bootstrap_path(entries: dict[str, str], relative: str) -> bool:
    source_path = Path("bootstrap") / relative
    for source, destination in entries.items():
        source_prefix = Path(source)
        destination_prefix = Path(destination)
        if source_path == source_prefix or source_path.is_relative_to(source_prefix):
            expected_destination = (destination_prefix / source_path.relative_to(source_prefix)).as_posix()
            return "_payload" in expected_destination
    return False


def _payload_inventory_warnings(*, repo_root: Path, package_name: str, expected: list[str]) -> list[BoundaryWarning]:
    actual = _package_payload_files(repo_root, package_name)
    missing = _missing_payload_sources(expected=expected, actual=actual)
    classified = _classified_source_only_payload_files(package_name=package_name, expected=expected, actual=actual)
    unexpected = [item["path"] for item in classified if item["classification"] == "unexpected-source-extra"]
    if not expected or (not missing and not unexpected):
        return []
    details: list[str] = []
    if missing:
        details.append("missing payload file(s): " + ", ".join(missing))
    if unexpected:
        details.append("unexpected source extra(s): " + ", ".join(unexpected))
    return [
        BoundaryWarning(
            WARNING_PAYLOAD_INVENTORY_DRIFT,
            f"packages/{package_name}/bootstrap",
            f"{package_name} bootstrap payload inventory drifted from package source contract; " + "; ".join(details),
        )
    ]


def _packaging_manifest_warnings(*, repo_root: Path, package_name: str, expected: list[str]) -> list[BoundaryWarning]:
    if not expected:
        return []
    entries = _force_include_entries(repo_root, package_name)
    missing = [relative for relative in expected if not _force_include_covers_bootstrap_path(entries, relative)]
    if not missing:
        return []
    return [
        BoundaryWarning(
            WARNING_PACKAGING_MANIFEST_DRIFT,
            f"packages/{package_name}/pyproject.toml",
            (
                f"{package_name} package manifest does not include required bootstrap payload path(s) in wheel _payload: "
                + ", ".join(missing[:8])
                + (" ..." if len(missing) > 8 else "")
            ),
        )
    ]


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


def _planning_checker_duplicate_warnings(*, repo_root: Path) -> list[BoundaryWarning]:
    canonical = repo_root / "packages" / "planning" / "scripts" / "check" / "check_planning_surfaces.py"
    package_checkout = repo_root / "packages" / "planning"
    if not (package_checkout / "scripts").exists():
        return []
    root_wrapper = repo_root / "scripts" / "check" / "check_planning_surfaces.py"
    duplicate_paths = [
        repo_root / ".agentic-workspace" / "planning" / "scripts" / "check" / "check_planning_surfaces.py",
        repo_root / "packages" / "planning" / "bootstrap" / "scripts" / "check" / "check_planning_surfaces.py",
        repo_root
        / "packages"
        / "planning"
        / "bootstrap"
        / ".agentic-workspace"
        / "planning"
        / "scripts"
        / "check"
        / "check_planning_surfaces.py",
    ]
    warnings: list[BoundaryWarning] = []
    if not canonical.exists():
        warnings.append(
            BoundaryWarning(
                WARNING_DUPLICATE_PLANNING_CHECKER_DRIFT,
                _render_path(canonical),
                "Package-owned planning checker source is missing; keep one canonical full implementation under packages/planning/scripts/check.",
            )
        )
    if root_wrapper.exists() and "def gather_planning_warnings" in root_wrapper.read_text(encoding="utf-8"):
        warnings.append(
            BoundaryWarning(
                WARNING_DUPLICATE_PLANNING_CHECKER_DRIFT,
                _render_path(root_wrapper),
                "Root planning checker command path must stay a thin wrapper, not a second full implementation.",
            )
        )
    for path in duplicate_paths:
        if path.exists():
            warnings.append(
                BoundaryWarning(
                    WARNING_DUPLICATE_PLANNING_CHECKER_DRIFT,
                    _render_path(path),
                    "Duplicate planning checker body found; use the package-owned checker source plus thin compatibility wrappers.",
                )
            )
    return warnings


def gather_boundary_warnings(*, repo_root: Path = REPO_ROOT) -> list[BoundaryWarning]:
    warnings: list[BoundaryWarning] = []

    package_local_candidates = {
        repo_root / "packages" / "memory" / ".agentic-workspace": (
            "Package-local installed memory surfaces detected under packages/memory; remove accidental installs and refresh the root operational install instead."
        ),
        repo_root / "packages" / "memory" / "memory": (
            "Legacy package-local memory tree detected under packages/memory/memory; bootstrap payload must live under packages/memory/bootstrap and must not duplicate installed repo memory."
        ),
        repo_root / "packages" / "planning" / ".agentic-workspace": (
            "Package-local installed planning surfaces detected under packages/planning; remove accidental installs and refresh the root operational install instead."
        ),
        repo_root / "packages" / "planning" / "bootstrap" / ".agentic-workspace" / "planning" / "state.toml": (
            "Active surface `state.toml` found in bootstrap; avoid checked-in active state in the payload."
        ),
        repo_root / "packages" / "memory" / "bootstrap" / "optional": (
            "Root-level optional fragments found in memory bootstrap; bootstrap payload must stay to structural README/AGENTS, templates, schemas, and managed workspace payload."
        ),
        repo_root / "packages" / "memory" / "bootstrap" / "scripts": (
            "Raw scripts found in memory bootstrap; package helper code belongs in package source or repo maintainer scripts, not bootstrap payload."
        ),
        repo_root / "packages" / "planning" / "bootstrap" / "scripts": (
            "Root-level scripts found in planning bootstrap; package helper code belongs in package source or repo maintainer scripts, not bootstrap payload."
        ),
        repo_root / "packages" / "planning" / "bootstrap" / "tools": (
            "Root-level generated tools found in planning bootstrap; generated adapters must not be shipped as bootstrap root directories."
        ),
        repo_root / "packages" / "planning" / "bootstrap" / ".agentic-workspace" / "planning" / "scripts": (
            "Raw planning scripts found in managed planning bootstrap; ship queryable contracts and schemas, not copied Python helper scripts."
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
    warnings.extend(_planning_checker_duplicate_warnings(repo_root=repo_root))
    planning_expected = _planning_expected_payload_files(repo_root)
    memory_expected = _memory_expected_payload_files(repo_root)
    warnings.extend(_executable_payload_warnings(repo_root=repo_root, package_name="planning"))
    warnings.extend(_executable_payload_warnings(repo_root=repo_root, package_name="memory"))
    warnings.extend(_payload_inventory_warnings(repo_root=repo_root, package_name="planning", expected=planning_expected))
    warnings.extend(_payload_inventory_warnings(repo_root=repo_root, package_name="memory", expected=memory_expected))
    warnings.extend(_packaging_manifest_warnings(repo_root=repo_root, package_name="planning", expected=planning_expected))
    warnings.extend(_packaging_manifest_warnings(repo_root=repo_root, package_name="memory", expected=memory_expected))

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


def _status_from_drift(*, missing: list[str], unexpected_extra_count: int = 0) -> str:
    return "current" if not missing and unexpected_extra_count == 0 else "drift"


def _missing_payload_sources(*, expected: list[str], actual: list[str]) -> list[str]:
    actual_set = set(actual)
    missing: list[str] = []
    for relative in expected:
        if relative in actual_set:
            continue
        if relative == "AGENTS.md" and "AGENTS.template.md" in actual_set:
            continue
        missing.append(relative)
    return sorted(missing)


def _classified_source_only_payload_files(*, package_name: str, expected: list[str], actual: list[str]) -> list[dict[str, str]]:
    extra = sorted(set(actual) - set(expected))
    classified: list[dict[str, str]] = []
    for relative in extra:
        classification = "unexpected-source-extra"
        rule = "Unexpected bootstrap source extras require classification before they can be treated as intentional."
        if package_name == "planning" and (
            "__pycache__" in relative
        ):
            classification = "intentional-source-extra"
            rule = "Transient planning bytecode/cache files are ignored as source-only extras."
        elif package_name == "memory" and _is_allowed_memory_bootstrap_extra(relative):
            classification = "intentional-source-extra"
            rule = "Memory bootstrap extras must stay structural or templated: directory README/AGENTS, *.template.md, schemas, and package-managed metadata."
        classified.append({"path": relative, "classification": classification, "rule": rule})
    return classified


def _is_allowed_memory_bootstrap_extra(relative: str) -> bool:
    path = Path(relative)
    if relative in {
        "AGENTS.template.md",
        "README.md",
        ".agentic-workspace/memory/VERSION.md",
        ".agentic-workspace/memory/repo/current/routing-feedback.md",
    }:
        return True
    if path.name in {"README.md", "AGENTS.md", "AGENTS.template.md"}:
        return True
    if path.name.endswith(".template.md") or path.name.endswith(".schema.json"):
        return True
    return False


def _classification_counts(items: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        classification = item.get("classification", "")
        if classification:
            counts[classification] = counts.get(classification, 0) + 1
    return dict(sorted(counts.items()))


def _root_status(repo_root: Path, sentinels: list[str]) -> dict[str, object]:
    missing = [relative for relative in sentinels if not (repo_root / relative).exists()]
    return {
        "status": "current" if not missing else "missing-root-surface",
        "sentinels": sentinels,
        "missing": missing,
        "rule": "Root operational sentinels prove the installed dogfooding layer exists; root-local content may intentionally differ from shipped payload state.",
    }


def _package_sync_proof(
    *,
    repo_root: Path,
    package_name: str,
    expected_payload: list[str],
    root_sentinels: list[str],
    intentional_differences: list[dict[str, str]],
) -> dict[str, object]:
    actual_payload = _package_payload_files(repo_root, package_name)
    missing = _missing_payload_sources(expected=expected_payload, actual=actual_payload)
    extra = sorted(set(actual_payload) - set(expected_payload))
    classified_source_only = _classified_source_only_payload_files(package_name=package_name, expected=expected_payload, actual=actual_payload)
    classification_counts = _classification_counts(classified_source_only)
    unexpected_extra = [item["path"] for item in classified_source_only if item["classification"] == "unexpected-source-extra"]
    force_include = _force_include_entries(repo_root, package_name)
    manifest_missing = sorted(relative for relative in expected_payload if not _force_include_covers_bootstrap_path(force_include, relative))
    root = _root_status(repo_root, root_sentinels)
    package_warnings = [
        warning.warning_class
        for warning in gather_boundary_warnings(repo_root=repo_root)
        if warning.path.startswith(f"packages/{package_name}") or f"packages/{package_name}" in warning.message
    ]
    package_local_warning_classes = sorted({warning for warning in package_warnings if warning == WARNING_PACKAGE_LOCAL_INSTALL_DRIFT})
    executable_payload_files = _executable_payload_files(repo_root, package_name)
    status = "current"
    if missing or unexpected_extra or manifest_missing or root["status"] != "current" or package_local_warning_classes or executable_payload_files:
        status = "warning"
    return {
        "package": package_name,
        "status": status,
        "owners": {
            "package_source": f"packages/{package_name}/src",
            "bootstrap_payload_source": f"packages/{package_name}/bootstrap",
            "packaging_manifest": f"packages/{package_name}/pyproject.toml",
            "root_operational_install": ".agentic-workspace/",
        },
        "refresh_rules": [
            "Edit package source and bootstrap payload for distributable behavior.",
            "Use package upgrade commands to refresh root operational install surfaces.",
            "Treat root operational state as dogfooding state unless a managed payload file is intentionally refreshed.",
        ],
        "source_to_payload_inventory": {
            "status": _status_from_drift(missing=missing, unexpected_extra_count=len(unexpected_extra)),
            "expected_count": len(expected_payload),
            "actual_count": len(actual_payload),
            "missing": missing,
            "unexpected": unexpected_extra,
            "extra_count": len(extra),
            "classification_counts": classification_counts,
            "classified_source_only_or_generated": classified_source_only,
            "ignored_transient_rule": "Bytecode and cache files under __pycache__ or with a .pyc suffix are ignored before payload classification.",
            "rule": "Missing package-declared payload sources are drift; extra bootstrap files are classified so intentional source-only or computed managed payloads do not look like unowned drift.",
        },
        "packaged_payload_manifest": {
            "status": "current" if not manifest_missing else "drift",
            "force_include_count": len(force_include),
            "missing_payload_destinations": manifest_missing,
            "rule": "Every required bootstrap payload path must be force-included into the package _payload tree.",
        },
        "payload_to_root_install": root,
        "intentional_differences": intentional_differences,
        "package_local_install_guard": {
            "status": "current" if not package_local_warning_classes else "warning",
            "warning_classes": package_local_warning_classes,
            "rule": "Package-local .agentic-workspace installs are drift; root operational install is the dogfooding layer.",
        },
        "executable_payload_guard": {
            "status": "current" if not executable_payload_files else "drift",
            "executable_files": executable_payload_files,
            "rule": "Bootstrap payload must not ship executable code; executable behavior belongs in CLI/package source outside checked-in payload files.",
        },
    }


def gather_sync_proof(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    planning_expected = _planning_expected_payload_files(repo_root)
    memory_expected = _memory_expected_payload_files(repo_root)
    proof = [
        _package_sync_proof(
            repo_root=repo_root,
            package_name="planning",
            expected_payload=planning_expected,
            root_sentinels=[
                ".agentic-workspace/planning/state.toml",
                ".agentic-workspace/planning/execplans/README.md",
                ".agentic-workspace/planning/agent-manifest.json",
            ],
            intentional_differences=[
                {
                    "path": ".agentic-workspace/planning/state.toml",
                    "classification": "root-operational-state",
                    "rule": "Active planning state is intentionally root-local and must not be shipped as package bootstrap payload.",
                },
                {
                    "path": ".agentic-workspace/planning/execplans/archive/",
                    "classification": "historical-dogfood-evidence",
                    "rule": "Root archives may exceed package templates; package payload only owns the reusable guidance and templates.",
                },
            ],
        ),
        _package_sync_proof(
            repo_root=repo_root,
            package_name="memory",
            expected_payload=memory_expected,
            root_sentinels=[
                ".agentic-workspace/memory/repo/index.md",
                ".agentic-workspace/memory/WORKFLOW.md",
                ".agentic-workspace/memory/SKILLS.md",
            ],
            intentional_differences=[
                {
                    "path": ".agentic-workspace/memory/repo/current/",
                    "classification": "root-operational-memory",
                    "rule": "Current memory can be root-local and time-sensitive; shipped payload owns only the starter/baseline notes.",
                },
                {
                    "path": ".agentic-workspace/memory/repo/",
                    "classification": "dogfood-knowledge-growth",
                    "rule": "Repo memory may grow beyond packaged starter examples without making package payload stale.",
                },
            ],
        ),
    ]
    return {
        "kind": "source-payload-root-sync-proof/v1",
        "status": "current" if all(item["status"] == "current" for item in proof) else "warning",
        "packages": proof,
        "intentional_difference_rule": "Intentional root dogfooding state is classified here and should not be reported as payload drift unless a managed payload file changed without refresh.",
        "operator_commands": [
            "uv run python scripts/check/check_source_payload_operational_install.py --format json --strict",
            "make maintainer-surfaces",
            "uv run agentic-planning upgrade --target .",
            "uv run agentic-memory upgrade --target .",
        ],
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
        "sync_proof": gather_sync_proof(repo_root=REPO_ROOT),
    }

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        if args.quiet_success and not warnings:
            print("[ok] source-payload boundary")
        else:
            _print_warnings(warnings)
            proof = summary["sync_proof"]
            print(f"Sync proof: {proof['status']}")
            for package in proof["packages"]:
                print(
                    f"- {package['package']}: {package['status']} "
                    f"(source/payload {package['source_to_payload_inventory']['status']}; "
                    f"packaging {package['packaged_payload_manifest']['status']}; "
                    f"root {package['payload_to_root_install']['status']})"
                )

    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())

