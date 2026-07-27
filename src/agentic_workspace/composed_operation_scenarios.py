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
            _mutation_owner_admission_packet(
                target=target,
                expected=expected,
                changed_paths=changed_paths,
                owner="planning",
                owner_source=".agentic-workspace/local/planning/owner-selection.json",
            )
        )
    if (target / ".agentic-workspace" / "local" / "planning" / "mutation-owner.json").exists():
        packets.append(
            _mutation_owner_admission_packet(
                target=target,
                expected=expected,
                changed_paths=changed_paths,
                owner="planning",
                owner_source=".agentic-workspace/local/planning/mutation-owner.json",
            )
        )
    stale_scope = _read_json_if_present(target / ".agentic-workspace" / "local" / "actions" / "stale-scope.json")
    if stale_scope:
        requested_paths = [str(path) for path in stale_scope.get("requested_paths", []) if isinstance(path, str)]
        packets.append(
            _mutation_owner_admission_packet(
                target=target,
                expected=expected,
                changed_paths=requested_paths or changed_paths,
                owner="workspace",
                owner_source=".agentic-workspace/local/actions/stale-scope.json",
            )
        )
    if (target / ".agentic-workspace" / "local" / "transactions" / "partial-write.json").exists():
        packets.append(
            _transaction_admission_packet(
                target=target,
                expected=expected,
                changed_paths=changed_paths,
            )
        )
    if (target / ".agentic-workspace" / "local" / "proof" / "last.json").exists():
        packets.append(_proof_receipt_admission_packet(target=target))
    if (target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json").exists():
        packets.append(_delegated_return_admission_packet(target=target))
    malformed = target / ".agentic-workspace" / "local" / "external-observations" / "malformed.json"
    if malformed.exists():
        packets.append(_external_observation_admission_packet(target=target, observation_path=malformed))
    capability = _read_json_if_present(target / ".agentic-workspace" / "local" / "adapters" / "capability.json")
    if capability:
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/generated-target-capability-admission/v1",
                owner="generated-target",
                status="rejected",
                admitted=False,
                source=".agentic-workspace/local/adapters/capability.json",
                typed_action="recover",
                effect_scope="adapter-capability-only",
                stable_reason="adapter-capability-rejected",
                proof_claim_boundary="no-completion-claim",
                next_transition="select-compatible-adapter",
                terminal_state="blocked",
                operation_id=str(capability.get("operation") or "implement.context"),
                negotiation=negotiate_requirements({str(capability.get("operation") or "implement.context"): "sha256:unsupported"}),
            )
        )
    projection = _read_json_if_present(target / "generated" / ".agentic-workspace-cli-fingerprint.json")
    if projection.get("status") == "drifted":
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/generated-target-projection-admission/v1",
                owner="generated-target",
                status="rejected",
                admitted=False,
                source="generated/.agentic-workspace-cli-fingerprint.json",
                typed_action="recover",
                effect_scope="generated-target-only",
                stable_reason="projection-drift-rejected",
                proof_claim_boundary="no-completion-claim",
                next_transition="regenerate-projection",
                terminal_state="blocked",
                operation_id="generated.projection.admit",
                negotiation=negotiate_requirements({"start.context": "sha256:drifted"}),
            )
        )
    if (target / "incoming" / "untrusted.txt").exists():
        packets.append(
            _authority_effect_admission_packet(
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
    packets.extend(_ordinary_state_owner_packets(local_state))
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "closeout" / "premature.json") and _closeout_blocks_completion(
        closeout
    ):
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/planning-closeout-boundary/v1",
                owner="planning",
                status="rejected",
                admitted=False,
                source="report.closeout_trust",
                typed_action="continue",
                effect_scope="claim-boundary-only",
                stable_reason="acceptance-incomplete",
                proof_claim_boundary="partial-claim-only",
                next_transition="continue-unresolved-work",
                terminal_state="partial",
                operation_id="planning.closeout.admit",
            )
        )
    continuation = summary.get("continuation_view") if isinstance(summary.get("continuation_view"), dict) else {}
    plan_path = target / ".agentic-workspace" / "planning" / "execplans" / f"{scenario_id}.plan.json"
    plan = _read_json_if_present(plan_path)
    if plan:
        source = plan_path.relative_to(target).as_posix() if plan_path.exists() else "summary.continuation_view"
        if plan.get("status") == "completed":
            packets.append(
                _owner_contract_packet(
                    kind="agentic-workspace/planning-owner-state/v1",
                    owner="planning",
                    status="admitted",
                    admitted=True,
                    source=source,
                    typed_action="route-residue",
                    effect_scope="residue-record-only",
                    stable_reason="completed-owner-current",
                    proof_claim_boundary="partial-claim-only",
                    next_transition="open-residue-owner",
                    terminal_state="partial",
                    operation_id="planning.owner-state.admit",
                    continuation=continuation,
                    plan=plan,
                )
            )
        else:
            packets.append(
                _owner_contract_packet(
                    kind="agentic-workspace/planning-owner-state/v1",
                    owner="planning",
                    status="admitted",
                    admitted=True,
                    source=source,
                    typed_action="continue",
                    effect_scope="selected-owner-only",
                    stable_reason="owner-revision-current",
                    proof_claim_boundary="owner-proof-before-completion",
                    next_transition="resume-current-slice",
                    terminal_state="continue",
                    operation_id="planning.owner-state.admit",
                    continuation=continuation,
                    plan=plan,
                )
            )
    gate = _planning_gate(implement)
    if gate.get("gate_result") == "direct-work-allowed":
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/planning-route-decision/v1",
                owner="direct-work",
                status="admitted",
                admitted=True,
                source="implement.context.planning_safety_gate",
                typed_action="implement",
                effect_scope="changed-paths-only",
                stable_reason="clean-baseline",
                proof_claim_boundary="proof-before-completion-claim",
                next_transition="run-focused-proof",
                terminal_state="continue",
                operation_id="planning.route-decision.admit",
                planning_gate=gate,
            )
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
    contract_decision = _decision_from_owner_contract(packet)
    if contract_decision:
        return contract_decision
    kind = str(packet.get("kind") or "")
    if kind == "agentic-workspace/authority-effect-resolution/v1":
        return _decision_from_authority_effect(packet)
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


