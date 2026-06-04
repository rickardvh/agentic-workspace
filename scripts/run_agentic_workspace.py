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
                files[_repo_relative(path, repo_root=repo_root)] = path
    return [files[relative] for relative in sorted(files)]


def compute_generated_cli_fingerprint(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    digest = hashlib.sha256()
    files = _fingerprint_files(repo_root=repo_root)
    for path in files:
        relative = _repo_relative(path, repo_root=repo_root)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {
        "schema": CACHE_SCHEMA,
        "algorithm": "sha256",
        "fingerprint": digest.hexdigest(),
        "file_count": len(files),
    }


def _read_cached_fingerprint(*, cache_path: Path = CACHE_PATH) -> str | None:
    if not cache_path.is_file():
        return None
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != CACHE_SCHEMA:
        return None
    fingerprint = payload.get("fingerprint")
    return fingerprint if isinstance(fingerprint, str) and fingerprint else None


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
    before = compute_generated_cli_fingerprint(repo_root=repo_root)
    cached = _read_cached_fingerprint(cache_path=effective_cache)
    force = os.environ.get("AW_FORCE_GENERATED_CLI_REFRESH") == "1"
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
