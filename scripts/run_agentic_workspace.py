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

GENERATION_DEPENDENCY_PATTERNS = (
    "pyproject.toml",
    "uv.lock",
    "LICENSE",
    ".github/release-ownership.json",
    "scripts/generate/generate_command_packages.py",
    "scripts/generate/workspace_command_generation.py",
    "src/agentic_workspace/contracts/command_package_ir.json",
    "src/agentic_workspace/contracts/operation_primitives.json",
    "src/agentic_workspace/contracts/python_primitive_support.py",
    "src/agentic_workspace/contracts/typescript_primitive_support.mjs",
    "generated/*/typescript/package.json",
)


def _operation_contract_paths(*, repo_root: Path) -> list[str]:
    """Return only operation contracts referenced by the command-package IR."""

    ir_path = repo_root / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json"
    try:
        manifest = json.loads(ir_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    paths: set[str] = set()

    def collect(command: object, *, root: str, inherited: str = "") -> None:
        if not isinstance(command, dict):
            return
        operation_ref = command.get("operation_ref")
        operation_path = inherited
        if isinstance(operation_ref, dict):
            operation_path = str(operation_ref.get("path") or inherited).strip()
        if root and operation_path:
            paths.add((Path(root) / operation_path).as_posix())
        interface = command.get("interface")
        if isinstance(interface, dict):
            for subcommand in interface.get("subcommands", []):
                collect(subcommand, root=root, inherited=operation_path)

    for package in manifest.get("packages", []) if isinstance(manifest, dict) else []:
        if not isinstance(package, dict):
            continue
        root = str(package.get("operation_contract_root") or "").strip()
        for command in package.get("commands", []):
            collect(command, root=root)
    return sorted(paths)


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _fingerprint_files(*, repo_root: Path) -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in GENERATION_DEPENDENCY_PATTERNS:
        for path in repo_root.glob(pattern):
            if path.is_file() and "__pycache__" not in path.parts:
                relative = _repo_relative(path, repo_root=repo_root)
                files[relative] = path
    for relative in _operation_contract_paths(repo_root=repo_root):
        path = repo_root / relative
        if path.is_file():
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
        # Every fingerprint input is a Git-tracked text surface with eol=lf.
        # Normalize an older Windows worktree so the witness identifies Git
        # content rather than the checkout platform's historical line endings.
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
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


def _git_input_paths_are_unmodified(*, repo_root: Path, paths: list[str]) -> bool:
    """Return whether the manifest's exact inputs are clean in the worktree.

    Unrelated local edits must not discard a source-owned freshness witness.
    Git is queried once without the 1,000+ path argv payload (which exceeds
    Windows' process limit), then porcelain records are filtered locally. A
    dirty relevant input, staged change, deletion, rename, or untracked
    replacement still fails closed.
    """

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    if result.returncode != 0:
        return False
    expected = set(paths)
    records = iter(result.stdout.split("\0"))
    for record in records:
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            return False
        status, path = record[:2], record[3:]
        if path in expected:
            return False
        if "R" in status or "C" in status:
            try:
                original_path = next(records)
            except StopIteration:
                return False
            if original_path in expected:
                return False
    return True


def _git_index_entries(*, repo_root: Path, paths: list[str]) -> dict[str, str] | None:
    """Return stage-zero Git index entries for exactly the fingerprint inputs."""

    if not paths:
        return None
    try:
        result = subprocess.run(
            # Windows process creation cannot carry the 1,000+ exact paths as
            # arguments. Read the index once and retain only the manifest set;
            # this is still metadata-only and never reads source contents.
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
            metadata, indexed_path = entry.split("\t", 1)
        except ValueError:
            return None
        fields = metadata.split()
        if len(fields) != 3 or fields[2] != "0":
            return None
        entries_by_path[indexed_path] = fields[1]
    if not set(paths).issubset(entries_by_path):
        return None
    return {path: entries_by_path[path] for path in paths}


def source_cli_fingerprint_manifest(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    """Build the merge-stable semantic identity of generation dependencies."""

    paths = [_repo_relative(path, repo_root=repo_root) for path in _fingerprint_files(repo_root=repo_root)]
    content_identity = compute_generated_cli_fingerprint(repo_root=repo_root)
    return {
        "schema": CACHE_SCHEMA,
        "kind": "generated-cli-source-manifest/v1",
        "file_count": len(paths),
        "file_paths": paths,
        "algorithm": content_identity["algorithm"],
        "fingerprint": content_identity["fingerprint"],
        "identity_role": "canonical-semantic-content",
        "context_rule": "Only actual generation dependencies are listed. Git checkout witnesses are derived locally and never carried across branches.",
        "generation_command": "uv run python scripts/generate/generate_command_packages.py",
    }


def source_cli_fingerprint_manifest_status(
    *,
    repo_root: Path = REPO_ROOT,
    manifest_path: Path | None = None,
) -> dict[str, str]:
    """Classify source-manifest freshness with semantic content as authority."""

    source_manifest = manifest_path or repo_root / "generated" / ".agentic-workspace-cli-fingerprint.json"
    payload = _read_cached_fingerprint_payload(cache_path=source_manifest)
    if payload is None:
        return {"status": "invalid", "reason": "invalid-manifest", "auxiliary_witness": "not-evaluated"}
    paths = payload.get("file_paths")
    expected_content_identity = payload.get("fingerprint")
    if (
        payload.get("kind") != "generated-cli-source-manifest/v1"
        or not isinstance(paths, list)
        or not all(isinstance(path, str) for path in paths)
        or not isinstance(expected_content_identity, str)
        or not expected_content_identity
    ):
        return {"status": "invalid", "reason": "invalid-manifest", "auxiliary_witness": "not-evaluated"}
    if "git_index_entries" in payload or "git_index_identity" in payload:
        return {"status": "invalid", "reason": "branch-carried-git-witness", "auxiliary_witness": "not-evaluated"}
    current_paths = [_repo_relative(path, repo_root=repo_root) for path in _fingerprint_files(repo_root=repo_root)]
    if current_paths != paths:
        return {"status": "stale", "reason": "semantic-path-set-drift", "auxiliary_witness": "not-evaluated"}
    current_entries = _git_index_entries(repo_root=repo_root, paths=paths)
    inputs_unmodified = current_entries is not None and _git_input_paths_are_unmodified(repo_root=repo_root, paths=paths)
    auxiliary_witness = "derived-clean-index" if inputs_unmodified else "unavailable" if current_entries is None else "dirty-inputs"
    current_content_identity = compute_generated_cli_fingerprint(repo_root=repo_root).get("fingerprint")
    if current_content_identity == expected_content_identity:
        return {"status": "current", "reason": "semantic-content-match", "auxiliary_witness": auxiliary_witness}
    return {"status": "stale", "reason": "semantic-content-drift", "auxiliary_witness": auxiliary_witness}


def _source_manifest_is_trustworthy(*, repo_root: Path) -> bool:
    """Validate semantic content in every context, using Git only as a fast path."""

    return source_cli_fingerprint_manifest_status(repo_root=repo_root)["status"] == "current"


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


def _should_refresh_generated_cli_for_argv(argv: Sequence[str]) -> bool:
    if os.environ.get("AW_SKIP_GENERATED_CLI_REFRESH") == "1":
        return False
    if os.environ.get("AW_FORCE_GENERATED_CLI_REFRESH") == "1":
        return True
    args = [arg for arg in argv if arg != "--"]
    return not args or args[0] != "start"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if _should_refresh_generated_cli_for_argv(args):
        ensure_generated_cli_current()
    return _dispatch_to_source_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
