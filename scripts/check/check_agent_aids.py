from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_AID_ROOT = PurePosixPath(".agentic-workspace/agent-aids")
MANIFEST_NAME = "manifest.json"
SCHEMA_PATH = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "schemas" / "agent_aid_manifest.schema.json"
TYPE_DIRS = {
    "scripts": "script",
    "skills": "skill",
    "runbooks": "runbook",
    "prompts": "prompt",
    "checks": "check",
    "templates": "template",
}


@dataclass(frozen=True)
class Finding:
    path: str
    message: str


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate checked-in agent aid manifests and ownership boundaries.")
    parser.add_argument(
        "--quiet-success",
        action="store_true",
        help="Emit a compact success message when checked-in agent aids are valid.",
    )
    return parser.parse_args(argv)


def _as_posix(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _tracked_files(root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(_as_posix(line.strip()) for line in result.stdout.splitlines() if line.strip())


def _is_agent_aid_path(path: str) -> bool:
    posix = PurePosixPath(_as_posix(path))
    return posix == AGENT_AID_ROOT or AGENT_AID_ROOT in (posix, *posix.parents)


def _agent_aid_paths(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if _is_agent_aid_path(path))


def _load_schema(root: Path = REPO_ROOT) -> dict[str, Any]:
    return json.loads((root / SCHEMA_PATH.relative_to(REPO_ROOT)).read_text(encoding="utf-8"))


def _load_json(path: str, root: Path = REPO_ROOT) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads((root / path).read_text(encoding="utf-8"))
    except OSError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, f"{exc.msg} at line {exc.lineno}, column {exc.colno}"
    if not isinstance(payload, dict):
        return None, "manifest must be a JSON object"
    return payload, None


def _manifest_paths(paths: list[str]) -> set[str]:
    return {path for path in _agent_aid_paths(paths) if PurePosixPath(path).name == MANIFEST_NAME}


def _nearest_manifest(path: str, manifest_paths: set[str]) -> str | None:
    posix = PurePosixPath(path)
    for parent in (posix.parent, *posix.parents):
        if parent == PurePosixPath("."):
            break
        if not _is_agent_aid_path(parent.as_posix()):
            break
        candidate = (parent / MANIFEST_NAME).as_posix()
        if candidate in manifest_paths:
            return candidate
    return None


def _expected_type_for_manifest(path: str) -> str | None:
    posix = PurePosixPath(path)
    try:
        relative_parts = posix.relative_to(AGENT_AID_ROOT).parts
    except ValueError:
        return None
    if len(relative_parts) < 2:
        return None
    return TYPE_DIRS.get(relative_parts[0])


def _entrypoint_findings(path: str, payload: dict[str, Any], tracked: set[str]) -> list[Finding]:
    entrypoint = payload.get("entrypoint")
    if not isinstance(entrypoint, str):
        return []
    normalized = _as_posix(entrypoint)
    if normalized not in tracked:
        return [Finding(path=path, message=f"entrypoint is not tracked or does not exist: {entrypoint}")]
    manifest_dir = PurePosixPath(path).parent
    entrypoint_path = PurePosixPath(normalized)
    if manifest_dir not in (entrypoint_path, *entrypoint_path.parents):
        return [Finding(path=path, message="entrypoint must live inside the aid directory")]
    return []


def agent_aid_findings(paths: list[str] | None = None, root: Path = REPO_ROOT) -> list[Finding]:
    tracked = _tracked_files(root) if paths is None else sorted(_as_posix(path) for path in paths)
    aid_paths = _agent_aid_paths(tracked)
    manifest_paths = _manifest_paths(aid_paths)
    findings: list[Finding] = []
    schema = _load_schema(root)
    validator = Draft202012Validator(schema)

    for path in aid_paths:
        if PurePosixPath(path).name == MANIFEST_NAME:
            continue
        if _nearest_manifest(path, manifest_paths) is None:
            findings.append(Finding(path=path, message=f"checked-in agent aid file must be covered by a nearby {MANIFEST_NAME}"))

    tracked_set = set(tracked)
    for path in sorted(manifest_paths):
        payload, error = _load_json(path, root)
        if payload is None:
            findings.append(Finding(path=path, message=f"manifest cannot be loaded: {error}"))
            continue
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path)):
            location = ".".join(str(part) for part in error.path) or "<root>"
            findings.append(Finding(path=path, message=f"{location}: {error.message}"))
        expected_type = _expected_type_for_manifest(path)
        if expected_type is None:
            findings.append(Finding(path=path, message=f"manifest must live below one of: {', '.join(sorted(TYPE_DIRS))}"))
        elif payload.get("type") != expected_type:
            findings.append(Finding(path=path, message=f"manifest type must be {expected_type!r} for {path}"))
        findings.extend(_entrypoint_findings(path, payload, tracked_set))

    return findings


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    findings = agent_aid_findings()
    if findings:
        for finding in findings:
            print(f"{finding.path}: {finding.message}", file=sys.stderr)
        return 1
    if args.quiet_success:
        print("Agent aid manifest check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
