"""Internal envelope protocol used by concrete context-authority owners.

This module never inspects a repository source and never decides whether an
authority is current. Concrete subsystem owners supply the complete semantic
decision. The protocol only seals that decision and its provenance into the
common result/receipt schema consumed by the context registry.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "revision": "sha256:" + _digest({key: value for key, value in payload.items() if key != "revision"}),
    }


def _source_id(root: Path, chosen: Path) -> str:
    return chosen.relative_to(root).as_posix() if chosen.is_relative_to(root) else chosen.as_posix()


def _issue_owner_result(
    *,
    surface: str,
    producer: str,
    result_kind: str,
    operation_id: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    revision: str,
    git_head: str,
    selection: dict[str, Any],
    status: str,
    reason: str,
    owner_boundary: str,
    schema_backing: dict[str, Any],
    lifecycle: dict[str, Any],
    population: dict[str, Any],
    supersession: dict[str, Any],
    surface_specific: dict[str, Any] | None = None,
    executor: str,
) -> dict[str, Any]:
    """Seal semantics already decided by one concrete subsystem owner."""

    if not all((surface, producer, result_kind, operation_id, owner_boundary, executor)):
        raise ValueError("owner result identity and boundary must be complete")
    if not all(isinstance(value, dict) and value for value in (schema_backing, lifecycle, population, supersession)):
        raise ValueError("owner result must include schema, lifecycle, population, and supersession decisions")
    if lifecycle.get("status") != ("current" if status == "current" else "repair-required"):
        raise ValueError("owner lifecycle decision does not match result status")
    if supersession.get("status") != ("not-superseded" if status == "current" else "unknown-until-repair"):
        raise ValueError("owner supersession decision does not match result status")

    source_id = _source_id(root, chosen)
    source_revision = "sha256:" + revision
    selection_revision = "sha256:" + _digest(selection)
    adapter_id = f"{surface}.owner-result"
    specific = dict(surface_specific or {})
    schema_backing_revision = "sha256:" + _digest(schema_backing)
    producer_identity = {
        "surface": surface,
        "producer": producer,
        "operation_id": operation_id,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": selection_revision,
        "status": status,
        "schema_backing_revision": schema_backing_revision,
        "surface_specific_revision": "sha256:" + _digest(specific),
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
    }
    producer_state = {
        "kind": "agentic-workspace/context-authority-producer-owner-state/v1",
        "status": status,
        "producer": producer,
        "operation_id": operation_id,
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": selection_revision,
        "revision": "sha256:" + _digest(producer_identity),
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
        "rule": "The concrete subsystem owner issued this complete semantic state before shared context admission.",
    }
    schema_status = str(schema_backing.get("parse_status") or ("valid" if status == "current" else "invalid"))
    source_owner_contract = {
        "kind": "agentic-workspace/context-authority-source-owner-contract/v1",
        "surface": surface,
        "producer": producer,
        "operation_id": operation_id,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": selection_revision,
        "status": "admitted" if status == "current" else "not-admitted",
        "schema": {
            "status": schema_status,
            "backing_revision": schema_backing_revision,
            "source_format": str(schema_backing.get("source_format") or ""),
            "missing_required_keys": list(schema_backing.get("missing_required_keys") or []),
            "missing_symbols": list(schema_backing.get("missing_symbols") or []),
        },
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
        "source_owner_rule": "The producing subsystem owns schema, lifecycle, population, and supersession semantics.",
    }
    semantic_evidence_revision = "sha256:" + _digest(
        {
            "status": status,
            "reason": reason,
            "owner_boundary": owner_boundary,
            "schema_backing": schema_backing,
            "surface_specific": specific,
            "producer_state_revision": producer_state["revision"],
        }
    )
    adapter_receipt = {
        "kind": "agentic-workspace/context-authority-owner-adapter-result/v1",
        "status": "produced",
        "producer": producer,
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": selection_revision,
        "semantic_evidence_revision": semantic_evidence_revision,
        "producer_state_revision": producer_state["revision"],
        "source_owner_contract_revision": "sha256:" + _digest(source_owner_contract),
        "operation_id": operation_id,
        "executor": executor,
        "rule": "The named concrete owner operation produced this semantic result and receipt.",
    }
    owner_result = _finalize(
        {
            "kind": result_kind,
            "producer": producer,
            "status": status,
            "surface": surface,
            "owner": owner,
            "source_id": source_id,
            "source_revision": source_revision,
            "git_head": git_head,
            "selection": selection,
            "adapter_id": adapter_id,
            "repair_operation_id": operation_id,
            "owner_boundary": owner_boundary,
            "schema_backing": schema_backing,
            "producer_owner_state": producer_state,
            "source_owner_contract": source_owner_contract,
            "owner_adapter_receipt": adapter_receipt,
            **({"reason": reason} if reason else {}),
            **specific,
        }
    )
    if status != "current":
        return owner_result

    adapter_receipt_revision = "sha256:" + _digest(adapter_receipt)
    source_owner_contract_revision = "sha256:" + _digest(source_owner_contract)
    operation_identity = {
        "operation_id": operation_id,
        "producer": producer,
        "surface": surface,
        "owner": owner,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": selection_revision,
        "schema_backing_revision": schema_backing_revision,
        "adapter_receipt_revision": adapter_receipt_revision,
        "source_owner_contract_revision": source_owner_contract_revision,
        "result_payload_revision": owner_result["revision"],
    }
    run_id = "sha256:" + _digest(operation_identity)
    receipt_identity = {
        **operation_identity,
        "run_id": run_id,
        "executor": executor,
        "receipt_schema": "src/agentic_workspace/contracts/schemas/context_authority_owner_result.schema.json",
    }
    receipt_id = "sha256:" + _digest(receipt_identity)
    common_operation = {
        "operation_id": operation_id,
        "producer": producer,
        "surface": surface,
        "owner": owner,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": selection_revision,
        "schema_backing_revision": schema_backing_revision,
        "adapter_receipt_revision": adapter_receipt_revision,
        "source_owner_contract_revision": source_owner_contract_revision,
        "result_payload_revision": owner_result["revision"],
    }
    owner_operation = {
        "kind": "agentic-workspace/context-authority-owner-operation/v1",
        "status": "executed",
        "run_id": run_id,
        "receipt_id": receipt_id,
        **common_operation,
        "admission_rule": "Shared context consumers may verify but cannot construct this owner-issued operation.",
    }
    execution_receipt = {
        "kind": "agentic-workspace/context-authority-owner-execution-receipt/v1",
        "status": "executed",
        "current_state": "current",
        "receipt_id": receipt_id,
        "run_id": run_id,
        **common_operation,
        "executor": executor,
        "receipt_schema": receipt_identity["receipt_schema"],
        "supersedes": "",
        "current_resolution": {
            "kind": "agentic-workspace/context-authority-current-resolution/v1",
            "status": "current",
            "resolution_mode": "deterministic-source-revision",
            "receipt_index_ref": f"context-authority-current:{surface}:{source_id}",
            "recompute_inputs": list(operation_identity),
            "rule": "Consumers revalidate the owner-issued receipt against current source and selection revisions.",
        },
        "admission_rule": "This execution receipt was issued by the named concrete subsystem operation.",
    }
    return _finalize(
        {
            **owner_result,
            "owner_operation": owner_operation,
            "owner_execution_receipt": execution_receipt,
        }
    )
