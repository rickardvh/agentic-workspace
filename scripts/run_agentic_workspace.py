from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = REPO_ROOT / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
SOURCE_MANIFEST_PATH = REPO_ROOT / "generated" / ".agentic-workspace-cli-fingerprint.json"
GENERATOR_SCRIPT = REPO_ROOT / "scripts" / "generate" / "generate_command_packages.py"
CACHE_SCHEMA = "generated-cli-fingerprint/v1"
RUNTIME_DISTRIBUTION_PATHS = {
    "agentic-workspace": Path("."),
    "agentic-workspace-memory": Path("packages/memory"),
    "agentic-workspace-planning": Path("packages/planning"),
    "agentic-workspace-verification": Path("packages/verification"),
}

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


def _git_prospective_entries(*, repo_root: Path, paths: list[str]) -> dict[str, str] | None:
    """Return the blob identities Git will index for the current text inputs.

    Fingerprint inputs are repo-declared LF text surfaces. Hashing their
    normalized worktree bytes makes generation stable whether each input is
    staged before or after the manifest is written.
    """

    if not paths:
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-object-format"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    algorithm = result.stdout.strip() if result.returncode == 0 else ""
    if algorithm not in {"sha1", "sha256"}:
        return None
    entries: dict[str, str] = {}
    try:
        for path in paths:
            content = (repo_root / path).read_bytes().replace(b"\r\n", b"\n")
            digest = hashlib.new(algorithm)
            digest.update(f"blob {len(content)}\0".encode("ascii"))
            digest.update(content)
            entries[path] = digest.hexdigest()
    except OSError:
        return None
    return entries


