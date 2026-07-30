"""Registered context-authority owner-operation front doors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _finalize_owner_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "revision": "sha256:"
        + _digest({key: value for key, value in payload.items() if key != "revision" and not str(key).endswith("_debug")}),
    }


_CURRENT_OWNER_RECEIPTS: dict[str, dict[str, Any]] = {}


def execute_context_owner_operation(
    *,
    surface: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    source_revision: str,
    git_head: str,
    selection: dict[str, Any],
    adapter_id: str,
    producer: str,
    operation_id: str,
    boundary: str,
    structural_backing: dict[str, Any],
    owner_result: dict[str, Any],
) -> dict[str, Any]:
    """Execute the registered owner operation and return an admitted result."""

    source_id = chosen.relative_to(root).as_posix() if chosen.is_relative_to(root) else chosen.as_posix()
    result_payload_revision = str(owner_result.get("revision") or "")
    schema_backing_revision = "sha256:" + _digest(structural_backing)
    operation_identity = {
        "operation_id": operation_id,
        "producer": producer,
        "surface": surface,
        "owner": owner,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": "sha256:" + _digest(selection),
        "schema_backing_revision": schema_backing_revision,
        "result_payload_revision": result_payload_revision,
    }
    run_id = "sha256:" + _digest(operation_identity)
    receipt_identity = {
        **operation_identity,
        "run_id": run_id,
        "executor": f"agentic_workspace.context_authority_owner_operations.{operation_id}",
        "receipt_schema": "src/agentic_workspace/contracts/schemas/context_authority_owner_result.schema.json",
    }
    receipt_id = "sha256:" + _digest(receipt_identity)
    owner_execution_receipt = {
        "kind": "agentic-workspace/context-authority-owner-execution-receipt/v1",
        "status": "executed",
        "current_state": "current",
        "receipt_id": receipt_id,
        "run_id": run_id,
        "operation_id": operation_id,
        "producer": producer,
        "surface": surface,
        "owner": owner,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": operation_identity["selection_revision"],
        "schema_backing_revision": schema_backing_revision,
        "result_payload_revision": result_payload_revision,
        "executor": receipt_identity["executor"],
        "receipt_schema": receipt_identity["receipt_schema"],
        "supersedes": "",
        "admission_rule": "Only this registered owner-operation front door can make this receipt current.",
    }
    owner_operation = {
        "kind": "agentic-workspace/context-authority-owner-operation/v1",
        "status": "executed",
        "operation_id": operation_id,
        "run_id": run_id,
        "receipt_id": receipt_id,
        "producer": producer,
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": operation_identity["selection_revision"],
        "schema_backing_revision": schema_backing_revision,
        "result_payload_revision": result_payload_revision,
        "admission_rule": (
            "Context authority admits current results only from a registered owner-operation front-door receipt. "
            "Checked-in owner-result JSON and caller-constructed receipts are evidence only."
        ),
    }
    admitted_result = _finalize_owner_result(
        {
            **owner_result,
            "owner_boundary": boundary,
            "schema_backing": structural_backing,
            "owner_operation": owner_operation,
            "owner_execution_receipt": owner_execution_receipt,
        }
    )
    _CURRENT_OWNER_RECEIPTS[receipt_id] = {
        "owner_operation": owner_operation,
        "owner_execution_receipt": owner_execution_receipt,
        "result_revision": admitted_result["revision"],
    }
    return admitted_result


def registered_context_owner_receipt_status(
    *,
    owner_operation: dict[str, Any],
    receipt: dict[str, Any],
    result_revision: str,
) -> tuple[bool, str]:
    receipt_id = str(receipt.get("receipt_id") or "")
    current = _CURRENT_OWNER_RECEIPTS.get(receipt_id)
    if not current:
        return False, "owner-operation-receipt-not-admitted"
    if current.get("owner_operation") != owner_operation:
        return False, "owner-operation-current-run-mismatch"
    if current.get("owner_execution_receipt") != receipt:
        return False, "owner-operation-current-receipt-mismatch"
    if current.get("result_revision") != result_revision:
        return False, "owner-operation-current-result-mismatch"
    return True, ""
