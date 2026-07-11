"""Shared actionability and progress-making next-action derivation."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def _operation(command: str) -> str:
    match = re.search(r"(?:agentic-workspace|run_agentic_workspace\.py)\s+([a-z][a-z0-9-]*)", command)
    return match.group(1) if match else ""


def derive_actionability(
    *,
    command_name: str,
    health: str,
    warnings: list[Any],
    repair_actions: list[Any],
    manual_review_actions: list[Any],
    proposed_next_action: dict[str, Any] | None,
    claim_limits: list[str] | None = None,
) -> dict[str, Any]:
    """Derive one coherent action decision and reject ordinary same-operation loops."""

    def identity(item: Any) -> str:
        if isinstance(item, dict):
            return str(
                item.get("id") or item.get("finding_id") or item.get("code") or item.get("message") or json.dumps(item, sort_keys=True)
            )
        return str(item)

    findings: list[dict[str, Any]] = []
    repair_ids = {identity(item) for item in repair_actions}
    if repair_actions:
        findings.append(
            {
                "class": "required-repair",
                "count": len(repair_ids),
                "owner": "workspace-or-repo-maintainer",
                "finding_ids": sorted(repair_ids),
            }
        )
    required_reviews = [
        item
        for item in manual_review_actions
        if isinstance(item, dict) and (item.get("action_required") is True or str(item.get("severity") or "").lower() == "error")
    ]
    advisory_reviews = [item for item in manual_review_actions if item not in required_reviews]
    if required_reviews:
        findings.append({"class": "required-review", "count": len(required_reviews), "owner": "human-or-reviewer"})
    required_ids = {identity(item) for item in required_reviews} - repair_ids
    advisory_ids = ({identity(item) for item in advisory_reviews} | {identity(item) for item in warnings}) - repair_ids - required_ids
    if required_reviews:
        findings[-1]["count"] = len(required_ids)
        findings[-1]["finding_ids"] = sorted(required_ids)
        if not required_ids:
            findings.pop()
    advisory_count = len(advisory_ids)
    if advisory_count:
        findings.append(
            {
                "class": "optional-advisory",
                "count": advisory_count,
                "owner": "current-actor-or-reviewer",
                "finding_ids": sorted(advisory_ids),
            }
        )
    if not findings:
        findings.append({"class": "resolved-or-informational", "count": 1, "owner": "none"})

    action_required = bool(repair_actions or required_reviews)
    proposed = dict(proposed_next_action or {})
    next_command = str(proposed.get("command") or proposed.get("run") or "").strip()
    same_operation = bool(next_command and _operation(next_command) == command_name)
    external_condition = str(proposed.get("external_change_condition") or "").strip()
    expected_transition = str(proposed.get("expected_transition") or proposed.get("state_transition") or "").strip()
    digest_input = {
        "operation": command_name,
        "health": health,
        "finding_classes": [item["class"] for item in findings],
        "finding_ids": sorted(repair_ids | required_ids | advisory_ids),
        "action_required": action_required,
        "claim_limits": list(claim_limits or []),
    }
    input_digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True).encode()).hexdigest()[:16]
    proposed_input_digest = str(proposed.get("input_digest") or "").strip()
    same_state = proposed_input_digest == input_digest if proposed_input_digest else not expected_transition
    self_loop_rejected = same_operation and same_state and not external_condition
    if not action_required:
        next_action = {
            "action": "no-immediate-action",
            "summary": (
                "No progress-making action is currently required; advisories and claim limits remain visible."
                if warnings or claim_limits
                else "No immediate action is required."
            ),
            "commands": [],
        }
    elif self_loop_rejected:
        next_action = {
            "action": "required-action-unavailable",
            "summary": "Required work remains, but the proposed action repeats the same operation against unchanged state.",
            "commands": [],
            "owner": str(proposed.get("owner") or "workspace-or-repo-maintainer"),
            "missing_precondition": str(proposed.get("missing_precondition") or "state change or a distinct transition-bearing action"),
        }
    else:
        next_action = proposed
    return {
        "kind": "agentic-workspace/actionability/v1",
        "status": "action-required" if action_required else "advisory-only" if warnings or claim_limits else "resolved",
        "health": health,
        "action_required": action_required,
        "findings": findings,
        "claim_limits": list(claim_limits or []),
        "next_action": next_action,
        "progress_check": {
            "input_digest": input_digest,
            "proposed_operation": _operation(next_command),
            "same_operation": same_operation,
            "same_state": same_state,
            "expected_transition": expected_transition,
            "external_change_condition": external_condition,
            "result": "rejected-same-state-loop" if self_loop_rejected else "progress-making" if next_command else "terminal",
        },
        "rule": "Status, required action, claim limits, and next action derive from one finding classification; ordinary same-state loops are not next actions.",
    }
