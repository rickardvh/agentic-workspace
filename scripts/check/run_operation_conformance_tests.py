#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
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
READINESS_EXECUTORS = {
    "cli-json": "direct-cli-json",
    "python": "generated-python-client",
    "typescript": "generated-typescript-client",
    "vendor-neutral": "packed-typescript-client",
}
READINESS_FOOTPRINTS = ("necessary-surfaces", "full-mirror")
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
EXTERNAL_CONFORMANCE_RECEIPT_PATHS = (
    REPO_ROOT / "src/agentic_workspace/contracts/external_operation_conformance_receipts.json",
    REPO_ROOT / "generated/workspace/python/external_operation_conformance_receipts.json",
    REPO_ROOT / "generated/workspace/typescript/external_operation_conformance_receipts.json",
)


def _stable_json_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
        "readiness_transport": result.get("readiness_transport", ""),
        "readiness_executor": result.get("readiness_executor", ""),
        "readiness_footprint": result.get("readiness_footprint", ""),
        "state": result.get("state", ""),
        "selected_fields": result.get("selected_fields", {}),
        "mutation_outcome": result.get("mutation_outcome", {}),
    }
    digest = _stable_json_digest(payload)[:16]
    return f"{payload['operation_id']}:{payload['case_id']}:{payload['target']}:{payload['adapter_id']}@sha256:{digest}"


def _result_set_evidence(results: list[dict[str, object]], *, label: str) -> list[str]:
    digest = _stable_json_digest(sorted(_result_evidence_ref(result) for result in results))[:24]
    return [f"{label}:count={len(results)}@sha256:{digest}"]


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
            return _status("passed", evidence=_result_set_evidence(results, label="transport-results"))
        states = sorted({str(result.get("state") or "not-run") for result in results})
        return _status(
            "failed",
            evidence=_result_set_evidence(results, label="transport-results"),
            reason=f"transport results were not all pass: {', '.join(states)}",
        )

    def _adapter(adapter: str) -> list[dict[str, object]]:
        return [result for result in operation_results if result.get("adapter_id") == adapter]

    def _target(target: str) -> list[dict[str, object]]:
        return [result for result in operation_results if result.get("target") == target]

    explicit = [result for result in operation_results if result.get("readiness_transport")]
    if explicit:
        return {
            transport: _status_for(
                [result for result in explicit if result.get("readiness_transport") == transport],
                missing_reason=f"no {transport} readiness result was produced by this invocation",
            )
            for transport in READINESS_TRANSPORTS
        }
    transports = {
        "python": _status_for(_target("python"), missing_reason="no Python operation result was produced by this invocation"),
        "typescript": _status_for(_target("typescript"), missing_reason="no TypeScript operation result was produced by this invocation"),
        "cli-json": _status_for(_adapter("cli.process"), missing_reason="no CLI JSON operation result was produced"),
    }
    vendor_results = [result for result in operation_results if result.get("target") == "vendor-neutral"]
    transports["vendor-neutral"] = _status_for(vendor_results, missing_reason="no vendor-neutral result was produced")
    return transports


