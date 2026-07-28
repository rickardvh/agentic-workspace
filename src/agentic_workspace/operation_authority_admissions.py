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

from agentic_workspace.assignment_lifecycle import (
    admit_delegated_return_result,
    composed_delegated_return_packet,
)
from agentic_workspace.authority_envelope import (
    admit_live_mutation_boundary,
    clear_overlapping_mutation_claims,
    composed_authority_effect_current_packet,
    composed_authority_effect_packet,
    composed_dirty_worktree_packet,
    composed_mutation_owner_packet,
    composed_transaction_packet,
    mutation_baseline_payload,
)
from agentic_workspace.client import (
    composed_generated_target_capability_current_packet,
    composed_generated_target_capability_packet,
    composed_generated_target_projection_current_packet,
    composed_generated_target_projection_packet,
)
from agentic_workspace.external_intent import (
    composed_external_observation_packet,
    replace_external_observation,
)
from agentic_workspace.proof_receipt_admission import composed_proof_receipt_packet, proof_receipt_admission
from agentic_workspace.workspace_runtime_implement import composed_external_intent_packet, composed_planning_direct_work_route_packet
from agentic_workspace.workspace_runtime_planning import (
    composed_planning_closeout_boundary_packet,
    composed_planning_closeout_current_packet,
    composed_planning_continuation_packet,
    composed_planning_owner_state_packet,
    composed_planning_task_switch_packet,
)
from agentic_workspace.workspace_runtime_startup import (
    composed_runtime_readiness_packet,
    composed_skill_routing_packet,
    composed_target_identity_packet,
    restore_runtime_availability,
    restore_workspace_startup_skill,
)

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
    "agentic-workspace/external-intent-admission/v1": "agentic_workspace.workspace_runtime_implement",
    "agentic-workspace/planning-continuation-admission/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/skill-routing-admission/v1": "agentic_workspace.workspace_runtime_startup",
    "agentic-workspace/dirty-worktree-admission/v1": "agentic_workspace.authority_envelope",
    "agentic-workspace/planning-closeout-boundary/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/planning-owner-state/v1": "agentic_workspace.workspace_runtime_planning",
    "agentic-workspace/planning-route-decision/v1": "agentic_workspace.workspace_runtime_implement",
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
    if not required.issubset(owner_packet):
        missing = sorted(required.difference(owner_packet))
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


def mutation_owner_admission_packet(
    *,
    target: Path,
    expected: dict[str, Any] | None,
    changed_paths: list[str],
    owner: str,
    owner_source: str,
) -> dict[str, Any]:
    return _normalize_owner_decision_packet(
        composed_mutation_owner_packet(
            target=target,
            expected=expected,
            changed_paths=changed_paths,
            owner=owner,
            owner_source=owner_source,
        )
    )


def transaction_admission_packet(*, target: Path, expected: dict[str, Any] | None, changed_paths: list[str]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_transaction_packet(target=target, expected=expected, changed_paths=changed_paths))


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
    return _normalize_owner_decision_packet(
        composed_proof_receipt_packet(receipt=receipt, source=".agentic-workspace/local/proof/last.json")
    )


def delegated_return_admission_packet(*, target: Path) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_delegated_return_packet(target=target))


def external_observation_admission_packet(*, target: Path, observation_path: Path) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_external_observation_packet(target=target, observation_path=observation_path))


def generated_target_capability_admission_packet(capability: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_generated_target_capability_packet(capability))


def generated_target_projection_admission_packet(projection: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_generated_target_projection_packet(projection))


def authority_effect_admission_packet(*, target: Path, changed_paths: list[str], task: str) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_authority_effect_packet(target=target, changed_paths=changed_paths, task=task))


def runtime_readiness_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_runtime_readiness_packet(payload))


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
    return _normalize_owner_decision_packet(composed_planning_closeout_boundary_packet(closeout))


def planning_owner_state_packet(*, source: str, plan: dict[str, Any], continuation: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_planning_owner_state_packet(source=source, plan=plan, continuation=continuation))


def planning_direct_work_route_packet(gate: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_planning_direct_work_route_packet(gate))


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
        repaired = _normalize_owner_decision_packet(composed_authority_effect_current_packet(target=target, changed_paths=changed_paths))
        return _repair_result(repaired.get("admitted") is True, transition, repaired, admission)
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
            composed_generated_target_capability_current_packet(str(owner_packet.get("operation_id") or "implement.context"))
        )
        return _repair_result(True, transition, repaired, admission)
    if operation_kind == "agentic-workspace/generated-target-projection-admission/v1":
        repaired = _normalize_owner_decision_packet(composed_generated_target_projection_current_packet())
        return _repair_result(True, transition, repaired, admission)
    if operation_kind == "agentic-workspace/skill-routing-admission/v1":
        repair_execution = restore_workspace_startup_skill(target=target)
        repaired = _skill_routing_packet(admitted=repair_execution.get("status") == "applied")
        return _repair_result(repaired.get("admitted") is True, transition, repaired, admission, repair_execution)
    if operation_kind == "agentic-workspace/planning-closeout-boundary/v1":
        repaired = _normalize_owner_decision_packet(composed_planning_closeout_current_packet())
        return _repair_result(True, transition, repaired, admission)
    return _repair_result(False, transition, {"kind": operation_kind, "status": "no-operation-specific-repair"}, admission)


def _workspace_target_identity_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_target_identity_packet(payload))


def _planning_task_switch_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_planning_task_switch_packet(payload))


def _external_intent_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_external_intent_packet(payload))


def _planning_continuation_packet(payload: dict[str, Any]) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_planning_continuation_packet(payload))


def _skill_routing_packet(*, admitted: bool = False) -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_skill_routing_packet(admitted=admitted))


def _dirty_worktree_packet() -> dict[str, Any]:
    return _normalize_owner_decision_packet(composed_dirty_worktree_packet())


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
