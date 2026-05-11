from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import exceptions as jsonschema_exceptions

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "structured_file_inventory.json"
SCHEMA_PATH = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "schemas" / "structured_file_inventory.schema.json"
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


def load_inventory() -> dict[str, Any]:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_inventory_shape(inventory: dict[str, Any]) -> list[Finding]:
    schema = load_schema()
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
    return sorted(_as_posix(line.strip()) for line in result.stdout.splitlines() if line.strip())


def tracked_structured_files(root: Path = REPO_ROOT) -> list[str]:
    files = _tracked_files(root)
    return sorted(path for path in files if PurePosixPath(path).suffix.lower() in STRUCTURED_SUFFIXES)


def _entry_matches(path: str, entry: dict[str, Any]) -> bool:
    if _structured_format(path) != entry["format"]:
        return False
    return _match_path_pattern(path, entry["pattern"])


def _match_path_pattern(path: str, pattern: str) -> bool:
    path_parts = _as_posix(path).split("/")
    pattern_parts = _as_posix(pattern).split("/")
    return _match_parts(path_parts, pattern_parts)


def _match_parts(path_parts: list[str], pattern_parts: list[str]) -> bool:
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


def _guardrail_findings(paths: list[str], entry: dict[str, Any]) -> list[Finding]:
    guardrails = entry.get("guardrails")
    if not isinstance(guardrails, dict):
        return []
    findings: list[Finding] = []
    for path in _matched_files(paths, entry):
        full_path = REPO_ROOT / path
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
    schema_payload, schema_error = _load_json_file(root / schema_path)
    if schema_error is not None:
        return [Finding(path=path, message=f"schema claim is not executable; cannot load {schema_path}: {schema_error}")]
    try:
        Draft202012Validator.check_schema(schema_payload)
    except jsonschema_exceptions.SchemaError as exc:
        return [Finding(path=schema_path, message=f"declared schema is invalid: {_schema_error_message(exc)}")]

    payload, payload_error = _load_json_file(root / path)
    if payload_error is not None:
        return [Finding(path=path, message=f"schema-backed file cannot be loaded for validation: {payload_error}")]
    errors = sorted(Draft202012Validator(schema_payload).iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        return [
            Finding(
                path=path,
                message=f"does not validate against {schema_path}: {_schema_error_message(errors[0])}",
            )
        ]
    return []


def _validate_draft_schema_file(path: str, root: Path) -> list[Finding]:
    payload, payload_error = _load_json_file(root / path)
    if payload_error is not None:
        return [Finding(path=path, message=f"schema-backed draft schema cannot be loaded: {payload_error}")]
    try:
        Draft202012Validator.check_schema(payload)
    except jsonschema_exceptions.SchemaError as exc:
        return [Finding(path=path, message=f"declared draft schema is invalid: {_schema_error_message(exc)}")]
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


def storage_policy_findings(paths: list[str], inventory: dict[str, Any]) -> list[Finding]:
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
                findings.append(Finding(path=location, message="generated-required-adapter entries must be generated-derived or validator-backed"))
        routes = _entry_routes(entry)
        if storage_class == "local-cache" and not routes:
            findings.append(Finding(path=location, message="checked-in local-cache entries must be routed to a cleanup issue"))
        if storage_class in {"reconstructable-external-snapshot", "removable-duplicate"} and not routes:
            findings.append(Finding(path=location, message=f"{storage_class} entries must be routed to a cleanup issue"))
        if storage_class == "historical-audit-distillation" and not routes:
            findings.append(Finding(path=location, message="historical-audit-distillation entries must route oversized audit compression work"))
        if storage_class in SOURCE_CLASSES and entry["generated"]:
            findings.append(Finding(path=location, message=f"{storage_class} entries must not be marked generated"))
        findings.extend(_guardrail_findings(paths, entry))
    return findings


def generated_mirror_policy_findings(paths: list[str], inventory: dict[str, Any]) -> list[Finding]:
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
        covered_paths.update(matched)
        max_bytes = mirror.get("max_bytes")
        if isinstance(max_bytes, int):
            for path in matched:
                full_path = REPO_ROOT / path
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
    missing_structured = sorted(path for path in structured_generated_paths if path not in covered_paths and path not in tracked_required_paths)
    findings.extend(
        Finding(path=path, message="generated-required-adapter inventory entry needs matching generated_mirrors metadata")
        for path in missing_structured
    )
    return findings


def inventory_findings(paths: list[str] | None = None) -> list[Finding]:
    inventory = load_inventory()
    findings = validate_inventory_shape(inventory)
    if findings:
        return findings
    checked_paths = tracked_structured_files() if paths is None else paths
    checked_all_paths = _tracked_files() if paths is None else checked_paths
    return (
        unmatched_structured_files(checked_paths, inventory)
        + claim_validation_findings(checked_paths, inventory)
        + storage_policy_findings(checked_paths, inventory)
        + generated_mirror_policy_findings(checked_all_paths, inventory)
    )


def routed_storage_cleanup_issues(inventory: dict[str, Any]) -> set[str]:
    routed: set[str] = set()
    for entry in inventory["entries"]:
        routed.update(_entry_routes(entry))
    return routed


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    findings = inventory_findings()
    if findings:
        print("Structured file inventory check failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding.path}: {finding.message}", file=sys.stderr)
        return 1
    if args.quiet_success:
        print("Structured file inventory check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
