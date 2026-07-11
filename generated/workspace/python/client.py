# Generated from command_package_ir.json. Do not edit.
from __future__ import annotations

import json
import subprocess
from importlib.resources import files
from pathlib import Path
from typing import Any, Sequence


def external_consumer_profile() -> dict[str, Any]:
    resource = files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def require_operations(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> None:
    entries = {entry["id"]: entry for entry in external_consumer_profile()["operations"]}
    failures = []
    for operation_id in operation_ids:
        entry = entries.get(operation_id)
        status = entry and entry["external_consumption"]["status"]
        if entry is None or status == "internal" or (status == "runtime-backed" and not allow_runtime_backed):
            failures.append(f"{operation_id}: {status or 'unknown'}")
    if failures:
        raise ValueError("incompatible operation requirements: " + ", ".join(failures))


def invoke_json(argv: Sequence[str], *, target: str | Path | None = None, executable: Sequence[str] = ("agentic-workspace",)) -> dict[str, Any]:
    command = [*executable, *argv]
    if target is not None and "--target" not in command:
        command.extend(["--target", str(target)])
    if "--format" not in command:
        command.extend(["--format", "json"])
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    stream = completed.stdout or completed.stderr
    try:
        payload = json.loads(stream)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AW returned non-JSON output (exit {completed.returncode})") from exc
    if completed.returncode:
        raise RuntimeError(json.dumps({"exit_code": completed.returncode, "error": payload}))
    return payload