def _git_index_identity_from_entries(*, paths: list[str], entries: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for expected_path in paths:
        digest.update(expected_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(entries[expected_path].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def source_cli_fingerprint_manifest(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    """Build a transportable content identity plus optional Git acceleration."""

    paths = [_repo_relative(path, repo_root=repo_root) for path in _fingerprint_files(repo_root=repo_root)]
    content_identity = compute_generated_cli_fingerprint(repo_root=repo_root)
    prospective_entries = _git_prospective_entries(repo_root=repo_root, paths=paths)
    return {
        "schema": CACHE_SCHEMA,
        "kind": "generated-cli-source-manifest/v1",
        "file_count": len(paths),
        "file_paths": paths,
        "algorithm": content_identity["algorithm"],
        "fingerprint": content_identity["fingerprint"],
        "identity_role": "canonical-semantic-content",
        "context_rule": "Every listed input is required in source and conformance contexts; Git metadata is auxiliary only.",
        "git_index_entries": prospective_entries,
        "git_index_identity": (
            _git_index_identity_from_entries(paths=paths, entries=prospective_entries) if prospective_entries is not None else None
        ),
        "git_identity_role": "optional-source-checkout-acceleration",
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
    expected_entries = payload.get("git_index_entries")
    expected_identity = payload.get("git_index_identity")
    expected_content_identity = payload.get("fingerprint")
    if (
        payload.get("kind") != "generated-cli-source-manifest/v1"
        or not isinstance(paths, list)
        or not all(isinstance(path, str) for path in paths)
        or not isinstance(expected_content_identity, str)
        or not expected_content_identity
    ):
        return {"status": "invalid", "reason": "invalid-manifest", "auxiliary_witness": "not-evaluated"}
    current_paths = [_repo_relative(path, repo_root=repo_root) for path in _fingerprint_files(repo_root=repo_root)]
    if current_paths != paths:
        return {"status": "stale", "reason": "semantic-path-set-drift", "auxiliary_witness": "not-evaluated"}
    current_entries = _git_index_entries(repo_root=repo_root, paths=paths)
    expected_entries_valid = (
        isinstance(expected_entries, dict)
        and set(expected_entries) == set(paths)
        and all(isinstance(entry, str) and entry for entry in expected_entries.values())
    )
    expected_identity_valid = isinstance(expected_identity, str) and bool(expected_identity)
    inputs_unmodified = current_entries is not None and _git_input_paths_are_unmodified(repo_root=repo_root, paths=paths)
    if (
        current_entries is not None
        and expected_entries_valid
        and expected_identity_valid
        and inputs_unmodified
        and current_entries == expected_entries
        and _git_index_identity_from_entries(paths=paths, entries=current_entries) == expected_identity
    ):
        return {"status": "current", "reason": "git-index-fast-path", "auxiliary_witness": "match"}

    if current_entries is None:
        auxiliary_witness = "unavailable"
    elif not expected_entries_valid or not expected_identity_valid:
        auxiliary_witness = "invalid"
    elif not inputs_unmodified:
        auxiliary_witness = "dirty-inputs"
    else:
        auxiliary_witness = "mismatch"
    current_content_identity = compute_generated_cli_fingerprint(repo_root=repo_root).get("fingerprint")
    if current_content_identity == expected_content_identity:
        return {"status": "current", "reason": "semantic-fallback", "auxiliary_witness": auxiliary_witness}
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


def _editable_distribution_origin(distribution: importlib.metadata.Distribution) -> Path | None:
    raw = distribution.read_text("direct_url.json")
    if not raw:
        return None
    try:
        direct_url = json.loads(raw)
    except json.JSONDecodeError:
        return None
    dir_info = direct_url.get("dir_info") if isinstance(direct_url, dict) else None
    if not isinstance(dir_info, dict) or not bool(dir_info.get("editable")):
        return None
    parsed = urlparse(str(direct_url.get("url") or ""))
    if parsed.scheme != "file":
        return None
    path_text = unquote(parsed.path)
    if os.name == "nt" and re.match(r"^/[A-Za-z]:/", path_text):
        path_text = path_text[1:]
    return Path(path_text).resolve()


def runtime_identity_admission(
    *,
    repo_root: Path = REPO_ROOT,
    distribution_lookup: Callable[[str], importlib.metadata.Distribution] = importlib.metadata.distribution,
) -> dict[str, object]:
    target_root = repo_root.resolve()
    observed: list[dict[str, str]] = []
    mismatches: list[dict[str, str]] = []
    for name, relative_expected in RUNTIME_DISTRIBUTION_PATHS.items():
        try:
            distribution = distribution_lookup(name)
        except importlib.metadata.PackageNotFoundError:
            continue
        origin = _editable_distribution_origin(distribution)
        if origin is None:
            continue
        expected = (target_root / relative_expected).resolve()
        item = {"distribution": name, "origin": origin.as_posix(), "expected": expected.as_posix()}
        observed.append(item)
        if origin != expected:
            mismatches.append(item)
    status = "mismatch" if mismatches else "matched" if observed else "no-editable-runtime"
    return {
        "kind": "agentic-workspace/runtime-identity/v1",
        "status": status,
        "target_root": target_root.as_posix(),
        "executable": Path(sys.executable).resolve().as_posix(),
        "environment": Path(os.environ["VIRTUAL_ENV"]).resolve().as_posix() if os.environ.get("VIRTUAL_ENV") else "",
        "editable_distributions": observed,
        "mismatches": mismatches,
    }


def _admit_runtime_identity() -> bool:
    identity = runtime_identity_admission()
    os.environ["AW_RUNTIME_IDENTITY"] = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    if identity["status"] != "mismatch":
        return True
    recovery = f'uv run --project "{REPO_ROOT.as_posix()}" --no-sync python scripts/run_agentic_workspace.py'
    print("Agentic Workspace refused a runtime from another checkout before command effects.", file=sys.stderr)
    print(f"Runtime identity: {json.dumps(identity, sort_keys=True)}", file=sys.stderr)
    print(f"Recovery: {recovery} <command arguments>", file=sys.stderr)
    return False


def _should_refresh_generated_cli_for_argv(argv: Sequence[str]) -> bool:
    if os.environ.get("AW_SKIP_GENERATED_CLI_REFRESH") == "1":
        return False
    if os.environ.get("AW_FORCE_GENERATED_CLI_REFRESH") == "1":
        return True
    args = [arg for arg in argv if arg != "--"]
    return not args or args[0] != "start"


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not _admit_runtime_identity():
        return 2
    if _should_refresh_generated_cli_for_argv(args):
        ensure_generated_cli_current()
    return _dispatch_to_source_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
