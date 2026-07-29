# Generated from command_package_ir.json. Do not edit.
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any, Sequence

READINESS_TRANSPORTS = ("cli-json", "python", "typescript", "vendor-neutral")
READINESS_CASES = ("absent", "disabled", "incompatible", "malformed", "retryable", "additive-field", "mutation-applied", "mutation-noop", "mutation-rejected", "mutation-failed")


def external_consumer_profile() -> dict[str, Any]:
    return json.loads(files("agentic_workspace._generated_cli_package_impl").joinpath("external_consumer_profile.json").read_text(encoding="utf-8"))


def external_operation_conformance_receipts() -> dict[str, Any]:
    resource = files("agentic_workspace._generated_cli_package_impl").joinpath("external_operation_conformance_receipts.json")
    if not resource.is_file():
        return {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": []}
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) and payload.get("kind") == "agentic-workspace/external-operation-conformance-receipt-store/v1" else {"kind": "agentic-workspace/external-operation-conformance-receipt-store/v1", "receipts": []}


def _conformance_receipt(entry: dict[str, Any], profile: dict[str, Any], receipt_store: dict[str, Any]) -> dict[str, Any] | None:
    operation_fingerprint = entry.get("operation_compatibility", {}).get("fingerprint", "")
    profile_fingerprint = profile.get("compatibility", {}).get("fingerprint", "")
    candidates = []
    for receipt in receipt_store.get("receipts", []):
        if not isinstance(receipt, dict): continue
        custody = receipt.get("custody", {}) if isinstance(receipt.get("custody"), dict) else {}
        if receipt.get("kind") != "agentic-workspace/external-operation-conformance-receipt/v1": continue
        if custody.get("producer") != "agentic-workspace.operation-conformance-runner": continue
        if receipt.get("operation_id") != entry.get("id"): continue
        if receipt.get("operation_fingerprint") != operation_fingerprint: continue
        if receipt.get("profile_fingerprint") != profile_fingerprint: continue
        if receipt.get("status") in {"revoked", "superseded", "stale"}: continue
        if receipt.get("revoked_at") or receipt.get("superseded_by"): continue
        expires_at = str(receipt.get("expires_at") or "")
        if expires_at:
            try: parsed_expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError: continue
            if parsed_expires_at.tzinfo is None: parsed_expires_at = parsed_expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= parsed_expires_at: continue
        candidates.append(receipt)
    return sorted(candidates, key=lambda item: str(item.get("executed_at") or item.get("receipt_ref") or ""))[-1] if candidates else None


def _conformance_readiness(entry: dict[str, Any], profile: dict[str, Any], receipt_store: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    evidence = _conformance_receipt(entry, profile, receipt_store)
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
    custody = evidence.get("custody", {}) if isinstance(evidence.get("custody"), dict) else {}
    return missing, {"status": evidence.get("status", ""), "operation_fingerprint": evidence.get("operation_fingerprint", ""), "profile_fingerprint": evidence.get("profile_fingerprint", ""), "runtime_exception_revision": evidence.get("runtime_exception_revision", ""), "transports": transports if isinstance(transports, dict) else {}, "cases": cases if isinstance(cases, dict) else {}, "receipt_ref": evidence.get("receipt_ref", ""), "producer": custody.get("producer", "")}


def external_readiness_report(operation_ids: Sequence[str]) -> dict[str, Any]:
    profile = external_consumer_profile()
    receipt_store = external_operation_conformance_receipts()
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
        conformance_missing, conformance_result = _conformance_readiness(entry, profile, receipt_store)
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
