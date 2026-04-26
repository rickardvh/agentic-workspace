from __future__ import annotations

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
        raise RepoDetectionError(f"Ambiguous repository root detected ({roots}). Pass --target explicitly.")
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
    parent_repo = _find_parent_repo_root(target_root)
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
        git_dir = candidate / ".git"
        if git_dir.is_dir() or git_dir.is_file():
            candidates.append(candidate)
            continue
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            candidates.append(candidate)
    return candidates


def _find_parent_repo_root(target_root: Path) -> Path | None:
    for candidate in target_root.parents:
        git_dir = candidate / ".git"
        if git_dir.is_dir() or git_dir.is_file():
            return candidate
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    return None


def _find_nested_repo_roots(target_root: Path) -> list[Path]:
    nested: list[Path] = []
    seen: set[Path] = set()
    for candidate in target_root.rglob(".git"):
        repo_root = candidate.parent
        if _is_generated_dependency_cache(repo_root=repo_root, target_root=target_root):
            continue
        if repo_root == target_root or repo_root in seen:
            continue
        nested.append(repo_root)
        seen.add(repo_root)
    return sorted(nested)


def _is_generated_dependency_cache(*, repo_root: Path, target_root: Path) -> bool:
    try:
        relative = repo_root.relative_to(target_root)
    except ValueError:
        return False
    return any(part.startswith(".uv-cache") for part in relative.parts)
