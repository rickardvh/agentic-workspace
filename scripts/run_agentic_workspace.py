from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = REPO_ROOT / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
SOURCE_MANIFEST_PATH = REPO_ROOT / "generated" / ".agentic-workspace-cli-fingerprint.json"
GENERATOR_SCRIPT = REPO_ROOT / "scripts" / "generate" / "generate_command_packages.py"
CACHE_SCHEMA = "generated-cli-fingerprint/v1"

FINGERPRINT_PATTERNS = (
    "pyproject.toml",
    "uv.lock",
    "scripts/**/*.py",
    "src/**/*.py",
    "src/**/*.json",
    "src/**/*.mjs",
    "packages/*/src/**/*.py",
    "packages/*/src/**/*.json",
    "packages/*/src/**/*.mjs",
    "generated/**/*.py",
    "generated/**/*.json",
    "generated/**/*.mjs",
)


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _fingerprint_files(*, repo_root: Path) -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in FINGERPRINT_PATTERNS:
        for path in repo_root.glob(pattern):
            if path.is_file() and "__pycache__" not in path.parts:
                relative = _repo_relative(path, repo_root=repo_root)
                if relative != "generated/.agentic-workspace-cli-fingerprint.json":
                    files[relative] = path
    return [files[relative] for relative in sorted(files)]


