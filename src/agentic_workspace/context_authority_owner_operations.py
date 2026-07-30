"""Registered context-authority owner-operation front doors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_CONTEXT_AUTHORITY_REGISTRY_RESOURCE = "context_authority_registry.json"
_CONTEXT_OWNER_ADAPTER_TOKEN = object()


class ContextOwnerAdapterResult:
    """Opaque result handle issued by a concrete context-authority owner adapter."""

    __slots__ = ("payload",)

    def __init__(self, *, _adapter_token: object, payload: dict[str, Any]) -> None:
        if _adapter_token is not _CONTEXT_OWNER_ADAPTER_TOKEN:
            raise ValueError("context owner adapter result must be issued by a registered owner adapter")
        self.payload = dict(payload)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _finalize_owner_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "revision": "sha256:"
        + _digest({key: value for key, value in payload.items() if key != "revision" and not str(key).endswith("_debug")}),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_registry_contract() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "contracts" / _CONTEXT_AUTHORITY_REGISTRY_RESOURCE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


_REGISTRY_CONTRACT = _load_registry_contract()
_OWNER_OPERATION_SPECS: dict[str, dict[str, str]] = {}
for _item in _as_list(_REGISTRY_CONTRACT.get("surfaces")):
    if not isinstance(_item, dict):
        continue
    _surface = str(_item.get("surface") or "")
    _owner_contract = _as_dict(_item.get("source_owner_contract"))
    if not _surface:
        continue
    _OWNER_OPERATION_SPECS[_surface] = {
        "producer": str(_owner_contract.get("owner_module") or ""),
        "result_kind": str(_owner_contract.get("owner_result_kind") or ""),
        "operation_id": str(_owner_contract.get("repair_operation_id") or f"context-authority.{_surface}.refresh-source"),
    }


def _issue_context_owner_adapter_result(payload: dict[str, Any]) -> ContextOwnerAdapterResult:
    return ContextOwnerAdapterResult(_adapter_token=_CONTEXT_OWNER_ADAPTER_TOKEN, payload=payload)


def admit_context_owner_operation_result(
    *,
    surface: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    source_revision: str,
    git_head: str,
    selection: dict[str, Any],
    adapter_id: str,
    owner_result_handle: ContextOwnerAdapterResult,
) -> dict[str, Any]:
    """Admit a result produced by the registered concrete owner adapter."""

    spec = _OWNER_OPERATION_SPECS.get(surface)
    if not spec or not spec.get("producer") or not spec.get("result_kind") or not spec.get("operation_id"):
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")
    producer = spec["producer"]
    result_kind = spec["result_kind"]
    operation_id = spec["operation_id"]
    if not isinstance(owner_result_handle, ContextOwnerAdapterResult):
        raise ValueError("context owner operation result requires a registered owner-adapter handle")
    owner_result = dict(owner_result_handle.payload)
    if owner_result.get("producer") != producer:
        raise ValueError("owner operation result producer does not match registered owner")
    if owner_result.get("kind") != result_kind:
        raise ValueError("owner operation result kind does not match registered owner")
    if owner_result.get("repair_operation_id") != operation_id:
        raise ValueError("owner operation result id does not match registered owner")
    if owner_result.get("source_revision") != source_revision:
        raise ValueError("owner operation result source revision is stale")
    if owner_result.get("git_head") != git_head:
        raise ValueError("owner operation result git head is stale")
    if owner_result.get("adapter_id") != adapter_id:
        raise ValueError("owner operation result adapter id does not match selected owner adapter")
    if owner_result.get("owner_operation") or owner_result.get("owner_execution_receipt"):
        raise ValueError("owner operation result must not carry caller-provided operation receipts")
    structural_backing = _as_dict(owner_result.get("schema_backing"))
    boundary = str(owner_result.get("owner_boundary") or "")
    if not structural_backing or not boundary:
        raise ValueError("context owner operation payload must provide owner boundary and schema backing")
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
        "current_resolution": {
            "kind": "agentic-workspace/context-authority-current-resolution/v1",
            "status": "current",
            "resolution_mode": "deterministic-source-revision",
            "receipt_index_ref": f"context-authority-current:{surface}:{source_id}",
            "recompute_inputs": [
                "operation_id",
                "producer",
                "surface",
                "source_id",
                "source_revision",
                "git_head",
                "selection_revision",
                "schema_backing_revision",
                "result_payload_revision",
            ],
            "rule": "Receipt currentness is re-resolved from producer-owned operation identity and current source revision; no process-local map is authoritative.",
        },
        "admission_rule": "Only this registered owner-operation front door can construct the producer-owned receipt.",
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
            "Checked-in owner-result JSON and caller-constructed receipts are evidence only; currentness is recomputable across processes."
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
    return admitted_result


def registered_context_owner_receipt_status(
    *,
    owner_operation: dict[str, Any],
    receipt: dict[str, Any],
    result_revision: str,
    root: Path | None = None,
) -> tuple[bool, str]:
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
    if owner_operation.get("result_payload_revision") != receipt.get("result_payload_revision"):
        return False, "owner-operation-current-result-mismatch"
    if root is not None:
        source_id = str(receipt.get("source_id") or "")
        source_path = root / source_id
        if not source_id or not source_path.exists():
            return False, "owner-operation-current-source-missing"
        try:
            current_source_revision = "sha256:" + (
                _digest(
                    {
                        path.relative_to(source_path).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(source_path.rglob("*"))
                        if path.is_file()
                    }
                )
                if source_path.is_dir()
                else hashlib.sha256(source_path.read_bytes()).hexdigest()
            )
        except OSError:
            return False, "owner-operation-current-source-unreadable"
        if receipt.get("source_revision") != current_source_revision:
            return False, "owner-operation-current-source-stale"
    if not str(result_revision or "").startswith("sha256:"):
        return False, "owner-operation-current-result-mismatch"
    return True, ""
