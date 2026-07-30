#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import check_contract_tooling_surfaces as contract_tooling_check  # noqa: E402
import check_generated_command_packages as generated_package_check  # noqa: E402
from command_generation.conformance import (  # noqa: E402
    FunctionConformanceTarget,
    OperationConformanceCase,
    ProcessConformanceCase,
    TypescriptFunctionConformanceTarget,
    materialize_case_fixture,
    run_function_conformance_case,
    run_typescript_function_conformance_case,
)

from agentic_workspace.contract_tooling import (  # noqa: E402
    contract_schema,
    operation_artifact_registry_manifest,
    operation_conformance_test_ir_manifest,
)

READINESS_TRANSPORTS = ("cli-json", "python", "typescript", "vendor-neutral")
READINESS_CASES = (
    "absent",
    "disabled",
    "incompatible",
    "malformed",
    "retryable",
    "additive-field",
    "mutation-applied",
    "mutation-noop",
    "mutation-rejected",
    "mutation-failed",
)
CONFORMANCE_RECEIPT_EXPIRES_AT = "2026-12-31T00:00:00Z"
CONFORMANCE_RECEIPT_TTL_DAYS = 14
EXTERNAL_CONFORMANCE_RECEIPT_PATHS = (
    REPO_ROOT / "src/agentic_workspace/contracts/external_operation_conformance_receipts.json",
    REPO_ROOT / "generated/workspace/python/external_operation_conformance_receipts.json",
    REPO_ROOT / "generated/workspace/typescript/external_operation_conformance_receipts.json",
)


