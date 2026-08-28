"""Canonical owner packets for delegated assignment lifecycle transitions."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

PRODUCER_MODULE = "agentic_workspace.assignment_lifecycle"


def load_indexed_assignment_task_proof(*, target_root: Path, receipt_ref: str) -> dict[str, Any]:
    """Resolve an AW task-proof receipt only through its producer-owned index."""

    store_root = (target_root / ".agentic-workspace" / "proof" / "receipts").resolve()
    ref = str(receipt_ref or "").strip()
    if not ref:
        return {}
    if ref.startswith("proof://receipts/"):
        receipt_id = ref.rsplit("/", 1)[-1].strip()
        if not receipt_id or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in receipt_id
        ):
            return {}
        receipt_path = store_root / f"{receipt_id}.json"
    else:
        candidate = Path(ref)
        if candidate.is_absolute():
            return {}
        receipt_path = (target_root / candidate).resolve()
        if not receipt_path.is_relative_to(store_root) or receipt_path.suffix != ".json":
            return {}
        receipt_id = receipt_path.stem
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        index = json.loads((store_root / "index.json").read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(receipt, dict) or not isinstance(index, dict):
        return {}
    if index.get("kind") != "agentic-workspace/trusted-producer-receipt-index/v1":
        return {}
    entries = index.get("receipts")
    entry = entries.get(receipt_id) if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        return {}
    indexed_path = (store_root / str(entry.get("path") or "")).resolve()
    if indexed_path != receipt_path or not indexed_path.is_relative_to(store_root):
        return {}
    if str(entry.get("status") or "current") not in {"current", "fresh", "accepted"} or entry.get("superseded_by"):
        return {}
    if str(entry.get("producer_class") or "") != "aw-proof" or str(receipt.get("producer_class") or "") != "aw-proof":
        return {}
    if str(entry.get("revision") or "") != str(receipt.get("revision") or ""):
        return {}
    if str(entry.get("source_ref") or "") != str(receipt.get("source_ref") or ""):
        return {}
    if str(receipt.get("receipt_id") or "") != receipt_id:
        return {}
    return receipt


def assignment_task_proof_binding(receipt: Mapping[str, Any]) -> str:
    """Bind an AW proof subject to one exact assignment obligation."""

    proof_subject = dict(receipt.get("proof_subject") or {}) if isinstance(receipt.get("proof_subject"), Mapping) else {}
    payload = {
        "assignment_proof_obligation": receipt.get("assignment_proof_obligation"),
        "proof_subject_fingerprint": proof_subject.get("fingerprint"),
        "command": receipt.get("command"),
        "result": receipt.get("result"),
        "changed_paths": sorted(str(path) for path in receipt.get("changed_paths", []) if str(path)),
        "authority": receipt.get("authority"),
        "producer_class": receipt.get("producer_class"),
    }
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(rendered).hexdigest()


def materialize_canonical_assignment(
    *,
    target_root: Path,
    assignment: Mapping[str, Any],
    proof_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist one decision-derived assignment and its structural proof.

    The ordinary implementation front door calls this only after resolving the
    live assignment decision.  The public assignment lifecycle then consumes
    these checked-in authorities; it never promotes caller-provided JSON.
    """

    assignment_id = str(assignment.get("assignment_id") or "").strip()
    if not assignment_id or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in assignment_id
    ):
        raise ValueError("canonical assignment id must use only letters, digits, '-' or '_'")
    assignment_root = target_root / ".agentic-workspace" / "planning" / "assignments"
    proof_root = target_root / ".agentic-workspace" / "proof" / "receipts"
    assignment_path = assignment_root / f"{assignment_id}.assignment.json"
    proof_path = proof_root / f"{assignment_id}.assignment-proof.json"
    desired_assignment = dict(assignment)
    desired_proof = dict(proof_receipt)
    try:
        existing_assignment = json.loads(assignment_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        existing_assignment = {}
    if (
        isinstance(existing_assignment, dict)
        and existing_assignment.get("current_revision") == desired_assignment.get("current_revision")
        and existing_assignment.get("status") == "current"
    ):
        desired_assignment = existing_assignment
    try:
        existing_proof = json.loads(proof_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        existing_proof = {}
    if (
        isinstance(existing_proof, dict)
        and existing_proof.get("assignment_revision") == desired_proof.get("assignment_revision")
        and existing_proof.get("result") == "passed"
    ):
        desired_proof = existing_proof

    def write_if_changed(path: Path, payload: Mapping[str, Any]) -> bool:
        rendered = json.dumps(dict(payload), indent=2, sort_keys=True) + "\n"
        try:
            if path.read_text(encoding="utf-8-sig") == rendered:
                return False
        except OSError:
            pass
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(rendered, encoding="utf-8")
        temporary.replace(path)
        return True

    proof_written = write_if_changed(proof_path, desired_proof)
    assignment_written = write_if_changed(assignment_path, desired_assignment)
    materialized_status = str(desired_assignment.get("status") or "current")
    return {
        "kind": "agentic-workspace/assignment-materialization/v1",
        "status": "materialized" if assignment_written or proof_written else materialized_status,
        "assignment_id": assignment_id,
        "assignment_revision": desired_assignment.get("current_revision"),
        "run_id": dict(desired_assignment.get("current_attempt") or {}).get("run_id"),
        "assignment_ref": assignment_path.relative_to(target_root).as_posix(),
        "proof_receipt_ref": proof_path.relative_to(target_root).as_posix(),
        "writes": [
            ref
            for ref, written in (
                (assignment_path.relative_to(target_root).as_posix(), assignment_written),
                (proof_path.relative_to(target_root).as_posix(), proof_written),
            )
            if written
        ],
        "rule": "Only the live ordinary assignment decision may materialize this authority; lifecycle adapters consume it without redefining it.",
    }


def delegated_return_owner_packet(*, admission: Mapping[str, Any]) -> dict[str, Any]:
    """Project one admission result into the composed-operation owner contract.

    The admission primitive remains the decision source.  This projection only
    gives its already-resolved result the common owner-packet shape consumed by
    the composed release gate.
    """

    admitted = admission.get("admitted") is True
    raw_failures = admission.get("failures")
    failures: list[Any] = list(raw_failures) if isinstance(raw_failures, list) else []
    first_failure = failures[0] if failures and isinstance(failures[0], Mapping) else {}
    stable_reason = "return-receipt-current" if admitted else str(first_failure.get("reason") or "return-admission-rejected")
    raw_assignment_identity = admission.get("assignment_identity")
    assignment_identity: dict[str, Any] = (
        {str(key): value for key, value in raw_assignment_identity.items()} if isinstance(raw_assignment_identity, Mapping) else {}
    )
    return {
        "kind": "agentic-workspace/delegated-return-admission/v1",
        "producer_module": PRODUCER_MODULE,
        "owner": "delegation",
        "status": "admitted" if admitted else "blocked",
        "source": "assignment.admit",
        "operation_id": "assignment.admit",
        "stable_reason": stable_reason,
        "effect_scope": "returned-result-admission" if admitted else "no-mutation",
        "proof_claim_boundary": "admitted-result-before-claim" if admitted else "no-completion-claim",
        "terminal_state": "continue" if admitted else "blocked",
        "typed_operation": {
            "id": "assignment.admit",
            "action": "admit-result" if admitted else "reject-result",
            "expected_transition": "admit-or-repair-return",
        },
        "repair_operation": {
            "id": "assignment.repair",
            "action": "repair-rejected-assignment",
        },
        "admission": {
            "admitted": admitted,
            "stable_reason": stable_reason,
            "failure_count": len(failures),
        },
        "producer_observation": {
            "kind": "agentic-workspace/delegated-return-owner-observation/v1",
            "assignment_revision": assignment_identity.get("revision") or admission.get("assignment_revision"),
            "target_identity_ref": assignment_identity.get("target_identity_ref"),
            "worker_reported_proof_trusted": False,
            "worker_reported_completion_trusted": False,
            "failure_reasons": [str(item.get("reason")) for item in failures if isinstance(item, Mapping) and item.get("reason")],
        },
        "rule": "The assignment owner admits returned evidence; the worker never acquires proof, integration, or completion authority.",
    }
