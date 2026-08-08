"""Selection and verification for subsystem-issued context authority.

This shared layer owns no source semantics and issues no authority result or
execution receipt. It selects a concrete owner operation and verifies the
opaque revision-bound result that operation returns.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _workspace_runner(surface: str) -> Callable[..., dict[str, Any]]:
    from agentic_workspace.context_authority_workspace_owners import workspace_owner_operation

    return workspace_owner_operation(surface)


def _planning_runner() -> Callable[..., dict[str, Any]]:
    from repo_planning_bootstrap.context_authority_owner import planning_context_authority_owner_operation

    return planning_context_authority_owner_operation


def _memory_runner() -> Callable[..., dict[str, Any]]:
    from repo_memory_bootstrap.context_authority_owner import memory_context_authority_owner_operation

    return memory_context_authority_owner_operation


def _proof_runner() -> Callable[..., dict[str, Any]]:
    from repo_verification_bootstrap.context_authority_owner import proof_context_authority_owner_operation

    return proof_context_authority_owner_operation


def _evaluation_runner() -> Callable[..., dict[str, Any]]:
    from agentic_workspace.evaluation import evaluation_context_authority_owner_operation

    return evaluation_context_authority_owner_operation


def _mutation_runner() -> Callable[..., dict[str, Any]]:
    from agentic_workspace.authority_envelope import mutation_baseline_context_authority_owner_operation

    return mutation_baseline_context_authority_owner_operation


def _generated_runner() -> Callable[..., dict[str, Any]]:
    from agentic_workspace.context_authority_generated_owner import generated_references_context_authority_owner_operation

    return generated_references_context_authority_owner_operation


_WORKSPACE_SURFACES = {
    "system-intent",
    "architecture-principles",
    "scoped-instructions",
    "ownership",
    "assignment",
    "autopilot-executor",
    "skills",
    "target-guidance",
    "terminal-outcome",
}


def registered_context_owner_operation_runner(surface: str) -> Callable[..., dict[str, Any]]:
    """Select the actual subsystem owner operation for a registered surface."""

    if surface in _WORKSPACE_SURFACES:
        return _workspace_runner(surface)
    if surface == "planning":
        return _planning_runner()
    if surface == "memory":
        return _memory_runner()
    if surface == "evaluation":
        return _evaluation_runner()
    if surface == "proof":
        return _proof_runner()
    if surface == "mutation-baseline":
        return _mutation_runner()
    if surface == "generated-references":
        return _generated_runner()
    raise ValueError(f"context owner operation is not registered for surface {surface!r}")


def registered_context_owner_receipt_status(
    *,
    owner_operation: dict[str, Any],
    receipt: dict[str, Any],
    result_revision: str,
    root: Path | None = None,
) -> tuple[bool, str]:
    """Verify, without issuing or repairing, one owner-provided receipt."""

    receipt_id = str(receipt.get("receipt_id") or "")
    if not receipt_id.startswith("sha256:"):
        return False, "owner-operation-receipt-id-missing"
    current_resolution = _as_dict(receipt.get("current_resolution"))
    if current_resolution.get("status") != "current":
        return False, "owner-operation-current-resolution-missing"
    if current_resolution.get("resolution_mode") != "deterministic-source-revision":
        return False, "owner-operation-current-resolution-unsupported"
    operation_identity = {
        "operation_id": receipt.get("operation_id"),
        "producer": receipt.get("producer"),
        "surface": receipt.get("surface"),
        "owner": receipt.get("owner"),
        "source_id": receipt.get("source_id"),
        "source_revision": receipt.get("source_revision"),
        "git_head": receipt.get("git_head"),
        "adapter_id": receipt.get("adapter_id"),
        "selection_revision": receipt.get("selection_revision"),
        "schema_backing_revision": receipt.get("schema_backing_revision"),
        "adapter_receipt_revision": receipt.get("adapter_receipt_revision"),
        "source_owner_contract_revision": receipt.get("source_owner_contract_revision"),
        "result_payload_revision": receipt.get("result_payload_revision"),
    }
    expected_run_id = "sha256:" + _digest(operation_identity)
    receipt_identity = {
        **operation_identity,
        "run_id": expected_run_id,
        "executor": receipt.get("executor"),
        "receipt_schema": receipt.get("receipt_schema"),
    }
    expected_receipt_id = "sha256:" + _digest(receipt_identity)
    if receipt.get("run_id") != expected_run_id or owner_operation.get("run_id") != expected_run_id:
        return False, "owner-operation-current-run-mismatch"
    if receipt_id != expected_receipt_id or owner_operation.get("receipt_id") != expected_receipt_id:
        return False, "owner-operation-current-receipt-mismatch"
    for field in (
        "operation_id",
        "producer",
        "surface",
        "owner",
        "source_id",
        "source_revision",
        "git_head",
        "adapter_id",
        "selection_revision",
        "schema_backing_revision",
        "adapter_receipt_revision",
        "source_owner_contract_revision",
        "result_payload_revision",
    ):
        if owner_operation.get(field) != receipt.get(field):
            return False, f"owner-operation-{field.replace('_', '-')}-mismatch"
    if root is not None:
        source_id = str(receipt.get("source_id") or "")
        source_path = root / source_id
        if not source_id or not source_path.exists():
            return False, "owner-operation-current-source-missing"
        try:
            if source_path.is_dir():
                current_revision = "sha256:" + _digest(
                    {
                        path.relative_to(source_path).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(source_path.rglob("*"))
                        if path.is_file()
                    }
                )
            else:
                current_revision = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()
        except OSError:
            return False, "owner-operation-current-source-unreadable"
        if receipt.get("source_revision") != current_revision:
            return False, "owner-operation-current-source-stale"
    if not str(result_revision or "").startswith("sha256:"):
        return False, "owner-operation-current-result-mismatch"
    return True, ""


def registered_context_owner_result_status(owner_result: dict[str, Any]) -> tuple[bool, str]:
    """Verify the complete opaque owner result without deriving its semantics."""

    producer_state = _as_dict(owner_result.get("producer_owner_state"))
    source_contract = _as_dict(owner_result.get("source_owner_contract"))
    adapter_receipt = _as_dict(owner_result.get("owner_adapter_receipt"))
    operation = _as_dict(owner_result.get("owner_operation"))
    receipt = _as_dict(owner_result.get("owner_execution_receipt"))
    if not all((producer_state, source_contract, adapter_receipt, operation, receipt)):
        return False, "owner-result-issued-evidence-missing"
    if producer_state.get("kind") != "agentic-workspace/context-authority-producer-owner-state/v1":
        return False, "producer-owner-state-kind-mismatch"
    lifecycle = _as_dict(producer_state.get("lifecycle"))
    population = _as_dict(producer_state.get("population"))
    supersession = _as_dict(producer_state.get("supersession"))
    if not all((lifecycle, population, supersession)):
        return False, "producer-owner-state-lifecycle-missing"
    structural = _as_dict(owner_result.get("schema_backing"))
    excluded = {
        "kind",
        "producer",
        "status",
        "surface",
        "owner",
        "source_id",
        "source_revision",
        "git_head",
        "selection",
        "adapter_id",
        "repair_operation_id",
        "owner_boundary",
        "schema_backing",
        "producer_owner_state",
        "source_owner_contract",
        "owner_adapter_receipt",
        "owner_operation",
        "owner_execution_receipt",
        "revision",
        "reason",
    }
    specific = {key: value for key, value in owner_result.items() if key not in excluded}
    producer_identity = {
        "surface": owner_result.get("surface"),
        "producer": owner_result.get("producer"),
        "operation_id": owner_result.get("repair_operation_id"),
        "source_id": owner_result.get("source_id"),
        "source_revision": owner_result.get("source_revision"),
        "git_head": owner_result.get("git_head"),
        "selection_revision": "sha256:" + _digest(owner_result.get("selection")),
        "status": owner_result.get("status"),
        "schema_backing_revision": "sha256:" + _digest(structural),
        "surface_specific_revision": "sha256:" + _digest(specific),
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
    }
    if producer_state.get("revision") != "sha256:" + _digest(producer_identity):
        return False, "producer-owner-state-revision-mismatch"
    expected_common = {
        "producer": owner_result.get("producer"),
        "surface": owner_result.get("surface"),
        "source_id": owner_result.get("source_id"),
        "source_revision": owner_result.get("source_revision"),
        "git_head": owner_result.get("git_head"),
        "operation_id": owner_result.get("repair_operation_id"),
        "selection_revision": "sha256:" + _digest(owner_result.get("selection")),
    }
    for field, expected in expected_common.items():
        if producer_state.get(field) != expected or source_contract.get(field) != expected or adapter_receipt.get(field) != expected:
            return False, f"owner-result-{field.replace('_', '-')}-mismatch"
    if source_contract.get("status") != "admitted":
        return False, "source-owner-contract-not-admitted"
    if adapter_receipt.get("producer_state_revision") != producer_state.get("revision"):
        return False, "owner-adapter-producer-state-revision-mismatch"
    if adapter_receipt.get("source_owner_contract_revision") != "sha256:" + _digest(source_contract):
        return False, "owner-adapter-source-contract-revision-mismatch"
    preliminary = {
        key: value for key, value in owner_result.items() if key not in {"owner_operation", "owner_execution_receipt", "revision"}
    }
    preliminary_revision = "sha256:" + _digest(preliminary)
    if operation.get("result_payload_revision") != preliminary_revision or receipt.get("result_payload_revision") != preliminary_revision:
        return False, "owner-operation-result-payload-revision-mismatch"
    final_payload = {key: value for key, value in owner_result.items() if key != "revision"}
    if owner_result.get("revision") != "sha256:" + _digest(final_payload):
        return False, "owner-result-revision-mismatch"
    return True, ""
