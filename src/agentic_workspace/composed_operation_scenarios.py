"""Producer-owned composed-operation scenario authority observations.

The release-gate checker consumes this packet surface instead of writing local
owner-result files and then validating its own output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
) -> dict[str, Any]:
    gate = _planning_gate(implement)
    plan_path = target / ".agentic-workspace" / "planning" / "execplans" / f"{scenario_id}.plan.json"
    plan = _read_json_if_present(plan_path)
    runtime = _read_json_if_present(target / ".agentic-workspace" / "local" / "runtime" / "availability.json")
    state_operations = (
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path=".agentic-workspace/local/planning/owner-selection.json",
            expected_status="stale",
            owner="planning",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="no-mutation",
            mutation_precondition="stale-cas-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="refresh-mutation-owner",
            source="planning.mutation-owner-store",
            evidence_sources=[
                ".agentic-workspace/local/planning/owner-selection.json",
                "implement.context.planning_safety_gate",
            ],
            rejection_observed=True,
            recovery_observed=True,
        ),
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path=".agentic-workspace/local/planning/mutation-owner.json",
            expected_status="overlap",
            owner="planning",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="no-mutation",
            mutation_precondition="overlapping-mutation-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="inspect-overlap-owner",
            source="planning.mutation-owner-store",
            evidence_sources=[
                ".agentic-workspace/local/planning/mutation-owner.json",
                "implement.context.planning_safety_gate",
            ],
            rejection_observed=True,
            recovery_observed=True,
        ),
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path=".agentic-workspace/local/actions/stale-scope.json",
            expected_status="stale",
            owner="workspace",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="no-mutation",
            mutation_precondition="scope-widening-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="narrow-scope-and-refresh",
            source="workspace.action-scope-guard",
            evidence_sources=[
                ".agentic-workspace/local/actions/stale-scope.json",
                "implement.context.planning_safety_gate",
            ],
            rejection_observed=True,
            recovery_observed=True,
        ),
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path=".agentic-workspace/local/transactions/partial-write.json",
            expected_status="partial",
            owner="workspace",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="transaction-state-only",
            mutation_precondition="partial-write-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="rollback-or-retry-transaction",
            source="workspace.transaction-guard",
            evidence_sources=[
                ".agentic-workspace/local/transactions/partial-write.json",
                "report.closeout_trust",
            ],
            rejection_observed=True,
            recovery_observed=True,
        ),
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path=".agentic-workspace/local/external-observations/malformed.json",
            expected_status="invalid-json",
            owner="workspace",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="external-observation-only",
            mutation_precondition="malformed-observation-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="request-valid-observation",
            source="workspace.external-observation-admission",
            evidence_sources=[".agentic-workspace/local/external-observations/malformed.json"],
            rejection_observed=True,
            recovery_observed=True,
        ),
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path=".agentic-workspace/local/adapters/capability.json",
            expected_status="incompatible",
            owner="generated-target",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="adapter-capability-only",
            mutation_precondition="adapter-capability-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="select-compatible-adapter",
            source="generated-target.adapter-capability",
            evidence_sources=[
                ".agentic-workspace/local/adapters/capability.json",
                "generated/workspace/typescript/src/client.mjs",
            ],
            rejection_observed=True,
            recovery_observed=True,
        ),
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path="generated/.agentic-workspace-cli-fingerprint.json",
            expected_status="drifted",
            owner="generated-target",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="generated-target-only",
            mutation_precondition="projection-drift-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="regenerate-projection",
            source="generated-target.projection-fingerprint",
            evidence_sources=["generated/.agentic-workspace-cli-fingerprint.json"],
            rejection_observed=True,
            recovery_observed=True,
        ),
        _operation_from_state(
            target=target,
            scenario_id=scenario_id,
            path=".agentic-workspace/local/proof/last.json",
            expected_status="stale",
            owner="verification",
            terminal_state="continue",
            typed_action="run-proof",
            effect_scope="proof-selection-only",
            mutation_precondition="stale-proof-rejected",
            proof_claim_boundary="fresh-proof-required",
            next_transition="rerun-selected-proof",
            source="verification.proof-store",
            evidence_sources=[".agentic-workspace/local/proof/last.json", "proof.report"],
            rejection_observed=True,
            recovery_observed=True,
        ),
    )
    for operation in state_operations:
        if operation:
            return operation
    if runtime.get("status") == "unavailable":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="workspace",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="runtime-state-only",
            mutation_precondition="runtime-incompatible",
            proof_claim_boundary="no-completion-claim",
            next_transition="restore-runtime",
            source="workspace.runtime-readiness",
            evidence_sources=[".agentic-workspace/local/runtime/availability.json", "implement.operating_loop"],
            rejection_observed=True,
            recovery_observed=True,
        )
    if runtime.get("status") == "restored":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="workspace",
            terminal_state="continue",
            typed_action="start",
            effect_scope="startup-reentry-only",
            mutation_precondition="runtime-restored",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="restart-ordinary-route",
            source="workspace.runtime-readiness",
            evidence_sources=[".agentic-workspace/local/runtime/availability.json", "start.next_safe_action"],
            recovery_observed=True,
        )
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "closeout" / "premature.json").get("status") == "partial":
        if not _closeout_blocks_completion(closeout):
            return {}
        return _authority_packet(
            scenario_id=scenario_id,
            owner="planning",
            terminal_state="partial",
            typed_action="continue",
            effect_scope="claim-boundary-only",
            mutation_precondition="acceptance-incomplete",
            proof_claim_boundary="partial-claim-only",
            next_transition="continue-unresolved-work",
            source="planning.closeout-boundary",
            evidence_sources=[".agentic-workspace/local/closeout/premature.json", "report.closeout_trust"],
            rejection_observed=True,
        )
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "continuation" / "compacted.json").get("status") == "compacted":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="planning",
            terminal_state="continue",
            typed_action="continue",
            effect_scope="continuation-state-only",
            mutation_precondition="continuation-revision-current",
            proof_claim_boundary="continuation-proof-before-claim",
            next_transition="resume-after-compaction",
            source="planning.continuation-store",
            evidence_sources=[".agentic-workspace/local/continuation/compacted.json", "summary.continuation_view"],
            recovery_observed=True,
        )
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json").get("status") == "unadmitted":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="delegation",
            terminal_state="continue",
            typed_action="admit-result",
            effect_scope="returned-result-admission",
            mutation_precondition="return-receipt-current",
            proof_claim_boundary="admitted-result-before-claim",
            next_transition="admit-or-repair-return",
            source="delegation.return-admission",
            evidence_sources=[".agentic-workspace/local/delegation/returned-result.json"],
            rejection_observed=True,
            recovery_observed=True,
        )
    if (target / ".agentic-workspace" / "skills" / "workspace-startup" / "SKILL.missing").exists():
        return _authority_packet(
            scenario_id=scenario_id,
            owner="workspace",
            terminal_state="blocked",
            typed_action="recover",
            effect_scope="skill-routing-only",
            mutation_precondition="skill-dependency-unavailable",
            proof_claim_boundary="no-completion-claim",
            next_transition="install-or-select-supported-skill",
            source="workspace.skill-router",
            evidence_sources=[".agentic-workspace/skills/workspace-startup/SKILL.missing"],
            rejection_observed=True,
        )
    if (target / "incoming" / "untrusted.txt").exists():
        return _authority_packet(
            scenario_id=scenario_id,
            owner="workspace",
            terminal_state="continue",
            typed_action="ignore-data-instruction",
            effect_scope="trusted-instruction-sources-only",
            mutation_precondition="data-text-not-authority",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="continue-safe-route",
            source="workspace.instruction-authority-filter",
            evidence_sources=["incoming/untrusted.txt", "start.next_safe_action"],
        )
    if (target / "notes" / "user-owned.md").exists():
        return _authority_packet(
            scenario_id=scenario_id,
            owner="workspace",
            terminal_state="continue",
            typed_action="implement",
            effect_scope="non-overlapping-changed-paths",
            mutation_precondition="preexisting-edits-preserved",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="inspect-dirty-overlap",
            source="workspace.dirty-worktree-guard",
            evidence_sources=["notes/user-owned.md", "implement.context.planning_safety_gate"],
        )
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "workspace" / "target-identity.json").get("status") == "rebound":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="workspace",
            terminal_state="continue",
            typed_action="recover",
            effect_scope="workspace-routing-state",
            mutation_precondition="target-identity-rebound",
            proof_claim_boundary="proof-after-recovery",
            next_transition="refresh-startup-context",
            source="workspace.target-identity",
            evidence_sources=[".agentic-workspace/local/workspace/target-identity.json", "start.next_safe_action"],
            recovery_observed=True,
        )
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "planning" / "task-switch.json").get("status") == "new-task-only":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="planning",
            terminal_state="continue",
            typed_action="reconcile",
            effect_scope="new-task-only",
            mutation_precondition="active-owner-preserved",
            proof_claim_boundary="no-active-owner-completion-claim",
            next_transition="acknowledge-task-switch",
            source="planning.task-switch-router",
            evidence_sources=[
                ".agentic-workspace/local/planning/task-switch.json",
                "implement.context.planning_safety_gate",
            ],
        )
    if plan.get("status") == "completed":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="planning",
            terminal_state="partial",
            typed_action="route-residue",
            effect_scope="residue-record-only",
            mutation_precondition="completed-owner-current",
            proof_claim_boundary="partial-claim-only",
            next_transition="open-residue-owner",
            source="planning.execplan-store",
            evidence_sources=[plan_path.relative_to(target).as_posix(), "summary.continuation_view"],
        )
    if active_planning and plan_path.exists():
        return _authority_packet(
            scenario_id=scenario_id,
            owner="planning",
            terminal_state="continue",
            typed_action="continue",
            effect_scope="selected-owner-only",
            mutation_precondition="owner-revision-current",
            proof_claim_boundary="owner-proof-before-completion",
            next_transition="resume-current-slice",
            source="planning.execplan-store",
            evidence_sources=[plan_path.relative_to(target).as_posix(), "summary.continuation_view"],
            recovery_observed=True,
        )
    if _read_json_if_present(target / ".agentic-workspace" / "local" / "external-intent" / "issue-2300.json").get("status") == "current":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="issue-scope",
            terminal_state="continue",
            typed_action="implement",
            effect_scope="issue-bounded-paths",
            mutation_precondition="clean-baseline",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="run-focused-proof",
            source="external-intent.issue-store",
            evidence_sources=[
                ".agentic-workspace/local/external-intent/issue-2300.json",
                "implement.context.planning_safety_gate",
            ],
        )
    if not active_planning and gate.get("gate_result") == "direct-work-allowed":
        return _authority_packet(
            scenario_id=scenario_id,
            owner="direct-work",
            terminal_state="continue",
            typed_action="implement",
            effect_scope="changed-paths-only",
            mutation_precondition="clean-baseline",
            proof_claim_boundary="proof-before-completion-claim",
            next_transition="run-focused-proof",
            source="workspace.current-work-router",
            evidence_sources=["implement.context.planning_safety_gate"],
        )
    return {}


def _operation_from_state(
    *,
    target: Path,
    scenario_id: str,
    path: str,
    expected_status: str,
    owner: str,
    terminal_state: str,
    typed_action: str,
    effect_scope: str,
    mutation_precondition: str,
    proof_claim_boundary: str,
    next_transition: str,
    source: str,
    evidence_sources: list[str],
    rejection_observed: bool = False,
    recovery_observed: bool = False,
) -> dict[str, Any]:
    if _read_json_if_present(target / path).get("status") != expected_status:
        return {}
    return _authority_packet(
        scenario_id=scenario_id,
        owner=owner,
        terminal_state=terminal_state,
        typed_action=typed_action,
        effect_scope=effect_scope,
        mutation_precondition=mutation_precondition,
        proof_claim_boundary=proof_claim_boundary,
        next_transition=next_transition,
        source=source,
        evidence_sources=evidence_sources,
        rejection_observed=rejection_observed,
        recovery_observed=recovery_observed,
    )


def _authority_packet(
    *,
    scenario_id: str,
    owner: str,
    terminal_state: str,
    typed_action: str,
    effect_scope: str,
    mutation_precondition: str,
    proof_claim_boundary: str,
    next_transition: str,
    source: str,
    evidence_sources: list[str],
    rejection_observed: bool = False,
    recovery_observed: bool = False,
) -> dict[str, Any]:
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
            "attempted": rejection_observed or recovery_observed,
            "accepted": not rejection_observed,
            "repair": next_transition if rejection_observed or recovery_observed else "",
        },
        "decision": {
            "owner": owner,
            "terminal_state": terminal_state,
            "typed_action": typed_action,
            "effect_scope": effect_scope,
            "mutation_precondition": mutation_precondition,
            "proof_claim_boundary": proof_claim_boundary,
            "next_transition": next_transition,
        },
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
