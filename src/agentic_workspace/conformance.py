from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from agentic_workspace.contract_tooling import contract_schema


def run_process_conformance(
    *,
    contract: Mapping[str, Any],
    fixture_root: Path,
    repo_root: Path,
    command_overrides: Mapping[str, Sequence[str]] | None = None,
) -> None:
    if contract.get("schema_version") != "agentic-workspace/conformance/v1":
        raise AssertionError("conformance contract has unexpected schema_version")
    adapter = _mapping(contract["adapter"])
    if adapter.get("kind") != "process":
        raise AssertionError(f"unsupported conformance adapter kind: {adapter.get('kind')}")

    expectations = _mapping(contract["expectations"])
    runs = 2 if _mapping(expectations["idempotency"]).get("run_twice") is True else 1
    before_fixture = _snapshot_tree(fixture_root)
    outside_sentinel = repo_root.parent / f".{fixture_root.name}-outside-sentinel"
    outside_sentinel.write_text("unchanged\n", encoding="utf-8")
    outside_hash = _file_hash(outside_sentinel)

    previous_stdout: str | None = None
    for run_index in range(runs):
        result = subprocess.run(
            _expand_command_template(_strings(adapter["command_template"]), command_overrides=command_overrides),
            cwd=fixture_root if adapter.get("cwd") == "fixture_root" else repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        _assert_process_result(result=result, expectations=expectations)
        if previous_stdout is not None and result.stdout != previous_stdout:
            raise AssertionError(f"stdout changed between conformance runs for {contract['id']}")
        previous_stdout = result.stdout
        after_fixture = _snapshot_tree(fixture_root)
        _assert_filesystem_effects(
            before=before_fixture,
            after=after_fixture,
            fixture_root=fixture_root,
            expectations=_mapping(expectations["filesystem"]),
            contract_id=str(contract["id"]),
        )
        if _mapping(expectations["safety"]).get("no_writes_outside_repo_root") is True and _file_hash(outside_sentinel) != outside_hash:
            raise AssertionError(f"{contract['id']} changed a file outside the fixture root on run {run_index + 1}")


def materialize_fixture(*, fixture: Mapping[str, Any], fixture_root: Path) -> None:
    for relative, contents in _mapping(fixture["files"]).items():
        path = _safe_join(fixture_root, str(relative))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(contents), encoding="utf-8")


def _assert_process_result(*, result: subprocess.CompletedProcess[str], expectations: Mapping[str, Any]) -> None:
    expected_exit = int(_mapping(expectations["exit"])["code"])
    if result.returncode != expected_exit:
        raise AssertionError(f"expected exit {expected_exit}, got {result.returncode}; stderr={result.stderr!r}")
    if _mapping(expectations["stderr"]).get("allow_non_empty") is False and result.stderr.strip():
        raise AssertionError(f"expected empty stderr, got {result.stderr!r}")
    stdout_expectations = _mapping(expectations["stdout"])
    if stdout_expectations.get("format") == "json":
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"stdout was not valid JSON: {result.stdout!r}") from exc
        schema_name = stdout_expectations.get("schema")
        if isinstance(schema_name, str) and schema_name:
            errors = sorted(Draft202012Validator(contract_schema(schema_name)).iter_errors(payload), key=lambda error: list(error.path))
            if errors:
                first = errors[0]
                location = ".".join(str(part) for part in first.path) or "<root>"
                raise AssertionError(f"stdout failed {schema_name} at {location}: {first.message}")
        for assertion in stdout_expectations.get("field_assertions", []):
            _assert_field(payload=payload, assertion=_mapping(assertion))
    elif not result.stdout.strip():
        raise AssertionError("expected non-empty stdout")


def _assert_field(*, payload: Any, assertion: Mapping[str, Any]) -> None:
    current = payload
    path = _strings(assertion["path"])
    for part in path:
        if not isinstance(current, dict) or part not in current:
            raise AssertionError(f"stdout JSON missing field {'.'.join(path)}")
        current = current[part]
    expected = assertion["equals"]
    if current != expected:
        raise AssertionError(f"stdout JSON field {'.'.join(path)} expected {expected!r}, got {current!r}")


def _assert_filesystem_effects(
    *,
    before: Mapping[str, str],
    after: Mapping[str, str],
    fixture_root: Path,
    expectations: Mapping[str, Any],
    contract_id: str,
) -> None:
    allowed = set(_strings(expectations["allowed_write_paths"]))
    changed = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
    unexpected = sorted(path for path in changed if path not in allowed)
    if unexpected:
        raise AssertionError(f"{contract_id} changed forbidden fixture paths: {unexpected}")
    for relative in _strings(expectations["required_paths"]):
        if not _safe_join(fixture_root, relative).exists():
            raise AssertionError(f"{contract_id} missing required fixture path: {relative}")
    for relative in _strings(expectations["forbidden_paths"]):
        if _safe_join(fixture_root, relative).exists():
            raise AssertionError(f"{contract_id} created forbidden fixture path: {relative}")


def _expand_command_template(
    template: Sequence[str],
    *,
    command_overrides: Mapping[str, Sequence[str]] | None,
) -> list[str]:
    overrides: dict[str, Sequence[str]] = {
        "agentic_workspace_cli": shlex.split(os.environ.get("AGENTIC_WORKSPACE_CONFORMANCE_CLI", "uv run agentic-workspace")),
        "agentic_planning_cli": shlex.split(os.environ.get("AGENTIC_PLANNING_CONFORMANCE_CLI", "uv run agentic-planning-bootstrap")),
        "python": [sys.executable],
    }
    if command_overrides:
        overrides.update(command_overrides)
    command: list[str] = []
    for token in template:
        if token.startswith("{") and token.endswith("}"):
            key = token[1:-1]
            if key not in overrides:
                raise AssertionError(f"unknown conformance command placeholder: {token}")
            command.extend(str(part) for part in overrides[key])
            continue
        command.append(token)
    return command


def _snapshot_tree(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    if not root.exists():
        return snapshot
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        snapshot[path.relative_to(root).as_posix()] = _file_hash(path)
    return snapshot


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_join(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    root_resolved = root.resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise AssertionError(f"fixture path escapes root: {relative}")
    return path


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AssertionError(f"expected mapping, got {type(value).__name__}")
    return value


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError("expected list of strings")
    return value