def compute_generated_cli_fingerprint(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    digest = hashlib.sha256()
    files = _fingerprint_files(repo_root=repo_root)
    relative_paths: list[str] = []
    for path in files:
        relative = _repo_relative(path, repo_root=repo_root)
        relative_paths.append(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {
        "schema": CACHE_SCHEMA,
        "algorithm": "sha256",
        "fingerprint": digest.hexdigest(),
        "file_count": len(files),
        "file_paths": relative_paths,
    }


def _read_cached_fingerprint_payload(*, cache_path: Path = CACHE_PATH) -> dict[str, object] | None:
    if not cache_path.is_file():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != CACHE_SCHEMA:
        return None
    return payload


def _read_cached_fingerprint(*, cache_path: Path = CACHE_PATH) -> str | None:
    payload = _read_cached_fingerprint_payload(cache_path=cache_path)
    if payload is None:
        return None
    fingerprint = payload.get("fingerprint")
    return fingerprint if isinstance(fingerprint, str) and fingerprint else None


def _git_worktree_is_clean(*, repo_root: Path) -> bool:
    """Return whether Git can establish that no source input is dirty.

    A source-owned manifest is valid only for a clean checkout.  This keeps the
    cold path cheap without allowing an edited or unobservable worktree to skip
    the content-fingerprint fallback.
    """

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and not result.stdout.strip()


def _git_index_identity(*, repo_root: Path, paths: list[str]) -> str | None:
    """Return the Git index identity for exactly the fingerprint inputs."""

    if not paths:
        return None
    try:
        result = subprocess.run(
            ["git", "ls-files", "-s", "-z"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    entries_by_path: dict[str, str] = {}
    for raw_entry in result.stdout.split(b"\0"):
        if not raw_entry:
            continue
        entry = raw_entry.decode("utf-8")
        try:
            _, indexed_path = entry.split("\t", 1)
        except ValueError:
            return None
        entries_by_path[indexed_path] = entry
    digest = hashlib.sha256()
    for expected_path in paths:
        entry = entries_by_path.get(expected_path)
        if entry is None:
            return None
        try:
            metadata, indexed_path = entry.split("\t", 1)
        except ValueError:
            return None
        fields = metadata.split()
        if indexed_path != expected_path or len(fields) != 3 or fields[2] != "0":
            return None
        digest.update(entry.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def source_cli_fingerprint_manifest(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    """Build the checked-in freshness witness from exact inputs and Git index."""

    paths = [_repo_relative(path, repo_root=repo_root) for path in _fingerprint_files(repo_root=repo_root)]
    return {
        "schema": CACHE_SCHEMA,
        "kind": "generated-cli-source-manifest/v1",
        "file_count": len(paths),
        "file_paths": paths,
        "git_index_identity": _git_index_identity(repo_root=repo_root, paths=paths),
        "generation_command": "uv run python scripts/generate/generate_command_packages.py",
    }


def _source_manifest_is_trustworthy(*, repo_root: Path) -> bool:
    """Use a clean source manifest only when it binds this exact Git index."""

    source_manifest = repo_root / "generated" / ".agentic-workspace-cli-fingerprint.json"
    payload = _read_cached_fingerprint_payload(cache_path=source_manifest)
    if payload is None or not _git_worktree_is_clean(repo_root=repo_root):
        return False
    paths = payload.get("file_paths")
    expected_identity = payload.get("git_index_identity")
    if (
        not isinstance(paths, list)
        or not all(isinstance(path, str) for path in paths)
        or not isinstance(expected_identity, str)
        or not expected_identity
    ):
        return False
    current_paths = [_repo_relative(path, repo_root=repo_root) for path in _fingerprint_files(repo_root=repo_root)]
    if current_paths != paths:
        return False
    return _git_index_identity(repo_root=repo_root, paths=paths) == expected_identity


def _cached_fingerprint_manifest_is_fresh(*, repo_root: Path, cache_path: Path) -> bool:
    payload = _read_cached_fingerprint_payload(cache_path=cache_path)
    if payload is None:
        return False
    cached_paths = payload.get("file_paths")
    if not isinstance(cached_paths, list) or not all(isinstance(path, str) for path in cached_paths):
        return False
    current_files = _fingerprint_files(repo_root=repo_root)
    current_paths = [_repo_relative(path, repo_root=repo_root) for path in current_files]
    if current_paths != cached_paths:
        return False
    try:
        cache_mtime_ns = cache_path.stat().st_mtime_ns
    except OSError:
        return False
    for path in current_files:
        try:
            if path.stat().st_mtime_ns > cache_mtime_ns:
                return False
        except OSError:
            return False
    return True


def _replace_cache_file_with_retries(
    source_path: Path,
    target_path: Path,
    *,
    replace_path: Callable[[Path, Path], object] | None = None,
    sleep: Callable[[float], object] = time.sleep,
    attempts: int = 5,
) -> None:
    replacer = replace_path or (lambda source, target: source.replace(target))
    for attempt in range(attempts):
        try:
            replacer(source_path, target_path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            sleep(0.05 * (attempt + 1))


def _write_cached_fingerprint(
    fingerprint: dict[str, object],
    *,
    cache_path: Path = CACHE_PATH,
    replace_path: Callable[[Path, Path], object] | None = None,
    sleep: Callable[[float], object] = time.sleep,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **fingerprint,
        "updated_at": datetime.now(UTC).isoformat(),
        "regeneration_command": "uv run python scripts/generate/generate_command_packages.py",
    }
    temporary_path = cache_path.with_name(f"{cache_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _replace_cache_file_with_retries(temporary_path, cache_path, replace_path=replace_path, sleep=sleep)
    finally:
        temporary_path.unlink(missing_ok=True)


def _default_run_generator(*, repo_root: Path, generator_script: Path) -> None:
    result = subprocess.run([sys.executable, str(generator_script)], cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        raise SystemExit(result.returncode)


def ensure_generated_cli_current(
    *,
    repo_root: Path = REPO_ROOT,
    cache_path: Path | None = None,
    generator_script: Path | None = None,
    run_generator: Callable[[Path, Path], None] | None = None,
) -> bool:
    effective_cache = cache_path or repo_root / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
    effective_generator = generator_script or repo_root / "scripts" / "generate" / "generate_command_packages.py"
    force = os.environ.get("AW_FORCE_GENERATED_CLI_REFRESH") == "1"
    if not force and _cached_fingerprint_manifest_is_fresh(repo_root=repo_root, cache_path=effective_cache):
        return False
    if not force and _source_manifest_is_trustworthy(repo_root=repo_root):
        return False
    before = compute_generated_cli_fingerprint(repo_root=repo_root)
    cached = _read_cached_fingerprint(cache_path=effective_cache)
    if not force and cached == before["fingerprint"]:
        return False

    runner = run_generator or (lambda root, generator: _default_run_generator(repo_root=root, generator_script=generator))
    runner(repo_root, effective_generator)
    after = compute_generated_cli_fingerprint(repo_root=repo_root)
    _write_cached_fingerprint(after, cache_path=effective_cache)
    return True


def _dispatch_to_source_cli(argv: Sequence[str]) -> int:
    source_root = REPO_ROOT / "src"
    for path in (str(source_root), str(REPO_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from agentic_workspace.cli import main as cli_main

    return int(cli_main(list(argv)))


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if os.environ.get("AW_SKIP_GENERATED_CLI_REFRESH") != "1":
        ensure_generated_cli_current()
    return _dispatch_to_source_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
