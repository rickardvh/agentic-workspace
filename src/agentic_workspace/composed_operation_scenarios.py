"""Producer-owned composed-operation scenario authority observations.

The scenario checker supplies fixture state, but this module does not use a
scenario-id oracle to author the final decision.  It attempts the same bounded
authority front doors used by ordinary AW consumers, then projects the compact
scenario contract from those producer-owned packets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentic_workspace.operation_authority_admissions import normalize_owner_decision_packet, revalidate_typed_repair

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
    target: Path,
    scenario_id: str,
    active_planning: bool,
    start: dict[str, Any],
    implement: dict[str, Any],
    summary: dict[str, Any],
    closeout: dict[str, Any],
    task: str = "",
    changed_paths: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    changed = [str(path) for path in changed_paths if str(path).strip()] or ["README.md"]
    owner_receipt = _owner_receipt(target=target, scenario_id=scenario_id)
    owner_packets = _attempt_owner_boundaries(
        target=target,
        scenario_id=scenario_id,
        task=task,
        changed_paths=changed,
        owner_receipt=owner_receipt,
        start=start,
        implement=implement,
        summary=summary,
        closeout=closeout,
    )
    for packet in owner_packets:
        decision = _project_decision_from_owner_packet(
            target=target,
            packet=packet,
            active_planning=active_planning,
            start=start,
            implement=implement,
            summary=summary,
            closeout=closeout,
            changed_paths=changed,
        )
        if decision:
            return _authority_packet(
                scenario_id=scenario_id,
                source=str(packet.get("kind") or packet.get("resolver_owner") or "unknown-owner-packet"),
                evidence_sources=_evidence_sources(packet),
                owner_packet=packet,
                decision=decision,
                rejection_observed=_packet_rejected(packet, decision),
                recovery_revalidation=revalidate_typed_repair(
                    target=target,
                    owner_packet=packet,
                    changed_paths=changed,
                ),
            )
    return {}


def _attempt_owner_boundaries(
    *,
    target: Path,
    scenario_id: str,
    task: str,
    changed_paths: list[str],
    owner_receipt: dict[str, Any],
    start: dict[str, Any],
    implement: dict[str, Any],
    summary: dict[str, Any],
    closeout: dict[str, Any],
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for source_packet in (start, implement, summary, closeout):
        emitted = source_packet.get("composed_operation_owner_packets") if isinstance(source_packet, dict) else None
        if not isinstance(emitted, list):
            continue
        for owner_packet in emitted:
            if isinstance(owner_packet, dict):
                packets.append(normalize_owner_decision_packet(owner_packet))
    return packets


def _project_decision_from_owner_packet(
    *,
    target: Path,
    packet: dict[str, Any],
    active_planning: bool,
    start: dict[str, Any],
    implement: dict[str, Any],
    summary: dict[str, Any],
    closeout: dict[str, Any],
    changed_paths: list[str],
) -> dict[str, str]:
    return _decision_from_producer_packet(packet)


def _authority_packet(
    *,
    scenario_id: str,
    source: str,
    evidence_sources: list[str],
    owner_packet: dict[str, Any],
    decision: dict[str, str],
    rejection_observed: bool = False,
    recovery_revalidation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recovery = recovery_revalidation if isinstance(recovery_revalidation, dict) else {}
    recovery_observed = recovery.get("status") == "valid-terminal-after-repair"
    repair = decision["next_transition"] if rejection_observed or recovery_observed else ""
    return {
        "kind": "agentic-workspace/composed-operation-authority-observation/v1",
        "producer_module": "agentic_workspace.composed_operation_scenarios",
        "scenario_id": scenario_id,
        "source": source,
        "evidence_sources": evidence_sources,
        "observed": True,
        "rejection_observed": rejection_observed,
        "recovery_observed": recovery_observed,
        "repair_revalidation": recovery,
        "protected_action": {
            "attempted": _packet_attempted(owner_packet),
            "accepted": not rejection_observed,
            "repair": repair,
        },
        "owner_packet": owner_packet,
        "decision": decision,
        "rule": (
            "Decision is projected from producer-owned admission, typed-operation, repair, and receipt fields; "
            "scenario fixtures may create state but do not author copied contract observations."
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


def _decision_from_producer_packet(packet: dict[str, Any]) -> dict[str, str]:
    admission = packet.get("admission")
    typed_operation = packet.get("typed_operation")
    repair_operation = packet.get("repair_operation")
    if not isinstance(admission, dict) or not isinstance(typed_operation, dict) or not isinstance(repair_operation, dict):
        return {}
    owner = str(packet.get("owner") or "")
    terminal_state = str(packet.get("terminal_state") or "")
    typed_action = str(typed_operation.get("action") or "")
    effect_scope = str(packet.get("effect_scope") or "")
    mutation_precondition = str(admission.get("stable_reason") or packet.get("stable_reason") or "")
    proof_claim_boundary = str(packet.get("proof_claim_boundary") or "")
    next_transition = str(repair_operation.get("id") or "")
    if not all((owner, terminal_state, typed_action, effect_scope, mutation_precondition, proof_claim_boundary, next_transition)):
        return {}
    return _decision(
        owner,
        terminal_state,
        typed_action,
        effect_scope,
        mutation_precondition,
        proof_claim_boundary,
        next_transition,
    )


def _owner_receipt(*, target: Path, scenario_id: str) -> dict[str, Any]:
    return _read_json_if_present(target / ".agentic-workspace" / "local" / "composed-operation-scenarios" / f"{scenario_id}.json")


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "invalid-json"}
    return payload if isinstance(payload, dict) else {"status": "not-object"}


def _planning_gate(packet: dict[str, Any]) -> dict[str, Any]:
    context = packet.get("context") if isinstance(packet.get("context"), dict) else {}
    gate = context.get("planning_safety_gate") if isinstance(context, dict) else {}
    return gate if isinstance(gate, dict) else {}


def _closeout_blocks_completion(closeout: dict[str, Any]) -> bool:
    answer = closeout.get("answer") if isinstance(closeout.get("answer"), dict) else closeout
    if not isinstance(answer, dict):
        return False
    options = answer.get("completion_options")
    if isinstance(options, list):
        for option in options:
            if isinstance(option, dict) and option.get("id") in {"claim-work-complete", "claim-slice-complete"}:
                return option.get("allowed") is False
    current = answer.get("current_task_closeout")
    if isinstance(current, dict):
        current_options = current.get("completion_options")
        if isinstance(current_options, list):
            return any(
                isinstance(option, dict)
                and option.get("id") in {"claim-work-complete", "claim-slice-complete"}
                and option.get("allowed") is False
                for option in current_options
            )
    return False


def _evidence_sources(packet: dict[str, Any]) -> list[str]:
    sources = [str(packet.get("source") or packet.get("resolver_owner") or packet.get("kind") or "owner-packet")]
    if isinstance(packet.get("failures"), list):
        sources.extend(str(item.get("field") or item.get("reason")) for item in packet["failures"] if isinstance(item, dict))
    if isinstance(packet.get("live_resolution"), dict):
        sources.append(str(packet["live_resolution"].get("source") or "boundary.live-resolution"))
    return [source for source in sources if source]


def _packet_attempted(packet: dict[str, Any]) -> bool:
    if isinstance(packet.get("admission"), dict) and isinstance(packet.get("typed_operation"), dict):
        return True
    return str(packet.get("kind") or "") in {
        "agentic-workspace/mutation-boundary-admission/v1",
        "agentic-workspace/authority-effect-resolution/v1",
        "agentic-workspace/external-observation-admission/v1",
        "agentic-workspace/generated-target-capability-admission/v1",
        "agentic-workspace/generated-target-projection-admission/v1",
        "agentic-workspace/runtime-readiness-admission/v1",
    }


def _packet_rejected(packet: dict[str, Any], decision: dict[str, str]) -> bool:
    admission = packet.get("admission")
    if isinstance(admission, dict):
        return admission.get("admitted") is False
    if packet.get("admitted") is False or packet.get("status") == "rejected":
        return True
    return decision.get("terminal_state") in {"blocked", "partial"} or decision.get("mutation_precondition", "").endswith("-rejected")


def _packet_recovery_observed(packet: dict[str, Any], decision: dict[str, str]) -> bool:
    recovery = packet.get("repair_revalidation")
    if isinstance(recovery, dict) and recovery:
        return recovery.get("status") == "valid-terminal-after-repair"
    repair = str(packet.get("repair") or "")
    return bool(repair and repair != "none") or decision.get("typed_action") in {"recover", "admit-result", "run-proof"}