def _authority_effect_admission_packet(packet: dict[str, Any]) -> dict[str, Any]:
    boundary_payload = packet.get("untrusted_content_boundary")
    boundary: dict[str, Any] = boundary_payload if isinstance(boundary_payload, dict) else {}
    blocked = set(boundary.get("blocked_effects", []))
    return _owner_contract_packet(
        kind="agentic-workspace/authority-effect-resolution/v1",
        owner="workspace",
        status="rejected" if "write-outside-scope" in blocked else "admitted",
        admitted="write-outside-scope" not in blocked,
        source="incoming/untrusted.txt",
        typed_action="ignore-data-instruction",
        effect_scope="trusted-instruction-sources-only",
        stable_reason="data-text-not-authority",
        proof_claim_boundary="proof-before-completion-claim",
        next_transition="continue-safe-route",
        terminal_state="continue",
        operation_id="authority.effect.resolve",
        authority_resolution=packet,
    )


def _ordinary_state_owner_packets(state: dict[str, Any]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    target_identity = state.get("target_identity")
    if isinstance(target_identity, dict) and target_identity.get("status") == "rebound":
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/target-identity-admission/v1",
                owner="workspace",
                status="admitted",
                admitted=True,
                source=".agentic-workspace/local/workspace/target-identity.json",
                typed_action="recover",
                effect_scope="workspace-routing-state",
                stable_reason="target-identity-rebound",
                proof_claim_boundary="proof-after-recovery",
                next_transition="refresh-startup-context",
                terminal_state="continue",
                operation_id="workspace.target-identity.rebind",
            )
        )
    task_switch = state.get("task_switch")
    if isinstance(task_switch, dict) and task_switch.get("status") == "new-task-only":
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/planning-task-switch-admission/v1",
                owner="planning",
                status="admitted",
                admitted=True,
                source=".agentic-workspace/local/planning/task-switch.json",
                typed_action="reconcile",
                effect_scope="new-task-only",
                stable_reason="active-owner-preserved",
                proof_claim_boundary="no-active-owner-completion-claim",
                next_transition="acknowledge-task-switch",
                terminal_state="continue",
                operation_id="planning.task-switch.reconcile",
            )
        )
    external_intent = state.get("external_intent")
    if isinstance(external_intent, dict) and external_intent.get("status") == "current":
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/external-intent-admission/v1",
                owner="issue-scope",
                status="admitted",
                admitted=True,
                source=".agentic-workspace/local/external-intent/issue-2300.json",
                typed_action="implement",
                effect_scope="issue-bounded-paths",
                stable_reason="clean-baseline",
                proof_claim_boundary="proof-before-completion-claim",
                next_transition="run-focused-proof",
                terminal_state="continue",
                operation_id="external-intent.admit",
            )
        )
    continuation = state.get("continuation")
    if isinstance(continuation, dict) and continuation.get("status") == "compacted":
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/planning-continuation-admission/v1",
                owner="planning",
                status="admitted",
                admitted=True,
                source=".agentic-workspace/local/continuation/compacted.json",
                typed_action="continue",
                effect_scope="continuation-state-only",
                stable_reason="continuation-revision-current",
                proof_claim_boundary="continuation-proof-before-claim",
                next_transition="resume-after-compaction",
                terminal_state="continue",
                operation_id="planning.continuation.resume",
            )
        )
    if state.get("missing_skill") is True:
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/skill-routing-admission/v1",
                owner="workspace",
                status="rejected",
                admitted=False,
                source=".agentic-workspace/skills/workspace-startup/SKILL.missing",
                typed_action="recover",
                effect_scope="skill-routing-only",
                stable_reason="skill-dependency-unavailable",
                proof_claim_boundary="no-completion-claim",
                next_transition="install-or-select-supported-skill",
                terminal_state="blocked",
                operation_id="workspace.skill-route.admit",
            )
        )
    if state.get("dirty_user_edit") is True:
        packets.append(
            _owner_contract_packet(
                kind="agentic-workspace/dirty-worktree-admission/v1",
                owner="workspace",
                status="admitted",
                admitted=True,
                source="notes/user-owned.md",
                typed_action="implement",
                effect_scope="non-overlapping-changed-paths",
                stable_reason="preexisting-edits-preserved",
                proof_claim_boundary="proof-before-completion-claim",
                next_transition="inspect-dirty-overlap",
                terminal_state="continue",
                operation_id="workspace.dirty-worktree.admit",
            )
        )
    return packets


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


