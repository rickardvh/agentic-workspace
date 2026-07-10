"""Authoritative admission contract for trusted proof receipts."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_UNRESOLVED_TEMPLATE = re.compile(r"<[^<>\r\n]+>|\{\{[^{}\r\n]+\}\}|\$\{[^{}\r\n]+\}")
_ACCEPTED_RESULTS = {"passed", "pass", "success", "succeeded", "failed", "fail", "failure", "error"}


def proof_command_admission(command: Any) -> dict[str, Any]:
    """Validate the command portion through the same rule used by receipt admission."""

    value = str(command or "").strip()
    if not value:
        reason = "missing-command"
        recovery = "Supply the exact command that was executed with --receipt-command."
    elif _UNRESOLVED_TEMPLATE.search(value):
        reason = "unresolved-command-template"
        recovery = "Substitute every placeholder, execute the concrete command, then record that exact command."
    else:
        reason = "admissible"
        recovery = "none"
    return {
        "admitted": reason == "admissible",
        "reason": reason,
        "safe_recovery": recovery,
    }


def proof_receipt_admission(receipt: dict[str, Any]) -> dict[str, Any]:
    """Return a stable, fail-closed admission decision for a proof receipt."""

    failures: list[dict[str, str]] = []

    def reject(rule: str, field: str, recovery: str) -> None:
        failures.append({"reason": rule, "field": field, "recovery": recovery})

    if receipt.get("kind") != "agentic-workspace/proof-receipt/v1":
        reject("unsupported-receipt-kind", "kind", "Record evidence through `agentic-workspace proof --record-receipt`.")
    command_admission = proof_command_admission(receipt.get("command"))
    if not command_admission["admitted"]:
        reject(command_admission["reason"], "command", command_admission["safe_recovery"])
    result = str(receipt.get("result") or "").strip().lower()
    if not result:
        reject("missing-result", "result", "Supply the observed result with --receipt-result.")
    elif result not in _ACCEPTED_RESULTS:
        reject("unsupported-result", "result", "Use an observed pass/fail result class: passed, success, failed, failure, or error.")
    recorded_at = str(receipt.get("recorded_at") or "").strip()
    try:
        parsed_at = datetime.fromisoformat(recorded_at.replace("Z", "+00:00")) if recorded_at else None
    except ValueError:
        parsed_at = None
    if parsed_at is None or parsed_at.tzinfo is None:
        reject("invalid-recorded-at", "recorded_at", "Record the receipt again so AW supplies an ISO-8601 timestamp with timezone.")
    changed_paths = receipt.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        reject("missing-changed-path-scope", "changed_paths", "Pass one or more concrete --changed paths matching the proof scope.")
    else:
        for path in changed_paths:
            value = str(path or "").strip()
            if not value or _UNRESOLVED_TEMPLATE.search(value):
                reject(
                    "invalid-changed-path-scope",
                    "changed_paths",
                    "Replace empty or templated --changed values with concrete repo-relative paths.",
                )
                break
    admitted = not failures
    return {
        "kind": "agentic-workspace/proof-receipt-admission/v1",
        "status": "admitted" if admitted else "rejected",
        "admitted": admitted,
        "failures": failures,
        "reason": "admissible" if admitted else failures[0]["reason"],
        "safe_recovery": "none" if admitted else failures[0]["recovery"],
        "rule": "Only admitted receipts may be persisted, selected, or counted as trusted proof state.",
    }
