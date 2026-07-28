"""Strict normalization for owner-authored composed-operation packets.

This module does not create decisions, inspect fixture state, or perform
repairs. It only validates that an already-emitted packet came from its
registered owning module and then annotates the normalized authority boundary.
"""

from __future__ import annotations

from typing import Any

ADAPTER_MODULE = "agentic_workspace.operation_authority_admissions"

OWNER_PACKET_PRODUCERS = {
    "agentic-workspace/mutation-boundary-admission/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/transaction-boundary-admission/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/proof-receipt-admission/v1": "agentic_workspace.proof_receipt_admission",
    "agentic-workspace/delegated-return-admission/v1": "agentic_workspace.assignment_lifecycle",
    "agentic-workspace/external-observation-admission/v1": "agentic_workspace.external_intent",
    "agentic-workspace/generated-target-capability-admission/v1": "agentic_workspace.client",
    "agentic-workspace/generated-target-projection-admission/v1": "agentic_workspace.client",
    "agentic-workspace/authority-effect-resolution/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/runtime-readiness-admission/v1": "agentic_workspace.workspace_runtime_startup",
    "agentic-workspace/target-identity-admission/v1": "agentic_workspace.workspace_runtime_startup",
    "agentic-workspace/planning-task-switch-admission/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/external-intent-admission/v1": "agentic_workspace.external_intent",
    "agentic-workspace/planning-continuation-admission/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/skill-routing-admission/v1": "agentic_workspace.workspace_runtime_startup",
    "agentic-workspace/dirty-worktree-admission/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/planning-closeout-boundary/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/planning-owner-state/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/planning-route-decision/v1": "agentic_workspace.workspace_runtime_planning",
}


def _normalize_owner_decision_packet(owner_packet: dict[str, Any]) -> dict[str, Any]:
    kind = str(owner_packet.get("kind") or "")
    producer_module = OWNER_PACKET_PRODUCERS.get(kind)
    if not producer_module:
        raise ValueError(f"no owner producer registered for {kind}")
    if owner_packet.get("producer_module") != producer_module:
        raise ValueError(f"{kind} produced by {owner_packet.get('producer_module')!r}, expected {producer_module!r}")
    if producer_module == ADAPTER_MODULE:
        raise ValueError("adapter-authored owner packets are not admissible")
    if owner_packet.get("normalizer_module"):
        raise ValueError("owner packet is already normalized")
    required = {
        "owner",
        "status",
        "source",
        "operation_id",
        "stable_reason",
        "effect_scope",
        "proof_claim_boundary",
        "terminal_state",
        "typed_operation",
        "repair_operation",
        "admission",
        "producer_observation",
    }
    missing = sorted(required.difference(owner_packet))
    if missing:
        raise ValueError(f"{kind} owner packet is missing decision fields: {', '.join(missing)}")
    if not isinstance(owner_packet.get("producer_observation"), dict) or not owner_packet["producer_observation"].get("kind"):
        raise ValueError(f"{kind} owner packet lacks producer observation")
    return {
        **owner_packet,
        "normalizer_module": ADAPTER_MODULE,
        "owner_decision_authority": {
            "status": "owner-produced",
            "producer_module": producer_module,
            "normalizer_module": ADAPTER_MODULE,
            "decision_fields": [
                "owner",
                "terminal_state",
                "typed_operation.action",
                "effect_scope",
                "admission.stable_reason",
                "proof_claim_boundary",
                "repair_operation.id",
            ],
            "normalizer_supplied_decision": False,
        },
    }


def normalize_owner_decision_packet(owner_packet: dict[str, Any]) -> dict[str, Any]:
    """Normalize one raw packet emitted by its canonical owner operation."""

    return _normalize_owner_decision_packet(owner_packet)
