"""Authority observations for the active composed-operation release gate.

The scenario matrix is the product contract, not an owner oracle. Rows are only
eligible for the release gate when the checker can derive their decision from
ordinary AW output or from a canonical owner packet emitted by the owning
operation. Rows without that evidence remain declared but are not certified.
"""

from __future__ import annotations

from typing import Any

ACTIVE_RELEASE_GATE_SCENARIOS = frozenset({"fresh-direct-work"})

CONTRACT_FIELDS = (
    "owner",
    "terminal_state",
    "typed_action",
    "effect_scope",
    "mutation_precondition",
    "proof_claim_boundary",
    "next_transition",
)


def observe_composed_operation_authority(
    *,
    target: object,
    scenario_id: str,
    active_planning: bool,
    start: dict[str, Any],
    implement: dict[str, Any],
    summary: dict[str, Any],
    closeout: dict[str, Any],
    task: str = "",
    changed_paths: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return an observation only when the ordinary packet owns the decision.

    Parameters beyond ``scenario_id`` and ``implement`` are accepted to keep the
    checker call site stable across future owner-backed rows.
    """

    del target, active_planning, start, summary, closeout, task, changed_paths
    if scenario_id not in ACTIVE_RELEASE_GATE_SCENARIOS:
        return {}
    gate = _planning_gate(implement)
    if gate.get("gate_result") != "direct-work-allowed" or gate.get("implementation_allowed") is not True:
        return {}
    decision_packet = implement.get("decision_packet")
    if not isinstance(decision_packet, dict) or decision_packet.get("surface") != "implement":
        return {}
    detail_routes = decision_packet.get("detail_routes")
    if not isinstance(detail_routes, dict) or "proof" not in str(detail_routes.get("proof_detail") or ""):
        return {}
    return _authority_packet(
        scenario_id=scenario_id,
        source="implement.context.planning_safety_gate",
        evidence_sources=[
            "implement.context.planning_safety_gate",
            "implement.decision_packet.detail_routes.proof_detail",
        ],
        decision=_decision(
            owner="direct-work",
            terminal_state="continue",
            typed_action="implement",
            effect_scope="changed-paths-only",
            mutation_precondition="clean-baseline",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="run-focused-proof",
        ),
        ordinary_packet_ref={
            "producer_module": "agentic_workspace.workspace_runtime_implement",
            "surface": "implement",
            "gate_result": str(gate.get("gate_result") or ""),
            "implementation_allowed": gate.get("implementation_allowed"),
            "decision_packet_kind": str(decision_packet.get("kind") or ""),
            "decision_packet_surface": str(decision_packet.get("surface") or ""),
            "proof_detail_route": str(detail_routes.get("proof_detail") or ""),
        },
    )


def _authority_packet(
    *,
    scenario_id: str,
    source: str,
    evidence_sources: list[str],
    decision: dict[str, str],
    ordinary_packet_ref: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/composed-operation-authority-observation/v1",
        "producer_module": "agentic_workspace.composed_operation_scenarios",
        "scenario_id": scenario_id,
        "source": source,
        "evidence_sources": evidence_sources,
        "observed": True,
        "rejection_observed": False,
        "recovery_observed": False,
        "repair_revalidation": {"status": "not-required"},
        "protected_action": {
            "attempted": True,
            "accepted": True,
            "repair": "",
        },
        "ordinary_packet_ref": ordinary_packet_ref,
        "decision": decision,
        "rule": (
            "The release-gated decision is derived from ordinary implement output. "
            "Scenario fixture files do not author decision-bearing packets."
        ),
    }


def _decision(
    owner: str,
    terminal_state: str,
    typed_action: str,
    effect_scope: str,
    mutation_precondition: str,
    proof_claim_boundary: str,
    next_transition: str,
) -> dict[str, str]:
    return {
        "owner": owner,
        "terminal_state": terminal_state,
        "typed_action": typed_action,
        "effect_scope": effect_scope,
        "mutation_precondition": mutation_precondition,
        "proof_claim_boundary": proof_claim_boundary,
        "next_transition": next_transition,
    }


def _planning_gate(packet: dict[str, Any]) -> dict[str, Any]:
    context = packet.get("context") if isinstance(packet.get("context"), dict) else {}
    gate = context.get("planning_safety_gate") if isinstance(context, dict) else {}
    return gate if isinstance(gate, dict) else {}
