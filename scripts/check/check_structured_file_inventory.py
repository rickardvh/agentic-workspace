from __future__ import annotations

import argparse
import fnmatch
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import exceptions as jsonschema_exceptions

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_RELATIVE_PATH = Path("src/agentic_workspace/contracts/structured_file_inventory.json")
SCHEMA_RELATIVE_PATH = Path("src/agentic_workspace/contracts/schemas/structured_file_inventory.schema.json")
INVENTORY_PATH = REPO_ROOT / INVENTORY_RELATIVE_PATH
SCHEMA_PATH = REPO_ROOT / SCHEMA_RELATIVE_PATH
STRUCTURED_SUFFIXES = frozenset({".json", ".toml", ".yaml", ".yml"})
GENERATED_MIRROR_REQUIRED_PATHS = frozenset(
    {
        "tools/agent-manifest.json",
        "tools/AGENT_QUICKSTART.md",
        "tools/AGENT_ROUTING.md",
        ".agentic-workspace/planning/agent-manifest.json",
        "packages/planning/bootstrap/.agentic-workspace/planning/agent-manifest.json",
    }
)
RECONSTRUCTABLE_CLASSES = frozenset(
    {
        "generated-required-adapter",
        "local-cache",
        "reconstructable-external-snapshot",
        "removable-duplicate",
    }
)
GUARDRAILED_CLASSES = frozenset({"reconstructable-external-snapshot", "historical-audit-distillation"})
SOURCE_CLASSES = frozenset({"source-of-truth", "non-reconstructable-decision"})
REVIEW_AUDIT_CLASSIFICATION_THRESHOLD = 10
REVIEW_AUDIT_RETENTION_FIELDS = (
    "source retention rule",
    "distillation path",
    "reconstructable refs",
    "fields intentionally omitted",
)
FULL_INVENTORY_AUTHORITY_PATHS = frozenset(
    {
        "scripts/check/check_structured_file_inventory.py",
        "src/agentic_workspace/contracts/structured_file_inventory.json",
        "src/agentic_workspace/contracts/schemas/structured_file_inventory.schema.json",
    }
)


@dataclass(frozen=True)
class Finding:
    path: str
    message: str


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate tracked structured files against the checked inventory.")
    parser.add_argument(
        "--quiet-success",
        action="store_true",
        help="Emit a compact success message when the inventory covers every tracked structured file.",
    )
    parser.add_argument(
        "--changed",
        nargs="*",
        default=None,
        help=(
            "Validate only the listed changed paths unless an inventory authority path changed, in which case "
            "the checker escalates to the full audit."
        ),
    )
    parser.add_argument(
        "--base-ref",
        default="",
        help=(
            "With --changed, construct an isolated proof subject from this Git baseline plus the explicit changed paths. "
            "Inventory-authority changes still receive a broad audit without adopting unrelated live-worktree dirt."
        ),
    )
    return parser.parse_args(argv)


