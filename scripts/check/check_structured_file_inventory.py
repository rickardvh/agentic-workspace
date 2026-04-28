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

REPO_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "structured_file_inventory.json"
SCHEMA_PATH = REPO_ROOT / "src" / "agentic_workspace" / "contracts" / "schemas" / "structured_file_inventory.schema.json"
STRUCTURED_SUFFIXES = frozenset({".json", ".toml", ".yaml", ".yml"})


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


def tracked_structured_files(root: Path = REPO_ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    files = [_as_posix(line.strip()) for line in result.stdout.splitlines() if line.strip()]
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


def inventory_findings(paths: list[str] | None = None) -> list[Finding]:
    inventory = load_inventory()
    findings = validate_inventory_shape(inventory)
    if findings:
        return findings
    checked_paths = tracked_structured_files() if paths is None else paths
    return unmatched_structured_files(checked_paths, inventory)


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
