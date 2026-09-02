"""Projection helpers for selected-proof execution results.

The runtime command owner performs effects; this module owns the read-only result
projection so proof admission changes do not expand the root runtime monolith.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.proof_receipt_admission import proof_command_admission, proof_receipt_admission
from agentic_workspace.proof_subject import build_proof_subject

PROOF_RUNS_RELATIVE_PATH = Path(".agentic-workspace/local/proof-receipts/runs")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def selected_proof_preexecution_admission(
    *,
    target_root: Path,
    changed_paths: list[str],
    command: str,
    selection: dict[str, Any],
    selected_command_resolver: Callable[..., dict[str, Any] | None],
) -> dict[str, Any]:
    """Prove that the canonical receipt writer can bind a command before launch."""

    command_decision = proof_command_admission(command)
    base = {
        "kind": "agentic-workspace/proof-preexecution-admission/v1",
        "command": command,
        "command_identity": hashlib.sha256(command.encode("utf-8")).hexdigest()[:16],
        "process_launched": False,
        "authority": "canonical-proof-receipt-selection-binding",
    }
    if not command_decision["admitted"]:
        return {
            **base,
            "status": "rejected",
            "reason": command_decision["reason"],
            "recovery": command_decision["safe_recovery"],
        }
    try:
        selected = selected_command_resolver(selection=selection, command=command)
    except WorkspaceUsageError as exc:
        return {
            **base,
            "status": "rejected",
            "reason": "current-selected-command-binding-rejected",
            "recovery": str(exc),
        }
    if not selected:
        return {
            **base,
            "status": "rejected",
            "reason": "missing-current-selected-command-binding",
            "recovery": "Rerun proof selection with the current task and execute only its typed selected command.",
        }
    subject = build_proof_subject(target_root=target_root, changed_paths=changed_paths, command=command)
    provisional = {
        "kind": "agentic-workspace/proof-receipt/v1",
        "command": command,
        "result": "passed",
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "changed_paths": changed_paths,
        "proof_subject": subject,
    }
    receipt_decision = proof_receipt_admission(provisional)
    if not receipt_decision["admitted"]:
        return {
            **base,
            "status": "rejected",
            "reason": receipt_decision["reason"],
            "recovery": receipt_decision["safe_recovery"],
        }
    return {
        **base,
        "status": "admitted",
        "reason": "current-selection-and-receipt-binding-admitted",
        "recovery": "none",
        "selected_command": {
            "lane": str(selected.get("lane") or selected.get("lane_id") or ""),
            "route_id": str(selected.get("route_id") or ""),
            "command_identity": str(selected.get("command_identity") or base["command_identity"]),
        },
        "proof_subject_revision": subject["fingerprint"],
        "receipt_admission": receipt_decision,
    }


def proof_execution_result_payload(
    *,
    run: dict[str, Any],
    selection: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    """Project proof execution coverage and its honest claim boundary."""

    run_receipt_ref = (PROOF_RUNS_RELATIVE_PATH / str(run["run_id"]) / "run.json").as_posix()
    command_records = [item for item in _as_list(run.get("commands")) if isinstance(item, dict)]
    record_by_command = {str(item.get("command") or ""): item for item in command_records}
    required_commands = [str(item) for item in _as_list(run.get("required_commands"))]
    selected_lanes = [item for item in _as_list(selection.get("selected_lanes")) if isinstance(item, dict)]
    owner_coverage = []
    for lane in selected_lanes:
        lane_commands = [str(item) for item in _as_list(lane.get("required_commands")) if str(item).strip()]
        if not lane_commands:
            continue
        passed = [command for command in lane_commands if record_by_command.get(command, {}).get("status") == "passed"]
        owner_coverage.append(
            {
                "owner": str(lane.get("id") or "unknown"),
                "status": "satisfied" if len(passed) == len(lane_commands) else "incomplete",
                "required_count": len(lane_commands),
                "passed_count": len(passed),
            }
        )
    passed_count = sum(record_by_command.get(command, {}).get("status") == "passed" for command in required_commands)
    failure_records = [item for item in command_records if item.get("status") in {"failed", "timeout", "cancelled", "admission-rejected"}]
    completed_failures = [item for item in failure_records if item.get("status") == "failed"]
    commands_complete = bool(required_commands) and passed_count == len(required_commands)
    aggregate_receipt = _as_dict(run.get("aggregate_receipt"))
    aggregate_admission = _as_dict(aggregate_receipt.get("admission"))
    aggregate_complete = aggregate_receipt.get("status") == "written" and aggregate_admission.get("proof_sufficient") is True
    selection_blockers: list[str] = []
    if _as_dict(selection.get("route_refinement_required")).get("status") == "required":
        selection_blockers.append("route-refinement-required")
    satisfied_owners = {str(item.get("owner") or "") for item in owner_coverage if item.get("status") == "satisfied"}
    unresolved_manual_obligations = [
        item
        for item in _as_list(selection.get("manual_proof_obligations"))
        if isinstance(item, dict) and str(item.get("id") or "") not in satisfied_owners
    ]
    if unresolved_manual_obligations:
        selection_blockers.append("manual-proof-obligations")
    if commands_complete and not aggregate_complete:
        selection_blockers.append("aggregate-receipt-admission")
    complete = commands_complete and aggregate_complete and not selection_blockers
    process_success = complete or status == "dry-run"
    exit_status = 0 if process_success else 1
    local_scope = _as_dict(run.get("subject")).get("claim_scope") == "machine-local-effective-config"
    if complete and local_scope:
        claim_boundary = {
            "status": "effective-local-configuration-verified",
            "scope": "machine-local",
            "completion_claim_allowed": True,
            "shared_repository_claim_allowed": False,
            "pr_release_or_parent_claim_allowed": False,
            "rule": "Current local evidence verifies only the effective machine-local configuration; it cannot satisfy shared repository, PR, release, or parent claims.",
        }
    elif complete:
        claim_boundary = {
            "status": "selected-proof-executed",
            "scope": "repository-selected-proof",
            "completion_claim_allowed": False,
            "shared_repository_claim_allowed": True,
            "rule": "Selected proof execution is current evidence; completion still requires intent and closeout reconciliation.",
        }
    else:
        claim_boundary = {
            "status": "blocked",
            "scope": "machine-local" if local_scope else "repository-selected-proof",
            "completion_claim_allowed": False,
            "shared_repository_claim_allowed": False,
            "rule": "Failed, timed-out, cancelled, or incomplete selected proof cannot authorize a completion claim.",
        }
    next_action = (
        {"action": "reconcile-closeout", "command": "agentic-workspace planning closeout --target . --proof-from last --format json"}
        if complete and not local_scope
        else {"action": "continue-with-verified-local-config", "command": None}
        if complete
        else {
            "action": "resume-selected-proof",
            "command": f"agentic-workspace proof --target . --changed <paths> --execute-selected --proof-run-id {run['run_id']} --format json",
            "reason": "aggregate-receipt-admission",
        }
        if commands_complete and not aggregate_complete
        else {
            "action": "repair-proof-route",
            "command": "agentic-workspace proof --target . --changed <paths> --select route_refinement_required,manual_proof_obligations --format json",
        }
        if commands_complete and selection_blockers
        else {
            "action": "diagnose-failed-proof",
            "command": "agentic-workspace proof --target . --changed <paths> --format json",
            "reason": "completed-command-failure",
            "revalidation_command": (
                "agentic-workspace proof --target . --changed <paths> --execute-selected --proof-run-id <new-run-id> --format json"
            ),
            "rule": "A completed failing command remains immutable in this run; diagnose or fix it, then revalidate under a new run identity.",
        }
        if completed_failures
        else {
            "action": "resume-selected-proof",
            "command": f"agentic-workspace proof --target . --changed <paths> --execute-selected --proof-run-id {run['run_id']} --format json",
        }
    )
    return {
        "kind": "agentic-workspace/proof-execution-result/v1",
        "exit_status": exit_status,
        "exit_class": "success" if process_success else "proof-incomplete-or-failed",
        "safe_to_retry": not process_success and not completed_failures,
        "mutation_occurred": status != "dry-run" and bool(command_records or aggregate_receipt),
        "status": "completed-with-unresolved-obligations" if commands_complete and selection_blockers else status,
        "outcome": "passed"
        if complete
        else "blocked"
        if commands_complete
        else str(failure_records[-1].get("status") if failure_records else "incomplete"),
        "run": {
            "id": run["run_id"],
            "attempt": run.get("attempt", 1),
            "subject_revision": _as_dict(run.get("subject")).get("revision"),
            "receipt_ref": run_receipt_ref,
        },
        "coverage": {
            "required_count": len(required_commands),
            "passed_count": passed_count,
            "remaining_count": max(0, len(required_commands) - passed_count),
            "owners": owner_coverage,
            "selection_obligations": selection_blockers,
        },
        "preexecution_admission": {
            "status": "admitted",
            "command_count": len(_as_list(run.get("preexecution_admission"))),
            "process_launch_count": sum(1 for item in command_records if item.get("status") != "cancelled"),
            "authority": "canonical-proof-receipt-selection-binding",
        },
        "canonical_receipt_admission": {
            "recorded_count": 1 if aggregate_receipt.get("status") in {"written", "dry-run"} else 0,
            "rejected_count": 1 if aggregate_receipt.get("status") == "rejected-after-runtime-state-change" else 0,
            "authority": "proof_receipt_admission",
            "scope": "selected-proof-aggregate",
        },
        "failures": [
            {"command_id": item.get("command_id"), "status": item.get("status"), "exit_code": item.get("exit_code")}
            for item in failure_records
        ],
        "claim_boundary": claim_boundary,
        "next_action": next_action,
        "detail_routes": {
            "run_receipt": run_receipt_ref,
            "command_receipts": [str(item.get("receipt_ref") or "") for item in command_records],
            "aggregate_receipt": str(aggregate_receipt.get("receipt_ref") or ""),
            "resume": next_action.get("command"),
            "revalidation": next_action.get("revalidation_command"),
        },
        "persistence": {
            "owner": ".agentic-workspace/local/proof-receipts/runs",
            "repository_residue": False,
            "tracked_file_count": 0,
            "delta_shape": "one local aggregate receipt plus one bounded run receipt and individually addressable local command receipts",
            "detailed_repository_publication": "manual --record-receipt interoperability route only",
        },
    }
