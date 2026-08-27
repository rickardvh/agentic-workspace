"""Authority observations for the active composed-operation release gate.

The scenario matrix is the product contract, not an owner oracle. Rows are only
eligible for the release gate when the checker can derive their decision from
ordinary AW output or from a canonical owner packet emitted by the owning
operation. Rows without that evidence remain declared but are not certified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentic_workspace.operating_decision import cross_owner_enforcement_projection
from agentic_workspace.operation_authority_admissions import normalize_owner_decision_packet

ACTIVE_RELEASE_GATE_SCENARIOS = frozenset({"fresh-direct-work", "handoff-return-admission"})

CONTRACT_FIELDS = (
    "owner",
    "terminal_state",
    "typed_action",
    "effect_scope",
    "mutation_precondition",
    "proof_claim_boundary",
    "next_transition",
)

CROSS_OWNER_INVARIANT_CASES = frozenset(
    {
        "target-identity-constructible",
        "proof-binding-before-execution",
        "proof-publication-fixed-point",
        "bounded-effect-custody",
        "future-residue-disposition",
        "peer-decision-identity",
        "nonlocal-delegation-lifecycle",
    }
)


def evaluate_cross_owner_invariant_case(case: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one release-gating counterexample without becoming runtime authority."""

    invariant = str(case.get("invariant") or "")
    observation = _as_dict(case.get("observation"))
    violations: list[str] = []
    if invariant not in CROSS_OWNER_INVARIANT_CASES:
        violations.append("unregistered-cross-owner-invariant")
    elif invariant == "target-identity-constructible":
        target_identity = str(observation.get("target_identity_ref") or "")
        blocker = _as_dict(observation.get("blocker"))
        recoveries = [str(item) for item in _as_list(blocker.get("recoveries")) if str(item)]
        if not target_identity and not (blocker.get("kind") == "typed-blocker" and len(recoveries) == 1):
            violations.append("offered-action-target-identity-is-not-constructible")
    elif invariant == "proof-binding-before-execution":
        if observation.get("deterministic_binding_mismatch") is True and observation.get("process_launched") is True:
            violations.append("deterministic-proof-mismatch-reached-process-launch")
    elif invariant == "proof-publication-fixed-point":
        semantic_changed = observation.get("semantic_dependency_changed") is True
        if not semantic_changed and observation.get("result_identity_before") != observation.get("result_identity_after"):
            violations.append("non-semantic-publication-invalidated-its-result")
        if observation.get("replay_count", 0) and observation.get("replay_result_identity") != observation.get("result_identity_after"):
            violations.append("proof-publication-replay-is-not-idempotent")
    elif invariant == "bounded-effect-custody":
        bounded = all(
            observation.get(field) is True
            for field in (
                "external_tracker_write",
                "bounded_candidate_set",
                "duplicate_check_complete",
                "repository_effects_excluded",
                "merge_close_effects_excluded",
            )
        )
        genuine_continuation = any(
            observation.get(field) is True for field in ("multi_session", "implementation_required", "owner_conflict")
        )
        if bounded and not genuine_continuation and observation.get("planning_custody_required") is True:
            violations.append("bounded-effect-acquired-custody-only-planning")
        if genuine_continuation and observation.get("planning_custody_required") is not True:
            violations.append("genuine-continuation-bypassed-planning-custody")
    elif invariant == "future-residue-disposition":
        if observation.get("future_relevant") is True:
            disposition = str(observation.get("disposition") or "")
            owner = str(observation.get("owner") or "")
            if disposition in {"", "none", "none_found", "not_evaluated"} or not owner:
                violations.append("future-relevant-residue-lacks-owner-backed-disposition")
    elif invariant == "peer-decision-identity":
        projection = cross_owner_enforcement_projection(
            decision=_as_dict(observation.get("decision")),
            peer_projections=[item for item in observation.get("peers", []) if isinstance(item, dict)],
        )
        violations.extend(str(item) for item in projection.get("findings", []) if str(item))
    elif invariant == "nonlocal-delegation-lifecycle":
        phase = str(observation.get("phase") or "")
        if phase == "assignment":
            if observation.get("binding_nonlocal") is not True or observation.get("identity_complete") is not True:
                violations.append("binding-nonlocal-assignment-is-not-current-and-complete")
            if observation.get("silent_local_fallback_allowed") is not False:
                violations.append("binding-nonlocal-assignment-allows-silent-local-fallback")
            if observation.get("executable_transport") is not True and observation.get("typed_manual_blocker") is not True:
                violations.append("binding-nonlocal-assignment-lacks-executable-or-manual-route")
        elif phase == "transport-parity":
            if observation.get("automatic_assignment_revision") != observation.get("manual_assignment_revision"):
                violations.append("transport-adapters-diverge-on-assignment-identity")
            if observation.get("semantic_contract_equal") is not True or observation.get("adapter_redefined_authority") is True:
                violations.append("transport-adapter-redefined-assignment-semantics")
        elif phase == "return-admission":
            expected = str(observation.get("expected") or "")
            actual = str(observation.get("actual") or "")
            if expected != actual:
                violations.append("returned-result-admission-did-not-fail-closed")
            if observation.get("worker_completion_authority") is not False:
                violations.append("worker-return-acquired-completion-authority")
            if actual == "admitted" and observation.get("next_action") != "orchestrator-integration-proof-closeout":
                violations.append("admitted-return-lacks-orchestrator-owned-continuation")
        elif phase == "direct-local-control":
            if observation.get("local_selected") is not True or observation.get("delegation_artifacts_created") is not False:
                violations.append("direct-local-control-acquired-delegation-custody")
        else:
            violations.append("unknown-nonlocal-delegation-phase")
    return {
        "kind": "agentic-workspace/cross-owner-invariant-result/v1",
        "case_id": str(case.get("id") or ""),
        "invariant": invariant,
        "status": "blocked" if violations else "admitted",
        "violations": violations,
        "rule": "This result is release-gating evidence; canonical runtime owners and the operating decision remain authoritative.",
    }


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

    del active_planning, start, summary, closeout, task, changed_paths
    if scenario_id not in ACTIVE_RELEASE_GATE_SCENARIOS:
        return {}
    if scenario_id == "handoff-return-admission":
        return _delegated_return_authority_packet(target=Path(str(target)), scenario_id=scenario_id)
    gate = _planning_gate(implement)
    if gate.get("gate_result") != "direct-work-allowed" or gate.get("workflow_sufficient") is not True:
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
            "workflow_sufficient": gate.get("workflow_sufficient"),
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


