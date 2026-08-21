"""Generic post-action reconciliation for the compiled operating decision."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _revision(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def compile_reconciliation(inputs: dict[str, Any] | None) -> dict[str, Any]:
    """Compose owner facts into one claim, residue, continuation, and next action.

    Domain owners supply facts. This function only applies cross-cutting claim
    limits and never infers intent satisfaction from proof success.
    """

    if not inputs:
        return {
            "kind": "agentic-workspace/reconciliation/v1",
            "status": "not-requested",
            "input_revision": _revision({}),
            "claim": {"permission": "not-evaluated", "level": "none", "reasons": []},
            "residue": {"status": "none", "owner": "none"},
            "continuation": {"status": "not-evaluated", "owner": "none"},
            "next_action": {},
            "blockers": [],
        }

    result = _as_dict(inputs.get("result"))
    intent = _as_dict(inputs.get("intent"))
    proof = _as_dict(inputs.get("proof"))
    external = _as_dict(inputs.get("external_evidence"))
    residue_input = _as_dict(inputs.get("residue"))
    continuation_input = _as_dict(inputs.get("continuation"))
    module_facts = [_as_dict(item) for item in _as_list(inputs.get("module_contributions"))]

    result_status = str(result.get("status") or "unknown")
    intent_status = str(intent.get("status") or "unknown")
    owner_level = str(intent.get("owner_level") or "direct")
    parent_status = str(intent.get("parent_status") or "not-applicable")
    proof_status = str(proof.get("status") or "not-required")
    external_status = str(external.get("status") or "not-applicable")
    blockers: list[dict[str, str]] = []

    if result_status not in {"succeeded", "completed", "no-change"}:
        blockers.append(
            {
                "reason_code": "action-result-incomplete",
                "owner": str(result.get("owner") or "action owner"),
                "repair": str(result.get("recovery") or "retry or explicitly dispose the action result"),
            }
        )
    if proof_status in {"missing", "failed", "stale", "unavailable"}:
        blockers.append(
            {
                "reason_code": f"proof-{proof_status}",
                "owner": str(proof.get("owner") or "proof authority"),
                "repair": str(proof.get("recovery") or "run or refresh the selected proof"),
            }
        )
    if external_status in {"stale", "unavailable", "contradicted", "externally-completed-awaiting-admission"}:
        blockers.append(
            {
                "reason_code": f"external-{external_status}",
                "owner": str(external.get("owner") or "local intent owner"),
                "repair": str(external.get("recovery") or "refresh and reconcile external evidence with local intent"),
            }
        )
    if intent_status not in {"satisfied", "not-applicable"}:
        blockers.append(
            {
                "reason_code": "intent-not-satisfied",
                "owner": str(intent.get("owner") or "intent owner"),
                "repair": str(intent.get("recovery") or "continue or explicitly defer the remaining intent"),
            }
        )
    if parent_status in {"active", "partial", "unsatisfied", "unknown"}:
        blockers.append(
            {
                "reason_code": "parent-intent-remains",
                "owner": str(intent.get("parent_owner") or "parent intent owner"),
                "repair": str(intent.get("parent_recovery") or "continue the parent owner without widening the local claim"),
            }
        )

    residue_status = str(residue_input.get("status") or "none")
    residue_owner = str(residue_input.get("owner") or "none")
    if residue_status not in {"none", "dismissed"} and residue_owner in {"", "none"}:
        blockers.append(
            {
                "reason_code": "residue-owner-missing",
                "owner": "residue classifier",
                "repair": "route durable residue to exactly one canonical or module owner",
            }
        )

    local_success = result_status in {"succeeded", "completed", "no-change"} and proof_status not in {
        "missing",
        "failed",
        "stale",
        "unavailable",
    }
    terminal = local_success and not blockers
    claim_level = "none"
    permission = "blocked"
    if terminal:
        claim_level, permission = (owner_level, "allowed")
    elif local_success:
        claim_level, permission = (owner_level, "bounded")

    continuation_status = str(continuation_input.get("status") or ("terminal" if terminal else "required"))
    continuation_owner = str(continuation_input.get("owner") or ("none" if terminal else blockers[0]["owner"]))
    next_action: dict[str, Any] = {}
    if not terminal:
        supplied = _as_dict(continuation_input.get("next_action"))
        if supplied.get("operation_id") or supplied.get("command") or supplied.get("human_decision"):
            next_action = supplied
        else:
            first = blockers[0]
            next_action = {
                "kind": "agentic-workspace/reconciliation-action/v1",
                "operation_id": "workspace.reconcile.refresh",
                "owner": first["owner"],
                "reason_code": first["reason_code"],
                "command": str(inputs.get("refresh_command") or "agentic-workspace start --target . --format json"),
            }

    identity = {
        "result": result,
        "intent": intent,
        "proof": proof,
        "external_evidence": external,
        "residue": residue_input,
        "continuation": continuation_input,
        "module_contributions": module_facts,
    }
    return {
        "kind": "agentic-workspace/reconciliation/v1",
        "status": "terminal" if terminal else "continue",
        "input_revision": _revision(identity),
        "result": result,
        "affected_owner": {"level": owner_level, "owner": str(intent.get("owner") or "direct-task")},
        "proof": proof,
        "external_evidence": external,
        "claim": {
            "permission": permission,
            "level": claim_level,
            "reasons": [item["reason_code"] for item in blockers],
            "parent_claim_allowed": terminal and parent_status in {"not-applicable", "satisfied"},
        },
        "residue": {"status": residue_status, "owner": residue_owner},
        "continuation": {"status": continuation_status, "owner": continuation_owner},
        "next_action": next_action,
        "blockers": blockers,
        "module_contributions": module_facts,
        "rule": "Proof may support only the affected owner-level claim; semantic intent, parent completion, residue ownership, and continuation remain independently owned facts.",
    }
