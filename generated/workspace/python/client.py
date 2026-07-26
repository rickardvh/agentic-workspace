# Generated from command_package_ir.json. Do not edit.
from __future__ import annotations

import json
import subprocess
from importlib.resources import files
from pathlib import Path
from typing import Any, Sequence

READINESS_TRANSPORTS = ("cli-json", "python", "typescript", "vendor-neutral")
READINESS_CASES = ("absent", "disabled", "incompatible", "malformed", "retryable", "additive-field", "mutation-applied", "mutation-noop", "mutation-rejected", "mutation-failed")


def external_consumer_profile() -> dict[str, Any]:
    return json.loads(files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json").read_text(encoding="utf-8"))


def _conformance_readiness(entry: dict[str, Any], profile: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    evidence = entry.get("conformance_evidence")
    if not isinstance(evidence, dict): return ["executed-conformance-receipt"], {}
    missing = []
    operation_fingerprint = entry.get("operation_compatibility", {}).get("fingerprint", "")
    profile_fingerprint = profile.get("compatibility", {}).get("fingerprint", "")
    if evidence.get("status") != "passed": missing.append("executed-conformance-passed")
    if evidence.get("operation_fingerprint") != operation_fingerprint: missing.append("current-operation-fingerprint")
    if evidence.get("profile_fingerprint") != profile_fingerprint: missing.append("current-profile-fingerprint")
    transports = evidence.get("transports", {})
    cases = evidence.get("cases", {})
    for transport in READINESS_TRANSPORTS:
        if not isinstance(transports.get(transport), dict) or transports[transport].get("status") != "passed": missing.append(f"transport-{transport}")
    for case in READINESS_CASES:
        if not isinstance(cases.get(case), dict) or cases[case].get("status") != "passed": missing.append(f"case-{case}")
    if entry.get("external_consumption", {}).get("runtime_exceptions") and not evidence.get("runtime_exception_revision"): missing.append("runtime-exception-current-revision")
    return missing, {"status": evidence.get("status", ""), "operation_fingerprint": evidence.get("operation_fingerprint", ""), "profile_fingerprint": evidence.get("profile_fingerprint", ""), "runtime_exception_revision": evidence.get("runtime_exception_revision", ""), "transports": transports if isinstance(transports, dict) else {}, "cases": cases if isinstance(cases, dict) else {}}


def external_readiness_report(operation_ids: Sequence[str]) -> dict[str, Any]:
    profile = external_consumer_profile()
    entries = {entry["id"]: entry for entry in profile["operations"]}
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
        conformance_missing, conformance_result = _conformance_readiness(entry, profile)
        missing.extend(conformance_missing)
        status = consumption.get("status", "unavailable")
        if status == "runtime-backed" and not consumption.get("runtime_exceptions"): missing.append("runtime-exception-disposition")
        if status == "supported" and not missing: supported.append(operation_id)
        else: excluded.append({"id": operation_id, "status": status, "missing_evidence": missing, "conformance_refs": conformance, "conformance_result": conformance_result})
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