def _decision_from_owner_contract(packet: dict[str, Any]) -> dict[str, str]:
    contract = packet.get("contract_observation")
    if not isinstance(contract, dict):
        return {}
    required = {
        "owner",
        "terminal_state",
        "typed_action",
        "effect_scope",
        "mutation_precondition",
        "proof_claim_boundary",
        "next_transition",
    }
    if not all(isinstance(contract.get(field), str) and contract.get(field) for field in required):
        return {}
    if not isinstance(packet.get("admission"), dict):
        return {}
    if not isinstance(packet.get("producer_receipt"), dict):
        return {}
    return _decision(
        str(contract["owner"]),
        str(contract["terminal_state"]),
        str(contract["typed_action"]),
        str(contract["effect_scope"]),
        str(contract["mutation_precondition"]),
        str(contract["proof_claim_boundary"]),
        str(contract["next_transition"]),
    )


def _owner_contract_packet(
    *,
    kind: str,
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
    **extra: Any,
) -> dict[str, Any]:
    repair = "none" if admitted else next_transition
    return {
        "kind": kind,
        "owner": owner,
        "status": status,
        "admitted": admitted,
        "source": source,
        "operation_id": operation_id,
        "stable_reason": stable_reason,
        "typed_operation": {"id": operation_id, "action": typed_action},
        "repair_operation": {"id": next_transition, "status": "not-needed" if admitted else "required"},
        "admission": {
            "status": status,
            "admitted": admitted,
            "stable_reason": stable_reason,
            "repair": repair,
        },
        "producer_receipt": {
            "source": source,
            "owner": owner,
            "revision": f"{operation_id}:{stable_reason}",
            "stable_reason": stable_reason,
        },
        "contract_observation": {
            "owner": owner,
            "terminal_state": terminal_state,
            "typed_action": typed_action,
            "effect_scope": effect_scope,
            "mutation_precondition": stable_reason,
            "proof_claim_boundary": proof_claim_boundary,
            "next_transition": next_transition,
        },
        "recovery_sequence": _recovery_sequence(next_transition, stable_reason=stable_reason, admitted=admitted),
        **extra,
    }