def _as_posix(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _structured_format(path: str) -> str | None:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix == ".json":
        return "json"
    if suffix == ".toml":
        return "toml"
    if suffix == ".yaml":
        return "yaml"
    if suffix == ".yml":
        return "yml"
    return None


def load_inventory(root: Path = REPO_ROOT) -> dict[str, Any]:
    return json.loads((root / INVENTORY_RELATIVE_PATH).read_text(encoding="utf-8"))


def load_schema(root: Path = REPO_ROOT) -> dict[str, Any]:
    return json.loads((root / SCHEMA_RELATIVE_PATH).read_text(encoding="utf-8"))


def validate_inventory_shape(inventory: dict[str, Any], root: Path = REPO_ROOT) -> list[Finding]:
    schema = load_schema(root)
    errors = sorted(Draft202012Validator(schema).iter_errors(inventory), key=lambda error: list(error.path))
    findings: list[Finding] = []
    for error in errors:
        location = ".".join(str(part) for part in error.path) or "<root>"
        findings.append(Finding(path=INVENTORY_PATH.relative_to(REPO_ROOT).as_posix(), message=f"{location}: {error.message}"))
    return findings


def _tracked_files(root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_paths = (_as_posix(line.strip()) for line in result.stdout.splitlines() if line.strip())
    return sorted(path for path in tracked_paths if (root / path).exists() or (root / path).is_symlink())


def staged_index_precondition_findings(root: Path = REPO_ROOT) -> list[Finding]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    findings: list[Finding] = []
    for record in result.stdout.split("\0"):
        if len(record) < 4:
            continue
        index_status = record[0]
        worktree_status = record[1]
        path = _as_posix(record[3:])
        if index_status == " " and worktree_status == "D" and _structured_format(path) is not None:
            findings.append(
                Finding(
                    path=path,
                    message=(
                        "structured file deletion or rename is not staged; run `git add -A` before broad structured-file proof "
                        "so git-index-backed inventory checks see the intended file set"
                    ),
                )
            )
    return findings


def tracked_structured_files(root: Path = REPO_ROOT) -> list[str]:
    files = _tracked_files(root)
    return sorted(path for path in files if PurePosixPath(path).suffix.lower() in STRUCTURED_SUFFIXES)


def _entry_matches(path: str, entry: dict[str, Any]) -> bool:
    if _structured_format(path) != entry["format"]:
        return False
    return _match_path_pattern(path, entry["pattern"])


def _match_path_pattern(path: str, pattern: str) -> bool:
    path_parts = tuple(_as_posix(path).split("/"))
    pattern_parts = tuple(_as_posix(pattern).split("/"))
    return _match_parts(path_parts, pattern_parts)


@lru_cache(maxsize=262_144)
def _match_parts(path_parts: tuple[str, ...], pattern_parts: tuple[str, ...]) -> bool:
    if not pattern_parts:
        return not path_parts
    pattern = pattern_parts[0]
    if pattern == "**":
        return any(_match_parts(path_parts[index:], pattern_parts[1:]) for index in range(len(path_parts) + 1))
    if not path_parts:
        return False
    if not fnmatch.fnmatchcase(path_parts[0], pattern):
        return False
    return _match_parts(path_parts[1:], pattern_parts[1:])


def unmatched_structured_files(paths: list[str], inventory: dict[str, Any]) -> list[Finding]:
    entries = inventory["entries"]
    findings: list[Finding] = []
    for path in sorted(_as_posix(item) for item in paths):
        if _structured_format(path) is None:
            continue
        if not any(_entry_matches(path, entry) for entry in entries):
            findings.append(
                Finding(
                    path=path,
                    message=(
                        "tracked structured file is not classified; add it to "
                        "src/agentic_workspace/contracts/structured_file_inventory.json"
                    ),
                )
            )
    return findings


def _matched_files(paths: list[str], entry: dict[str, Any]) -> list[str]:
    return sorted(path for path in paths if _entry_matches(path, entry))


def _generated_mirror_matches(path: str, mirror: dict[str, Any]) -> bool:
    return _match_path_pattern(path, mirror["pattern"])


def _json_item_count(path: Path) -> int | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("items", "entries", "records", "issue_classifications", "findings"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    return None


def _review_audit_retention_findings(path: str, payload: dict[str, Any]) -> list[Finding]:
    if payload.get("kind") != "planning-review/v1":
        return []
    issue_classifications = payload.get("issue_classifications")
    if not isinstance(issue_classifications, list) or len(issue_classifications) <= REVIEW_AUDIT_CLASSIFICATION_THRESHOLD:
        return []
    retention = payload.get("retention")
    if not isinstance(retention, dict):
        return [
            Finding(
                path=path,
                message=(
                    "large review/audit records must include retention metadata with source refs and a "
                    "distillation path instead of copied source history"
                ),
            )
        ]
    missing = [field for field in REVIEW_AUDIT_RETENTION_FIELDS if not retention.get(field)]
    if missing:
        return [
            Finding(
                path=path,
                message=f"large review/audit record is missing retention fields: {', '.join(missing)}",
            )
        ]
    return []


def _guardrail_findings(paths: list[str], entry: dict[str, Any], *, root: Path = REPO_ROOT) -> list[Finding]:
    guardrails = entry.get("guardrails")
    if not isinstance(guardrails, dict):
        return []
    findings: list[Finding] = []
    for path in _matched_files(paths, entry):
        full_path = root / path
        max_bytes = guardrails.get("max_bytes")
        if isinstance(max_bytes, int) and full_path.exists() and full_path.stat().st_size > max_bytes:
            findings.append(
                Finding(
                    path=path,
                    message=f"file exceeds storage guardrail max_bytes={max_bytes}",
                )
            )
        max_items = guardrails.get("max_items")
        if isinstance(max_items, int) and _structured_format(path) == "json":
            item_count = _json_item_count(full_path)
            if item_count is not None and item_count > max_items:
                findings.append(
                    Finding(
                        path=path,
                        message=f"file exceeds storage guardrail max_items={max_items}",
                    )
                )
        if _structured_format(path) == "json":
            try:
                payload = json.loads(full_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict):
                findings.extend(_review_audit_retention_findings(path, payload))
    return findings


def _load_json_file(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except OSError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc.msg}"


@lru_cache(maxsize=None)
def _load_schema_validator(schema_path: str) -> tuple[Draft202012Validator | None, str | None, str | None]:
    schema_payload, schema_error = _load_json_file(REPO_ROOT / schema_path)
    if schema_error is not None:
        return None, schema_error, None
    try:
        Draft202012Validator.check_schema(schema_payload)
    except jsonschema_exceptions.SchemaError as exc:
        return None, None, _schema_error_message(exc)
    return Draft202012Validator(schema_payload), None, None


def _schema_error_message(error: jsonschema_exceptions.ValidationError | jsonschema_exceptions.SchemaError) -> str:
    location = ".".join(str(part) for part in error.path) or "<root>"
    return f"{location}: {error.message}"


def _is_draft_schema_claim(claim: str) -> bool:
    return "JSON Schema draft 2020-12" in claim


def _explicit_schema_path(claim: str) -> str | None:
    normalized = _as_posix(claim.strip())
    if normalized.endswith(".schema.json") and " " not in normalized:
        return normalized
    return None


def _known_delegated_validator_claim(claim: str) -> bool:
    executable_markers = (
        "scripts/check/",
        "_typed_validator_findings",
        "validator",
        "check",
        "doctor",
        "verification",
        "discovery",
        "parser",
        "pre-commit",
        "uv/build-backend",
        "agentic-workspace",
        "runtime",
    )
    return any(marker in claim for marker in executable_markers)


def _validate_against_schema(path: str, schema_path: str, root: Path) -> list[Finding]:
    if root != REPO_ROOT:
        schema_payload, schema_error = _load_json_file(root / schema_path)
        if schema_error is not None:
            return [Finding(path=path, message=f"schema claim is not executable; cannot load {schema_path}: {schema_error}")]
        try:
            Draft202012Validator.check_schema(schema_payload)
        except jsonschema_exceptions.SchemaError as exc:
            return [Finding(path=schema_path, message=f"declared schema is invalid: {_schema_error_message(exc)}")]
        validator = Draft202012Validator(schema_payload)
    else:
        validator, load_error, schema_error = _load_schema_validator(schema_path)
        if load_error is not None:
            return [Finding(path=path, message=f"schema claim is not executable; cannot load {schema_path}: {load_error}")]
        if schema_error is not None or validator is None:
            return [Finding(path=schema_path, message=f"declared schema is invalid: {schema_error}")]

    payload, payload_error = _load_json_file(root / path)
    if payload_error is not None:
        return [Finding(path=path, message=f"schema-backed file cannot be loaded for validation: {payload_error}")]
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        return [
            Finding(
                path=path,
                message=f"does not validate against {schema_path}: {_schema_error_message(errors[0])}",
            )
        ]
    return []


def _validate_schema_payload(path: str, root: Path) -> list[Finding]:
    payload, payload_error = _load_json_file(root / path)
    if payload_error is not None:
        return [Finding(path=path, message=f"schema-backed draft schema cannot be loaded: {payload_error}")]
    try:
        Draft202012Validator.check_schema(payload)
    except jsonschema_exceptions.SchemaError as exc:
        return [Finding(path=path, message=f"declared draft schema is invalid: {_schema_error_message(exc)}")]
    return []


def _validate_draft_schema_file(path: str, root: Path) -> list[Finding]:
    if root != REPO_ROOT:
        return _validate_schema_payload(path, root)
    validator, load_error, schema_error = _load_schema_validator(path)
    if load_error is not None:
        return [Finding(path=path, message=f"schema-backed draft schema cannot be loaded: {load_error}")]
    if schema_error is not None or validator is None:
        return [Finding(path=path, message=f"declared draft schema is invalid: {schema_error}")]
    return []


def claim_validation_findings(paths: list[str], inventory: dict[str, Any], root: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for index, entry in enumerate(inventory["entries"]):
        location = f"{INVENTORY_PATH.relative_to(REPO_ROOT).as_posix()}#entries[{index}]"
        status = entry["status"]
        claim = entry["schema_or_validator"]
        matched = _matched_files(paths, entry)
        if status == "schema-backed" and entry["format"] == "json" and matched:
            schema_path = _explicit_schema_path(claim)
            if schema_path is not None:
                for path in matched:
                    findings.extend(_validate_against_schema(path, schema_path, root))
            elif _is_draft_schema_claim(claim):
                for path in matched:
                    findings.extend(_validate_draft_schema_file(path, root))
            else:
                findings.append(
                    Finding(
                        path=location,
                        message="schema-backed JSON entries must use a repo-relative .schema.json path or JSON Schema draft 2020-12 claim",
                    )
                )
        if status == "typed-validator-backed" and not _known_delegated_validator_claim(claim):
            findings.append(
                Finding(
                    path=location,
                    message="typed-validator-backed entries must name an executable validator, checker, parser, doctor, or delegated runtime",
                )
            )
    return findings


def _entry_routes(entry: dict[str, Any]) -> set[str]:
    routes: set[str] = set()
    for key in ("routed_to", "storage_routed_to"):
        value = entry.get(key)
        if isinstance(value, str):
            routes.add(value)
    guardrails = entry.get("guardrails")
    if isinstance(guardrails, dict):
        guardrail_route = guardrails.get("routed_to")
        if isinstance(guardrail_route, str):
            routes.add(guardrail_route)
    return routes


def storage_policy_findings(paths: list[str], inventory: dict[str, Any], *, root: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    for index, entry in enumerate(inventory["entries"]):
        location = f"{INVENTORY_PATH.relative_to(REPO_ROOT).as_posix()}#entries[{index}]"
        storage_class = entry["storage_class"]
        if storage_class in RECONSTRUCTABLE_CLASSES and not entry.get("reconstructable_from"):
            findings.append(Finding(path=location, message=f"{storage_class} entries must declare reconstructable_from"))
        if storage_class in GUARDRAILED_CLASSES:
            guardrails = entry.get("guardrails")
            has_size_or_count = isinstance(guardrails, dict) and (
                isinstance(guardrails.get("max_items"), int) or isinstance(guardrails.get("max_bytes"), int)
            )
            if not has_size_or_count:
                findings.append(Finding(path=location, message=f"{storage_class} entries must declare max_items or max_bytes guardrails"))
        if storage_class == "generated-required-adapter":
            if not entry["generated"]:
                findings.append(Finding(path=location, message="generated-required-adapter entries must set generated=true"))
            if entry["status"] not in {"generated-derived", "typed-validator-backed", "schema-backed"}:
                findings.append(
                    Finding(path=location, message="generated-required-adapter entries must be generated-derived or validator-backed")
                )
        routes = _entry_routes(entry)
        if storage_class == "local-cache" and not routes:
            findings.append(Finding(path=location, message="checked-in local-cache entries must be routed to a cleanup issue"))
        if storage_class in {"reconstructable-external-snapshot", "removable-duplicate"} and not routes:
            findings.append(Finding(path=location, message=f"{storage_class} entries must be routed to a cleanup issue"))
        if storage_class == "historical-audit-distillation" and not routes:
            findings.append(
                Finding(path=location, message="historical-audit-distillation entries must route oversized audit compression work")
            )
        if storage_class in SOURCE_CLASSES and entry["generated"]:
            findings.append(Finding(path=location, message=f"{storage_class} entries must not be marked generated"))
        findings.extend(_guardrail_findings(paths, entry, root=root))
    return findings


BRANCH_COLLECTION_KEYS = frozenset({"items", "entries", "records", "scopes", "observations", "evaluations", "findings"})


def merge_safety_findings(paths: list[str], inventory: dict[str, Any], *, root: Path = REPO_ROOT) -> list[Finding]:
    """Require merge-order classification for branch-carried collection state."""

    findings: list[Finding] = []
    for index, entry in enumerate(inventory["entries"]):
        policy = entry.get("merge_safety")
        location = f"{INVENTORY_PATH.relative_to(REPO_ROOT).as_posix()}#entries[{index}]"
        pattern = str(entry.get("pattern") or "")
        matched = _matched_files(paths, entry)
        relevant = pattern.endswith("/.agentic-workspace-cli-fingerprint.json")
        if entry.get("editable_by_agents") and pattern.startswith(".agentic-workspace/"):
            for path in matched:
                payload, error = _load_json_file(root / path)
                if error is None and isinstance(payload, dict) and any(isinstance(payload.get(key), list) for key in BRANCH_COLLECTION_KEYS):
                    relevant = True
                    break
        if relevant and not isinstance(policy, dict):
            findings.append(
                Finding(
                    path=location,
                    message="branch-carried collection/generated state must declare merge_safety classification, owner_boundary, and reason",
                )
            )
            continue
        if not isinstance(policy, dict):
            continue
        classification = policy.get("classification")
        if classification == "owner-scoped" and not any(token in pattern for token in ("*", "?", "[")):
            findings.append(
                Finding(path=location, message="owner-scoped merge safety requires a path pattern containing an owner selector")
            )
        if classification == "derived" and (not entry.get("generated") or not entry.get("reconstructable_from")):
            findings.append(Finding(path=location, message="derived merge safety requires generated=true and reconstructable_from"))
        if classification == "true-singleton" and any(token in pattern for token in ("*", "?", "[")):
            findings.append(Finding(path=location, message="true-singleton merge safety requires one exact path"))
    return findings


def generated_mirror_policy_findings(
    paths: list[str], inventory: dict[str, Any], *, root: Path = REPO_ROOT
) -> list[Finding]:
    mirrors = inventory.get("generated_mirrors", [])
    findings: list[Finding] = []
    if not isinstance(mirrors, list):
        return [Finding(path=INVENTORY_PATH.relative_to(REPO_ROOT).as_posix(), message="generated_mirrors must be a list")]

    covered_paths: set[str] = set()
    for index, mirror in enumerate(mirrors):
        location = f"{INVENTORY_PATH.relative_to(REPO_ROOT).as_posix()}#generated_mirrors[{index}]"
        matched = [path for path in paths if _generated_mirror_matches(path, mirror)]
        if not matched:
            findings.append(Finding(path=location, message="generated mirror declaration matches no tracked file"))
            continue
        route = str(mirror.get("ordinary_agent_route", ""))
        pattern = str(mirror.get("pattern", ""))
        if pattern.startswith("generated/") and "drill-down only" not in route:
            findings.append(Finding(path=location, message="generated mirror ordinary_agent_route must be explicit drill-down only"))
        if "plugins/" in pattern and "plugin/catalogue drill-down only" not in route:
            findings.append(Finding(path=location, message="generated plugin mirror route must be plugin/catalogue drill-down only"))
        covered_paths.update(matched)
        max_bytes = mirror.get("max_bytes")
        if isinstance(max_bytes, int):
            for path in matched:
                full_path = root / path
                if full_path.exists() and full_path.stat().st_size > max_bytes:
                    findings.append(Finding(path=path, message=f"generated mirror exceeds max_bytes={max_bytes}"))

    tracked_required_paths = GENERATED_MIRROR_REQUIRED_PATHS.intersection(paths)
    missing_required = sorted(path for path in tracked_required_paths if path not in covered_paths)
    findings.extend(
        Finding(path=path, message="generated mirror must declare source command, named consumer, freshness check, and demotion path")
        for path in missing_required
    )

    structured_generated_paths: set[str] = set()
    for entry in inventory["entries"]:
        if entry["storage_class"] != "generated-required-adapter":
            continue
        structured_generated_paths.update(_matched_files(paths, entry))
    missing_structured = sorted(
        path for path in structured_generated_paths if path not in covered_paths and path not in tracked_required_paths
    )
    findings.extend(
        Finding(path=path, message="generated-required-adapter inventory entry needs matching generated_mirrors metadata")
        for path in missing_structured
    )
    return findings


def _normalize_changed_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for path in paths:
        value = _as_posix(str(path).strip())
        if not value:
            continue
        if value not in normalized:
            normalized.append(value)
    return normalized


def _requires_full_inventory_audit(paths: list[str]) -> bool:
    changed = set(_normalize_changed_paths(paths))
    return bool(changed.intersection(FULL_INVENTORY_AUTHORITY_PATHS))


def _git_tree_files(base_ref: str, *, root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", base_ref],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return sorted(_as_posix(path.decode("utf-8")) for path in result.stdout.split(b"\0") if path)


def _patch_subject_paths(*, base_ref: str, changed_paths: list[str], root: Path = REPO_ROOT) -> list[str]:
    subject_paths = set(_git_tree_files(base_ref, root=root))
    for path in _normalize_changed_paths(changed_paths):
        source = root / path
        if source.is_file() or source.is_symlink():
            subject_paths.add(path)
        else:
            subject_paths.discard(path)
    return sorted(subject_paths)


def _safe_subject_path(subject_root: Path, path: str) -> Path:
    candidate = (subject_root / _as_posix(path)).resolve()
    if not candidate.is_relative_to(subject_root.resolve()):
        raise ValueError(f"patch subject path escapes repository root: {path}")
    return candidate


@contextmanager
def isolated_patch_subject(
    *, base_ref: str, changed_paths: list[str], root: Path = REPO_ROOT
) -> Iterator[tuple[Path, list[str]]]:
    archive = subprocess.run(
        ["git", "archive", "--format=tar", base_ref],
        cwd=root,
        check=True,
        capture_output=True,
    )
    with tempfile.TemporaryDirectory(prefix="aw-structured-patch-") as temporary:
        subject_root = Path(temporary).resolve()
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as payload:
            members = payload.getmembers()
            for member in members:
                _safe_subject_path(subject_root, member.name)
            payload.extractall(subject_root, members=members, filter="fully_trusted")
        for path in _normalize_changed_paths(changed_paths):
            source = root / path
            destination = _safe_subject_path(subject_root, path)
            if source.is_symlink():
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.unlink(missing_ok=True)
                destination.symlink_to(source.readlink())
            elif source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            elif destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink(missing_ok=True)
        yield subject_root, _patch_subject_paths(base_ref=base_ref, changed_paths=changed_paths, root=root)


def ambient_structured_state_findings(paths: list[str], *, root: Path = REPO_ROOT) -> list[Finding]:
    proposed = set(_normalize_changed_paths(paths))
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    findings: list[Finding] = []
    records = result.stdout.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        status = record[:2]
        candidates = [_as_posix(record[3:])]
        if "R" in status or "C" in status:
            if index < len(records) and records[index]:
                candidates.append(_as_posix(records[index]))
                index += 1
        for path in candidates:
            if path in proposed or _structured_format(path) is None:
                continue
            findings.append(
                Finding(
                    path=path,
                    message=f"ambient checkout state {status!r} is visible but excluded from the explicit patch proof subject",
                )
            )
    return findings


def inventory_findings(
    paths: list[str] | None = None,
    *,
    all_paths: list[str] | None = None,
    enforce_staged_precondition: bool = True,
    root: Path = REPO_ROOT,
) -> list[Finding]:
    inventory = load_inventory(root)
    findings = validate_inventory_shape(inventory, root)
    if findings:
        return findings
    if paths is None and enforce_staged_precondition:
        precondition_findings = staged_index_precondition_findings(root)
        if precondition_findings:
            return precondition_findings
    checked_paths = tracked_structured_files(root) if paths is None else paths
    checked_all_paths = _tracked_files(root) if all_paths is None and paths is None else all_paths if all_paths is not None else checked_paths
    return (
        unmatched_structured_files(checked_paths, inventory)
        + claim_validation_findings(checked_paths, inventory, root=root)
        + storage_policy_findings(checked_paths, inventory, root=root)
        + merge_safety_findings(checked_all_paths, inventory, root=root)
        + generated_mirror_policy_findings(checked_all_paths, inventory, root=root)
    )


def changed_path_inventory_findings(
    paths: list[str], *, base_ref: str = "", root: Path = REPO_ROOT
) -> list[Finding]:
    changed_paths = _normalize_changed_paths(paths)
    if _requires_full_inventory_audit(changed_paths):
        if base_ref:
            with isolated_patch_subject(base_ref=base_ref, changed_paths=changed_paths, root=root) as (subject_root, subject_paths):
                structured_paths = [path for path in subject_paths if _structured_format(path) is not None]
                return inventory_findings(
                    paths=structured_paths,
                    all_paths=subject_paths,
                    enforce_staged_precondition=False,
                    root=subject_root,
                )
        return inventory_findings(root=root)
    changed_structured = [path for path in changed_paths if _structured_format(path) is not None]
    tracked_paths = _tracked_files(root)
    all_paths = sorted(set(tracked_paths).union(changed_structured))
    return inventory_findings(paths=changed_structured, all_paths=all_paths, enforce_staged_precondition=False, root=root)


def routed_storage_cleanup_issues(inventory: dict[str, Any]) -> set[str]:
    routed: set[str] = set()
    for entry in inventory["entries"]:
        routed.update(_entry_routes(entry))
    return routed


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.base_ref and args.changed is None:
        print("--base-ref requires --changed so the proposed patch subject is explicit", file=sys.stderr)
        return 2
    findings = (
        changed_path_inventory_findings(args.changed, base_ref=args.base_ref)
        if args.changed is not None
        else inventory_findings()
    )
    ambient = ambient_structured_state_findings(args.changed) if args.base_ref and args.changed is not None else []
    if findings:
        print("Structured file inventory check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.path}: {finding.message}", file=sys.stderr)
        if ambient:
            print("Ambient structured checkout state (excluded from this patch proof):", file=sys.stderr)
            for finding in ambient:
                print(f"- {finding.path}: {finding.message}", file=sys.stderr)
        return 1
    if ambient:
        print("Ambient structured checkout state (excluded from this patch proof):", file=sys.stderr)
        for finding in ambient:
            print(f"- {finding.path}: {finding.message}", file=sys.stderr)
    if args.quiet_success:
        print("Structured file inventory check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
