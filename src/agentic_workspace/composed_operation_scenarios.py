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
    operation_authority = _operation_authority(implement)
    if not _operation_authority_supports_contract(operation_authority):
        return {}
    decision_packet = implement.get("decision_packet")
    if not isinstance(decision_packet, dict) or decision_packet.get("surface") != "implement":
        return {}
    detail_routes = decision_packet.get("detail_routes")
    if not isinstance(detail_routes, dict) or "proof" not in str(detail_routes.get("proof_detail") or ""):
        return {}
    decision = operation_authority.get("decision")
    if not isinstance(decision, dict):
        return {}
    return _authority_packet(
        scenario_id=scenario_id,
        source="implement.context.operation_authority",
        evidence_sources=[
            "implement.context.planning_safety_gate",
            "implement.context.operation_authority.typed_invocation",
            "implement.context.operation_authority.effect_authority",
            "implement.context.operation_authority.mutation_authority",
            "implement.context.operation_authority.proof_authority",
            "implement.decision_packet.detail_routes.proof_detail",
        ],
        decision={field: str(decision.get(field) or "") for field in CONTRACT_FIELDS},
        ordinary_packet_ref={
            "producer_module": "agentic_workspace.workspace_runtime_implement",
            "surface": "implement",
            "gate_result": str(gate.get("gate_result") or ""),
            "implementation_allowed": gate.get("implementation_allowed"),
            "decision_packet_kind": str(decision_packet.get("kind") or ""),
            "decision_packet_surface": str(decision_packet.get("surface") or ""),
            "proof_detail_route": str(detail_routes.get("proof_detail") or ""),
            "operation_authority_kind": str(operation_authority.get("kind") or ""),
            "operation_authority_status": str(operation_authority.get("status") or ""),
            "field_authority": operation_authority.get("field_authority", {}),
            "operating_decision": operation_authority.get("operating_decision", {}),
            "typed_invocation": operation_authority.get("typed_invocation", {}),
            "effect_authority": operation_authority.get("effect_authority", {}),
            "mutation_authority": operation_authority.get("mutation_authority", {}),
            "proof_authority": operation_authority.get("proof_authority", {}),
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


def _planning_gate(packet: dict[str, Any]) -> dict[str, Any]:
    context = packet.get("context") if isinstance(packet.get("context"), dict) else {}
    gate = context.get("planning_safety_gate") if isinstance(context, dict) else {}
    return gate if isinstance(gate, dict) else {}


def _operation_authority(packet: dict[str, Any]) -> dict[str, Any]:
    context = packet.get("context") if isinstance(packet.get("context"), dict) else {}
    authority = context.get("operation_authority") if isinstance(context, dict) else {}
    return authority if isinstance(authority, dict) else {}


def _operation_authority_supports_contract(authority: dict[str, Any]) -> bool:
    if authority.get("kind") != "agentic-workspace/operation-authority-projection/v1":
        return False
    if authority.get("producer_module") != "agentic_workspace.workspace_runtime_implement":
        return False
    if authority.get("surface") != "implement" or authority.get("status") != "admitted":
        return False
    decision = authority.get("decision")
    if not isinstance(decision, dict) or not all(isinstance(decision.get(field), str) and decision.get(field) for field in CONTRACT_FIELDS):
        return False
    operating_decision = _as_dict(authority.get("operating_decision"))
    if not _compiled_decision_supports_contract(operating_decision):
        return False
    typed_invocation = _as_dict(authority.get("typed_invocation"))
    if not _typed_invocation_supports_contract(typed_invocation, operating_decision):
        return False
    compiled_primary = _as_dict(operating_decision.get("primary_action"))
    compiled_owner = _as_dict(operating_decision.get("selected_owner"))
    if decision.get("owner") != compiled_owner.get("id"):
        return False
    if decision.get("terminal_state") != operating_decision.get("terminal_state"):
        return False
    if decision.get("typed_action") != compiled_primary.get("action"):
        return False
    if decision.get("next_transition") != compiled_primary.get("expected_transition"):
        return False
    if _as_dict(authority.get("effect_authority")).get("status") != "admitted":
        return False
    mutation_authority = _as_dict(authority.get("mutation_authority"))
    if mutation_authority.get("status") != "clean-baseline":
        return False
    if mutation_authority.get("allowed_path_count") != mutation_authority.get("changed_path_count"):
        return False
    if mutation_authority.get("allowed_scope_fingerprint") != mutation_authority.get("changed_scope_fingerprint"):
        return False
    if not str(mutation_authority.get("changed_scope_fingerprint") or "").startswith("sha256:"):
        return False
    if _as_dict(authority.get("proof_authority")).get("status") != "required-before-claim":
        return False
    field_authority = authority.get("field_authority")
    return isinstance(field_authority, dict) and set(CONTRACT_FIELDS).issubset(field_authority)


def _compiled_decision_supports_contract(decision: dict[str, Any]) -> bool:
    primary = _as_dict(decision.get("primary_action"))
    selected_owner = _as_dict(decision.get("selected_owner"))
    return (
        decision.get("status") == "actionable"
        and str(decision.get("decision_id") or "").startswith("operating-decision:")
        and str(decision.get("canonical_decision_input_revision") or "").startswith("sha256:")
        and selected_owner.get("id") == "direct-work"
        and decision.get("terminal_state") == "continue"
        and primary.get("action") == "implement"
        and primary.get("operation_id") == "implement.context"
        and primary.get("expected_transition") == "run-focused-proof"
    )


def _typed_invocation_supports_contract(invocation: dict[str, Any], operating_decision: dict[str, Any]) -> bool:
    arguments = _as_dict(invocation.get("arguments"))
    changed = arguments.get("changed")
    return (
        invocation.get("status") == "observed"
        and invocation.get("operation_id") == "implement.context"
        and invocation.get("contract_version") == "agentic-workspace/operation/v1"
        and invocation.get("action") == "implement"
        and invocation.get("expected_transition") == "run-focused-proof"
        and invocation.get("source") == "operating_decision.primary_action.operation_invocation"
        and str(invocation.get("expected_input_revision") or "").startswith("sha256:")
        and invocation.get("expected_input_revision") == operating_decision.get("canonical_decision_input_revision")
        and bool(invocation.get("idempotency_key"))
        and arguments.get("target") == "."
        and isinstance(changed, list)
        and all(isinstance(path, str) and path for path in changed)
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