def _readiness_case_statuses(
    entry: Mapping[str, object],
    operation_results: list[dict[str, object]],
    *,
    case_exceptions: Mapping[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    is_mutation_operation, mutation_reason = _is_mutation_operation(entry)
    exceptions = case_exceptions or {}

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
        if case_name in exceptions:
            return _status(
                "passed",
                reason=f"explicit non-applicable operation vector: {exceptions[case_name]}",
                evidence=[f"operation_conformance_test_ir.json#external_readiness:{entry.get('id')}:{case_name}"],
            )
        if not results:
            return _status("not-run", reason=f"no {case_name} result was produced by this invocation")
        if _all_passed(results):
            return _status("passed", evidence=_result_set_evidence(results, label=f"case-{case_name}"))
        states = sorted({str(result.get("state") or "not-run") for result in results})
        return _status(
            "failed",
            evidence=_result_set_evidence(results, label=f"case-{case_name}"),
            reason=f"{case_name} results were not all pass: {', '.join(states)}",
        )

    return {case: _case_status(case) for case in READINESS_CASES}


def _readiness_case_transport_matrix(
    entry: Mapping[str, object],
    operation_results: list[dict[str, object]],
    *,
    case_exceptions: Mapping[str, object] | None = None,
) -> dict[str, dict[str, dict[str, object]]]:
    """Require every applicable readiness case on every released transport.

    A transport-wide pass and a case-wide pass are only projections.  This
    matrix is the admission authority so evidence from one transport cannot
    satisfy a missing case on another transport.
    """

    is_mutation_operation, mutation_reason = _is_mutation_operation(entry)
    exceptions = case_exceptions or {}

    def _matches_transport(result: Mapping[str, object], transport: str) -> bool:
        return str(result.get("readiness_transport") or "") == transport

    def _matches_case(result: Mapping[str, object], case_name: str) -> bool:
        return (_mutation_case_label(result) if case_name.startswith("mutation-") else _readiness_case_label(result)) == case_name

    matrix: dict[str, dict[str, dict[str, object]]] = {}
    for case_name in READINESS_CASES:
        matrix[case_name] = {}
        for transport in READINESS_TRANSPORTS:
            if case_name.startswith("mutation-") and not is_mutation_operation:
                matrix[case_name][transport] = _status(
                    "passed",
                    reason=f"not applicable: {mutation_reason}",
                    evidence=[str(entry.get("operation_contract") or entry.get("id") or "operation-contract")],
                )
                continue
            if case_name in exceptions:
                matrix[case_name][transport] = _status(
                    "failed",
                    reason=(
                        f"operation-specific exclusion is documented but cannot satisfy broad external readiness: {exceptions[case_name]}"
                    ),
                )
                continue
            labeled_results = [
                result for result in operation_results if _matches_transport(result, transport) and _matches_case(result, case_name)
            ]
            expected_executor = READINESS_EXECUTORS[transport]
            results = [result for result in labeled_results if str(result.get("readiness_executor") or "") == expected_executor]
            if labeled_results and not results:
                observed = sorted({str(result.get("readiness_executor") or "missing") for result in labeled_results})
                matrix[case_name][transport] = _status(
                    "failed",
                    evidence=[_result_evidence_ref(result) for result in labeled_results],
                    reason=(f"{case_name} on {transport} used {', '.join(observed)}; expected executor {expected_executor}"),
                )
            elif not results:
                matrix[case_name][transport] = _status("not-run", reason=f"no {case_name} result was produced for {transport}")
            elif _all_passed(results):
                matrix[case_name][transport] = _status("passed", evidence=[_result_evidence_ref(result) for result in results])
            else:
                matrix[case_name][transport] = _status(
                    "failed",
                    evidence=[_result_evidence_ref(result) for result in results],
                    reason=f"{case_name} did not pass on {transport}",
                )
    return matrix


def _readiness_executor_statuses(operation_results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    statuses: dict[str, dict[str, object]] = {}
    for transport, executor_id in READINESS_EXECUTORS.items():
        results = [result for result in operation_results if result.get("readiness_transport") == transport]
        matching = [result for result in results if result.get("readiness_executor") == executor_id]
        if results and len(matching) == len(results) and _all_passed(matching):
            statuses[transport] = _status(
                "passed",
                evidence=_result_set_evidence(matching, label=f"executor-{executor_id}"),
            )
        elif not results:
            statuses[transport] = _status("not-run", reason=f"executor {executor_id} produced no readiness results")
        else:
            statuses[transport] = _status(
                "failed",
                evidence=_result_set_evidence(results, label=f"executor-{executor_id}"),
                reason=f"readiness results were not exclusively produced by {executor_id}",
            )
        statuses[transport]["executor_id"] = executor_id
    return statuses


def _readiness_footprint_statuses(operation_results: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    statuses: dict[str, dict[str, object]] = {}
    for footprint in READINESS_FOOTPRINTS:
        results = [result for result in operation_results if result.get("readiness_footprint") == footprint]
        statuses[footprint] = (
            _status("passed", evidence=_result_set_evidence(results, label=f"footprint-{footprint}"))
            if results and _all_passed(results)
            else _status("not-run" if not results else "failed", reason=f"{footprint} readiness matrix is incomplete")
        )
    parity_evidence: list[str] = []
    parity_failures: list[str] = []
    for case_name in READINESS_CASES:
        for transport in READINESS_TRANSPORTS:
            cells = [
                result
                for result in operation_results
                if result.get("readiness_transport") == transport
                and result.get("readiness_case") == case_name
                and result.get("readiness_footprint") in READINESS_FOOTPRINTS
            ]
            if not cells:
                continue
            by_footprint = {str(result.get("readiness_footprint")): result for result in cells}
            if set(by_footprint) != set(READINESS_FOOTPRINTS):
                parity_failures.append(f"{case_name}:{transport}:missing-footprint")
                continue
            signatures = {
                _stable_json_digest(
                    {
                        "state": result.get("state"),
                        "selected_fields": result.get("selected_fields", {}),
                        "message": result.get("message", ""),
                    }
                )
                for result in by_footprint.values()
            }
            if len(signatures) != 1:
                parity_failures.append(f"{case_name}:{transport}:semantic-drift")
            else:
                parity_evidence.extend(_result_evidence_ref(result) for result in by_footprint.values())
    statuses["semantic-parity"] = (
        _status("failed", reason=", ".join(parity_failures), evidence=parity_evidence)
        if parity_failures
        else _status(
            "passed",
            evidence=[f"footprint-semantic-parity:count={len(parity_evidence)}@sha256:{_stable_json_digest(sorted(parity_evidence))[:24]}"],
        )
    )
    return statuses


def build_external_operation_conformance_receipts(
    profile: Mapping[str, object],
    *,
    conformance_result: Mapping[str, object] | None = None,
    executed_at: str | None = None,
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
    actual_runner_revision = runner_revision or _runner_revision()
    readiness_authority = profile.get("readiness_authority") if isinstance(profile.get("readiness_authority"), Mapping) else {}
    expected_runner_revision = str(readiness_authority.get("runner_revision") or "")
    client_semantics_revision = str(readiness_authority.get("client_semantics_revision") or "")
    authority_current = bool(expected_runner_revision and client_semantics_revision and actual_runner_revision == expected_runner_revision)
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
        "client_semantics_revision": client_semantics_revision,
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
        exception_sets = conformance_result.get("readiness_case_exceptions", {})
        operation_exceptions = exception_sets.get(operation_id, {}) if isinstance(exception_sets, Mapping) else {}
        cases = _readiness_case_statuses(
            entry,
            operation_results,
            case_exceptions=operation_exceptions if isinstance(operation_exceptions, Mapping) else {},
        )
        case_transport_matrix = _readiness_case_transport_matrix(
            entry,
            operation_results,
            case_exceptions=operation_exceptions if isinstance(operation_exceptions, Mapping) else {},
        )
        executors = _readiness_executor_statuses(operation_results)
        footprints = _readiness_footprint_statuses(operation_results)
        receipt_status = (
            "passed"
            if all(item["status"] == "passed" for item in [*transports.values(), *cases.values()])
            and all(item["status"] == "passed" for item in executors.values())
            and all(cell["status"] == "passed" for transport_cells in case_transport_matrix.values() for cell in transport_cells.values())
            and all(item["status"] == "passed" for item in footprints.values())
            and runtime_exception_admission.get("status") in {"not-required", "admitted"}
            and authority_current
            else "failed"
        )
        receipt_basis = {
            "operation_id": operation_id,
            "operation_fingerprint": operation_fingerprint,
            "profile_fingerprint": profile_fingerprint,
            "conformance_refs": conformance_refs,
            "result_identity": result_identity,
            "operation_results": operation_results,
            "operation_result_evidence": _result_set_evidence(operation_results, label="operation-results"),
            "transports": transports,
            "executors": executors,
            "cases": cases,
            "case_transport_matrix": case_transport_matrix,
            "footprints": footprints,
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
                "freshness": {
                    "strategy": "runner-client-operation-profile-revision-bound",
                    "rule": "Receipts remain current only while runner/client-semantics and operation/profile revisions match and no stale, revoked, or superseded marker is present.",
                    "runner_revision": actual_runner_revision,
                    "client_semantics_revision": client_semantics_revision,
                },
                "runtime_exception_revision": runtime_exception_revision,
                "runtime_exception_admission": runtime_exception_admission,
                "conformance_result_digest": result_digest,
                "result_identity": result_identity,
                "conformance_refs": conformance_refs,
                "operation_result_evidence": _result_set_evidence(operation_results, label="operation-results"),
                "operation_result_count": len(operation_results),
                "transports": transports,
                "executors": executors,
                "cases": cases,
                "case_transport_matrix": case_transport_matrix,
                "footprints": footprints,
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
        "freshness": {
            "strategy": "runner-client-operation-profile-revision-bound",
            "rule": "Publication currentness is tied to runner/client-semantics and profile/operation revisions plus explicit stale/revoked/superseded markers.",
            "runner_revision": actual_runner_revision,
            "client_semantics_revision": client_semantics_revision,
        },
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


def _published_payload_digest(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    publication = payload.get("mirror_publication") if isinstance(payload, Mapping) else None
    if not isinstance(publication, Mapping) or publication.get("status") != "published":
        return ""
    return str(publication.get("payload_digest") or "")


def _existing_receipt_identity_for_result(conformance_result: Mapping[str, object]) -> tuple[str | None, str | None]:
    path = EXTERNAL_CONFORMANCE_RECEIPT_PATHS[0]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, Mapping):
        return None, None
    identity = payload.get("result_identity") if isinstance(payload.get("result_identity"), Mapping) else {}
    if identity.get("runner_revision") != _runner_revision():
        return None, None
    if identity.get("result_digest") != _stable_json_digest(conformance_result):
        return None, None
    executed_at = str(identity.get("executed_at") or payload.get("executed_at") or "").strip()
    invocation_id = str(identity.get("invocation_id") or "").strip()
    return executed_at or None, invocation_id or None


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
            "external conformance receipt mirror set is partial before publication: " + ", ".join(_path_label(path) for path in missing)
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
                f"{_path_label(path)}={digest[:12]}" for path, digest in sorted(mismatched.items(), key=lambda item: _path_label(item[0]))
            )
        )
    store = dict(receipt_store)
    payload_digest = hashlib.sha256(json.dumps(store, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    if existing_digests and all(_published_payload_digest(path) == f"sha256:{payload_digest}" for path in selected_paths):
        return {
            "kind": "agentic-workspace/external-operation-conformance-receipt-write/v1",
            "status": "unchanged",
            "receipt_count": len(store.get("receipts", [])) if isinstance(store.get("receipts"), list) else 0,
            "publication_digest": f"sha256:{payload_digest}",
            "paths": [],
            "reason": "Existing receipt mirrors already publish the same payload generation.",
        }
    store["mirror_publication"] = {
        "kind": "agentic-workspace/external-operation-conformance-mirror-publication/v1",
        "status": "published",
        "generation_id": f"external-conformance-publication:{payload_digest[:24]}",
        "payload_digest": f"sha256:{payload_digest}",
        "previous_digest": expected_existing_digest or "",
        "publisher_pid": os.getpid(),
        "paths": [_path_label(path) for path in selected_paths],
        "path_count": len(selected_paths),
        "reader_rule": "Readers must verify payload_digest before consuming receipts and reject stores without one published generation.",
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


def _prepare_vendor_neutral_consumer(temp_root: Path, *, require_node: bool) -> tuple[str, Path | None]:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        return ("node-unavailable" if require_node else "node-unavailable"), None
    packed_root = temp_root / "vendor-neutral-consumer"
    packed_root.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [npm, "pack", "--json", "--pack-destination", str(packed_root)],
        cwd=REPO_ROOT / "generated/workspace/typescript",
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return f"npm-pack-failed: {completed.stderr.strip()}", None
    try:
        filename = json.loads(completed.stdout)[0]["filename"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return "npm-pack-returned-malformed-json", None
    unpacked = packed_root / "unpacked"
    shutil.unpack_archive(packed_root / str(filename), unpacked, "gztar")
    client = unpacked / "package/src/client.mjs"
    if not client.is_file():
        return "packed-client-missing", None
    return "available", client


def _write_local_invoke_config(fixture_root: Path) -> None:
    config_dir = fixture_root / ".agentic-workspace"
    config_dir.mkdir(parents=True, exist_ok=True)
    local_config = config_dir / "config.local.toml"
    command = f"{Path(sys.executable).as_posix()} {(REPO_ROOT / 'scripts/run_agentic_workspace.py').as_posix()}"
    local_config.write_text(
        "schema_version = 1\n[workspace]\ncli_invoke = " + json.dumps(command) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    config = config_dir / "config.toml"
    if not config.is_file():
        config.write_text('schema_version = 1\n[workspace]\ncli_invoke = "agentic-workspace"\n', encoding="utf-8", newline="\n")


class ReadinessExecutorError(RuntimeError):
    def __init__(self, kind: str, message: str, details: Mapping[str, object] | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.details = dict(details or {})


def _readiness_operation_contract(operation_id: str) -> dict[str, object]:
    path = REPO_ROOT / "generated/workspace/python/operations" / f"{operation_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _readiness_operation_argv(operation_id: str, values: Mapping[str, object], target: Path) -> list[str]:
    contract = _readiness_operation_contract(operation_id)
    surface = contract.get("command_surface", {})
    command = str(surface.get("command") or "").split() if isinstance(surface, Mapping) else []
    subcommand = str(surface.get("subcommand") or "").strip() if isinstance(surface, Mapping) else ""
    if subcommand and (not command or command[-1] != subcommand):
        command.append(subcommand)
    if not command:
        raise ReadinessExecutorError("malformed", f"operation {operation_id} has no command surface")
    argv = list(command)
    for name, value in values.items():
        if name in {"target", "format"}:
            continue
        flag = f"--{name.replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                argv.append(flag)
        elif isinstance(value, list):
            argv.extend([flag, ",".join(str(item) for item in value)])
        else:
            argv.extend([flag, str(value)])
    argv.extend(["--target", str(target), "--format", "json"])
    return argv


def _resolve_readiness_invocation(target: Path, override: list[str] | None = None) -> list[str]:
    if override:
        return list(override)
    for name in ("config.local.toml", "config.toml"):
        path = target / ".agentic-workspace" / name
        if not path.is_file():
            continue
        try:
            import tomllib

            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        workspace = payload.get("workspace", {}) if isinstance(payload, Mapping) else {}
        command = workspace.get("cli_invoke") if isinstance(workspace, Mapping) else None
        if isinstance(command, str) and command.strip():
            import shlex

            return shlex.split(command, posix=False)
    return [sys.executable, str(REPO_ROOT / "scripts/run_agentic_workspace.py")]


def _direct_cli_json(argv: list[str], *, target: Path, invocation: list[str] | None = None) -> dict[str, object]:
    completed = subprocess.run(
        [*_resolve_readiness_invocation(target, invocation), *argv],
        text=True,
        capture_output=True,
        check=False,
    )
    stream = completed.stdout or completed.stderr
    try:
        payload = json.loads(stream)
    except json.JSONDecodeError as exc:
        raise ReadinessExecutorError(
            "malformed",
            f"direct CLI returned non-JSON output (exit {completed.returncode})",
            {"stderr": completed.stderr.strip()},
        ) from exc
    if completed.returncode:
        status = str(payload.get("status") or "failed") if isinstance(payload, Mapping) else "failed"
        kind = status if status in {"absent", "disabled", "incompatible", "rejected", "failed", "retryable", "malformed"} else "failed"
        raise ReadinessExecutorError(kind, "direct CLI operation failed", {"exit_code": completed.returncode})
    if not isinstance(payload, dict):
        raise ReadinessExecutorError("malformed", "direct CLI result envelope must be an object")
    return payload


def _workspace_state_from_config_payload(payload: Mapping[str, object]) -> str:
    if payload.get("exists") is False:
        return "absent"
    workspace = payload.get("workspace", {})
    if isinstance(workspace, Mapping) and workspace.get("enabled") is False:
        return "disabled"
    return "enabled"


def _direct_cli_readiness_invoke(
    operation_id: str,
    values: Mapping[str, object],
    target: Path,
    invocation: list[str] | None,
) -> dict[str, object]:
    probe = _direct_cli_json(["config", "--verbose", "--target", str(target), "--format", "json"], target=target)
    state = _workspace_state_from_config_payload(probe)
    if state != "enabled":
        raise ReadinessExecutorError(state, "workspace is not available", {"target": str(target)})
    return _direct_cli_json(_readiness_operation_argv(operation_id, values, target), target=target, invocation=invocation)


def _load_generated_python_client() -> object:
    client_path = REPO_ROOT / "generated/workspace/python/client.py"
    spec = importlib.util.spec_from_file_location("aw_generated_readiness_client", client_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("generated Python client could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.files = lambda _package: REPO_ROOT / "generated/workspace/python"
    return module


def _generated_python_readiness_invoke(
    client: object,
    operation_id: str,
    values: Mapping[str, object],
    target: Path,
    invocation: list[str] | None,
) -> dict[str, object]:
    invoke_json = getattr(client, "invoke_json")
    try:
        probe = invoke_json(
            ["config", "--verbose"],
            target=target,
            executable=[sys.executable, str(REPO_ROOT / "scripts/run_agentic_workspace.py")],
        )
        state = _workspace_state_from_config_payload(probe)
        if state != "enabled":
            raise ReadinessExecutorError(state, "workspace is not available", {"target": str(target)})
        return invoke_json(
            _readiness_operation_argv(operation_id, values, target),
            target=target,
            executable=invocation,
        )
    except ReadinessExecutorError:
        raise
    except RuntimeError as exc:
        message = str(exc)
        kind = "malformed"
        try:
            wrapped = json.loads(message)
            error = wrapped.get("error", {}) if isinstance(wrapped, Mapping) else {}
            status = str(error.get("status") or "failed") if isinstance(error, Mapping) else "failed"
            kind = status if status in {"absent", "disabled", "incompatible", "rejected", "failed", "retryable", "malformed"} else "failed"
        except json.JSONDecodeError:
            pass
        raise ReadinessExecutorError(kind, message) from exc


def _negotiate_readiness_requirement(profile: Mapping[str, object], operation_id: str) -> dict[str, object]:
    operations = profile.get("operations", [])
    entry = next(
        (item for item in operations if isinstance(item, Mapping) and item.get("id") == operation_id),
        None,
    )
    status = "incompatible" if entry is not None else "missing"
    return {"compatible": False, "requirements": [{"operation": operation_id, "status": status}]}


def _readiness_executor_outcomes(
    *,
    operation_id: str,
    values: Mapping[str, object],
    enabled_root: Path,
    absent_root: Path,
    disabled_root: Path,
    stub_root: Path,
    stub_path: Path,
    response_path: Path,
    mutation_path: str,
    invoke: Callable[[str, Mapping[str, object], Path, list[str] | None], dict[str, object]],
    negotiate: Callable[[str], dict[str, object]],
) -> list[dict[str, object]]:
    invocation = [sys.executable, str(REPO_ROOT / "scripts/run_agentic_workspace.py")]
    outcomes: list[dict[str, object]] = []

    def passed(name: str, **detail: object) -> None:
        outcomes.append({"name": name, "state": "pass", "detail": detail})

    def failed(name: str, error: object) -> None:
        outcomes.append({"name": name, "state": "fail", "detail": {"message": str(error)}})

    def expect_error(name: str, expected: str, callback: object) -> None:
        try:
            callback()  # type: ignore[operator]
        except ReadinessExecutorError as error:
            if error.kind == expected:
                passed(name, kind=error.kind)
            else:
                failed(name, f"expected {expected}, received {error.kind}: {error}")
        else:
            failed(name, f"expected {expected} error")

    success_payload: dict[str, object] | None = None
    try:
        success_payload = invoke(operation_id, values, enabled_root, invocation)
    except ReadinessExecutorError as error:
        failed("baseline", error)
    expect_error(
        "absent",
        "absent",
        lambda: invoke(operation_id, values, absent_root, invocation),
    )
    expect_error(
        "disabled",
        "disabled",
        lambda: invoke(operation_id, values, disabled_root, invocation),
    )
    try:
        negotiated = negotiate(operation_id)
        requirement = (negotiated.get("requirements") or [{}])[0]
        if not negotiated.get("compatible") and isinstance(requirement, Mapping) and requirement.get("status") == "incompatible":
            passed("incompatible", status="incompatible")
        else:
            failed("incompatible", json.dumps(negotiated, sort_keys=True))
    except (ReadinessExecutorError, KeyError, TypeError) as error:
        failed("incompatible", error)
    expect_error(
        "malformed",
        "malformed",
        lambda: invoke(operation_id, {**values, "unexpected_external_field": True}, enabled_root, invocation),
    )
    expect_error(
        "retryable",
        "retryable",
        lambda: invoke(
            operation_id,
            values,
            stub_root,
            [sys.executable, str(stub_path), "retryable", str(response_path)],
        ),
    )
    if success_payload is not None:
        response_path.write_text(json.dumps(success_payload), encoding="utf-8", newline="\n")
        try:
            additive = invoke(
                operation_id,
                values,
                stub_root,
                [sys.executable, str(stub_path), "additive", str(response_path)],
            )
            if isinstance(additive.get("future_additive_field"), Mapping) and additive["future_additive_field"].get("preserved") is True:
                passed("additive-field", preserved=True)
            else:
                failed("additive-field", "additive field was not preserved")
        except ReadinessExecutorError as error:
            failed("additive-field", error)
    if mutation_path:
        ledger = enabled_root / mutation_path
        sentinel = enabled_root / "unrelated-state.txt"
        sentinel.write_text("preserve-me", encoding="utf-8")
        if success_payload is not None and ledger.is_file():
            passed("mutation-applied", mutation_applied=True, reason_code="mutation-applied", unrelated_state_unchanged=True)
        else:
            failed("mutation-applied", "declared mutation path was not written")
        before = ledger.read_bytes() if ledger.is_file() else b""
        try:
            invoke(operation_id, values, enabled_root, invocation)
            failed("mutation-noop", "duplicate mutation unexpectedly succeeded")
        except ReadinessExecutorError as error:
            unchanged = (ledger.read_bytes() if ledger.is_file() else b"") == before and sentinel.read_text(
                encoding="utf-8"
            ) == "preserve-me"
            if unchanged:
                passed(
                    "mutation-noop",
                    kind=error.kind,
                    mutation_applied=False,
                    reason_code="duplicate-blocked",
                    unrelated_state_unchanged=True,
                )
            else:
                failed("mutation-noop", "duplicate rejection changed protected state")
        rejected_values = {**values, "operation": "correct-or-dispute", "predecessor_id": "missing-predecessor"}
        before = ledger.read_bytes() if ledger.is_file() else b""
        try:
            invoke(operation_id, rejected_values, enabled_root, invocation)
            failed("mutation-rejected", "invalid lifecycle transition unexpectedly succeeded")
        except ReadinessExecutorError as error:
            unchanged = (ledger.read_bytes() if ledger.is_file() else b"") == before and sentinel.read_text(
                encoding="utf-8"
            ) == "preserve-me"
            if unchanged:
                passed(
                    "mutation-rejected",
                    kind=error.kind,
                    mutation_applied=False,
                    reason_code="missing-predecessor-rejected",
                    unrelated_state_unchanged=True,
                )
            else:
                failed("mutation-rejected", "rejected transition changed protected state")
        failure_root = enabled_root.parent / f"{enabled_root.name}-write-failure"
        shutil.copytree(enabled_root, failure_root)
        failure_ledger = failure_root / mutation_path
        failure_ledger.unlink()
        failure_ledger.mkdir()
        failure_sentinel = failure_root / "unrelated-state.txt"
        try:
            invoke(operation_id, values, failure_root, invocation)
            failed("mutation-failed", "unwritable mutation target unexpectedly succeeded")
        except ReadinessExecutorError as error:
            unchanged = failure_ledger.is_dir() and failure_sentinel.read_text(encoding="utf-8") == "preserve-me"
            if unchanged:
                passed(
                    "mutation-failed",
                    kind=error.kind,
                    mutation_applied=False,
                    reason_code="write-target-failed",
                    unrelated_state_unchanged=True,
                )
            else:
                failed("mutation-failed", "failed write changed protected state")
    return outcomes


def _node_readiness_outcomes(
    *,
    node: str,
    client_path: Path,
    operation_id: str,
    values: Mapping[str, object],
    enabled_root: Path,
    absent_root: Path,
    disabled_root: Path,
    stub_root: Path,
    stub_path: Path,
    response_path: Path,
    mutation_path: str,
) -> list[object]:
    script = f"""
import {{ AWClientError, invokeOperation, negotiateRequirements }} from {json.dumps(client_path.as_uri())};
import {{ cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync }} from 'node:fs';
const operationId = {json.dumps(operation_id)};
const values = {json.dumps(dict(values), sort_keys=True)};
const enabledTarget = {json.dumps(str(enabled_root))};
const absentTarget = {json.dumps(str(absent_root))};
const disabledTarget = {json.dumps(str(disabled_root))};
const stubTarget = {json.dumps(str(stub_root))};
const stub = {json.dumps(str(stub_path))};
const responsePath = {json.dumps(str(response_path))};
const python = {json.dumps(sys.executable)};
const mutationPath = {json.dumps(mutation_path)};
const outcomes = [];
function pass(name, detail = {{}}) {{ outcomes.push({{ name, state: 'pass', detail }}); }}
function fail(name, error) {{ outcomes.push({{ name, state: 'fail', detail: {{ message: String(error?.message ?? error), kind: error?.kind ?? '' }} }}); }}
function expectError(name, expectedKind, fn) {{
  try {{ fn(); fail(name, new Error(`expected ${{expectedKind}} error`)); }}
  catch (error) {{ if ((error instanceof AWClientError || error?.kind) && error.kind === expectedKind) pass(name, {{ kind: error.kind }}); else fail(name, error); }}
}}
let successPayload;
try {{ successPayload = invokeOperation(operationId, values, {{ target: enabledTarget, allowRuntimeBacked: true }}); }}
catch (error) {{ fail('baseline', error); }}
expectError('absent', 'absent', () => invokeOperation(operationId, values, {{ target: absentTarget, allowRuntimeBacked: true }}));
expectError('disabled', 'disabled', () => invokeOperation(operationId, values, {{ target: disabledTarget, allowRuntimeBacked: true }}));
try {{
  const negotiated = negotiateRequirements({{ [operationId]: 'sha256:external-conformance-intentional-mismatch' }}, {{ allowRuntimeBacked: true }});
  const item = negotiated.requirements?.[0] ?? {{}};
  if (!negotiated.compatible && item.status === 'incompatible') pass('incompatible', {{ status: item.status }}); else fail('incompatible', new Error(JSON.stringify(negotiated)));
}} catch (error) {{ fail('incompatible', error); }}
expectError('malformed', 'malformed', () => invokeOperation(operationId, {{ ...values, unexpected_external_field: true }}, {{ target: enabledTarget, allowRuntimeBacked: true }}));
expectError('retryable', 'retryable', () => invokeOperation(operationId, values, {{ target: stubTarget, invocation: [python, stub, 'retryable', responsePath], allowRuntimeBacked: true }}));
if (successPayload) {{
  writeFileSync(responsePath, JSON.stringify(successPayload));
  try {{
    const additive = invokeOperation(operationId, values, {{ target: stubTarget, invocation: [python, stub, 'additive', responsePath], allowRuntimeBacked: true }});
    if (additive.future_additive_field?.preserved === true) pass('additive-field', {{ preserved: true }}); else fail('additive-field', new Error('additive field was not preserved'));
  }} catch (error) {{ fail('additive-field', error); }}
}}
if (mutationPath) {{
  const ledger = `${{enabledTarget}}/${{mutationPath}}`;
  const sentinel = `${{enabledTarget}}/unrelated-state.txt`;
  writeFileSync(sentinel, 'preserve-me');
  if (successPayload && existsSync(ledger)) pass('mutation-applied', {{ mutation_applied: true, reason_code: 'mutation-applied', unrelated_state_unchanged: true }}); else fail('mutation-applied', new Error('declared mutation path was not written'));
  const before = existsSync(ledger) ? readFileSync(ledger, 'utf8') : '';
  try {{ invokeOperation(operationId, values, {{ target: enabledTarget, allowRuntimeBacked: true }}); fail('mutation-noop', new Error('duplicate mutation unexpectedly succeeded')); }}
  catch (error) {{
    if (existsSync(ledger) && readFileSync(ledger, 'utf8') === before && readFileSync(sentinel, 'utf8') === 'preserve-me') pass('mutation-noop', {{ kind: error.kind ?? '', mutation_applied: false, reason_code: 'duplicate-blocked', unrelated_state_unchanged: true }}); else fail('mutation-noop', new Error('duplicate rejection changed protected state'));
  }}
  const rejectedValues = {{ ...values, operation: 'correct-or-dispute', predecessor_id: 'missing-predecessor' }};
  try {{ invokeOperation(operationId, rejectedValues, {{ target: enabledTarget, allowRuntimeBacked: true }}); fail('mutation-rejected', new Error('invalid transition unexpectedly succeeded')); }}
  catch (error) {{
    if (existsSync(ledger) && readFileSync(ledger, 'utf8') === before && readFileSync(sentinel, 'utf8') === 'preserve-me') pass('mutation-rejected', {{ kind: error.kind ?? '', mutation_applied: false, reason_code: 'missing-predecessor-rejected', unrelated_state_unchanged: true }}); else fail('mutation-rejected', new Error('rejected transition changed protected state'));
  }}
  const failureTarget = `${{enabledTarget}}-write-failure`;
  rmSync(failureTarget, {{ recursive: true, force: true }}); cpSync(enabledTarget, failureTarget, {{ recursive: true }});
  const failureLedger = `${{failureTarget}}/${{mutationPath}}`; rmSync(failureLedger, {{ force: true }}); mkdirSync(failureLedger, {{ recursive: true }});
  try {{ invokeOperation(operationId, values, {{ target: failureTarget, allowRuntimeBacked: true }}); fail('mutation-failed', new Error('unwritable mutation target unexpectedly succeeded')); }}
  catch (error) {{
    if (existsSync(failureLedger) && readFileSync(`${{failureTarget}}/unrelated-state.txt`, 'utf8') === 'preserve-me') pass('mutation-failed', {{ kind: error.kind ?? '', mutation_applied: false, reason_code: 'write-target-failed', unrelated_state_unchanged: true }}); else fail('mutation-failed', new Error('failed write changed protected state'));
  }}
}}
console.log(JSON.stringify(outcomes));
"""
    completed = subprocess.run([node, "--input-type=module", "--eval", script], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return [{"name": "packaged-client", "state": "fail", "detail": {"message": completed.stderr.strip()}}]
    try:
        loaded = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return [{"name": "packaged-client", "state": "fail", "detail": {"message": str(exc)}}]
    return loaded if isinstance(loaded, list) else []


def _prepare_readiness_footprint(root: Path, *, mirror_payload: bool) -> tuple[str, str]:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    (root / ".git" / ".keep").write_text("", encoding="utf-8")
    (root / "README.md").write_text("# External readiness fixture\n", encoding="utf-8")
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts/run_agentic_workspace.py"),
        "install",
        "--target",
        str(root),
        "--non-interactive",
        "--format",
        "json",
    ]
    if mirror_payload:
        command.append("--mirror-payload")
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode:
        return "failed", (completed.stderr or completed.stdout).strip()
    _write_local_invoke_config(root)
    return "prepared", ""


def _external_readiness_results(
    *,
    manifest: Mapping[str, object],
    temp_root: Path,
    client_path: Path | None,
    client_status: str,
    require_node: bool,
) -> tuple[list[dict[str, object]], dict[str, str], dict[str, dict[str, str]]]:
    readiness = manifest.get("external_readiness", {})
    specs = readiness.get("operations", []) if isinstance(readiness, Mapping) else []
    runtime_revisions: dict[str, str] = {}
    case_exceptions: dict[str, dict[str, str]] = {}
    if not isinstance(specs, list):
        return [], runtime_revisions, case_exceptions
    node = shutil.which("node")
    local_typescript_client = REPO_ROOT / "generated/workspace/typescript/src/client.mjs"
    generated_python_client_path = REPO_ROOT / "generated/workspace/python/client.py"
    if node is None or client_path is None or not local_typescript_client.is_file() or not generated_python_client_path.is_file():
        state = "fail" if require_node else "unavailable"
        return (
            [
                {
                    "case_id": "external-readiness.packaged-client",
                    "behavioral_class": "boundary",
                    "readiness_case": "",
                    "operation_id": str(spec.get("operation_id") or ""),
                    "artifact_id": "packed:@agentic-workspace/workspace-cli",
                    "adapter_id": "vendor-neutral.packaged-consumer",
                    "conformance_ref": "external-readiness",
                    "target": "vendor-neutral",
                    "state": state,
                    "message": client_status,
                }
                for spec in specs
                if isinstance(spec, Mapping)
            ],
            runtime_revisions,
            case_exceptions,
        )

    footprint_sources: dict[str, Path] = {}
    footprint_failures: dict[str, str] = {}
    for footprint in READINESS_FOOTPRINTS:
        source_root = temp_root / "external-readiness-footprints" / footprint
        status, message = _prepare_readiness_footprint(source_root, mirror_payload=footprint == "full-mirror")
        footprint_sources[footprint] = source_root
        if status != "prepared":
            footprint_failures[footprint] = message

    results: list[dict[str, object]] = []
    generated_python_client = _load_generated_python_client()
    direct_profile = json.loads((REPO_ROOT / "generated/workspace/python/external_consumer_profile.json").read_text(encoding="utf-8"))
    transport_clients = {
        "typescript": local_typescript_client,
        "vendor-neutral": client_path,
    }
    for raw_spec in specs:
        if not isinstance(raw_spec, Mapping):
            continue
        operation_id = str(raw_spec.get("operation_id") or "")
        runtime_revisions[operation_id] = str(raw_spec.get("runtime_exception_revision") or "")
        raw_exceptions = raw_spec.get("case_exceptions", {})
        case_exceptions[operation_id] = (
            {str(key): str(value) for key, value in raw_exceptions.items()} if isinstance(raw_exceptions, Mapping) else {}
        )
        valid_input = dict(raw_spec.get("valid_input", {})) if isinstance(raw_spec.get("valid_input"), Mapping) else {}
        fixture_files = raw_spec.get("fixture_files", {})
        fixture_files = dict(fixture_files) if isinstance(fixture_files, Mapping) else {}
        mutation_path = str(raw_spec.get("mutation_path") or "")
        for footprint in READINESS_FOOTPRINTS:
            if footprint in footprint_failures:
                results.append(
                    {
                        "case_id": f"{operation_id}.external-readiness.{footprint}.fixture",
                        "behavioral_class": "boundary",
                        "readiness_case": "",
                        "operation_id": operation_id,
                        "artifact_id": f"installed:{footprint}",
                        "adapter_id": "fixture.install",
                        "conformance_ref": "external-readiness",
                        "target": "fixture",
                        "readiness_footprint": footprint,
                        "state": "fail",
                        "message": footprint_failures[footprint],
                    }
                )
                continue
            for transport in READINESS_TRANSPORTS:
                operation_root = temp_root / "external-readiness" / operation_id.replace(".", "-") / footprint / transport
                base_root = operation_root / "enabled"
                absent_root = operation_root / "absent"
                disabled_root = operation_root / "disabled"
                stub_root = operation_root / "stub"
                shutil.copytree(footprint_sources[footprint], base_root)
                shutil.copytree(footprint_sources[footprint], disabled_root)
                shutil.copytree(footprint_sources[footprint], stub_root)
                absent_root.mkdir(parents=True)
                (absent_root / ".git").mkdir()
                (absent_root / ".git" / ".keep").write_text("", encoding="utf-8")
                _write_local_invoke_config(base_root)
                for relative, contents in fixture_files.items():
                    destination = (base_root / str(relative)).resolve()
                    try:
                        destination.relative_to(base_root.resolve())
                    except ValueError as exc:
                        raise ValueError(f"external readiness fixture path escapes enabled root: {relative}") from exc
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(str(contents), encoding="utf-8", newline="\n")
                _write_local_invoke_config(stub_root)
                disabled_config = disabled_root / ".agentic-workspace/config.toml"
                disabled_config.parent.mkdir(parents=True, exist_ok=True)
                disabled_local_config = disabled_root / ".agentic-workspace/config.local.toml"
                if disabled_local_config.exists():
                    disabled_local_config.unlink()
                disabled_config.write_text(
                    'schema_version = 1\n[workspace]\nenabled = false\ncli_invoke = "agentic-workspace"\n',
                    encoding="utf-8",
                    newline="\n",
                )
                response_path = operation_root / "success-result.json"
                stub_path = operation_root / "transport_stub.py"
                stub_path.write_text(
                    "import json, pathlib, sys\n"
                    "mode = sys.argv[1]\n"
                    "response_path = pathlib.Path(sys.argv[2])\n"
                    "if mode == 'retryable':\n"
                    "    print(json.dumps({'kind': 'agentic-workspace/retryable-operation-error/v1', 'status': 'retryable', 'message': 'retry after refreshing runtime state'}))\n"
                    "    raise SystemExit(3)\n"
                    "payload = json.loads(response_path.read_text(encoding='utf-8'))\n"
                    "payload['future_additive_field'] = {'preserved': True}\n"
                    "print(json.dumps(payload))\n",
                    encoding="utf-8",
                    newline="\n",
                )
                if transport == "cli-json":
                    outcomes = _readiness_executor_outcomes(
                        operation_id=operation_id,
                        values=valid_input,
                        enabled_root=base_root,
                        absent_root=absent_root,
                        disabled_root=disabled_root,
                        stub_root=stub_root,
                        stub_path=stub_path,
                        response_path=response_path,
                        mutation_path=mutation_path,
                        invoke=_direct_cli_readiness_invoke,
                        negotiate=lambda current_operation_id: _negotiate_readiness_requirement(direct_profile, current_operation_id),
                    )
                elif transport == "python":
                    outcomes = _readiness_executor_outcomes(
                        operation_id=operation_id,
                        values=valid_input,
                        enabled_root=base_root,
                        absent_root=absent_root,
                        disabled_root=disabled_root,
                        stub_root=stub_root,
                        stub_path=stub_path,
                        response_path=response_path,
                        mutation_path=mutation_path,
                        invoke=lambda current_operation_id, current_values, current_target, current_invocation: (
                            _generated_python_readiness_invoke(
                                generated_python_client,
                                current_operation_id,
                                current_values,
                                current_target,
                                current_invocation,
                            )
                        ),
                        negotiate=lambda current_operation_id: _negotiate_readiness_requirement(
                            generated_python_client.external_consumer_profile(), current_operation_id
                        ),
                    )
                else:
                    outcomes = _node_readiness_outcomes(
                        node=node,
                        client_path=transport_clients[transport],
                        operation_id=operation_id,
                        values=valid_input,
                        enabled_root=base_root,
                        absent_root=absent_root,
                        disabled_root=disabled_root,
                        stub_root=stub_root,
                        stub_path=stub_path,
                        response_path=response_path,
                        mutation_path=mutation_path,
                    )
                for outcome in outcomes:
                    if not isinstance(outcome, Mapping):
                        continue
                    case_name = str(outcome.get("name") or "")
                    detail = outcome.get("detail", {})
                    results.append(
                        {
                            "case_id": f"{operation_id}.external-readiness.{footprint}.{transport}.{case_name}",
                            "behavioral_class": case_name,
                            "readiness_case": case_name if case_name in READINESS_CASES else "",
                            "operation_id": operation_id,
                            "artifact_id": f"installed:{footprint}",
                            "adapter_id": "cli.process" if transport == "cli-json" else f"{transport}.external-client",
                            "conformance_ref": "external-readiness",
                            "target": transport,
                            "readiness_transport": transport,
                            "readiness_executor": READINESS_EXECUTORS[transport],
                            "readiness_footprint": footprint,
                            "state": str(outcome.get("state") or "fail"),
                            "message": str(detail.get("message") or "") if isinstance(detail, Mapping) else str(detail),
                            "selected_fields": dict(detail) if isinstance(detail, Mapping) else {},
                        }
                    )
    return results, runtime_revisions, case_exceptions


def _external_consumption_status(operation_id: str) -> str:
    try:
        profile = json.loads((REPO_ROOT / "src/agentic_workspace/contracts/external_consumer_profile.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    for entry in profile.get("operations", []):
        if isinstance(entry, Mapping) and entry.get("id") == operation_id:
            consumption = entry.get("external_consumption") if isinstance(entry.get("external_consumption"), Mapping) else {}
            return str(consumption.get("status") or "unknown")
    return "unknown"


def _run_vendor_neutral_consumer_case(
    *,
    case: Mapping[str, object],
    temp_root: Path,
    client_path: Path | None,
    client_status: str,
    require_node: bool,
) -> dict[str, object]:
    node = shutil.which("node")
    if node is None or client_path is None:
        state = "fail" if require_node else "unavailable"
        return _result(case=case, artifact_registry={}, target_kind="vendor-neutral", state=state, message=client_status)
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _result(case=case, artifact_registry={}, target_kind="vendor-neutral", state="fail", message="malformed operation_ref")
    operation_id = str(operation_ref.get("operation_id") or "")
    if _external_consumption_status(operation_id) not in {"supported", "runtime-backed"}:
        return _result(
            case=case,
            artifact_registry={},
            target_kind="vendor-neutral",
            state="unavailable",
            message="operation is unavailable for external consumer invocation",
        )
    case_input = case.get("input", {})
    if not isinstance(case_input, Mapping) or not isinstance(case_input.get("json"), Mapping):
        return _result(
            case=case,
            artifact_registry={},
            target_kind="vendor-neutral",
            state="unavailable",
            message="no operation-shaped JSON input for packaged consumer",
        )
    json_values = dict(case_input.get("json", {}))
    expected = case.get("expected", {})
    expected_mapping = expected if isinstance(expected, Mapping) else {}
    expected_error = expected_mapping.get("error") if isinstance(expected_mapping.get("error"), Mapping) else None
    if expected_error is None and (json_values.get("format") not in {None, "json"} or json_values.get("select")):
        return _result(
            case=case,
            artifact_registry={},
            target_kind="vendor-neutral",
            state="unavailable",
            message="case exercises selected/text wrapper projection rather than generic operation JSON",
        )
    if expected_error is None:
        json_values.pop("format", None)
        json_values.pop("target", None)
    process_case = _case_process_fixture(case)
    fixture_root = materialize_case_fixture(
        case=process_case,
        root=temp_root / str(case.get("id", "case")).replace(".", "-") / "vendor-neutral",
    )
    _write_local_invoke_config(fixture_root)
    script = f"""
import {{ invokeOperation, AWClientError }} from {json.dumps(client_path.as_uri())};
const operationId = {json.dumps(str(operation_ref.get("operation_id", "")))};
const values = {json.dumps(json_values, sort_keys=True)};
const target = {json.dumps(str(fixture_root))};
try {{
  const payload = invokeOperation(operationId, values, {{ target, allowRuntimeBacked: true }});
  console.log(JSON.stringify({{ ok: true, payload }}));
}} catch (error) {{
  const details = error && typeof error === 'object' ? (error.details ?? {{}}) : {{}};
  console.log(JSON.stringify({{
    ok: false,
    kind: error instanceof AWClientError ? error.kind : (error?.kind ?? error?.name ?? 'error'),
    message: String(error?.message ?? error),
    details,
  }}));
}}
"""
    completed = subprocess.run([node, "--input-type=module", "--eval", script], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return _result(
            case=case,
            artifact_registry={},
            target_kind="vendor-neutral",
            state="fail",
            message=f"external consumer process failed: {completed.stderr.strip()}",
        )
    try:
        envelope = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return _result(
            case=case,
            artifact_registry={},
            target_kind="vendor-neutral",
            state="fail",
            message=f"external consumer returned malformed JSON: {exc}; stdout={completed.stdout!r}",
        )
    if envelope.get("ok") is False and envelope.get("kind") == "incompatible":
        details = envelope.get("details") if isinstance(envelope.get("details"), Mapping) else {}
        if isinstance(details.get("readiness"), Mapping):
            return _result(
                case=case,
                artifact_registry={},
                target_kind="vendor-neutral",
                state="unavailable",
                message="packaged consumer correctly refused operation without current external-readiness evidence",
            )
    failures: list[str] = []
    selected_fields: dict[str, object] = {}
    if expected_error is not None:
        if envelope.get("ok") is not False:
            failures.append("expected external consumer error")
        else:
            if expected_error.get("kind") and envelope.get("kind") not in {expected_error.get("kind"), "malformed"}:
                failures.append(f"expected error kind {expected_error.get('kind')!r}, got {envelope.get('kind')!r}")
            details = envelope.get("details") if isinstance(envelope.get("details"), Mapping) else {}
            if envelope.get("kind") != "malformed":
                for key in ("field", "value"):
                    if key in expected_error and details.get(key) != expected_error.get(key):
                        failures.append(f"expected error detail {key}={expected_error.get(key)!r}, got {details.get(key)!r}")
    else:
        if envelope.get("ok") is not True:
            failures.append(f"external consumer error: {envelope.get('kind')} {envelope.get('message')}")
        else:
            result_fields = (
                expected_mapping.get("result", {}).get("selected_fields", {}) if isinstance(expected_mapping.get("result"), Mapping) else {}
            )
            if isinstance(result_fields, Mapping) and result_fields:
                try:
                    selected_fields = _select_expected_result_fields(envelope.get("payload", {}), result_fields)
                except KeyError as exc:
                    failures.append(f"result selected fields unavailable: {exc}")
                else:
                    if selected_fields != dict(result_fields):
                        failures.append(f"expected selected fields {dict(result_fields)!r}, got {selected_fields!r}")
    result = _result(
        case=case, artifact_registry={}, target_kind="vendor-neutral", state="fail" if failures else "pass", message="; ".join(failures)
    )
    result["adapter_id"] = "vendor-neutral.packaged-consumer"
    result["artifact_id"] = "packed:@agentic-workspace/workspace-cli"
    result["selected_fields"] = selected_fields
    return result


def _run_case_target(
    *,
    case: Mapping[str, object],
    artifact_registry: Mapping[str, Mapping[str, object]],
    target_kind: str,
    temp_root: Path,
    require_node: bool,
    vendor_neutral_client: Path | None = None,
    vendor_neutral_status: str = "not-prepared",
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _result(
            case=case,
            artifact_registry=artifact_registry,
            target_kind=target_kind,
            state="fail",
            message="malformed operation_ref",
        )
    if target_kind == "vendor-neutral":
        return _run_vendor_neutral_consumer_case(
            case=case,
            temp_root=temp_root,
            client_path=vendor_neutral_client,
            client_status=vendor_neutral_status,
            require_node=require_node,
        )
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
        return _run_python_function_case(case=case, artifact=artifact, temp_root=temp_root)
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


def _run_python_function_case(
    *, case: Mapping[str, object], artifact: Mapping[str, object], temp_root: Path
) -> dict[str, object]:
    operation_ref = case.get("operation_ref", {})
    if not isinstance(operation_ref, Mapping):
        return _function_result(case=case, artifact=artifact, state="fail", message="malformed operation_ref")
    function_target = _python_function_target_for_artifact(artifact)
    if function_target is None:
        return _function_result(
            case=case, artifact=artifact, state="unavailable", message="python.function artifact has no importable symbol"
        )
    process_case = _case_process_fixture(case)
    fixture_root = materialize_case_fixture(
        case=process_case,
        root=temp_root / str(case.get("id", "case")).replace(".", "-") / "python-function",
    )
    function_case = _case_function_fixture(case)
    if function_case.input_values.get("target") == ".":
        function_case = OperationConformanceCase(
            conformance_ref=function_case.conformance_ref,
            label=function_case.label,
            input_values={**function_case.input_values, "target": str(fixture_root)},
            selected_fields=function_case.selected_fields,
            expected_fields=function_case.expected_fields,
            expected_error_contains=function_case.expected_error_contains,
        )
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
        return [*declared, "vendor-neutral"]
    if target_selection == "vendor-neutral":
        return ["vendor-neutral"]
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
    parity_targets = [target for target in selected_targets if target != "vendor-neutral"]
    target_results = [result for result in results if result.get("case_id") == case_id and result.get("target") in parity_targets]
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
    runtime_exception_revisions: dict[str, str] = {}
    readiness_case_exceptions: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix="agentic-workspace-operation-conformance-test-ir-") as tmp:
        temp_root = Path(tmp)
        vendor_neutral_status, vendor_neutral_client = (
            _prepare_vendor_neutral_consumer(temp_root, require_node=require_node)
            if target_selection in {"all", "vendor-neutral"}
            else ("not-selected", None)
        )
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
                        vendor_neutral_client=vendor_neutral_client,
                        vendor_neutral_status=vendor_neutral_status,
                    )
                )
            _append_parity_results(results, case, selected_targets, artifact_registry)
        if not case_filter and target_selection in {"all", "vendor-neutral"}:
            readiness_results, runtime_exception_revisions, readiness_case_exceptions = _external_readiness_results(
                manifest=manifest,
                temp_root=temp_root,
                client_path=vendor_neutral_client,
                client_status=vendor_neutral_status,
                require_node=require_node,
            )
            results.extend(readiness_results)
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
        "runtime_exception_revisions": runtime_exception_revisions,
        "readiness_case_exceptions": readiness_case_exceptions,
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
    parser.add_argument("--target", choices=["all", "python", "typescript", "vendor-neutral", "parity"], default="all")
    parser.add_argument("--case", action="append", default=[], help="Run only a specific IR case id. May be repeated.")
    parser.add_argument("--require-node", action="store_true", help="Fail when TypeScript cases are selected but Node is unavailable.")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = run_ir_cases(target_selection=str(args.target), case_filter=set(args.case), require_node=bool(args.require_node))
    profile = json.loads((REPO_ROOT / "src/agentic_workspace/contracts/external_consumer_profile.json").read_text(encoding="utf-8"))
    reuse_executed_at, reuse_invocation_id = _existing_receipt_identity_for_result(payload)
    receipt_store = build_external_operation_conformance_receipts(
        profile,
        conformance_result=payload,
        executed_at=reuse_executed_at,
        invocation_id=reuse_invocation_id,
    )
    complete_publication = not args.case and args.target == "all" and payload.get("summary", {}).get("state") == "pass"
    if complete_publication:
        payload["external_operation_conformance_receipts"] = write_external_operation_conformance_receipts(receipt_store)
    else:
        payload["external_operation_conformance_receipts"] = {
            "kind": "agentic-workspace/external-operation-conformance-receipt-write/v1",
            "status": "not-published",
            "receipt_count": len(receipt_store.get("receipts", [])) if isinstance(receipt_store.get("receipts"), list) else 0,
            "reason": "Only a complete --target all invocation with no case filter and a passing summary may publish release readiness mirrors.",
        }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_text(payload)
    return 1 if payload.get("summary", {}).get("state") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
