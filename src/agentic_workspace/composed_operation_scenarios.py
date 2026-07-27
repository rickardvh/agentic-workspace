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

from agentic_workspace.authority_envelope import admit_live_mutation_boundary, resolve_authority_effect_envelope
from agentic_workspace.client import negotiate_requirements

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
                recovery_observed=_packet_recovery_observed(packet, decision),
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
    expected = owner_receipt.get("mutation_baseline") if isinstance(owner_receipt.get("mutation_baseline"), dict) else None
    packets: list[dict[str, Any]] = []
    if (target / ".agentic-workspace" / "local" / "planning" / "owner-selection.json").exists():
        packets.append(
            _with_fault_ref(
                admit_live_mutation_boundary(
                    boundary_id="destructive-mutation",
                    target_root=target,
                    expected=expected,
                    allowed_paths=changed_paths,
                    owner_id="planning",
                    claim_action="inspect",
                ),
                ".agentic-workspace/local/planning/owner-selection.json",
            )
        )
    if (target / ".agentic-workspace" / "local" / "planning" / "mutation-owner.json").exists():
        packets.append(
            admit_live_mutation_boundary(
                boundary_id="destructive-mutation",
                target_root=target,
                expected=expected,
                allowed_paths=changed_paths,
                owner_id="planning",
                claim_action="inspect",
            )
        )
    stale_scope = _read_json_if_present(target / ".agentic-workspace" / "local" / "actions" / "stale-scope.json")
    if stale_scope:
        requested_paths = [str(path) for path in stale_scope.get("requested_paths", []) if isinstance(path, str)]
        packets.append(
            admit_live_mutation_boundary(
                boundary_id="destructive-mutation",
                target_root=target,
                expected=expected,
                allowed_paths=requested_paths or changed_paths,
                owner_id="workspace",
                claim_action="inspect",
            )
        )
    if (target / ".agentic-workspace" / "local" / "transactions" / "partial-write.json").exists():
        packets.append(
            _with_fault_ref(
                admit_live_mutation_boundary(
                    boundary_id="destructive-mutation",
                    target_root=target,
                    expected=expected,
                    allowed_paths=changed_paths,
                    owner_id="workspace",
                    claim_action="inspect",
                ),
                ".agentic-workspace/local/transactions/partial-write.json",
            )
        )
    if (target / ".agentic-workspace" / "local" / "proof" / "last.json").exists():
        packets.append(
            admit_live_mutation_boundary(
                boundary_id="proof-admission",
                target_root=target,
                expected=expected,
                allowed_paths=changed_paths,
                owner_id="verification",
                claim_action="inspect",
            )
        )
    if (target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json").exists():
        packets.append(
            admit_live_mutation_boundary(
                boundary_id="returned-worker-admission",
                target_root=target,
                expected=expected,
                allowed_paths=changed_paths,
                owner_id="delegation",
                claim_action="inspect",
            )
        )
    malformed = target / ".agentic-workspace" / "local" / "external-observations" / "malformed.json"
    if malformed.exists():
        packets.append(_external_observation_admission_packet(target=target, observation_path=malformed))
    capability = _read_json_if_present(target / ".agentic-workspace" / "local" / "adapters" / "capability.json")
    if capability:
        packets.append(
            {
                "kind": "agentic-workspace/generated-target-capability-admission/v1",
                "status": "rejected",
                "admitted": False,
                "source": ".agentic-workspace/local/adapters/capability.json",
                "operation": capability.get("operation") or "implement.context",
                "negotiation": negotiate_requirements({str(capability.get("operation") or "implement.context"): "sha256:unsupported"}),
                "repair": "select-compatible-adapter",
            }
        )
    projection = _read_json_if_present(target / "generated" / ".agentic-workspace-cli-fingerprint.json")
    if projection.get("status") == "drifted":
        packets.append(
            {
                "kind": "agentic-workspace/generated-target-projection-admission/v1",
                "status": "rejected",
                "admitted": False,
                "source": "generated/.agentic-workspace-cli-fingerprint.json",
                "negotiation": negotiate_requirements({"start.context": "sha256:drifted"}),
                "repair": "regenerate-projection",
            }
        )
    if (target / "incoming" / "untrusted.txt").exists():
        packets.append(
            resolve_authority_effect_envelope(
                target_root=target,
                changed_paths=changed_paths,
                task_text=task,
                requested_effects=["write-outside-scope"],
                instruction_sources=[
                    {
                        "class": "untrusted-content",
                        "source": "incoming/untrusted.txt",
                        "requested_effects": ["write-outside-scope"],
                    }
                ],
            )
        )
    runtime = _read_json_if_present(target / ".agentic-workspace" / "local" / "runtime" / "availability.json")
    if runtime:
        packets.append(_runtime_readiness_packet(runtime))
    packets.extend(
        _ordinary_route_owner_packets(
            target=target,
            scenario_id=scenario_id,
            start=start,
            implement=implement,
            summary=summary,
            closeout=closeout,
        )
    )
    return packets


def _ordinary_route_owner_packets(
    *,
    target: Path,
    scenario_id: str,
    start: dict[str, Any],
    implement: dict[str, Any],
    summary: dict[str, Any],
    closeout: dict[str, Any],
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    local_state = {
        "task_switch": _read_json_if_present(target / ".agentic-workspace" / "local" / "planning" / "task-switch.json"),
        "target_identity": _read_json_if_present(target / ".agentic-workspace" / "local" / "workspace" / "target-identity.json"),
        "external_intent": _read_json_if_present(target / ".agentic-workspace" / "local" / "external-intent" / "issue-2300.json"),
        "continuation": _read_json_if_present(target / ".agentic-workspace" / "local" / "continuation" / "compacted.json"),
        "missing_skill": (target / ".agentic-workspace" / "skills" / "workspace-startup" / "SKILL.missing").exists(),
        "dirty_user_edit": (target / "notes" / "user-owned.md").exists(),
    }
    if any(bool(value) for value in local_state.values()):
        packets.append({"kind": "agentic-workspace/ordinary-route-state/v1", "state": local_state, "source": "ordinary-consumer-packets"})
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "closeout" / "premature.json") and _closeout_blocks_completion(
        closeout
    ):
        packets.append({"kind": "agentic-workspace/planning-closeout-boundary/v1", "status": "rejected", "source": "report.closeout_trust"})
    continuation = summary.get("continuation_view") if isinstance(summary.get("continuation_view"), dict) else {}
    plan_path = target / ".agentic-workspace" / "planning" / "execplans" / f"{scenario_id}.plan.json"
    plan = _read_json_if_present(plan_path)
    if continuation or plan:
        packets.append(
            {
                "kind": "agentic-workspace/planning-owner-state/v1",
                "continuation": continuation,
                "plan": plan,
                "plan_path": plan_path.relative_to(target).as_posix() if plan_path.exists() else "",
                "source": "summary.continuation_view",
            }
        )
    gate = _planning_gate(implement)
    if gate:
        packets.append(
            {
                "kind": "agentic-workspace/planning-route-decision/v1",
                "planning_gate": gate,
                "source": "implement.context.planning_safety_gate",
            }
        )
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
    kind = str(packet.get("kind") or "")
    if kind == "agentic-workspace/mutation-boundary-admission/v1":
        return _decision_from_mutation_admission(packet)
    if kind == "agentic-workspace/authority-effect-resolution/v1":
        return _decision_from_authority_effect(packet)
    if kind == "agentic-workspace/external-observation-admission/v1":
        return _decision(
            "workspace",
            "blocked",
            "recover",
            "external-observation-only",
            "malformed-observation-rejected",
            "no-completion-claim",
            "request-valid-observation",
        )
    if kind == "agentic-workspace/generated-target-capability-admission/v1":
        return _decision(
            "generated-target",
            "blocked",
            "recover",
            "adapter-capability-only",
            "adapter-capability-rejected",
            "no-completion-claim",
            "select-compatible-adapter",
        )
    if kind == "agentic-workspace/generated-target-projection-admission/v1":
        return _decision(
            "generated-target",
            "blocked",
            "recover",
            "generated-target-only",
            "projection-drift-rejected",
            "no-completion-claim",
            "regenerate-projection",
        )
    if kind == "agentic-workspace/runtime-readiness-admission/v1":
        return _decision_from_runtime(packet)
    if kind == "agentic-workspace/planning-closeout-boundary/v1" and _closeout_blocks_completion(closeout):
        return _decision(
            "planning",
            "partial",
            "continue",
            "claim-boundary-only",
            "acceptance-incomplete",
            "partial-claim-only",
            "continue-unresolved-work",
        )
    if kind == "agentic-workspace/planning-owner-state/v1":
        decision = _decision_from_planning_owner_state(packet)
        if decision:
            return decision
    if kind == "agentic-workspace/ordinary-route-state/v1":
        decision = _decision_from_ordinary_state(packet, target=target)
        if decision:
            return decision
    if kind == "agentic-workspace/planning-route-decision/v1":
        return _decision_from_route_packet(packet, active_planning=active_planning, start=start, implement=implement)
    return {}


def _decision_from_mutation_admission(packet: dict[str, Any]) -> dict[str, str]:
    boundary = str(packet.get("boundary_id") or "")
    fault_ref = str(packet.get("scenario_fault_ref") or "")
    failures = [item for item in packet.get("failures", []) if isinstance(item, dict)]
    reasons = {str(item.get("reason") or "") for item in failures}
    if "owner-selection.json" in fault_ref:
        return _decision(
            "planning",
            "blocked",
            "recover",
            "no-mutation",
            "stale-cas-rejected",
            "no-completion-claim",
            "refresh-mutation-owner",
        )
    if "partial-write.json" in fault_ref:
        return _decision(
            "workspace",
            "blocked",
            "recover",
            "transaction-state-only",
            "partial-write-rejected",
            "no-completion-claim",
            "rollback-or-retry-transaction",
        )
    if boundary == "proof-admission":
        return _decision(
            "verification",
            "continue",
            "run-proof",
            "proof-selection-only",
            "stale-proof-rejected",
            "fresh-proof-required",
            "rerun-selected-proof",
        )
    if boundary == "returned-worker-admission":
        return _decision(
            "delegation",
            "continue",
            "admit-result",
            "returned-result-admission",
            "return-receipt-current",
            "admitted-result-before-claim",
            "admit-or-repair-return",
        )
    if "overlapping-mutation-claim" in reasons:
        return _decision(
            "planning",
            "blocked",
            "recover",
            "no-mutation",
            "overlapping-mutation-rejected",
            "no-completion-claim",
            "inspect-overlap-owner",
        )
    if "scope-expanded" in reasons:
        return _decision(
            "workspace",
            "blocked",
            "recover",
            "no-mutation",
            "scope-widening-rejected",
            "no-completion-claim",
            "narrow-scope-and-refresh",
        )
    if {"unexpected-path-overlap", "untracked-managed-state"} & reasons:
        return _decision(
            "workspace",
            "blocked",
            "recover",
            "transaction-state-only",
            "partial-write-rejected",
            "no-completion-claim",
            "rollback-or-retry-transaction",
        )
    if {"baseline-head-changed", "scoped-state-fingerprint-changed"} & reasons:
        return _decision(
            "planning",
            "blocked",
            "recover",
            "no-mutation",
            "stale-cas-rejected",
            "no-completion-claim",
            "refresh-mutation-owner",
        )
    return {}


def _decision_from_authority_effect(packet: dict[str, Any]) -> dict[str, str]:
    boundary_payload = packet.get("untrusted_content_boundary")
    boundary: dict[str, Any] = boundary_payload if isinstance(boundary_payload, dict) else {}
    if "write-outside-scope" in set(boundary.get("blocked_effects", [])):
        return _decision(
            "workspace",
            "continue",
            "ignore-data-instruction",
            "trusted-instruction-sources-only",
            "data-text-not-authority",
            "proof-before-completion-claim",
            "continue-safe-route",
        )
    return {}


def _decision_from_runtime(packet: dict[str, Any]) -> dict[str, str]:
    status = str(packet.get("status") or "")
    if status == "unavailable":
        return _decision(
            "workspace",
            "blocked",
            "recover",
            "runtime-state-only",
            "runtime-incompatible",
            "no-completion-claim",
            "restore-runtime",
        )
    if status == "restored":
        return _decision(
            "workspace",
            "continue",
            "start",
            "startup-reentry-only",
            "runtime-restored",
            "proof-before-completion-claim",
            "restart-ordinary-route",
        )
    return {}


def _decision_from_planning_owner_state(packet: dict[str, Any]) -> dict[str, str]:
    plan_payload = packet.get("plan")
    plan: dict[str, Any] = plan_payload if isinstance(plan_payload, dict) else {}
    continuation_payload = packet.get("continuation")
    continuation: dict[str, Any] = continuation_payload if isinstance(continuation_payload, dict) else {}
    if plan.get("status") == "completed":
        return _decision(
            "planning",
            "partial",
            "route-residue",
            "residue-record-only",
            "completed-owner-current",
            "partial-claim-only",
            "open-residue-owner",
        )
    if str((continuation or {}).get("status") or "") == "present" or plan:
        return _decision(
            "planning",
            "continue",
            "continue",
            "selected-owner-only",
            "owner-revision-current",
            "owner-proof-before-completion",
            "resume-current-slice",
        )
    return {}


def _decision_from_ordinary_state(packet: dict[str, Any], *, target: Path) -> dict[str, str]:
    state_payload = packet.get("state")
    state: dict[str, Any] = state_payload if isinstance(state_payload, dict) else {}
    target_identity = state.get("target_identity")
    if isinstance(target_identity, dict) and target_identity.get("status") == "rebound":
        return _decision(
            "workspace",
            "continue",
            "recover",
            "workspace-routing-state",
            "target-identity-rebound",
            "proof-after-recovery",
            "refresh-startup-context",
        )
    task_switch = state.get("task_switch")
    if isinstance(task_switch, dict) and task_switch.get("status") == "new-task-only":
        return _decision(
            "planning",
            "continue",
            "reconcile",
            "new-task-only",
            "active-owner-preserved",
            "no-active-owner-completion-claim",
            "acknowledge-task-switch",
        )
    external_intent = state.get("external_intent")
    if isinstance(external_intent, dict) and external_intent.get("status") == "current":
        return _decision(
            "issue-scope",
            "continue",
            "implement",
            "issue-bounded-paths",
            "clean-baseline",
            "proof-before-completion-claim",
            "run-focused-proof",
        )
    continuation = state.get("continuation")
    if isinstance(continuation, dict) and continuation.get("status") == "compacted":
        return _decision(
            "planning",
            "continue",
            "continue",
            "continuation-state-only",
            "continuation-revision-current",
            "continuation-proof-before-claim",
            "resume-after-compaction",
        )
    if state.get("missing_skill") is True:
        return _decision(
            "workspace",
            "blocked",
            "recover",
            "skill-routing-only",
            "skill-dependency-unavailable",
            "no-completion-claim",
            "install-or-select-supported-skill",
        )
    if state.get("dirty_user_edit") is True:
        return _decision(
            "workspace",
            "continue",
            "implement",
            "non-overlapping-changed-paths",
            "preexisting-edits-preserved",
            "proof-before-completion-claim",
            "inspect-dirty-overlap",
        )
    return {}


def _decision_from_route_packet(
    packet: dict[str, Any], *, active_planning: bool, start: dict[str, Any], implement: dict[str, Any]
) -> dict[str, str]:
    gate_payload = packet.get("planning_gate")
    gate: dict[str, Any] = gate_payload if isinstance(gate_payload, dict) else {}
    if not active_planning and gate.get("gate_result") == "direct-work-allowed":
        return _decision(
            "direct-work",
            "continue",
            "implement",
            "changed-paths-only",
            "clean-baseline",
            "proof-before-completion-claim",
            "run-focused-proof",
        )
    return {}


def _authority_packet(
    *,
    scenario_id: str,
    source: str,
    evidence_sources: list[str],
    owner_packet: dict[str, Any],
    decision: dict[str, str],
    rejection_observed: bool = False,
    recovery_observed: bool = False,
) -> dict[str, Any]:
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
        "protected_action": {
            "attempted": _packet_attempted(owner_packet),
            "accepted": not rejection_observed,
            "repair": repair,
        },
        "owner_packet": owner_packet,
        "decision": decision,
        "rule": "Decision is projected from the embedded owner_packet; scenario fixtures may create state but do not author contract fields.",
    }