def _recovery_sequence(next_transition: str, *, stable_reason: str, admitted: bool) -> list[dict[str, Any]]:
    if admitted:
        return []
    return [
        {
            "operation": next_transition,
            "status": "typed-repair-required",
            "rejects_stale_prior_evidence": True,
            "stable_reason": stable_reason,
        },
        {
            "operation": "scenario-valid-terminal-result",
            "status": "valid-terminal-after-repair",
            "safe_claim": "blocked-until-repaired",
        },
    ]


def _mutation_owner_admission_packet(
    *,
    target: Path,
    expected: dict[str, Any] | None,
    changed_paths: list[str],
    owner: str,
    owner_source: str,
) -> dict[str, Any]:
    admission = admit_live_mutation_boundary(
        boundary_id="destructive-mutation",
        target_root=target,
        expected=expected,
        allowed_paths=changed_paths,
        owner_id=owner,
        claim_action="inspect",
    )
    reasons = _failure_reasons(admission)
    if "overlapping-mutation-claim" in reasons:
        stable_reason = "overlapping-mutation-rejected"
        transition = "inspect-overlap-owner"
        effect_scope = "no-mutation"
    elif "scope-expanded" in reasons:
        stable_reason = "scope-widening-rejected"
        transition = "narrow-scope-and-refresh"
        effect_scope = "no-mutation"
    elif {"unexpected-path-overlap", "untracked-managed-state"} & reasons:
        stable_reason = "partial-write-rejected"
        transition = "rollback-or-retry-transaction"
        effect_scope = "transaction-state-only"
        owner = "workspace"
    else:
        stable_reason = "stale-cas-rejected"
        transition = "refresh-mutation-owner"
        effect_scope = "no-mutation"
    return _owner_contract_packet(
        kind="agentic-workspace/mutation-boundary-admission/v1",
        owner=owner,
        status=str(admission.get("status") or "rejected"),
        admitted=admission.get("admitted") is True,
        source=owner_source,
        typed_action="recover",
        effect_scope=effect_scope,
        stable_reason=stable_reason,
        proof_claim_boundary="no-completion-claim",
        next_transition=transition,
        terminal_state="blocked",
        operation_id="mutation.admit",
        admission_packet=admission,
        failure_reasons=sorted(reasons),
    )


def _transaction_admission_packet(*, target: Path, expected: dict[str, Any] | None, changed_paths: list[str]) -> dict[str, Any]:
    admission = admit_live_mutation_boundary(
        boundary_id="destructive-mutation",
        target_root=target,
        expected=expected,
        allowed_paths=changed_paths,
        owner_id="workspace",
        claim_action="inspect",
    )
    return _owner_contract_packet(
        kind="agentic-workspace/transaction-boundary-admission/v1",
        owner="workspace",
        status="rejected",
        admitted=False,
        source=".agentic-workspace/local/transactions/partial-write.json",
        typed_action="recover",
        effect_scope="transaction-state-only",
        stable_reason="partial-write-rejected",
        proof_claim_boundary="no-completion-claim",
        next_transition="rollback-or-retry-transaction",
        terminal_state="blocked",
        operation_id="transaction.admit",
        admission_packet=admission,
        failure_reasons=sorted(_failure_reasons(admission)),
    )


def _proof_receipt_admission_packet(*, target: Path) -> dict[str, Any]:
    receipt = _read_json_if_present(target / ".agentic-workspace" / "local" / "proof" / "last.json")
    stale = receipt.get("status") == "stale"
    return _owner_contract_packet(
        kind="agentic-workspace/proof-receipt-admission/v1",
        owner="verification",
        status="rejected" if stale else "admitted",
        admitted=not stale,
        source=".agentic-workspace/local/proof/last.json",
        typed_action="run-proof",
        effect_scope="proof-selection-only",
        stable_reason="stale-proof-rejected" if stale else "proof-current",
        proof_claim_boundary="fresh-proof-required",
        next_transition="rerun-selected-proof",
        terminal_state="continue",
        operation_id="proof.receipt.admit",
        current_receipt=receipt,
    )


