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

    findings: list[dict[str, Any]] = []
    if repair_actions:
        findings.append({"class": "required-repair", "count": len(repair_actions), "owner": "workspace-or-repo-maintainer"})
    required_reviews = [
        item
        for item in manual_review_actions
        if isinstance(item, dict) and (item.get("action_required") is True or str(item.get("severity") or "").lower() == "error")
    ]
    advisory_reviews = [item for item in manual_review_actions if item not in required_reviews]
    if required_reviews:
        findings.append({"class": "required-review", "count": len(required_reviews), "owner": "human-or-reviewer"})
    advisory_count = len(advisory_reviews) + len(warnings)
    if advisory_count:
        findings.append({"class": "optional-advisory", "count": advisory_count, "owner": "current-actor-or-reviewer"})
    if not findings:
        findings.append({"class": "resolved-or-informational", "count": 1, "owner": "none"})

    action_required = bool(repair_actions or required_reviews)
    proposed = dict(proposed_next_action or {})
    next_command = str(proposed.get("command") or proposed.get("run") or "").strip()
    same_operation = bool(next_command and _operation(next_command) == command_name)
    external_condition = str(proposed.get("external_change_condition") or "").strip()
    self_loop_rejected = same_operation and not external_condition
    if not action_required or self_loop_rejected:
        next_action = {
            "action": "no-immediate-action",
            "summary": (
                "No progress-making action is currently required; advisories and claim limits remain visible."
                if warnings or claim_limits
                else "No immediate action is required."
            ),
            "commands": [],
        }
    else:
        next_action = proposed

    digest_input = {
        "operation": command_name,
        "health": health,
        "finding_classes": [item["class"] for item in findings],
        "action_required": action_required,
        "claim_limits": list(claim_limits or []),
    }
    return {
        "kind": "agentic-workspace/actionability/v1",
        "status": "action-required" if action_required else "advisory-only" if warnings or claim_limits else "resolved",
        "health": health,
        "action_required": action_required,
        "findings": findings,
        "claim_limits": list(claim_limits or []),
        "next_action": next_action,
        "progress_check": {
            "input_digest": hashlib.sha256(json.dumps(digest_input, sort_keys=True).encode()).hexdigest()[:16],
            "proposed_operation": _operation(next_command),
            "same_operation": same_operation,
            "external_change_condition": external_condition,
            "result": "rejected-same-state-loop" if self_loop_rejected else "progress-making" if next_command else "terminal",
        },
        "rule": "Status, required action, claim limits, and next action derive from one finding classification; ordinary same-state loops are not next actions.",
    }
