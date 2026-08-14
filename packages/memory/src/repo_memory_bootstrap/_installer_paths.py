from __future__ import annotations

import os
import tomllib
from pathlib import Path

from repo_memory_bootstrap._installer_shared import (
    BOOTSTRAP_WORKSPACE_ROOT,
    LEGACY_BOOTSTRAP_WORKSPACE_ROOT,
    LEGACY_SHIPPED_SKILLS_ROOT,
    LEGACY_SYSTEM_ROOT,
    MANAGED_ROOT,
    PROJECT_MARKERS,
    SHIPPED_SKILLS_ROOT,
    RepoDetectionError,
)


def resolve_target_root(target: str | Path | None) -> Path:
    explicit_target = target is not None
    start = Path(target or Path.cwd()).resolve()
    if not start.exists():
        raise RepoDetectionError(f"Target does not exist: {start}")
    if start.is_file():
        raise RepoDetectionError(f"Target must be a directory: {start}")
    if explicit_target:
        return start

    candidates = _find_repo_candidates(start)
    if not candidates:
        raise RepoDetectionError("Could not find a repository root from the current directory. Pass --target explicitly.")
    if len(candidates) > 1:
        roots = ", ".join(str(path) for path in candidates)
        raise RepoDetectionError(f"Ambiguous repository root detected ({roots}). Pass --target explicitly. Retry with --target .")
    return candidates[0]


def payload_root() -> Path:
    package_root = Path(__file__).resolve().parent
    packaged = package_root / "_payload"
    if packaged.exists():
        return packaged

    dev_payload = package_root.parents[1] / "bootstrap"
    if dev_payload.exists():
        return dev_payload

    raise FileNotFoundError("Bootstrap payload directory is not available.")


def skills_root() -> Path:
    package_root = Path(__file__).resolve().parent
    packaged = package_root / "_skills"
    if packaged.exists():
        return packaged

    dev_skills = package_root.parents[1] / "skills"
    if dev_skills.exists():
        return dev_skills

    raise FileNotFoundError("Bundled skills directory is not available.")


def detect_bootstrap_layout(target_root: Path) -> str:
    has_managed_root = any(
        (target_root / path).exists()
        for path in (
            MANAGED_ROOT,
            BOOTSTRAP_WORKSPACE_ROOT,
            SHIPPED_SKILLS_ROOT,
        )
    )
    has_legacy_root = any(
        (target_root / path).exists()
        for path in (
            LEGACY_SYSTEM_ROOT,
            LEGACY_BOOTSTRAP_WORKSPACE_ROOT,
            LEGACY_SHIPPED_SKILLS_ROOT,
        )
    )
    if has_managed_root and has_legacy_root:
        return "mixed"
    if has_managed_root:
        return "managed-root"
    if has_legacy_root:
        return "legacy"
    return "none"


def _record_repo_context_warnings(target_root: Path, result) -> None:
    parent_repo = None if _has_git_boundary(target_root) else _find_parent_repo_root(target_root)
    if parent_repo is not None:
        result.add(
            "warning",
            target_root,
            (f"target is inside parent repository {parent_repo}; --target is being treated as authoritative"),
            role="target-context",
            safety="safe",
        )

    for nested_repo in _find_nested_repo_roots(target_root):
        result.add(
            "warning",
            nested_repo,
            ("nested repository detected under target; installer will not recurse into repo roots automatically"),
            role="target-context",
            safety="safe",
        )


def _find_repo_candidates(start: Path) -> list[Path]:
    candidates: list[Path] = []
    for candidate in [start, *start.parents]:
        if _has_git_boundary(candidate):
            candidates.append(candidate)
            continue
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            candidates.append(candidate)
    return candidates


def _find_parent_repo_root(target_root: Path) -> Path | None:
    for candidate in target_root.parents:
        if _has_git_boundary(candidate):
            return candidate
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    return None


def _has_git_boundary(path: Path) -> bool:
    git_dir = path / ".git"
    return git_dir.is_dir() or git_dir.is_file()


def _find_nested_repo_roots(target_root: Path) -> list[Path]:
    nested: list[Path] = []
    seen: set[Path] = set()
    for current, directory_names, _file_names in os.walk(target_root, topdown=True, followlinks=False):
        current_path = Path(current)
        if current_path != target_root and _is_owned_harness_evidence_root(current_path, target_root=target_root):
            directory_names[:] = []
            continue
        if ".git" not in directory_names:
            continue
        repo_root = current_path
        directory_names.remove(".git")
        if _is_generated_dependency_cache(repo_root=repo_root, target_root=target_root):
            continue
        if repo_root == target_root or repo_root in seen:
            continue
        nested.append(repo_root)
        seen.add(repo_root)
    return sorted(nested)


def _is_owned_harness_evidence_root(path: Path, *, target_root: Path) -> bool:
    """Trust only contained, non-linked scratch roots with an AW producer manifest."""
    scratch_root = target_root / ".agentic-workspace" / "local" / "scratch"
    try:
        path.resolve(strict=False).relative_to(scratch_root.resolve(strict=False))
    except ValueError:
        return False
    for candidate in [path, *path.parents]:
        if candidate == target_root:
            break
        if candidate.is_symlink():
            return False
    is_junction = getattr(os.path, "isjunction", lambda _path: False)
    if is_junction(path):
        return False
    manifest = path / ".aw-scratch.toml"
    if not manifest.is_file() or manifest.is_symlink():
        return False
    try:
        payload = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return False
    return payload.get("owner") == "agentic-workspace" and payload.get("producer") in {
        "model-cli-harness",
        "model-cli-harness.run-suite",
    }


def _is_generated_dependency_cache(*, repo_root: Path, target_root: Path) -> bool:
    try:
        relative = repo_root.relative_to(target_root)
    except ValueError:
        return False
    return any(part.startswith(".uv-cache") for part in relative.parts)
