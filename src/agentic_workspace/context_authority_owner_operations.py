"""Registered context-authority owner-operation front doors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_CONTEXT_AUTHORITY_REGISTRY_RESOURCE = "context_authority_registry.json"


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


def _source_id_for(root: Path, chosen: Path) -> str:
    return chosen.relative_to(root).as_posix() if chosen.is_relative_to(root) else chosen.as_posix()


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


def _admit_context_owner_operation_result(
    *,
    surface: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    source_revision: str,
    git_head: str,
    selection: dict[str, Any],
    adapter_id: str,
    owner_result: dict[str, Any],
) -> dict[str, Any]:
    """Admit a result produced by a registered concrete owner adapter."""

    spec = _OWNER_OPERATION_SPECS.get(surface)
    if not spec or not spec.get("producer") or not spec.get("result_kind") or not spec.get("operation_id"):
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")
    producer = spec["producer"]
    result_kind = spec["result_kind"]
    operation_id = spec["operation_id"]
    owner_result = dict(owner_result)
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


def _owner_result_payload(
    *,
    surface: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    source_revision: str,
    git_head: str,
    selection: dict[str, Any],
    adapter_id: str,
    status: str,
    reason: str,
    boundary: str,
    structural_backing: dict[str, Any],
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    spec = _OWNER_OPERATION_SPECS.get(surface)
    if not spec or not spec.get("producer") or not spec.get("result_kind") or not spec.get("operation_id"):
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")
    payload: dict[str, Any] = {
        "kind": spec["result_kind"],
        "producer": spec["producer"],
        "status": status,
        "surface": surface,
        "owner": owner,
        "source_id": _source_id_for(root, chosen),
        "source_revision": source_revision,
        "git_head": git_head,
        "selection": selection,
        "adapter_id": adapter_id,
        "repair_operation_id": spec["operation_id"],
        "owner_boundary": boundary,
        "schema_backing": structural_backing,
    }
    if reason:
        payload["reason"] = reason
    payload.update(extra or {})
    return _finalize_owner_result(payload)


def _run_registered_context_owner_operation(
    *,
    surface: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    revision: str,
    git_head: str,
    selection: dict[str, Any],
    adapter_id: str,
    boundary: str,
    structural_backing: dict[str, Any],
    status: str = "current",
    reason: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_revision = "sha256:" + revision
    owner_result = _owner_result_payload(
        surface=surface,
        owner=owner,
        root=root,
        chosen=chosen,
        source_revision=source_revision,
        git_head=git_head,
        selection=selection,
        adapter_id=adapter_id,
        status=status,
        reason=reason,
        boundary=boundary,
        structural_backing=structural_backing,
        extra=extra,
    )
    if status != "current":
        return owner_result
    return _admit_context_owner_operation_result(
        surface=surface,
        owner=owner,
        root=root,
        chosen=chosen,
        source_revision=source_revision,
        git_head=git_head,
        selection=selection,
        adapter_id=adapter_id,
        owner_result=owner_result,
    )


def _system_intent_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="system-intent", **kwargs)


def _architecture_principles_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="architecture-principles", **kwargs)


def _scoped_instructions_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="scoped-instructions", **kwargs)


def _ownership_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="ownership", **kwargs)


def _assignment_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="assignment", **kwargs)


def _evaluation_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="evaluation", **kwargs)


def _proof_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="proof", **kwargs)


def _autopilot_executor_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="autopilot-executor", **kwargs)


def _target_guidance_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="target-guidance", **kwargs)


def _terminal_outcome_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="terminal-outcome", **kwargs)


def _module_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="module", **kwargs)


def _planning_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="planning", **kwargs)


def _memory_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="memory", **kwargs)


def _mutation_baseline_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="mutation-baseline", **kwargs)


def _skills_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="skills", **kwargs)


def _generated_references_owner_operation(**kwargs: Any) -> dict[str, Any]:
    return _run_registered_context_owner_operation(surface="generated-references", **kwargs)


_CONTEXT_OWNER_OPERATION_RUNNERS = {
    "system-intent": _system_intent_owner_operation,
    "architecture-principles": _architecture_principles_owner_operation,
    "scoped-instructions": _scoped_instructions_owner_operation,
    "ownership": _ownership_owner_operation,
    "assignment": _assignment_owner_operation,
    "evaluation": _evaluation_owner_operation,
    "proof": _proof_owner_operation,
    "autopilot-executor": _autopilot_executor_owner_operation,
    "target-guidance": _target_guidance_owner_operation,
    "terminal-outcome": _terminal_outcome_owner_operation,
    "module": _module_owner_operation,
    "planning": _planning_owner_operation,
    "memory": _memory_owner_operation,
    "mutation-baseline": _mutation_baseline_owner_operation,
    "skills": _skills_owner_operation,
    "generated-references": _generated_references_owner_operation,
}


def registered_context_owner_operation_runner(surface: str):
    runner = _CONTEXT_OWNER_OPERATION_RUNNERS.get(surface)
    if runner is None:
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")
    return runner


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
