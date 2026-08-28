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


def _registered_operation_action(action: dict[str, Any]) -> bool:
    invocation = _as_dict(action.get("operation_invocation"))
    operation_id = str(invocation.get("operation_id") or "")
    operation_path = str(invocation.get("operation_path") or "")
    authority = str(invocation.get("authority") or "")
    return bool(operation_id and operation_path.endswith(f"/{operation_id}.json") and authority)


def _future_context_disposition(signal: dict[str, Any]) -> dict[str, Any]:
    declared = _as_dict(signal.get("disposition"))
    status = str(signal.get("status") or "unresolved").strip().lower()
    outcome = str(declared.get("outcome") or "").strip().lower().replace("_", "-")
    status_defaults = {
        "captured": "capture",
        "updated": "update-existing",
        "routed": "route-stronger",
        "already-absorbed": "already-absorbed",
        "absorbed": "already-absorbed",
        "dismissed": "dismiss",
        "resolved": "already-absorbed",
    }
    outcome = outcome or status_defaults.get(status, "unresolved")
    allowed = {"capture", "update-existing", "route-stronger", "already-absorbed", "dismiss", "unresolved"}
    if outcome not in allowed:
        outcome = "unresolved"
    owner = str(declared.get("owner") or signal.get("owner") or "").strip()
    rationale = str(declared.get("rationale") or signal.get("rationale") or "").strip()
    next_action = str(declared.get("next_action") or signal.get("required_decision") or "").strip()
    complete = (
        bool(owner) and bool(rationale)
        if outcome in {"capture", "update-existing", "route-stronger", "already-absorbed"}
        else bool(rationale)
        if outcome == "dismiss"
        else bool(owner) and bool(next_action)
    )
    effective_outcome = outcome if complete else "unresolved"
    return {
        "kind": "agentic-workspace/future-context-disposition/v1",
        "signal_id": str(signal.get("signal_id") or ""),
        "source_class": str(signal.get("source_class") or ""),
        "source_authority_state": str(signal.get("authority_state") or "candidate"),
        "outcome": effective_outcome,
        "owner": owner or "unassigned",
        "rationale": rationale,
        "next_action": next_action if effective_outcome == "unresolved" else "",
        "duplicate_memory_record_required": effective_outcome not in {"route-stronger", "already-absorbed", "dismiss"},
        "status": "disposed" if effective_outcome != "unresolved" else "unresolved",
        "authority_effect": "none",
        "rule": "Disposition transfers custody without upgrading source authority; stronger canonical owners avoid duplicate Memory residue.",
    }


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
    future_context_signals = [
        _as_dict(item)
        for item in _as_list(inputs.get("future_context_signals"))
        if isinstance(item, dict) and item.get("relevant") is not False
    ]
    future_context_capture = _as_dict(inputs.get("future_context_capture"))
    future_context_dispositions = [_future_context_disposition(signal) for signal in future_context_signals]
    capture_status = str(future_context_capture.get("status") or "not-provided").strip().lower()
    normalized_capture_status = capture_status.replace("_", "-")
    assessment_required = normalized_capture_status in {"not-evaluated", "skipped"} and bool(future_context_capture.get("evidence_count"))

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
    unresolved_future_context = [
        signal
        for signal, disposition in zip(future_context_signals, future_context_dispositions, strict=True)
        if disposition["status"] == "unresolved"
    ]
    if unresolved_future_context:
        signal = unresolved_future_context[0]
        blockers.append(
            {
                "reason_code": "future-context-unresolved",
                "owner": str(signal.get("owner") or "future-context source owner"),
                "repair": str(signal.get("required_decision") or "route or explicitly dismiss the known future-context signal"),
            }
        )
    elif assessment_required:
        blockers.append(
            {
                "reason_code": "future-context-assessment-required",
                "owner": str(future_context_capture.get("owner") or "outcome evidence producer"),
                "repair": "assess known evidence as material, already absorbed, or no-retention; unsupported observation must remain explicit",
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
        future_action = _as_dict(unresolved_future_context[0].get("operation_invocation")) if unresolved_future_context else {}
        if future_action and _registered_operation_action({"operation_invocation": future_action}):
            next_action = {
                "kind": "agentic-workspace/reconciliation-owner-operation/v1",
                "owner": str(unresolved_future_context[0].get("owner") or "future-context source owner"),
                "reason_code": "future-context-unresolved",
                "operation_invocation": future_action,
                "required_decision": str(unresolved_future_context[0].get("required_decision") or ""),
            }
        elif supplied.get("human_decision") or _registered_operation_action(supplied):
            next_action = supplied
        else:
            first = blockers[0]
            next_action = {
                "kind": "agentic-workspace/reconciliation-human-decision/v1",
                "human_decision": "select a supported recovery route from the named owner",
                "owner": first["owner"],
                "reason_code": first["reason_code"],
                "required_facts": [first["repair"]],
            }

    identity = {
        "result": result,
        "intent": intent,
        "proof": proof,
        "external_evidence": external,
        "residue": residue_input,
        "continuation": continuation_input,
        "module_contributions": module_facts,
        "future_context_signals": future_context_signals,
        "future_context_capture": future_context_capture,
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
        "future_context_signals": future_context_signals,
        "future_context_reconciliation": {
            "kind": "agentic-workspace/future-context-reconciliation/v1",
            "status": (
                "assessment-required"
                if assessment_required and not unresolved_future_context
                else "none-found"
                if not future_context_signals
                else "unresolved"
                if unresolved_future_context
                else "disposed"
            ),
            "capture_input_status": capture_status,
            "dispositions": future_context_dispositions,
            "none_found_allowed": not future_context_signals and not assessment_required,
            "custody_transfer_safe": not unresolved_future_context and not assessment_required,
            "rule": "none-found is available only when no explicit relevant candidate remains; skipped evaluation cannot erase a known signal.",
        },
        "rule": "Proof may support only the affected owner-level claim; semantic intent, parent completion, residue ownership, and continuation remain independently owned facts.",
    }
