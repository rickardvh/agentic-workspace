"""Repository file enumeration with Git ignore semantics when available."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from pathlib import Path

REPOSITORY_SCAN_FALLBACK_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "dist",
    "build",
}

_MANAGED_WORKSPACE_ROOT = ".agentic-workspace"
_GIT_TIMEOUT_SECONDS = 10


def repository_scan_files(
    target_root: Path,
    *,
    relative_roots: Iterable[str | Path] | None = None,
    exclude_relative_roots: Iterable[str | Path] | None = None,
    include_untracked: bool = True,
    include_managed_workspace: bool = True,
    suffixes: Iterable[str] | None = None,
    max_files: int | None = None,
) -> list[Path]:
    """Return repository files using Git ignore semantics when possible.

    In real Git repositories this lists tracked files and, by default, untracked
    non-ignored files. The managed ``.agentic-workspace`` tree is included
    explicitly when requested because AW command surfaces intentionally read
    checked-in and local workflow state there even when a host repo ignores it.
    Non-Git targets fall back to conservative directory pruning.
    """

    root = Path(target_root).resolve(strict=False)
    if not root.exists():
        return []

    normalized_roots = _normalize_relative_roots(relative_roots)
    excluded_roots = _normalize_excluded_relative_roots(exclude_relative_roots)
    suffix_filter = _normalize_suffixes(suffixes)
    git_files = _git_repository_files(
        target_root=root,
        relative_roots=normalized_roots,
        include_untracked=include_untracked,
    )
    if git_files is None:
        files = _fallback_repository_files(target_root=root, relative_roots=normalized_roots)
    else:
        files = git_files
        if include_managed_workspace:
            for managed_root in _managed_exception_roots(normalized_roots):
                files.extend(_walk_files(target_root=root, scan_root=root / managed_root))

    return _dedupe_sort_filter(
        files,
        target_root=root,
        exclude_relative_roots=excluded_roots,
        suffixes=suffix_filter,
        max_files=max_files,
    )


def _normalize_relative_roots(relative_roots: Iterable[str | Path] | None) -> list[str]:
    if relative_roots is None:
        return ["."]
    normalized: list[str] = []
    for raw_root in relative_roots:
        text = Path(raw_root).as_posix().strip()
        if not text or text == ".":
            normalized.append(".")
            continue
        normalized.append(text.strip("/"))
    return normalized or ["."]


def _normalize_suffixes(suffixes: Iterable[str] | None) -> set[str]:
    normalized: set[str] = set()
    for suffix in suffixes or ():
        text = str(suffix).strip().lower()
        if not text:
            continue
        normalized.add(text if text.startswith(".") else f".{text}")
    return normalized


def _normalize_excluded_relative_roots(exclude_relative_roots: Iterable[str | Path] | None) -> list[str]:
    normalized = [root for root in _normalize_relative_roots(exclude_relative_roots) if root != "."]
    return sorted(set(normalized), key=lambda value: (len(value), value))


def _git_repository_files(
    *,
    target_root: Path,
    relative_roots: list[str],
    include_untracked: bool,
) -> list[Path] | None:
    git_root = _git_root_for(target_root)
    if git_root is None:
        return None
    pathspecs = _git_pathspecs(git_root=git_root, target_root=target_root, relative_roots=relative_roots)
    if not pathspecs:
        return []
    command = ["git", "-C", str(git_root), "ls-files", "-z", "--cached"]
    if include_untracked:
        command.extend(["--others", "--exclude-standard"])
    command.extend(["--", *pathspecs])
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired, TypeError):
        return None
    if result.returncode != 0:
        return None
    files: list[Path] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = raw_path.decode("utf-8", errors="replace")
        path = git_root / relative
        if _is_within(path, target_root) and path.is_file():
            files.append(path)
    return files


def _git_root_for(target_root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(target_root), "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired, TypeError):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    if not text:
        return None
    return Path(text)


def _git_pathspecs(*, git_root: Path, target_root: Path, relative_roots: list[str]) -> list[str]:
    try:
        target_prefix = target_root.resolve().relative_to(git_root.resolve()).as_posix()
    except ValueError:
        return []
    pathspecs: list[str] = []
    for relative_root in relative_roots:
        if relative_root == ".":
            pathspec = target_prefix or "."
        elif target_prefix:
            pathspec = f"{target_prefix.rstrip('/')}/{relative_root}"
        else:
            pathspec = relative_root
        pathspecs.append(pathspec)
    return pathspecs


def _managed_exception_roots(relative_roots: list[str]) -> list[str]:
    roots: set[str] = set()
    for relative_root in relative_roots:
        if relative_root == ".":
            roots.add(_MANAGED_WORKSPACE_ROOT)
        elif relative_root == _MANAGED_WORKSPACE_ROOT or relative_root.startswith(f"{_MANAGED_WORKSPACE_ROOT}/"):
            roots.add(relative_root)
    return sorted(roots)


def _fallback_repository_files(*, target_root: Path, relative_roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for relative_root in relative_roots:
        scan_root = target_root if relative_root == "." else target_root / relative_root
        files.extend(_walk_files(target_root=target_root, scan_root=scan_root))
    return files


def _walk_files(*, target_root: Path, scan_root: Path) -> list[Path]:
    if not scan_root.exists():
        return []
    files: list[Path] = []
    for root, dirnames, filenames in os.walk(scan_root):
        dirnames[:] = sorted(
            dirname for dirname in dirnames if dirname not in REPOSITORY_SCAN_FALLBACK_SKIP_DIRS and not dirname.startswith(".uv-cache")
        )
        root_path = Path(root)
        for filename in sorted(filenames):
            path = root_path / filename
            if not _is_within(path, target_root) or not path.is_file():
                continue
            files.append(path)
    return files


def _dedupe_sort_filter(
    files: Iterable[Path],
    *,
    target_root: Path,
    exclude_relative_roots: list[str],
    suffixes: set[str],
    max_files: int | None,
) -> list[Path]:
    unique: dict[str, Path] = {}
    for path in files:
        if _is_excluded(path=path, target_root=target_root, exclude_relative_roots=exclude_relative_roots):
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        key = str(path.resolve(strict=False)).casefold()
        unique[key] = path
    sorted_files = sorted(unique.values(), key=lambda path: _relative_sort_key(path=path, target_root=target_root))
    if max_files is not None:
        return sorted_files[:max_files]
    return sorted_files


def _relative_sort_key(*, path: Path, target_root: Path) -> str:
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_excluded(*, path: Path, target_root: Path, exclude_relative_roots: list[str]) -> bool:
    if not exclude_relative_roots:
        return False
    relative = _relative_sort_key(path=path, target_root=target_root)
    for excluded_root in exclude_relative_roots:
        if relative == excluded_root or relative.startswith(f"{excluded_root.rstrip('/')}/"):
            return True
    return False


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True
