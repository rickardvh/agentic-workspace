from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = REPO_ROOT / ".agentic-workspace" / "local" / "cache" / "generated-cli-fingerprint.json"
SOURCE_MANIFEST_NAME = ".agentic-workspace-cli-fingerprint.json"
GENERATOR_SCRIPT = REPO_ROOT / "scripts" / "generate" / "generate_command_packages.py"
CACHE_SCHEMA = "generated-cli-fingerprint/v1"
RUNTIME_DISTRIBUTION_PATHS = {
    "agentic-workspace": Path("."),
    "agentic-workspace-memory": Path("packages/memory"),
    "agentic-workspace-planning": Path("packages/planning"),
    "agentic-workspace-verification": Path("packages/verification"),
}
CODEX_SESSION_IDENTITY_ENV = "CODEX_THREAD_ID"
AW_SESSION_IDENTITY_ENV = "AW_SESSION_LOGICAL_IDENTITY"

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
)


def _command_package_manifest(*, repo_root: Path) -> dict[str, object]:
    ir_path = repo_root / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json"
    try:
        payload = json.loads(ir_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _package_operation_contract_paths(package: dict[str, object]) -> list[str]:
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

    root = str(package.get("operation_contract_root") or "").strip()
    for command in package.get("commands", []):
        collect(command, root=root)
    return sorted(paths)


def _package_generation_owner(package: dict[str, object]) -> str:
    for target in package.get("targets", []):
        if not isinstance(target, dict):
            continue
        generated_root = Path(str(target.get("generated_root") or ""))
        if len(generated_root.parts) >= 2 and generated_root.parts[0] == "generated":
            return generated_root.parts[1]
    return str(package.get("id") or "").strip()


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _shared_generation_dependency_files(*, repo_root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for pattern in GENERATION_DEPENDENCY_PATTERNS:
        for path in repo_root.glob(pattern):
            if path.is_file() and "__pycache__" not in path.parts:
                relative = _repo_relative(path, repo_root=repo_root)
                files[relative] = path
    return files


def _generation_dependency_domains(*, repo_root: Path) -> dict[str, list[Path]]:
    shared = _shared_generation_dependency_files(repo_root=repo_root)
    domains: dict[str, list[Path]] = {}
    manifest = _command_package_manifest(repo_root=repo_root)
    for package in manifest.get("packages", []):
        if not isinstance(package, dict):
            continue
        owner = _package_generation_owner(package)
        if not owner:
            continue
        files = dict(shared)
        package_json = repo_root / "generated" / owner / "typescript" / "package.json"
        if package_json.is_file():
            files[_repo_relative(package_json, repo_root=repo_root)] = package_json
        for relative in _package_operation_contract_paths(package):
            path = repo_root / relative
            if path.is_file():
                files[relative] = path
        domains[owner] = [files[relative] for relative in sorted(files)]
    return dict(sorted(domains.items()))


def _fingerprint_files(*, repo_root: Path) -> list[Path]:
    files: dict[str, Path] = {}
    for domain_files in _generation_dependency_domains(repo_root=repo_root).values():
        for path in domain_files:
            files[_repo_relative(path, repo_root=repo_root)] = path
    return [files[relative] for relative in sorted(files)]


def _fingerprint_payload(*, repo_root: Path, files: list[Path]) -> dict[str, object]:
    digest = hashlib.sha256()
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


def compute_generated_cli_fingerprint(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    return _fingerprint_payload(repo_root=repo_root, files=_fingerprint_files(repo_root=repo_root))


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


def _git_index_identity(*, paths: list[str], entries: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(entries[path].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def source_cli_fingerprint_manifests(*, repo_root: Path = REPO_ROOT) -> dict[str, dict[str, object]]:
    """Build one transportable semantic receipt per generated package owner."""

    manifests: dict[str, dict[str, object]] = {}
    for owner, files in _generation_dependency_domains(repo_root=repo_root).items():
        content_identity = _fingerprint_payload(repo_root=repo_root, files=files)
        manifests[owner] = {
            **content_identity,
            "kind": "generated-cli-owner-source-manifest/v1",
            "owner": owner,
            "identity_role": "owner-scoped-semantic-content",
            "context_rule": (
                "This receipt contains shared generator inputs plus only this generated owner's operation contracts. "
                "Git checkout witnesses are derived locally and never carried across branches."
            ),
            "generation_command": "uv run python scripts/generate/generate_command_packages.py",
        }
    return manifests


def source_cli_fingerprint_manifest(*, repo_root: Path = REPO_ROOT, owner: str) -> dict[str, object]:
    return source_cli_fingerprint_manifests(repo_root=repo_root)[owner]


def source_cli_fingerprint_manifest_path(*, repo_root: Path, owner: str) -> Path:
    return repo_root / "generated" / owner / SOURCE_MANIFEST_NAME


def _source_cli_fingerprint_manifest_payload_status(
    *, repo_root: Path, owner: str, payload: dict[str, object]
) -> dict[str, str]:
    domains = _generation_dependency_domains(repo_root=repo_root)
    files = domains.get(owner)
    if files is None:
        return {"status": "stale", "reason": "owner-domain-drift", "auxiliary_witness": "not-evaluated"}
    paths = payload.get("file_paths")
    expected_content_identity = payload.get("fingerprint")
    if (
        payload.get("kind") != "generated-cli-owner-source-manifest/v1"
        or payload.get("owner") != owner
        or not isinstance(paths, list)
        or not all(isinstance(path, str) for path in paths)
        or not isinstance(expected_content_identity, str)
        or not expected_content_identity
    ):
        return {"status": "invalid", "reason": "invalid-manifest", "auxiliary_witness": "not-evaluated"}
    if "git_index_entries" in payload or "git_index_identity" in payload:
        return {"status": "invalid", "reason": "branch-carried-git-witness", "auxiliary_witness": "not-evaluated"}
    current_paths = [_repo_relative(path, repo_root=repo_root) for path in files]
    if current_paths != paths:
        return {"status": "stale", "reason": "semantic-path-set-drift", "auxiliary_witness": "not-evaluated"}
    current_entries = _git_index_entries(repo_root=repo_root, paths=paths)
    inputs_unmodified = current_entries is not None and _git_input_paths_are_unmodified(repo_root=repo_root, paths=paths)
    auxiliary_witness = "derived-clean-index" if inputs_unmodified else "unavailable" if current_entries is None else "dirty-inputs"
    current_content_identity = _fingerprint_payload(repo_root=repo_root, files=files).get("fingerprint")
    if current_content_identity == expected_content_identity:
        return {"status": "current", "reason": "semantic-content-match", "auxiliary_witness": auxiliary_witness}
    return {"status": "stale", "reason": "semantic-content-drift", "auxiliary_witness": auxiliary_witness}


def source_cli_fingerprint_manifest_status(
    *,
    repo_root: Path = REPO_ROOT,
    manifest_path: Path | None = None,
) -> dict[str, str]:
    """Classify source-manifest freshness with semantic content as authority."""

    if manifest_path is not None:
        payload = _read_cached_fingerprint_payload(cache_path=manifest_path)
        if payload is None:
            return {"status": "invalid", "reason": "invalid-manifest", "auxiliary_witness": "not-evaluated"}
        owner = str(payload.get("owner") or manifest_path.parent.name)
        return _source_cli_fingerprint_manifest_payload_status(repo_root=repo_root, owner=owner, payload=payload)
    manifests = source_cli_fingerprint_manifests(repo_root=repo_root)
    if not manifests:
        return {"status": "invalid", "reason": "no-owner-domains", "auxiliary_witness": "not-evaluated"}
    actual_owners = {
        path.parent.name for path in (repo_root / "generated").glob(f"*/{SOURCE_MANIFEST_NAME}") if path.is_file()
    }
    if actual_owners != set(manifests):
        return {"status": "stale", "reason": "owner-manifest-set-drift", "auxiliary_witness": "not-evaluated"}
    statuses = []
    for owner in manifests:
        path = source_cli_fingerprint_manifest_path(repo_root=repo_root, owner=owner)
        payload = _read_cached_fingerprint_payload(cache_path=path)
        if payload is None:
            return {"status": "invalid", "reason": f"missing-owner-manifest:{owner}", "auxiliary_witness": "not-evaluated"}
        status = _source_cli_fingerprint_manifest_payload_status(repo_root=repo_root, owner=owner, payload=payload)
        if status["status"] != "current":
            return {**status, "reason": f"{owner}:{status['reason']}"}
        statuses.append(status)
    witnesses = {status["auxiliary_witness"] for status in statuses}
    witness = witnesses.pop() if len(witnesses) == 1 else "mixed"
    return {"status": "current", "reason": "owner-manifests-current", "auxiliary_witness": witness}


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
    current_paths = [_repo_relative(path, repo_root=repo_root) for path in _fingerprint_files(repo_root=repo_root)]
    if current_paths != cached_paths:
        return False
    cached_git_identity = payload.get("local_git_index_identity")
    if not isinstance(cached_git_identity, str) or not cached_git_identity:
        return False
    entries = _git_index_entries(repo_root=repo_root, paths=current_paths)
    return bool(
        entries is not None
        and _git_input_paths_are_unmodified(repo_root=repo_root, paths=current_paths)
        and _git_index_identity(paths=current_paths, entries=entries) == cached_git_identity
    )


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
    repo_root: Path = REPO_ROOT,
    replace_path: Callable[[Path, Path], object] | None = None,
    sleep: Callable[[float], object] = time.sleep,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    paths = fingerprint.get("file_paths")
    normalized_paths = [str(path) for path in paths] if isinstance(paths, list) else []
    entries = _git_index_entries(repo_root=repo_root, paths=normalized_paths)
    local_git_identity = None
    if (
        entries is not None
        and set(normalized_paths).issubset(entries)
        and _git_input_paths_are_unmodified(repo_root=repo_root, paths=normalized_paths)
    ):
        local_git_identity = _git_index_identity(paths=normalized_paths, entries=entries)
    payload = {
        **fingerprint,
        "local_git_index_identity": local_git_identity,
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
        _write_cached_fingerprint(compute_generated_cli_fingerprint(repo_root=repo_root), cache_path=effective_cache, repo_root=repo_root)
        return False
    before = compute_generated_cli_fingerprint(repo_root=repo_root)
    cached = _read_cached_fingerprint(cache_path=effective_cache)
    if not force and cached == before["fingerprint"]:
        return False

    runner = run_generator or (lambda root, generator: _default_run_generator(repo_root=root, generator_script=generator))
    runner(repo_root, effective_generator)
    after = compute_generated_cli_fingerprint(repo_root=repo_root)
    _write_cached_fingerprint(after, cache_path=effective_cache, repo_root=repo_root)
    return True


def _powershell_command(parts: Sequence[str]) -> str:
    def quote(part: str) -> str:
        return part if re.fullmatch(r"[A-Za-z0-9_./:-]+", part) else "'" + part.replace("'", "''") + "'"

    return " ".join(quote(part) for part in parts)


def _missing_runtime_dependency_result(*, missing_module: str, argv: Sequence[str]) -> int:
    sync_argv = ["uv", "sync", "--frozen", "--project", REPO_ROOT.as_posix()]
    retry_argv = [
        "uv",
        "run",
        "--project",
        REPO_ROOT.as_posix(),
        "--frozen",
        "--active",
        "--no-sync",
        "python",
        "scripts/run_agentic_workspace.py",
        *argv,
    ]
    payload = {
        "kind": "agentic-workspace/source-runtime-recovery/v1",
        "outcome": "blocked",
        "reason_code": "unsynchronized-source-runtime",
        "missing_module": missing_module,
        "message": "The source-checkout runtime is missing a required dependency; synchronize this checkout before retrying.",
        "recovery_command": _powershell_command(sync_argv),
        "recovery_argv": sync_argv,
        "retry_command": _powershell_command(retry_argv),
        "retry_argv": retry_argv,
    }
    json_requested = any(
        arg == "--format=json" or (arg == "json" and index > 0 and argv[index - 1] == "--format")
        for index, arg in enumerate(argv)
    )
    if json_requested:
        print(json.dumps(payload, indent=2))
    else:
        print(payload["message"], file=sys.stderr)
        print(f"Missing module: {missing_module}", file=sys.stderr)
        print(f"Recovery: {payload['recovery_command']}", file=sys.stderr)
        print(f"Retry: {payload['retry_command']}", file=sys.stderr)
    return 2


def _dispatch_to_source_cli(argv: Sequence[str]) -> int:
    source_root = REPO_ROOT / "src"
    for path in (str(source_root), str(REPO_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    try:
        from agentic_workspace.cli import main as cli_main
    except ModuleNotFoundError as exc:
        missing_module = str(exc.name or "").strip()
        if not missing_module or missing_module == "agentic_workspace" or missing_module.startswith("agentic_workspace."):
            raise
        return _missing_runtime_dependency_result(missing_module=missing_module, argv=argv)

    return int(cli_main(list(argv)))


def _bridge_codex_session_identity() -> bool:
    """Map Codex's opaque thread identity into AW's portable session contract."""

    if os.environ.get(AW_SESSION_IDENTITY_ENV, "").strip():
        return False
    codex_identity = os.environ.get(CODEX_SESSION_IDENTITY_ENV, "").strip()
    if not codex_identity:
        return False
    os.environ[AW_SESSION_IDENTITY_ENV] = codex_identity
    return True


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


def _source_distribution_version(*, repo_root: Path, relative_project: Path) -> str | None:
    pyproject_path = repo_root / relative_project / "pyproject.toml"
    try:
        document = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = document.get("project")
    if not isinstance(project, dict):
        return None
    version = project.get("version")
    return str(version).strip() if isinstance(version, str) and version.strip() else None


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
            continue
        source_version = _source_distribution_version(repo_root=target_root, relative_project=relative_expected)
        installed_version = str(getattr(distribution, "version", "") or "").strip()
        if source_version is not None and installed_version and installed_version != source_version:
            mismatches.append(
                {
                    **item,
                    "mismatch": "stale-editable-metadata",
                    "source_version": source_version,
                    "installed_version": installed_version,
                }
            )
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
    stale_metadata = any(
        mismatch.get("mismatch") == "stale-editable-metadata" for mismatch in identity.get("mismatches", [])
    )
    if stale_metadata:
        message = "Agentic Workspace refused stale editable distribution metadata before command effects."
        recovery = f'uv sync --frozen --project "{REPO_ROOT.as_posix()}"'
        recovery_suffix = ""
    else:
        message = "Agentic Workspace refused a runtime from another checkout before command effects."
        recovery = f'uv run --project "{REPO_ROOT.as_posix()}" --no-sync python scripts/run_agentic_workspace.py'
        recovery_suffix = " <command arguments>"
    print(message, file=sys.stderr)
    print(f"Runtime identity: {json.dumps(identity, sort_keys=True)}", file=sys.stderr)
    print(f"Recovery: {recovery}{recovery_suffix}", file=sys.stderr)
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
    _bridge_codex_session_identity()
    if not _admit_runtime_identity():
        return 2
    if _should_refresh_generated_cli_for_argv(args):
        ensure_generated_cli_current()
    return _dispatch_to_source_cli(args)


if __name__ == "__main__":
    raise SystemExit(main())