def _with_fault_ref(packet: dict[str, Any], fault_ref: str) -> dict[str, Any]:
    return {**packet, "scenario_fault_ref": fault_ref}


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


def _owner_receipt(*, target: Path, scenario_id: str) -> dict[str, Any]:
    return _read_json_if_present(target / ".agentic-workspace" / "local" / "composed-operation-scenarios" / f"{scenario_id}.json")


def _external_observation_admission_packet(*, target: Path, observation_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(observation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "kind": "agentic-workspace/external-observation-admission/v1",
            "status": "rejected",
            "admitted": False,
            "source": observation_path.relative_to(target).as_posix(),
            "reason": "malformed-json",
            "repair": "request-valid-observation",
            "error": exc.__class__.__name__,
        }
    return {
        "kind": "agentic-workspace/external-observation-admission/v1",
        "status": "admitted" if isinstance(payload, dict) else "rejected",
        "admitted": isinstance(payload, dict),
        "source": observation_path.relative_to(target).as_posix(),
        "reason": "valid-json" if isinstance(payload, dict) else "not-object",
        "repair": "none" if isinstance(payload, dict) else "request-valid-observation",
    }


def _runtime_readiness_packet(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "")
    return {
        "kind": "agentic-workspace/runtime-readiness-admission/v1",
        "status": status,
        "admitted": status != "unavailable",
        "source": ".agentic-workspace/local/runtime/availability.json",
        "repair": "restore-runtime" if status == "unavailable" else "restart-ordinary-route" if status == "restored" else "none",
    }


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
    return str(packet.get("kind") or "") in {
        "agentic-workspace/mutation-boundary-admission/v1",
        "agentic-workspace/authority-effect-resolution/v1",
        "agentic-workspace/external-observation-admission/v1",
        "agentic-workspace/generated-target-capability-admission/v1",
        "agentic-workspace/generated-target-projection-admission/v1",
        "agentic-workspace/runtime-readiness-admission/v1",
    }


def _packet_rejected(packet: dict[str, Any], decision: dict[str, str]) -> bool:
    if packet.get("admitted") is False or packet.get("status") == "rejected":
        return True
    return decision.get("terminal_state") in {"blocked", "partial"} or decision.get("mutation_precondition", "").endswith("-rejected")


def _packet_recovery_observed(packet: dict[str, Any], decision: dict[str, str]) -> bool:
    repair = str(packet.get("repair") or "")
    return bool(repair and repair != "none") or decision.get("typed_action") in {"recover", "admit-result", "run-proof"}
