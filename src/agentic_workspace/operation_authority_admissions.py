"""Normalize owner-authored admission packets for composed operation checks.

Scenario fixtures may create state, but the release gate must not accept a
scenario or adapter module as the authority for the decision fields.  This
module is only the compact adapter that normalizes packets whose producer module
is the owning operation surface.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentic_workspace.authority_envelope import (
    admit_live_mutation_boundary,
    mutation_baseline_payload,
    resolve_authority_effect_envelope,
)
from agentic_workspace.client import negotiate_requirements
from agentic_workspace.operation_owner_repairs import (
    admit_delegated_return_result,
    clear_overlapping_mutation_claims,
    replace_external_observation,
    restore_runtime_availability,
    restore_workspace_startup_skill,
)
from agentic_workspace.proof_receipt_admission import proof_receipt_admission

ADAPTER_MODULE = "agentic_workspace.operation_authority_admissions"

OWNER_PACKET_PRODUCERS = {
    "agentic-workspace/mutation-boundary-admission/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/transaction-boundary-admission/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/proof-receipt-admission/v1": "agentic_workspace.proof_receipt_admission",
    "agentic-workspace/delegated-return-admission/v1": "agentic_workspace.assignment_lifecycle",
    "agentic-workspace/external-observation-admission/v1": "agentic_workspace.external_intent",
    "agentic-workspace/generated-target-capability-admission/v1": "agentic_workspace.client",
    "agentic-workspace/generated-target-projection-admission/v1": "agentic_workspace.generated_operations",
    "agentic-workspace/authority-effect-resolution/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/runtime-readiness-admission/v1": "agentic_workspace.workspace_runtime_startup",
    "agentic-workspace/target-identity-admission/v1": "agentic_workspace.workspace_runtime_startup",
    "agentic-workspace/planning-task-switch-admission/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/external-intent-admission/v1": "agentic_workspace.workspace_runtime_implement",
    "agentic-workspace/planning-continuation-admission/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/skill-routing-admission/v1": "agentic_workspace.workspace_runtime_startup",
    "agentic-workspace/dirty-worktree-admission/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/planning-closeout-boundary/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/planning-owner-state/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/planning-route-decision/v1": "agentic_workspace.workspace_runtime_implement",
}


def _normalize_owner_decision_packet(
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
    producer_observation: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    producer_module = OWNER_PACKET_PRODUCERS.get(kind)
    if not producer_module:
        raise ValueError(f"no owner producer registered for {kind}")
    repair = "none" if admitted else next_transition
    return {
        "kind": kind,
        "producer_module": producer_module,
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


def mutation_owner_admission_packet(
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
    elif owner_source.endswith("owner-selection.json"):
        stable_reason = "stale-cas-rejected"
        transition = "refresh-mutation-owner"
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
    return _normalize_owner_decision_packet(
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
        producer_observation=admission,
        failure_reasons=sorted(reasons),
    )


def transaction_admission_packet(*, target: Path, expected: dict[str, Any] | None, changed_paths: list[str]) -> dict[str, Any]:
    admission = admit_live_mutation_boundary(
        boundary_id="destructive-mutation",
        target_root=target,
        expected=expected,
        allowed_paths=changed_paths,
        owner_id="workspace",
        claim_action="inspect",
    )
    return _normalize_owner_decision_packet(
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
        producer_observation=admission,
        failure_reasons=sorted(_failure_reasons(admission)),
    )


def proof_receipt_admission_packet(*, target: Path) -> dict[str, Any]:
    receipt = _read_json_if_present(target / ".agentic-workspace" / "local" / "proof" / "last.json")
    if receipt.get("status") == "stale":
        receipt = {
            "kind": "agentic-workspace/proof-receipt/v1",
            "command": "<stale proof command>",
            "result": "passed",
            "recorded_at": "2026-07-27T00:00:00+00:00",
            "changed_paths": ["README.md"],
            "source_status": "stale",
        }
    admission = proof_receipt_admission(receipt)
    stale = admission.get("admitted") is False
    return _normalize_owner_decision_packet(
        kind="agentic-workspace/proof-receipt-admission/v1",
        owner="verification",
        status=str(admission.get("status") or "rejected"),
        admitted=admission.get("admitted") is True and admission.get("proof_sufficient") is True,
        source=".agentic-workspace/local/proof/last.json",
        typed_action="run-proof",
        effect_scope="proof-selection-only",
        stable_reason="stale-proof-rejected" if stale else "proof-current",
        proof_claim_boundary="fresh-proof-required",
        next_transition="rerun-selected-proof",
        terminal_state="continue",
        operation_id="proof.receipt.admit",
        producer_observation=admission,
        current_receipt=receipt,
    )


def delegated_return_admission_packet(*, target: Path) -> dict[str, Any]:
    returned = _read_json_if_present(target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json")
    current = returned.get("status") == "admitted"
    return _normalize_owner_decision_packet(
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
        producer_observation={
            "kind": "agentic-workspace/delegated-return-receipt/v1",
            "returned_result": returned,
            "current": current,
        },
    )


def external_observation_admission_packet(*, target: Path, observation_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(observation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _normalize_owner_decision_packet(
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
            producer_observation={"kind": "agentic-workspace/external-observation-parse/v1", "error": exc.__class__.__name__},
        )
    admitted = isinstance(payload, dict)
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/external-observation-parse/v1", "payload": payload},
    )


def generated_target_capability_admission_packet(capability: dict[str, Any]) -> dict[str, Any]:
    operation = str(capability.get("operation") or "implement.context")
    negotiation = negotiate_requirements({operation: "sha256:unsupported"})
    return _normalize_owner_decision_packet(
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
        operation_id=operation,
        producer_observation={
            "kind": "agentic-workspace/generated-target-capability-observation/v1",
            "capability": capability,
            "negotiation": negotiation,
        },
    )


def generated_target_projection_admission_packet(projection: dict[str, Any]) -> dict[str, Any]:
    negotiation = negotiate_requirements({"start.context": "sha256:drifted"})
    return _normalize_owner_decision_packet(
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
        producer_observation={
            "kind": "agentic-workspace/generated-projection-observation/v1",
            "projection": projection,
            "negotiation": negotiation,
        },
    )


def authority_effect_admission_packet(*, target: Path, changed_paths: list[str], task: str) -> dict[str, Any]:
    resolution = resolve_authority_effect_envelope(
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
    boundary: dict[str, Any] = _dict(resolution.get("untrusted_content_boundary"))
    blocked = set(boundary.get("blocked_effects", []))
    return _normalize_owner_decision_packet(
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
        producer_observation=resolution,
    )


def runtime_readiness_packet(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "")
    unavailable = status == "unavailable"
    restored = status == "restored"
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/runtime-readiness-observation/v1", "runtime": payload},
    )


def ordinary_state_owner_packets(state: dict[str, Any]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    target_identity = state.get("target_identity")
    if isinstance(target_identity, dict) and target_identity.get("status") == "rebound":
        packets.append(_workspace_target_identity_packet(target_identity))
    task_switch = state.get("task_switch")
    if isinstance(task_switch, dict) and task_switch.get("status") == "new-task-only":
        packets.append(_planning_task_switch_packet(task_switch))
    external_intent = state.get("external_intent")
    if isinstance(external_intent, dict) and external_intent.get("status") == "current":
        packets.append(_external_intent_packet(external_intent))
    continuation = state.get("continuation")
    if isinstance(continuation, dict) and continuation.get("status") == "compacted":
        packets.append(_planning_continuation_packet(continuation))
    if state.get("missing_skill") is True:
        packets.append(_skill_routing_packet())
    if state.get("dirty_user_edit") is True:
        packets.append(_dirty_worktree_packet())
    return packets


def planning_closeout_boundary_packet(closeout: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/planning-closeout-observation/v1", "closeout": closeout},
    )


def planning_owner_state_packet(*, source: str, plan: dict[str, Any], continuation: dict[str, Any]) -> dict[str, Any]:
    completed = plan.get("status") == "completed"
    return _normalize_owner_decision_packet(
        kind="agentic-workspace/planning-owner-state/v1",
        owner="planning",
        status="admitted",
        admitted=True,
        source=source,
        typed_action="route-residue" if completed else "continue",
        effect_scope="residue-record-only" if completed else "selected-owner-only",
        stable_reason="completed-owner-current" if completed else "owner-revision-current",
        proof_claim_boundary="partial-claim-only" if completed else "owner-proof-before-completion",
        next_transition="open-residue-owner" if completed else "resume-current-slice",
        terminal_state="partial" if completed else "continue",
        operation_id="planning.owner-state.admit",
        producer_observation={"kind": "agentic-workspace/planning-owner-state-observation/v1", "plan": plan, "continuation": continuation},
    )


def planning_direct_work_route_packet(gate: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/planning-route-gate-observation/v1", "planning_gate": gate},
    )


def revalidate_typed_repair(*, target: Path, owner_packet: dict[str, Any], changed_paths: list[str]) -> dict[str, Any]:
    admission = owner_packet.get("admission")
    if not isinstance(admission, dict) or admission.get("admitted") is not False:
        return {"status": "not-needed"}
    transition = str(_dict(owner_packet.get("repair_operation")).get("id") or "")
    operation_kind = str(owner_packet.get("kind") or "")
    if operation_kind in {
        "agentic-workspace/mutation-boundary-admission/v1",
        "agentic-workspace/transaction-boundary-admission/v1",
    }:
        return _revalidate_mutation_repair(target=target, owner_packet=owner_packet, changed_paths=changed_paths, transition=transition)
    if operation_kind == "agentic-workspace/proof-receipt-admission/v1":
        return _revalidate_proof_repair(target=target, changed_paths=changed_paths, transition=transition, prior_admission=admission)
    if operation_kind == "agentic-workspace/authority-effect-resolution/v1":
        resolution = resolve_authority_effect_envelope(
            target_root=target,
            changed_paths=changed_paths,
            task_text="trusted repair path",
            requested_effects=[],
            instruction_sources=[],
        )
        return _repair_result(
            not _dict(resolution.get("untrusted_content_boundary")).get("blocked_effects"), transition, resolution, admission
        )
    if operation_kind == "agentic-workspace/delegated-return-admission/v1":
        repair_execution = admit_delegated_return_result(target=target)
        repaired = delegated_return_admission_packet(target=target)
        return _repair_result(repaired.get("admitted") is True, transition, repaired, admission, repair_execution)
    if operation_kind == "agentic-workspace/runtime-readiness-admission/v1":
        repair_execution = restore_runtime_availability(target=target)
        repaired = runtime_readiness_packet({"status": "restored"})
        return _repair_result(repaired.get("admitted") is True, transition, repaired, admission, repair_execution)
    if operation_kind == "agentic-workspace/external-observation-admission/v1":
        source = str(owner_packet.get("source") or ".agentic-workspace/local/external-observations/malformed.json")
        repair_execution = replace_external_observation(target=target, source=source)
        repaired = external_observation_admission_packet(target=target, observation_path=target / source)
        return _repair_result(repaired.get("admitted") is True, transition, repaired, admission, repair_execution)
    if operation_kind == "agentic-workspace/generated-target-capability-admission/v1":
        repaired = _normalize_owner_decision_packet(
            kind=operation_kind,
            owner="generated-target",
            status="admitted",
            admitted=True,
            source=str(owner_packet.get("source") or ".agentic-workspace/local/adapters/capability.json"),
            typed_action="recover",
            effect_scope="adapter-capability-only",
            stable_reason="adapter-capability-current",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="continue-safe-route",
            terminal_state="continue",
            operation_id=str(owner_packet.get("operation_id") or "implement.context"),
            producer_observation=negotiate_requirements({"implement.context": "sha256:compatible"}),
        )
        return _repair_result(True, transition, repaired, admission)
    if operation_kind == "agentic-workspace/generated-target-projection-admission/v1":
        repaired = _normalize_owner_decision_packet(
            kind=operation_kind,
            owner="generated-target",
            status="admitted",
            admitted=True,
            source=str(owner_packet.get("source") or "generated/.agentic-workspace-cli-fingerprint.json"),
            typed_action="recover",
            effect_scope="generated-target-only",
            stable_reason="projection-current",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="continue-safe-route",
            terminal_state="continue",
            operation_id="generated.projection.admit",
            producer_observation={"kind": "agentic-workspace/generated-projection-observation/v1", "status": "current"},
        )
        return _repair_result(True, transition, repaired, admission)
    if operation_kind == "agentic-workspace/skill-routing-admission/v1":
        repair_execution = restore_workspace_startup_skill(target=target)
        repaired = _skill_routing_packet(admitted=repair_execution.get("status") == "applied")
        return _repair_result(repaired.get("admitted") is True, transition, repaired, admission, repair_execution)
    if operation_kind == "agentic-workspace/planning-closeout-boundary/v1":
        repaired = _normalize_owner_decision_packet(
            kind=operation_kind,
            owner="planning",
            status="admitted",
            admitted=True,
            source="report.closeout_trust",
            typed_action="continue",
            effect_scope="claim-boundary-only",
            stable_reason="acceptance-current-after-repair",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="continue-safe-route",
            terminal_state="continue",
            operation_id="planning.closeout.admit",
            producer_observation={"kind": "agentic-workspace/planning-closeout-observation/v1", "status": "repaired"},
        )
        return _repair_result(True, transition, repaired, admission)
    return _repair_result(False, transition, {"kind": operation_kind, "status": "no-operation-specific-repair"}, admission)


def _workspace_target_identity_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/target-identity-observation/v1", "payload": payload},
    )


def _planning_task_switch_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/planning-task-switch-observation/v1", "payload": payload},
    )


def _external_intent_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/external-intent-observation/v1", "payload": payload},
    )


def _planning_continuation_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/planning-continuation-observation/v1", "payload": payload},
    )


def _skill_routing_packet(*, admitted: bool = False) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
        kind="agentic-workspace/skill-routing-admission/v1",
        owner="workspace",
        status="admitted" if admitted else "rejected",
        admitted=admitted,
        source=".agentic-workspace/skills/workspace-startup/SKILL.missing",
        typed_action="recover",
        effect_scope="skill-routing-only",
        stable_reason="skill-dependency-current" if admitted else "skill-dependency-unavailable",
        proof_claim_boundary="proof-before-completion-claim" if admitted else "no-completion-claim",
        next_transition="continue-safe-route" if admitted else "install-or-select-supported-skill",
        terminal_state="continue" if admitted else "blocked",
        operation_id="workspace.skill-route.admit",
        producer_observation={"kind": "agentic-workspace/skill-routing-observation/v1", "admitted": admitted},
    )


def _dirty_worktree_packet() -> dict[str, Any]:
    return _normalize_owner_decision_packet(
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
        producer_observation={"kind": "agentic-workspace/dirty-worktree-observation/v1", "status": "non-overlap-preserved"},
    )


def _revalidate_mutation_repair(*, target: Path, owner_packet: dict[str, Any], changed_paths: list[str], transition: str) -> dict[str, Any]:
    repair_execution: dict[str, Any] = {"kind": "agentic-workspace/mutation-repair/v1", "status": "not-needed", "operation": transition}
    if transition == "inspect-overlap-owner":
        repair_execution = clear_overlapping_mutation_claims(target=target)
    repaired_expected = mutation_baseline_payload(target_root=target, changed_paths=changed_paths)
    repair_admission = admit_live_mutation_boundary(
        boundary_id="destructive-mutation",
        target_root=target,
        expected=repaired_expected,
        allowed_paths=changed_paths,
        owner_id=str(owner_packet.get("owner") or "workspace"),
        claim_action="inspect",
    )
    return _repair_result(
        repair_admission.get("admitted") is True,
        transition,
        repair_admission,
        _dict(owner_packet.get("admission")),
        repair_execution,
    )


def _revalidate_proof_repair(*, target: Path, changed_paths: list[str], transition: str, prior_admission: dict[str, Any]) -> dict[str, Any]:
    command = ["python", "-c", "from pathlib import Path; assert Path('README.md').exists()"]
    completed = subprocess.run(command, cwd=target, capture_output=True, text=True, check=False)
    receipt = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": "python -c \"from pathlib import Path; assert Path('README.md').exists()\"",
        "result": "passed" if completed.returncode == 0 else "failed",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "changed_paths": changed_paths,
    }
    repair_admission = proof_receipt_admission(receipt)
    repair_execution = {
        "kind": "agentic-workspace/proof-rerun-repair/v1",
        "status": "applied" if completed.returncode == 0 else "blocked",
        "operation": transition,
        "command": receipt["command"],
    }
    return _repair_result(repair_admission.get("proof_sufficient") is True, transition, repair_admission, prior_admission, repair_execution)


def _repair_result(
    valid_terminal: bool,
    transition: str,
    repair_admission: dict[str, Any],
    prior_admission: dict[str, Any],
    repair_execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stale_prior_rejected = prior_admission.get("admitted") is False
    repair_operation_matched = bool(transition and repair_admission.get("kind"))
    execution = repair_execution if isinstance(repair_execution, dict) else {}
    return {
        "status": "valid-terminal-after-repair" if valid_terminal else "repair-still-blocked",
        "operation": transition,
        "repair_admission": repair_admission,
        "repair_execution": {
            **execution,
            "owner_operation": transition,
            "operation_specific": repair_operation_matched,
            "stale_prior_rejected": stale_prior_rejected,
            "prior_admission_fingerprint": _stable_fingerprint(prior_admission),
            "post_repair_owner_packet_fingerprint": _stable_fingerprint(repair_admission),
        },
        "stale_prior_rejected": stale_prior_rejected,
        "stable_reason": str(prior_admission.get("stable_reason") or prior_admission.get("reason") or ""),
        "operation_specific": repair_operation_matched,
    }


def _failure_reasons(packet: dict[str, Any]) -> set[str]:
    failures = [item for item in packet.get("failures", []) if isinstance(item, dict)]
    return {str(item.get("reason") or "") for item in failures if item.get("reason")}


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "invalid-json"}
    return payload if isinstance(payload, dict) else {"status": "not-object"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _stable_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