def _delegated_return_authority_packet(*, target: Path, scenario_id: str) -> dict[str, Any]:
    admission_root = target / ".agentic-workspace" / "local" / "assignment-runs"
    receipts = sorted(admission_root.glob("*/admission/*.admit.json")) if admission_root.exists() else []
    if not receipts:
        return {}
    try:
        receipt = json.loads(receipts[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw_owner_packet = receipt.get("owner_packet") if isinstance(receipt, dict) else None
    if not isinstance(raw_owner_packet, dict):
        return {}
    try:
        owner_packet = normalize_owner_decision_packet(raw_owner_packet)
    except ValueError:
        return {}
    typed_operation = _as_dict(owner_packet.get("typed_operation"))
    repair_operation = _as_dict(owner_packet.get("repair_operation"))
    admission = _as_dict(owner_packet.get("admission"))
    admitted = admission.get("admitted") is True
    return {
        "kind": "agentic-workspace/composed-operation-authority-observation/v1",
        "producer_module": "agentic_workspace.composed_operation_scenarios",
        "scenario_id": scenario_id,
        "source": "assignment.admit.owner_packet",
        "evidence_sources": [
            receipts[-1].relative_to(target).as_posix(),
            "assignment_identity.revision",
            "assignment.admit.current_authority",
        ],
        "observed": True,
        "rejection_observed": not admitted,
        "recovery_observed": not admitted,
        "repair_revalidation": {"status": "not-required"},
        "protected_action": {
            "attempted": True,
            "accepted": admitted,
            "repair": str(repair_operation.get("id") or ""),
        },
        "owner_packet": owner_packet,
        "decision": {
            "owner": str(owner_packet.get("owner") or ""),
            "terminal_state": str(owner_packet.get("terminal_state") or ""),
            "typed_action": str(typed_operation.get("action") or ""),
            "effect_scope": str(owner_packet.get("effect_scope") or ""),
            "mutation_precondition": str(admission.get("stable_reason") or ""),
            "proof_claim_boundary": str(owner_packet.get("proof_claim_boundary") or ""),
            "next_transition": str(typed_operation.get("expected_transition") or ""),
        },
        "rule": "The release-gated decision is projected from the assignment owner's persisted admission packet.",
    }


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
    direct = packet.get("planning_safety_gate")
    if isinstance(direct, dict):
        return direct
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
        and decision.get("producer_module") == "agentic_workspace.operating_decision"
        and decision.get("producer_function") == "compile_operating_decision"
        and str(decision.get("decision_id") or "").startswith("operating-decision:")
        and str(decision.get("canonical_decision_input_revision") or "").startswith("sha256:")
        and bool(selected_owner.get("id"))
        and bool(decision.get("terminal_state"))
        and bool(primary.get("action"))
        and bool(primary.get("operation_id"))
        and bool(primary.get("expected_transition"))
    )


def _typed_invocation_supports_contract(invocation: dict[str, Any], operating_decision: dict[str, Any]) -> bool:
    arguments = _as_dict(invocation.get("arguments"))
    changed = arguments.get("changed")
    return (
        invocation.get("status") == "observed"
        and invocation.get("producer_module") == "agentic_workspace.actionability"
        and invocation.get("producer_function") == "operation_invocation"
        and invocation.get("contract_version") == "agentic-workspace/operation/v1"
        and invocation.get("operation_id") == _as_dict(operating_decision.get("primary_action")).get("operation_id")
        and invocation.get("action") == _as_dict(operating_decision.get("primary_action")).get("action")
        and invocation.get("expected_transition") == _as_dict(operating_decision.get("primary_action")).get("expected_transition")
        and invocation.get("source") == "operating_decision.primary_action.operation_invocation"
        and str(invocation.get("expected_input_revision") or "").startswith("sha256:")
        and invocation.get("producer_revision") == invocation.get("expected_input_revision")
        and invocation.get("expected_input_revision") == operating_decision.get("canonical_decision_input_revision")
        and bool(invocation.get("idempotency_key"))
        and arguments.get("target") == "."
        and isinstance(changed, list)
        and all(isinstance(path, str) and path for path in changed)
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
