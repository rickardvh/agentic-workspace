"""Shared packet shape for owner-produced composed-operation decisions."""

from __future__ import annotations

from typing import Any


def owner_decision_packet(
    *,
    kind: str,
    producer_module: str,
    owner: str,
    status: str,
    admitted: bool,
    source: str,
    typed_action: str,
    effect_scope: str,
    stable_reason: str,
    proof_claim_boundary: str,
    next_transition: str,
    terminal_state: str,
    operation_id: str,
    producer_observation: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    repair = "none" if admitted else next_transition
    return {
        "kind": kind,
        "producer_module": producer_module,
        "owner": owner,
        "status": status,
        "admitted": admitted,
        "source": source,
        "operation_id": operation_id,
        "stable_reason": stable_reason,
        "effect_scope": effect_scope,
        "proof_claim_boundary": proof_claim_boundary,
        "terminal_state": terminal_state,
        "typed_operation": {"id": operation_id, "action": typed_action},
        "repair_operation": {"id": next_transition, "owner": owner, "status": "not-needed" if admitted else "required"},
        "admission": {"status": status, "admitted": admitted, "stable_reason": stable_reason, "repair": repair},
        "producer_observation": producer_observation,
        **extra,
    }
