"""Timestamp decoding adapter for the shared proof receipt admission owner."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from agentic_workspace.decision import proof_receipt

PROOF_RECEIPT_RESULT_OPTIONS = ("passed", "failed", "skipped", "waived")


def proof_receipt_result_contract(result: Any) -> dict[str, Any]:
    return proof_receipt({"action": "result", "value": result})


def proof_command_admission(command: Any) -> dict[str, Any]:
    return proof_receipt({"action": "command", "value": command})


def _timestamp_valid(receipt: dict[str, Any]) -> bool:
    recorded_at = str(receipt.get("recorded_at") or "").strip()
    try:
        decoded = datetime.fromisoformat(recorded_at.replace("Z", "+00:00")) if recorded_at else None
    except ValueError:
        decoded = None
    return decoded is not None and decoded.tzinfo is not None


def proof_receipt_admission(receipt: dict[str, Any]) -> dict[str, Any]:
    return proof_receipt({"action": "admit", "receipt": receipt, "timestamp_valid": _timestamp_valid(receipt)})


def proof_receipt_admissions(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Batch codec observations across the process transport, without storing evidence."""
    results = []
    for offset in range(0, len(receipts), 128):
        items = [{"receipt": receipt, "timestamp_valid": _timestamp_valid(receipt)} for receipt in receipts[offset : offset + 128]]
        results.extend(proof_receipt({"action": "admit-many", "items": items})["items"])
    return results