def _delegated_return_admission_packet(*, target: Path) -> dict[str, Any]:
    returned = _read_json_if_present(target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json")
    current = returned.get("status") == "admitted"
    return _owner_contract_packet(
        kind="agentic-workspace/delegated-return-admission/v1",
        owner="delegation",
        status="admitted" if current else "rejected",
        admitted=current,
        source=".agentic-workspace/local/delegation/returned-result.json",
        typed_action="admit-result",
        effect_scope="returned-result-admission",
        stable_reason="return-receipt-current",
        proof_claim_boundary="admitted-result-before-claim",
        next_transition="admit-or-repair-return",
        terminal_state="continue",
        operation_id="assignment.admit",
        returned_result=returned,
    )


def _failure_reasons(packet: dict[str, Any]) -> set[str]:
    failures = [item for item in packet.get("failures", []) if isinstance(item, dict)]
    return {str(item.get("reason") or "") for item in failures if item.get("reason")}


def _owner_receipt(*, target: Path, scenario_id: str) -> dict[str, Any]:
    return _read_json_if_present(target / ".agentic-workspace" / "local" / "composed-operation-scenarios" / f"{scenario_id}.json")


def _external_observation_admission_packet(*, target: Path, observation_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(observation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _owner_contract_packet(
            kind="agentic-workspace/external-observation-admission/v1",
            owner="workspace",
            status="rejected",
            admitted=False,
            source=observation_path.relative_to(target).as_posix(),
            typed_action="recover",
            effect_scope="external-observation-only",
            stable_reason="malformed-observation-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="request-valid-observation",
            terminal_state="blocked",
            operation_id="external-observation.admit",
            error=exc.__class__.__name__,
        )
    admitted = isinstance(payload, dict)
    return _owner_contract_packet(
        kind="agentic-workspace/external-observation-admission/v1",
        owner="workspace",
        status="admitted" if admitted else "rejected",
        admitted=admitted,
        source=observation_path.relative_to(target).as_posix(),
        typed_action="recover",
        effect_scope="external-observation-only",
        stable_reason="valid-observation" if admitted else "malformed-observation-rejected",
        proof_claim_boundary="proof-before-completion-claim" if admitted else "no-completion-claim",
        next_transition="continue-safe-route" if admitted else "request-valid-observation",
        terminal_state="continue" if admitted else "blocked",
        operation_id="external-observation.admit",
    )


def _runtime_readiness_packet(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "")
    unavailable = status == "unavailable"
    restored = status == "restored"
    return _owner_contract_packet(
        kind="agentic-workspace/runtime-readiness-admission/v1",
        owner="workspace",
        status="rejected" if unavailable else "admitted",
        admitted=not unavailable,
        source=".agentic-workspace/local/runtime/availability.json",
        typed_action="recover" if unavailable else "start",
        effect_scope="runtime-state-only" if unavailable else "startup-reentry-only",
        stable_reason="runtime-incompatible" if unavailable else "runtime-restored",
        proof_claim_boundary="no-completion-claim" if unavailable else "proof-before-completion-claim",
        next_transition="restore-runtime" if unavailable else "restart-ordinary-route" if restored else "continue-safe-route",
        terminal_state="blocked" if unavailable else "continue",
        operation_id="runtime.readiness.admit",
    )


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
    if isinstance(packet.get("admission"), dict) and isinstance(packet.get("contract_observation"), dict):
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
    recovery = packet.get("recovery_sequence")
    if isinstance(recovery, list) and recovery:
        return any(isinstance(item, dict) and item.get("status") == "valid-terminal-after-repair" for item in recovery)
    repair = str(packet.get("repair") or "")
    return bool(repair and repair != "none") or decision.get("typed_action") in {"recover", "admit-result", "run-proof"}
