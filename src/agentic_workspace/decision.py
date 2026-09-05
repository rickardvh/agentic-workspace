"""Thin Python transport to the shared Agentic Workspace semantic core."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


class DecisionContractError(ValueError):
    """Raised when the shared core rejects a source-decision request."""


def _core_binary() -> Path:
    configured = os.environ.get("AGENTIC_WORKSPACE_CORE_BINARY")
    if configured:
        path = Path(configured)
    else:
        name = "agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core"
        path = Path(__file__).with_name("_native") / name
    if not path.is_file():
        raise DecisionContractError(
            "shared Agentic Workspace core is unavailable; install a supported native package "
            "or set AGENTIC_WORKSPACE_CORE_BINARY to the admitted core binary"
        )
    return path


def _request(payload: Mapping[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        [str(_core_binary())],
        input=json.dumps(payload, separators=(",", ":")),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        try:
            message = json.loads(completed.stderr)["error"]["message"]
        except (KeyError, TypeError, json.JSONDecodeError):
            message = completed.stderr.strip() or f"shared core exited with status {completed.returncode}"
        raise DecisionContractError(str(message))
    return dict(json.loads(completed.stdout))


def compile_source_decision(
    contributions: Iterable[Mapping[str, Any]],
    *,
    intent: Mapping[str, Any] | None = None,
    capability_contract: Mapping[str, Any] | None = None,
    decision_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"contributions": list(contributions), "intent": dict(intent or {})}
    if capability_contract is not None:
        payload["capability_contract"] = dict(capability_contract)
    if decision_context is not None:
        payload["decision_context"] = dict(decision_context)
    return _request(payload)


def admit_invocation(
    decision: Mapping[str, Any], invocation: Mapping[str, Any], previous: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    return _request({"admission": {"decision": decision, "invocation": invocation, "previous_invocation": previous}})


def prepare_request(request: Mapping[str, Any], current_work: Mapping[str, Any], capability_contract: Mapping[str, Any]) -> dict[str, Any]:
    return _request({"prepare_request": {"request": request, "current_work": current_work, "capability_contract": capability_contract}})


def answer_decision(decision: Mapping[str, Any], consequence: str, answer: Any, capability_contract: Mapping[str, Any]) -> dict[str, Any]:
    return _request(
        {"answer_decision": {"decision": decision, "question": consequence, "answer": answer, "capability_contract": capability_contract}}
    )


def operation_result(invocation: Mapping[str, Any], outcome: Mapping[str, Any], decision: Mapping[str, Any] | None) -> dict[str, Any]:
    return _request({"operation_result": {"invocation": invocation, "outcome": outcome, "decision": decision}})


def admit_attempt(decision: Mapping[str, Any], invocation: Mapping[str, Any], record: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return _request({"admit_attempt": {"decision": decision, "invocation": invocation, "record": record}})


def commit_attempt(record: Mapping[str, Any], outcome: Mapping[str, Any]) -> dict[str, Any]:
    return _request({"commit_attempt": {"record": record, "outcome": outcome}})


def admit_stored_attempt(
    target: str, decision: Mapping[str, Any], invocation: Mapping[str, Any], custody: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    return _request({"admit_stored_attempt": {"target": target, "decision": decision, "invocation": invocation, "custody": custody}})


def commit_stored_attempt(target: str, custody: Mapping[str, Any], outcome: Mapping[str, Any]) -> dict[str, Any]:
    return _request({"commit_stored_attempt": {"target": target, "custody": custody, "outcome": outcome}})


def select_decision_detail(decision: Mapping[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/decision-view/v1",
        "decision_id": decision.get("decision_id"),
        "input_revision": decision.get("input_revision"),
        "authoritative": False,
        "values": {field: decision[field] for field in fields if field in decision},
    }


def planning_view(context: Mapping[str, Any]) -> dict[str, Any]:
    return _request({"planning_view": context})


def reconcile_planning(context: Mapping[str, Any]) -> dict[str, Any]:
    return _request({"reconcile_planning": context})


__all__ = [
    "normalize_decision_record",
    "DecisionContractError",
    "compile_source_decision",
    "select_decision_detail",
    "admit_invocation",
    "prepare_request",
    "answer_decision",
    "operation_result",
    "admit_attempt",
    "commit_attempt",
    "admit_stored_attempt",
    "commit_stored_attempt",
    "planning_view",
    "reconcile_planning",
]


def normalize_decision_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return _request({"normalize_decision_record": record})
