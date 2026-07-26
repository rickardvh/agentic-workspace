# Generated from command_package_ir.json. Do not edit.
from __future__ import annotations

import json
import subprocess
from importlib.resources import files
from pathlib import Path
from typing import Any, Sequence


def external_consumer_profile() -> dict[str, Any]:
    return json.loads(files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json").read_text(encoding="utf-8"))


def external_readiness_report(operation_ids: Sequence[str]) -> dict[str, Any]:
    entries = {entry["id"]: entry for entry in external_consumer_profile()["operations"]}
    supported, excluded = [], []
    for operation_id in operation_ids:
        entry = entries.get(operation_id, {})
        consumption = entry.get("external_consumption", {})
        resources, targets = entry.get("operation_resources", {}), entry.get("targets", {})
        schemas, conformance = entry.get("schemas", {}), entry.get("conformance", [])
        missing = []
        for language in ("python", "typescript"):
            if not resources.get(language, {}).get("exists"): missing.append(f"released-{language}-resource")
            if targets.get(language, {}).get("status") not in {"adapter", "mutation-capable-adapter"}: missing.append(f"released-{language}-adapter")
        if not schemas.get("input") or not schemas.get("output"): missing.append("input-output-schema-coverage")
        if not conformance: missing.append("conformance-reference")
        status = consumption.get("status", "unavailable")
        if status == "runtime-backed" and not consumption.get("runtime_exceptions"): missing.append("runtime-exception-disposition")
        if status == "supported" and not missing: supported.append(operation_id)
        else: excluded.append({"id": operation_id, "status": status, "missing_evidence": missing, "conformance_refs": conformance})
    return {"kind": "agentic-workspace/external-readiness-report/v1", "status": "ready" if not excluded else "subset-only" if supported else "not-ready", "supported_operations": supported, "excluded_operations": excluded}


def require_operations(operation_ids: Sequence[str], *, allow_runtime_backed: bool = False) -> None:
    entries = {entry["id"]: entry for entry in external_consumer_profile()["operations"]}
    failures = []
    for operation_id in operation_ids:
        status = entries.get(operation_id, {}).get("external_consumption", {}).get("status", "unknown")
        if status in {"internal", "unknown"} or (status == "runtime-backed" and not allow_runtime_backed):
            failures.append(f"{operation_id}: {status}")
    if failures: raise ValueError("incompatible operation requirements: " + ", ".join(failures))


def invoke_json(argv: Sequence[str], *, target: str | Path | None = None, executable: Sequence[str] = ("agentic-workspace",)) -> dict[str, Any]:
    command = [*executable, *argv]
    if target is not None and "--target" not in command: command.extend(["--target", str(target)])
    if "--format" not in command: command.extend(["--format", "json"])
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    try: payload = json.loads(completed.stdout or completed.stderr)
    except json.JSONDecodeError as exc: raise RuntimeError(f"AW returned non-JSON output (exit {completed.returncode})") from exc
    if completed.returncode: raise RuntimeError(json.dumps({"exit_code": completed.returncode, "error": payload}))
    return payload