def _stable_json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expires_from(executed_at: str) -> str:
    parsed = datetime.fromisoformat(executed_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (parsed + timedelta(days=CONFORMANCE_RECEIPT_TTL_DAYS)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _runner_revision() -> str:
    runner_path = REPO_ROOT / "scripts/check/run_operation_conformance_tests.py"
    return f"{runner_path.relative_to(REPO_ROOT).as_posix()}@sha256:{hashlib.sha256(runner_path.read_bytes()).hexdigest()}"


def _all_passed(results: list[dict[str, object]]) -> bool:
    return bool(results) and all(result.get("state") == "pass" for result in results)


def _status(
    state: str,
    *,
    evidence: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"status": state}
    if evidence:
        payload["evidence"] = sorted(set(evidence))
    if reason:
        payload["reason"] = reason
    return payload


def _result_evidence_ref(result: Mapping[str, object]) -> str:
    payload = {
        "operation_id": result.get("operation_id", ""),
        "case_id": result.get("case_id", ""),
        "target": result.get("target", ""),
        "adapter_id": result.get("adapter_id", ""),
        "state": result.get("state", ""),
        "selected_fields": result.get("selected_fields", {}),
        "mutation_outcome": result.get("mutation_outcome", {}),
    }
    digest = _stable_json_digest(payload)[:16]
    return (
        f"{payload['operation_id']}:{payload['case_id']}:"
        f"{payload['target']}:{payload['adapter_id']}@sha256:{digest}"
    )


def _passed_results(results: list[dict[str, object]]) -> list[dict[str, object]]:
    return [result for result in results if result.get("state") == "pass"]


def _operation_contract(entry: Mapping[str, object]) -> Mapping[str, object]:
    operation_contract_ref = str(entry.get("operation_contract") or "").strip()
    if not operation_contract_ref:
        return {}
    try:
        loaded_contract = json.loads((REPO_ROOT / operation_contract_ref).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded_contract if isinstance(loaded_contract, Mapping) else {}


def _is_mutation_operation(entry: Mapping[str, object]) -> tuple[bool, str]:
    operation_contract = _operation_contract(entry)
    effects = operation_contract.get("effects") if isinstance(operation_contract.get("effects"), Mapping) else {}
    writes = operation_contract.get("writes") if isinstance(operation_contract.get("writes"), list) else []
    locality = operation_contract.get("locality") if isinstance(operation_contract.get("locality"), Mapping) else {}
    if isinstance(effects, Mapping) and effects.get("read_only") is True and not writes:
        return False, "operation contract is read-only and declares no writes"
    if isinstance(effects, Mapping) and effects.get("writes_repo_state") is True:
        return True, "effects.writes_repo_state=true"
    if writes:
        return True, "operation contract declares writes"
    if isinstance(effects, Mapping) and effects.get("read_only") is False:
        return True, "effects.read_only=false"
    if isinstance(locality, Mapping) and str(locality.get("outside_repo_writes") or "") not in {"", "forbidden"}:
        return True, "operation locality allows outside-repo writes"
    return False, "operation contract has no declared mutation effect"


def _readiness_case_label(result: Mapping[str, object]) -> str:
    explicit = str(result.get("readiness_case") or "").strip()
    if explicit:
        return explicit
    behavioral_class = str(result.get("behavioral_class") or "").strip()
    if behavioral_class in READINESS_CASES:
        return behavioral_class
    if behavioral_class == "error":
        return "malformed"
    return ""


def _mutation_case_label(result: Mapping[str, object]) -> str:
    explicit = _readiness_case_label(result)
    if explicit.startswith("mutation-"):
        return explicit
    mutation_outcome = result.get("mutation_outcome")
    if isinstance(mutation_outcome, Mapping):
        reason_code = str(mutation_outcome.get("reason_code") or mutation_outcome.get("outcome") or "")
        mutation_applied = mutation_outcome.get("mutation_applied")
    else:
        selected_fields = result.get("selected_fields")
        selected = selected_fields if isinstance(selected_fields, Mapping) else {}
        reason_code = str(selected.get("reason_code") or selected.get("outcome") or selected.get("status") or "")
        mutation_applied = selected.get("mutation_applied")
    if mutation_applied is True or reason_code in {"mutation-applied", "applied", "recorded", "written", "appended"}:
        return "mutation-applied"
    if mutation_applied is False and reason_code in {
        "mutation-noop",
        "noop",
        "no-op",
        "idempotent",
        "already-present",
        "duplicate",
        "blocked",
    }:
        return "mutation-noop"
    if reason_code in {"mutation-rejected", "rejected", "invalid", "invalid-input", "forbidden", "unauthorized"}:
        return "mutation-rejected"
    if reason_code in {"mutation-failed", "failed", "error"}:
        return "mutation-failed"
    return ""


def _runtime_exception_revision_for_operation(
    *,
    entry: Mapping[str, object],
    conformance_result: Mapping[str, object],
    operation_id: str,
    operation_fingerprint: str,
    profile_fingerprint: str,
    operation_results: list[dict[str, object]],
) -> tuple[str, dict[str, object]]:
    consumption = entry.get("external_consumption", {})
    runtime_exceptions = consumption.get("runtime_exceptions") if isinstance(consumption, Mapping) else None
    if not runtime_exceptions:
        return "", {"status": "not-required"}
    revisions = conformance_result.get("runtime_exception_revisions", {})
    revision = ""
    if isinstance(revisions, Mapping):
        revision = str(revisions.get(operation_id) or "")
    if revision and revision != "#2044@accepted":
        return revision, {
            "status": "admitted",
            "operation_id": operation_id,
            "revision": revision,
            "rule": "Runtime exception evidence is operation-specific and supplied by a separate authoritative owner.",
        }
    if revision == "#2044@accepted":
        return "", {
            "status": "rejected",
            "reason": "missing-operation-specific-runtime-exception-revision",
            "rule": "Blanket issue labels are not executable operation-specific runtime-exception evidence.",
        }
    return "", {
        "status": "rejected",
        "reason": "missing-operation-specific-runtime-exception-revision",
        "rule": "Runtime exceptions must be admitted per operation/profile by an authority outside the conformance result.",
    }


def _readiness_transport_statuses(operation_results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    def _status_for(results: list[dict[str, object]], *, missing_reason: str) -> dict[str, object]:
        if not results:
            return _status("not-run", reason=missing_reason)
        if _all_passed(results):
            return _status("passed", evidence=[_result_evidence_ref(result) for result in results])
        states = sorted({str(result.get("state") or "not-run") for result in results})
        return _status(
            "failed",
            evidence=[_result_evidence_ref(result) for result in results],
            reason=f"transport results were not all pass: {', '.join(states)}",
        )

    def _adapter(adapter: str) -> list[dict[str, object]]:
        return [result for result in operation_results if result.get("adapter_id") == adapter]

    def _target(target: str) -> list[dict[str, object]]:
        return [result for result in operation_results if result.get("target") == target]

    transports = {
        "python": _status_for(
            _target("python"),
            missing_reason="no Python operation result was produced by this invocation",
        ),
        "typescript": _status_for(
            _target("typescript"),
            missing_reason="no TypeScript operation result was produced by this invocation",
        ),
        "cli-json": _status_for(
            _adapter("cli.process"),
            missing_reason="no CLI JSON operation result was produced by this invocation",
        ),
    }
    vendor_results = [
        result
        for result in operation_results
        if result.get("target") == "vendor-neutral" or str(result.get("adapter_id") or "").startswith("vendor-neutral")
    ]
    transports["vendor-neutral"] = _status_for(
        vendor_results,
        missing_reason="no independently packaged vendor-neutral consumer result was produced by this invocation",
    )
    return transports


def _readiness_case_statuses(entry: Mapping[str, object], operation_results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    is_mutation_operation, mutation_reason = _is_mutation_operation(entry)

    def _results_for(case_name: str) -> list[dict[str, object]]:
        if case_name.startswith("mutation-"):
            return [result for result in operation_results if _mutation_case_label(result) == case_name]
        return [result for result in operation_results if _readiness_case_label(result) == case_name]

    def _case_status(case_name: str) -> dict[str, object]:
        results = _results_for(case_name)
        if case_name.startswith("mutation-") and not is_mutation_operation:
            return _status(
                "passed",
                reason=f"not applicable: {mutation_reason}",
                evidence=[str(entry.get("operation_contract") or entry.get("id") or "operation-contract")],
            )
        if not results:
            return _status("not-run", reason=f"no {case_name} result was produced by this invocation")
        if _all_passed(results):
            return _status("passed", evidence=[_result_evidence_ref(result) for result in results])
        states = sorted({str(result.get("state") or "not-run") for result in results})
        return _status(
            "failed",
            evidence=[_result_evidence_ref(result) for result in results],
            reason=f"{case_name} results were not all pass: {', '.join(states)}",
        )

    return {case: _case_status(case) for case in READINESS_CASES}


def build_external_operation_conformance_receipts(
    profile: Mapping[str, object],
    *,
    conformance_result: Mapping[str, object] | None = None,
    executed_at: str | None = None,
    expires_at: str | None = None,
    runner_revision: str | None = None,
    invocation_id: str | None = None,
) -> dict[str, object]:
    """Build producer-owned external readiness receipts for packaged operations.

    The readiness report consumes this receipt store instead of trusting profile
    declarations as evidence. The receipt content is intentionally tied to the
    current operation/profile fingerprints so stale, revoked, superseded, or
    expired receipts fail closed at runtime.
    """

    if conformance_result is None:
        return {
            "kind": "agentic-workspace/external-operation-conformance-receipt-store/v1",
            "receipts": [],
            "producer": "scripts/check/run_operation_conformance_tests.py",
            "status": "not-run",
            "rule": "No packaged conformance receipts are synthesized from profile declarations; run conformance and pass its result set to build receipts.",
        }

    receipts: list[dict[str, object]] = []
    actual_executed_at = executed_at or _utc_timestamp()
    actual_expires_at = expires_at or _expires_from(actual_executed_at)
    actual_runner_revision = runner_revision or _runner_revision()
    profile_fingerprint = (
        str((profile.get("compatibility") or {}).get("fingerprint", "")) if isinstance(profile.get("compatibility"), Mapping) else ""
    )
    all_results = [dict(result) for result in conformance_result.get("cases", []) if isinstance(result, Mapping)]
    result_digest = _stable_json_digest(conformance_result)
    actual_invocation_id = invocation_id or (
        f"operation-conformance:{actual_runner_revision[:12]}:{result_digest[:24]}:{actual_executed_at}"
    )
    result_identity = {
        "kind": "agentic-workspace/external-operation-conformance-result-identity/v1",
        "status": "current",
        "invocation_id": actual_invocation_id,
        "runner_revision": actual_runner_revision,
        "result_digest": result_digest,
        "executed_at": actual_executed_at,
    }

    def _state_for_results(results: list[dict[str, object]]) -> str:
        states = {str(result.get("state") or "not-run") for result in results}
        if not results:
            return "not-run"
        if "fail" in states:
            return "failed"
        if "unavailable" in states:
            return "unavailable"
        if "skipped" in states:
            return "skipped"
        return "passed" if states == {"pass"} else "failed"

    for entry in profile.get("operations", []):
        if not isinstance(entry, Mapping):
            continue
        consumption = entry.get("external_consumption", {})
        if not isinstance(consumption, Mapping) or consumption.get("status") == "internal":
            continue
        operation_id = str(entry.get("id") or "")
        operation_compatibility = entry.get("operation_compatibility", {})
        operation_fingerprint = str(operation_compatibility.get("fingerprint", "")) if isinstance(operation_compatibility, Mapping) else ""
        conformance_refs = [str(ref) for ref in entry.get("conformance", []) if isinstance(ref, str)]
        operation_results = [result for result in all_results if str(result.get("operation_id") or "") == operation_id]
        if not operation_results:
            continue
        runtime_exception_revision, runtime_exception_admission = _runtime_exception_revision_for_operation(
            entry=entry,
            conformance_result=conformance_result,
            operation_id=operation_id,
            operation_fingerprint=operation_fingerprint,
            profile_fingerprint=profile_fingerprint,
            operation_results=operation_results,
        )
        transports = _readiness_transport_statuses(operation_results)
        cases = _readiness_case_statuses(entry, operation_results)
        receipt_status = (
            "passed"
            if all(item["status"] == "passed" for item in [*transports.values(), *cases.values()])
            and runtime_exception_admission.get("status") in {"not-required", "admitted"}
            else "failed"
        )
        receipt_basis = {
            "operation_id": operation_id,
            "operation_fingerprint": operation_fingerprint,
            "profile_fingerprint": profile_fingerprint,
            "conformance_refs": conformance_refs,
            "result_identity": result_identity,
            "operation_results": operation_results,
            "operation_result_evidence": [_result_evidence_ref(result) for result in operation_results],
            "transports": transports,
            "cases": cases,
            "producer": "scripts/check/run_operation_conformance_tests.py",
        }
        digest = _stable_json_digest(receipt_basis)[:24]
        receipts.append(
            {
                "kind": "agentic-workspace/external-operation-conformance-receipt/v1",
                "receipt_ref": f"external-conformance:{operation_id}:{digest}",
                "operation_id": operation_id,
                "operation_fingerprint": operation_fingerprint,
                "profile_fingerprint": profile_fingerprint,
                "status": receipt_status,
                "executed_at": actual_executed_at,
                "expires_at": actual_expires_at,
                "runtime_exception_revision": runtime_exception_revision,
                "runtime_exception_admission": runtime_exception_admission,
                "conformance_result_digest": result_digest,
                "result_identity": result_identity,
                "conformance_refs": conformance_refs,
                "operation_result_evidence": [_result_evidence_ref(result) for result in operation_results],
                "transports": transports,
                "cases": cases,
                "custody": {
                    "operation_id": "external-operation-conformance.run",
                    "producer": "agentic-workspace.operation-conformance-runner",
                    "trusted_channel": "packaged-conformance-receipt",
                    "source": "scripts/check/run_operation_conformance_tests.py",
                    "result_kind": conformance_result.get("kind", ""),
                },
            }
        )
    return {
        "kind": "agentic-workspace/external-operation-conformance-receipt-store/v1",
        "receipts": receipts,
        "producer": "scripts/check/run_operation_conformance_tests.py",
        "executed_at": actual_executed_at,
        "expires_at": actual_expires_at,
        "result_identity": result_identity,
        "status": "recorded" if receipts else "no-operation-results",
        "rule": "Readiness consumes producer-owned executed conformance receipts from this store; profile-authored inline evidence is ignored.",
    }


def _path_label(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else path.as_posix()


def _existing_mirror_digests(paths: tuple[Path, ...]) -> dict[Path, str]:
    digests: dict[Path, str] = {}
    for path in paths:
        if path.exists():
            digests[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def write_external_operation_conformance_receipts(
    receipt_store: Mapping[str, object],
    *,
    paths: tuple[Path, ...] | None = None,
    expected_existing_digest: str | None = None,
) -> dict[str, object]:
    """Persist the authoritative receipt mirrors consumed by packaged clients."""
    selected_paths = paths or EXTERNAL_CONFORMANCE_RECEIPT_PATHS
    existing_digests = _existing_mirror_digests(selected_paths)
    if existing_digests and len(existing_digests) != len(selected_paths):
        missing = [path for path in selected_paths if path not in existing_digests]
        raise RuntimeError(
            "external conformance receipt mirror set is partial before publication: "
            + ", ".join(_path_label(path) for path in missing)
        )
    if expected_existing_digest is None and existing_digests:
        unique_existing_digests = set(existing_digests.values())
        if len(unique_existing_digests) != 1:
            raise RuntimeError(
                "external conformance receipt mirrors are not in one pre-publication revision: "
                + ", ".join(
                    f"{_path_label(path)}={digest[:12]}"
                    for path, digest in sorted(existing_digests.items(), key=lambda item: _path_label(item[0]))
                )
            )
        expected_existing_digest = next(iter(unique_existing_digests))
    mismatched = {
        path: digest
        for path, digest in existing_digests.items()
        if expected_existing_digest is not None and digest != expected_existing_digest
    }
    if mismatched:
        raise RuntimeError(
            "external conformance receipt mirror revision changed before publication: "
            + ", ".join(
                f"{_path_label(path)}={digest[:12]}"
                for path, digest in sorted(mismatched.items(), key=lambda item: _path_label(item[0]))
            )
        )
    store = dict(receipt_store)
    store["mirror_publication"] = {
        "kind": "agentic-workspace/external-operation-conformance-mirror-publication/v1",
        "status": "locked-staged-mirror-publication",
        "previous_digest": expected_existing_digest or "",
        "publisher_pid": os.getpid(),
        "path_count": len(selected_paths),
        "mixed_read_boundary": "Readers may rely only on matching publication_digest across all mirrors; this is not a single-filesystem atomic multi-path transaction.",
    }
    text = json.dumps(store, indent=2, sort_keys=True) + "\n"
    publication_digest = hashlib.sha256(text.encode()).hexdigest()
    written: list[str] = []
    staged: list[tuple[Path, Path]] = []
    originals = {path: path.read_bytes() for path in selected_paths if path.exists()}
    lock_path = selected_paths[0].parent / ".external_operation_conformance_receipts.lock"
    lock_fd: int | None = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(f"external conformance receipt mirror publication is locked: {_path_label(lock_path)}") from exc
        os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        for path in selected_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
            tmp.write_text(text, encoding="utf-8", newline="\n")
            staged.append((path, tmp))
        for path, tmp in staged:
            tmp.replace(path)
            written.append(_path_label(path))
    except Exception:
        for path, tmp in staged:
            if tmp.exists():
                tmp.unlink()
            if path in originals:
                path.write_bytes(originals[path])
        raise
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
            lock_path.unlink(missing_ok=True)
    return {
        "kind": "agentic-workspace/external-operation-conformance-receipt-write/v1",
        "status": "written",
        "receipt_count": len(store.get("receipts", [])) if isinstance(store.get("receipts"), list) else 0,
        "previous_digest": expected_existing_digest or "",
        "publication_digest": publication_digest,
        "paths": written,
    }


def _selected_field(payload: object, field_path: str) -> object:
    current = payload
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise KeyError(field_path)
        current = current[part]
    return current


def _case_process_fixture(case: Mapping[str, object]) -> ProcessConformanceCase:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed operation_ref")
    expected = case.get("expected", {})
    if not isinstance(expected, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed expected block")
    stdout = expected.get("stdout", {})
    stderr = expected.get("stderr", {})
    case_input = case.get("input", {})
    if not isinstance(case_input, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed input block")
    fixture_files = case_input.get("fixture_files", {})
    if not isinstance(fixture_files, Mapping):
        raise ValueError(f"case {case.get('id')} fixture_files must be an object")
    stdout_fields = stdout.get("selected_fields", {}) if isinstance(stdout, Mapping) else {}
    stdout_contains = stdout.get("contains", []) if isinstance(stdout, Mapping) else []
    allow_stderr = bool(stderr.get("allow_non_empty", False)) if isinstance(stderr, Mapping) else False
    return ProcessConformanceCase(
        conformance_ref=str(operation_ref.get("conformance_ref") or case.get("id", "")),
        label=str(case.get("title", case.get("id", ""))),
        success_args=tuple(str(item) for item in case_input.get("argv", []) if isinstance(item, str)),
        selected_fields=lambda stdout_text, expected_fields=stdout_fields: _select_expected_fields(stdout_text, expected_fields),
        expected_fields=dict(stdout_fields) if isinstance(stdout_fields, Mapping) else {},
        stdout_contains=tuple(str(item) for item in stdout_contains if isinstance(item, str)),
        fixture_id=str(case_input.get("fixture_id", case.get("id", ""))),
        fixture_files={str(path): str(contents) for path, contents in fixture_files.items()},
        expected_exit=int(expected.get("exit_code", 0)),
        allow_stderr=allow_stderr,
    )


def _case_function_fixture(case: Mapping[str, object]) -> OperationConformanceCase:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed operation_ref")
    expected = case.get("expected", {})
    if not isinstance(expected, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed expected block")
    result = expected.get("result", {})
    case_input = case.get("input", {})
    if not isinstance(case_input, Mapping):
        raise ValueError(f"case {case.get('id')} has malformed input block")
    result_fields = result.get("selected_fields", {}) if isinstance(result, Mapping) else {}
    error = expected.get("error", {})
    error_contains = error.get("contains", []) if isinstance(error, Mapping) else []
    return OperationConformanceCase(
        conformance_ref=str(operation_ref.get("conformance_ref") or case.get("id", "")),
        label=str(case.get("title", case.get("id", ""))),
        input_values=dict(case_input.get("json", {})) if isinstance(case_input.get("json", {}), Mapping) else {},
        selected_fields=lambda output, expected_fields=result_fields: _select_expected_result_fields(output, expected_fields),
        expected_fields=dict(result_fields) if isinstance(result_fields, Mapping) else {},
        expected_error_contains=tuple(str(item) for item in error_contains if isinstance(item, str)),
    )


def _select_expected_fields(stdout_text: str, expected_fields: object) -> dict[str, object]:
    if not isinstance(expected_fields, Mapping) or not expected_fields:
        return {}
    payload = json.loads(stdout_text)
    return {str(field): _selected_field(payload, str(field)) for field in expected_fields}


def _select_expected_result_fields(output: object, expected_fields: object) -> dict[str, object]:
    if not isinstance(expected_fields, Mapping) or not expected_fields:
        return {}
    return {str(field): _selected_field(output, str(field)) for field in expected_fields}


def _package_by_id(manifest: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    packages = manifest.get("packages", [])
    if not isinstance(packages, list):
        return {}
    return {str(package.get("id", "")): package for package in packages if isinstance(package, Mapping)}


def _typescript_command_for_package(package: Mapping[str, object]) -> tuple[str, list[str] | None]:
    node = shutil.which("node")
    if node is None:
        return "node-unavailable", None
    for target in package.get("targets", []):
        if isinstance(target, Mapping) and target.get("kind") == "typescript":
            cli = REPO_ROOT / str(target.get("generated_root", "")) / "src" / "cli.mjs"
            return "available", [node, str(cli)]
    return "target-unavailable", None


def _run_case_target(
    *,
    case: Mapping[str, object],
    artifact_registry: Mapping[str, Mapping[str, object]],
    target_kind: str,
    temp_root: Path,
    require_node: bool,
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _result(case=case, target_kind=target_kind, state="fail", message="malformed operation_ref")
    artifact = _artifact_for_target(case, target_kind, artifact_registry)
    if artifact is None:
        return _result(
            case=case, artifact_registry=artifact_registry, target_kind=target_kind, state="fail", message="no registry artifact for target"
        )
    package_id = str(artifact.get("package_id", operation_ref.get("package_id", "")))
    command_package_ir = generated_package_check.load_workspace_command_package_ir(repo_root=REPO_ROOT)
    package = _package_by_id(command_package_ir).get(package_id)
    if package is None:
        return _result(
            case=case, artifact_registry=artifact_registry, target_kind=target_kind, state="fail", message=f"unknown package {package_id!r}"
        )
    adapter_id = str(artifact.get("adapter_id", "cli.process"))
    if target_kind == "python" and adapter_id == "python.function":
        return _run_python_function_case(case=case, artifact=artifact)
    if target_kind == "typescript" and adapter_id == "typescript.function":
        return _run_typescript_function_case(case=case, artifact=artifact, temp_root=temp_root, require_node=require_node)
    process_case = _case_process_fixture(case)
    fixture_root = materialize_case_fixture(
        case=process_case,
        root=temp_root / str(case.get("id", "case")).replace(".", "-") / target_kind,
    )
    if target_kind == "python":
        command = generated_package_check._python_command_for_package(package_id)
        env = generated_package_check._conformance_env()
    elif target_kind == "typescript":
        status, command = _typescript_command_for_package(package)
        if command is None:
            state = "fail" if require_node else "unavailable"
            return _result(case=case, artifact_registry=artifact_registry, target_kind=target_kind, state=state, message=status)
        env = generated_package_check._conformance_env(runtime="")
    else:
        return _result(
            case=case, artifact_registry=artifact_registry, target_kind=target_kind, state="skipped", message="target not selected"
        )
    completed = subprocess.run(
        [*command, *process_case.success_args],
        cwd=fixture_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    failures = _evaluate_process_result(case=case, process_case=process_case, completed=completed, fixture_root=fixture_root)
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "readiness_case": str(case.get("readiness_case", "")),
        "operation_id": str(operation_ref.get("operation_id", "")),
        "artifact_id": str(artifact.get("artifact_id", "")) if isinstance(artifact, Mapping) else "",
        "adapter_id": str(artifact.get("adapter_id", "cli.process")) if isinstance(artifact, Mapping) else "cli.process",
        "conformance_ref": str(operation_ref.get("conformance_ref", "")),
        "target": target_kind,
        "state": "fail" if failures else "pass",
        "exit_code": completed.returncode,
        "selected_fields": _selected_fields_or_empty(process_case, completed.stdout) if not failures else {},
        "message": "; ".join(failures) if failures else "",
    }


def _run_python_function_case(*, case: Mapping[str, object], artifact: Mapping[str, object]) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _function_result(case=case, artifact=artifact, state="fail", message="malformed operation_ref")
    function_target = _python_function_target_for_artifact(artifact)
    if function_target is None:
        return _function_result(
            case=case, artifact=artifact, state="unavailable", message="python.function artifact has no importable symbol"
        )
    function_case = _case_function_fixture(case)
    result, failures = run_function_conformance_case(case=function_case, target=function_target)
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "readiness_case": str(case.get("readiness_case", "")),
        "operation_id": str(operation_ref.get("operation_id", "")),
        "artifact_id": str(artifact.get("artifact_id", "")),
        "adapter_id": str(artifact.get("adapter_id", "python.function")),
        "conformance_ref": str(operation_ref.get("conformance_ref", "")),
        "target": "python",
        "state": "fail" if failures else "pass",
        "selected_fields": result.selected_fields if result is not None and result.selected_fields is not None else {},
        "message": "; ".join(failure.message for failure in failures),
    }


def _python_function_target_for_artifact(artifact: Mapping[str, object]) -> FunctionConformanceTarget | None:
    symbol = str(artifact.get("symbol", ""))
    if ":" not in symbol:
        return None
    module_name, function_name = symbol.rsplit(":", 1)
    if not module_name or not function_name:
        return None

    def invoke(values: Mapping[str, object]) -> object:
        module = __import__(module_name, fromlist=[function_name])
        function = getattr(module, function_name)
        return function(dict(values))

    return FunctionConformanceTarget(label=str(artifact.get("artifact_id", "python.function")), invoke=invoke)


def _typescript_runtime_symbol(artifact: Mapping[str, object]) -> tuple[Path, str] | None:
    symbol = str(artifact.get("symbol", ""))
    if ":" not in symbol:
        return None
    runtime_path, function_name = symbol.rsplit(":", 1)
    if not runtime_path or not function_name:
        return None
    return REPO_ROOT / runtime_path, function_name


def _run_typescript_function_case(
    *,
    case: Mapping[str, object],
    artifact: Mapping[str, object],
    temp_root: Path,
    require_node: bool,
) -> dict[str, object]:
    node = shutil.which("node")
    if node is None:
        state = "fail" if require_node else "unavailable"
        return _function_result(case=case, artifact=artifact, state=state, message="node-unavailable")
    runtime_symbol = _typescript_runtime_symbol(artifact)
    if runtime_symbol is None:
        return _function_result(
            case=case, artifact=artifact, state="unavailable", message="typescript.function artifact has no runtime symbol"
        )
    runtime_path, function_name = runtime_symbol
    if not runtime_path.is_file():
        return _function_result(
            case=case,
            artifact=artifact,
            state="unavailable",
            message=f"typescript.function runtime is missing: {runtime_path.relative_to(REPO_ROOT).as_posix()}",
        )

    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _function_result(case=case, artifact=artifact, state="fail", message="malformed operation_ref")
    case_input = case.get("input", {})
    if not isinstance(case_input, Mapping):
        return _function_result(case=case, artifact=artifact, state="fail", message="malformed input block")
    process_case = _case_process_fixture(case)
    fixture_root = materialize_case_fixture(
        case=process_case,
        root=temp_root / str(case.get("id", "case")).replace(".", "-") / "typescript-function",
    )
    function_case = _case_function_fixture(case)
    result, failures = run_typescript_function_conformance_case(
        case=function_case,
        target=TypescriptFunctionConformanceTarget(
            label=str(artifact.get("artifact_id", "typescript.function")),
            runtime_path=runtime_path,
            operation_id=str(operation_ref.get("operation_id", "")),
            operation_path=str(operation_ref.get("operation_path", "")),
            cwd=fixture_root,
            node_command=node,
            function_name=function_name,
            env=generated_package_check._conformance_env(runtime=""),
        ),
    )
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "operation_id": str(operation_ref.get("operation_id", "")),
        "artifact_id": str(artifact.get("artifact_id", "")),
        "adapter_id": str(artifact.get("adapter_id", "typescript.function")),
        "conformance_ref": str(operation_ref.get("conformance_ref", "")),
        "target": "typescript",
        "state": "fail" if failures else "pass",
        "selected_fields": result.selected_fields if result is not None and result.selected_fields is not None else {},
        "message": "; ".join(failure.message for failure in failures),
    }


def _function_result(
    *,
    case: Mapping[str, object],
    artifact: Mapping[str, object],
    state: str,
    message: str,
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    operation_id = operation_ref.get("operation_id", "") if isinstance(operation_ref, Mapping) else ""
    conformance_ref = operation_ref.get("conformance_ref", "") if isinstance(operation_ref, Mapping) else ""
    adapter_id = str(artifact.get("adapter_id", "python.function"))
    target = adapter_id.split(".", 1)[0] if "." in adapter_id else "python"
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "readiness_case": str(case.get("readiness_case", "")),
        "operation_id": str(operation_id),
        "artifact_id": str(artifact.get("artifact_id", "")),
        "adapter_id": adapter_id,
        "conformance_ref": str(conformance_ref),
        "target": target,
        "state": state,
        "message": message,
    }


def _artifact_by_id(registry: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {str(artifact.get("artifact_id", "")): artifact for artifact in registry.get("artifacts", []) if isinstance(artifact, Mapping)}


def _artifact_for_target(
    case: Mapping[str, object],
    target_kind: str,
    artifact_registry: Mapping[str, Mapping[str, object]],
) -> Mapping[str, object] | None:
    for artifact in case.get("artifacts", []):
        if isinstance(artifact, Mapping) and artifact.get("target") == target_kind:
            return artifact_registry.get(str(artifact.get("artifact_id", "")))
    return None


def _evaluate_process_result(
    *,
    case: Mapping[str, object],
    process_case: ProcessConformanceCase,
    completed: subprocess.CompletedProcess[str],
    fixture_root: Path,
) -> list[str]:
    failures: list[str] = []
    if completed.returncode != process_case.expected_exit:
        failures.append(f"expected exit {process_case.expected_exit}, got {completed.returncode}; stderr={completed.stderr!r}")
    expected = case.get("expected", {})
    stderr = expected.get("stderr", {}) if isinstance(expected, Mapping) else {}
    if completed.stderr.strip() and not process_case.allow_stderr:
        failures.append(f"unexpected stderr: {completed.stderr!r}")
    if isinstance(stderr, Mapping):
        missing_stderr = [str(item) for item in stderr.get("contains", []) if str(item) not in completed.stderr]
        if missing_stderr:
            failures.append(f"stderr missing substrings {missing_stderr!r}; stderr={completed.stderr!r}")
    missing_stdout = [item for item in process_case.stdout_contains if item not in completed.stdout]
    if missing_stdout:
        failures.append(f"stdout missing substrings {missing_stdout!r}; stdout={completed.stdout!r}")
    if process_case.expected_fields:
        try:
            selected = process_case.selected_fields(completed.stdout)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            failures.append(f"stdout selected fields unavailable: {exc}; stdout={completed.stdout!r}")
        else:
            if selected != process_case.expected_fields:
                failures.append(f"expected selected fields {process_case.expected_fields!r}, got {selected!r}")
    filesystem = expected.get("filesystem", {}) if isinstance(expected, Mapping) else {}
    if isinstance(filesystem, Mapping):
        for rel_path in filesystem.get("required_paths", []):
            if isinstance(rel_path, str) and not (fixture_root / rel_path).exists():
                failures.append(f"required path missing: {rel_path}")
        for rel_path in filesystem.get("forbidden_paths", []):
            if isinstance(rel_path, str) and (fixture_root / rel_path).exists():
                failures.append(f"forbidden path exists: {rel_path}")
    return failures


def _selected_fields_or_empty(process_case: ProcessConformanceCase, stdout: str) -> dict[str, object]:
    if not process_case.expected_fields:
        return {}
    try:
        return process_case.selected_fields(stdout)
    except (json.JSONDecodeError, KeyError, ValueError):
        return {}


def _result(
    *,
    case: Mapping[str, object],
    artifact_registry: Mapping[str, Mapping[str, object]],
    target_kind: str,
    state: str,
    message: str,
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    operation_id = operation_ref.get("operation_id", "") if isinstance(operation_ref, Mapping) else ""
    conformance_ref = operation_ref.get("conformance_ref", "") if isinstance(operation_ref, Mapping) else ""
    artifact = _artifact_for_target(case, target_kind, artifact_registry)
    return {
        "case_id": str(case.get("id", "")),
        "behavioral_class": str(case.get("behavioral_class", "")),
        "readiness_case": str(case.get("readiness_case", "")),
        "operation_id": str(operation_id),
        "artifact_id": str(artifact.get("artifact_id", "")) if isinstance(artifact, Mapping) else "",
        "adapter_id": str(artifact.get("adapter_id", "")) if isinstance(artifact, Mapping) else "",
        "conformance_ref": str(conformance_ref),
        "target": target_kind,
        "state": state,
        "message": message,
    }


def _case_targets(case: Mapping[str, object], target_selection: str) -> list[str]:
    declared = [str(target.get("kind", "")) for target in case.get("targets", []) if isinstance(target, Mapping)]
    if target_selection == "all":
        return declared
    if target_selection == "parity":
        return declared if case.get("behavioral_class") == "cross-target-parity" else []
    return [target_selection] if target_selection in declared else []


def _append_parity_results(
    results: list[dict[str, object]],
    case: Mapping[str, object],
    selected_targets: list[str],
    artifact_registry: Mapping[str, Mapping[str, object]],
) -> None:
    if case.get("behavioral_class") != "cross-target-parity" or len(selected_targets) < 2:
        return
    case_id = str(case.get("id", ""))
    target_results = [result for result in results if result.get("case_id") == case_id and result.get("target") in selected_targets]
    if any(result.get("state") == "fail" for result in target_results):
        results.append(
            _result(
                case=case, artifact_registry=artifact_registry, target_kind="parity", state="fail", message="one or more target runs failed"
            )
        )
        return
    unavailable = [result for result in target_results if result.get("state") == "unavailable"]
    if unavailable:
        results.append(
            _result(
                case=case,
                artifact_registry=artifact_registry,
                target_kind="parity",
                state="unavailable",
                message="one or more targets unavailable",
            )
        )
        return
    comparable = [(result.get("exit_code"), result.get("selected_fields")) for result in target_results]
    state = "pass" if len(set(json.dumps(item, sort_keys=True) for item in comparable)) == 1 else "fail"
    message = "" if state == "pass" else f"parity drift across targets: {comparable!r}"
    results.append(_result(case=case, artifact_registry=artifact_registry, target_kind="parity", state=state, message=message))


def run_ir_cases(*, target_selection: str, case_filter: set[str], require_node: bool) -> dict[str, object]:
    manifest = operation_conformance_test_ir_manifest()
    registry = operation_artifact_registry_manifest()
    schema_errors = sorted(
        Draft202012Validator(contract_schema("operation_conformance_test_ir.schema.json")).iter_errors(manifest), key=str
    )
    registry_schema_errors = sorted(
        Draft202012Validator(contract_schema("operation_artifact_registry.schema.json")).iter_errors(registry), key=str
    )
    semantic_errors = contract_tooling_check._validate_operation_conformance_test_ir(
        manifest
    ) + contract_tooling_check._validate_operation_artifact_registry(registry)
    all_schema_errors = schema_errors + registry_schema_errors
    if all_schema_errors or semantic_errors:
        return {
            "kind": "operation-conformance-proof/v1",
            "summary": {"state": "fail", "failure_count": len(all_schema_errors) + len(semantic_errors)},
            "cases": [],
            "validation_errors": [error.message for error in all_schema_errors] + semantic_errors,
        }
    cases = [case for case in manifest["initial_cases"] if not case_filter or str(case["id"]) in case_filter]
    artifact_registry = _artifact_by_id(registry)
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-operation-conformance-test-ir-") as tmp:
        temp_root = Path(tmp)
        for case in cases:
            selected_targets = _case_targets(case, target_selection)
            if not selected_targets:
                results.append(
                    _result(
                        case=case,
                        artifact_registry=artifact_registry,
                        target_kind=target_selection,
                        state="skipped",
                        message="case not selected",
                    )
                )
                continue
            for target_kind in selected_targets:
                results.append(
                    _run_case_target(
                        case=case,
                        artifact_registry=artifact_registry,
                        target_kind=target_kind,
                        temp_root=temp_root,
                        require_node=require_node,
                    )
                )
            _append_parity_results(results, case, selected_targets, artifact_registry)
    fail_count = sum(1 for result in results if result.get("state") == "fail")
    unavailable_count = sum(1 for result in results if result.get("state") == "unavailable")
    skipped_count = sum(1 for result in results if result.get("state") == "skipped")
    return {
        "kind": "operation-conformance-proof/v1",
        "target_selection": target_selection,
        "artifact_registry": "operation_artifact_registry.json",
        "case_count": len(cases),
        "summary": {
            "state": "fail" if fail_count else "pass",
            "pass_count": sum(1 for result in results if result.get("state") == "pass"),
            "fail_count": fail_count,
            "unavailable_count": unavailable_count,
            "skipped_count": skipped_count,
        },
        "cases": results,
    }


def _print_text(payload: Mapping[str, object]) -> None:
    summary = payload.get("summary", {})
    state = summary.get("state") if isinstance(summary, Mapping) else "unknown"
    print(f"Operation conformance tests: {state}")
    if isinstance(summary, Mapping):
        print(
            "Cases: "
            f"pass={summary.get('pass_count', 0)} "
            f"fail={summary.get('fail_count', 0)} "
            f"unavailable={summary.get('unavailable_count', 0)} "
            f"skipped={summary.get('skipped_count', 0)}"
        )
    for result in payload.get("cases", []):
        if isinstance(result, Mapping) and result.get("state") != "pass":
            print(f"- {result.get('case_id')} [{result.get('target')}]: {result.get('state')} {result.get('message', '')}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run operation conformance tests.")
    parser.add_argument("--target", choices=["all", "python", "typescript", "parity"], default="all")
    parser.add_argument("--case", action="append", default=[], help="Run only a specific IR case id. May be repeated.")
    parser.add_argument("--require-node", action="store_true", help="Fail when TypeScript cases are selected but Node is unavailable.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = run_ir_cases(target_selection=str(args.target), case_filter=set(args.case), require_node=bool(args.require_node))
    profile = json.loads((REPO_ROOT / "src/agentic_workspace/contracts/external_consumer_profile.json").read_text(encoding="utf-8"))
    receipt_store = build_external_operation_conformance_receipts(profile, conformance_result=payload)
    payload["external_operation_conformance_receipts"] = write_external_operation_conformance_receipts(receipt_store)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_text(payload)
    return 1 if payload.get("summary", {}).get("state") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
