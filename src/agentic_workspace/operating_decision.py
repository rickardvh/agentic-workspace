"""Compose current AW authorities into one internal operating decision."""

from __future__ import annotations

import hashlib
import json
from typing import Any

BLOCKER_PRECEDENCE = [
    "missing-authority",
    "stale-revision",
    "conflicting-input",
    "denied-effect",
    "stale-mutation-baseline",
    "stale-proof",
    "context-coverage-gap",
    "missing-capability",
]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def context_authority_declarations() -> list[dict[str, Any]]:
    return [
        {
            "surface": "system-intent",
            "owner": "workspace-system-intent",
            "authority_class": "canonical",
            "consumer": "startup, implement, proof, report",
            "activation": "durable shaping input, not active task state",
            "editable_by": "system-intent sync and explicit repo edits",
            "stale_when": "mirror revision differs from source declaration",
            "proof_route": "system-intent sync and contract tooling checks",
            "disposition": "retain as durable shaping authority",
        },
        {
            "surface": "planning",
            "owner": "planning package",
            "authority_class": "canonical",
            "consumer": "current-work, task relation, owner posture, continuation",
            "activation": "active TODO item, selected owner, or current lane slice",
            "editable_by": "planning operations",
            "stale_when": "planning revision or selected owner revision changes",
            "proof_route": "planning package tests and lane health checks",
            "disposition": "retain as current-work authority",
        },
        {
            "surface": "memory",
            "owner": "memory package",
            "authority_class": "historical/evidence",
            "consumer": "reuse, lessons, prior durable findings",
            "activation": "route-selected by task/path/stage",
            "editable_by": "memory operations",
            "stale_when": "manifest route no longer selects or finding is superseded",
            "proof_route": "memory doctor and freshness checks",
            "disposition": "retain as routed evidence, not current-task authority",
        },
        {
            "surface": "proof",
            "owner": "verification and proof runtime",
            "authority_class": "canonical",
            "consumer": "completion claims, reusable evidence, proof freshness",
            "activation": "selected proof subject for current changed paths",
            "editable_by": "proof receipt admission and verification operations",
            "stale_when": "proof subject, selected command, or changed-path fingerprint changes",
            "proof_route": "proof report and receipt reconciliation tests",
            "disposition": "retain as claim authority",
        },
        {
            "surface": "generated-references",
            "owner": "command-generation and contract tooling",
            "authority_class": "generated",
            "consumer": "CLI, Python, TypeScript, adapter parity",
            "activation": "generated freshness and operation registry selection",
            "editable_by": "generators only",
            "stale_when": "source contract revision differs from generated projection",
            "proof_route": "generated command package checks",
            "disposition": "regenerate rather than hand edit",
        },
    ]


def derive_context_gaps(*, declarations: list[dict[str, Any]], selected_surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    declared = {str(item.get("surface") or ""): item for item in declarations if isinstance(item, dict)}
    gaps: list[dict[str, Any]] = []
    for surface in selected_surfaces:
        if not isinstance(surface, dict):
            continue
        surface_id = str(surface.get("surface") or "").strip()
        status = str(surface.get("status") or "present").strip()
        required = bool(surface.get("required"))
        minimum_useful = bool(surface.get("minimum_useful", True))
        routed = bool(surface.get("routed", True))
        if surface_id not in declared:
            gap_class = "consumer-without-source"
        elif required and status == "missing":
            gap_class = "configured-but-missing"
        elif required and not minimum_useful:
            gap_class = "configured-but-unpopulated"
        elif status == "present" and not routed:
            gap_class = "declared-but-unroutable"
        elif surface.get("coverage_gap"):
            gap_class = "coverage-gap"
        elif surface.get("inference_fallback"):
            gap_class = "inference-fallback"
        elif surface.get("unresolved_finding"):
            gap_class = "unresolved-populated-finding"
        else:
            continue
        owner = str(_as_dict(declared.get(surface_id)).get("owner") or surface.get("owner") or "workspace-maintainer")
        gaps.append(
            {
                "kind": "agentic-workspace/context-gap/v1",
                "id": f"{gap_class}:{surface_id or 'unknown'}",
                "gap_class": gap_class,
                "surface": surface_id,
                "affected_capability": str(surface.get("affected_capability") or "ordinary-operating-decision"),
                "affected_decisions": _as_list(surface.get("affected_decisions")) or ["routing", "claim-boundary"],
                "evidence_refs": _as_list(surface.get("evidence_refs")),
                "confidence": str(surface.get("confidence") or "high"),
                "severity": str(surface.get("severity") or ("blocking" if required else "advisory")),
                "current_task_effect": str(surface.get("current_task_effect") or "weakens current AW decision input"),
                "owner": owner,
                "next_route": str(surface.get("next_route") or f"repair or declare lifecycle for {surface_id}"),
            }
        )
    return gaps


def compile_operating_decision(*, inputs: dict[str, Any]) -> dict[str, Any]:
    """Return one primary typed action or one typed external blocker."""

    revisions = _as_dict(inputs.get("revisions"))
    actionability = _as_dict(inputs.get("actionability"))
    action = _as_dict(actionability.get("next_action") or inputs.get("primary_action"))
    progress_check = _as_dict(actionability.get("progress_check"))
    invocation = _as_dict(action.get("operation_invocation"))
    blockers = [item for item in _as_list(inputs.get("blockers")) if isinstance(item, dict)]
    for gap in _as_list(inputs.get("context_gaps")):
        if isinstance(gap, dict) and str(gap.get("severity") or "") == "blocking":
            blockers.append({"reason_code": "context-coverage-gap", "owner": gap.get("owner", ""), "repair": gap.get("next_route", "")})
    if (
        not invocation
        and action
        and str(action.get("action") or "") not in {"no-immediate-action", ""}
        and progress_check.get("result") != "rejected-stale-action"
    ):
        blockers.append(
            {
                "reason_code": "missing-authority",
                "owner": "operation-invocation",
                "repair": "attach a typed operation_invocation before treating this action as executable",
            }
        )
    if progress_check.get("result") == "rejected-stale-action":
        blockers.append(
            {
                "reason_code": "stale-revision",
                "owner": "operation-invocation",
                "repair": "refresh the operating decision and rebuild the typed action from current owner/context/proof state",
            }
        )
    if inputs.get("stale_revision"):
        blockers.append({"reason_code": "stale-revision", "owner": "input-revision", "repair": "refresh authoritative input projection"})
    if inputs.get("conflict"):
        blockers.append(
            {"reason_code": "conflicting-input", "owner": "conflicting authorities", "repair": "resolve specialist input conflict"}
        )
    if inputs.get("denied_effect"):
        blockers.append(
            {"reason_code": "denied-effect", "owner": "effect authority", "repair": "select an allowed effect or request authority"}
        )
    if inputs.get("stale_mutation_baseline"):
        blockers.append({"reason_code": "stale-mutation-baseline", "owner": "mutation authority", "repair": "refresh mutation baseline"})
    if inputs.get("stale_proof"):
        blockers.append({"reason_code": "stale-proof", "owner": "proof authority", "repair": "rerun or re-record selected proof"})
    blockers.sort(
        key=lambda item: (
            BLOCKER_PRECEDENCE.index(str(item.get("reason_code"))) if str(item.get("reason_code")) in BLOCKER_PRECEDENCE else 99
        )
    )
    blocker = blockers[0] if blockers else {}
    if blocker:
        status = "blocked"
        primary_action: dict[str, Any] = {}
        external_blocker = {
            "kind": "agentic-workspace/operating-decision-blocker/v1",
            "reason_code": str(blocker.get("reason_code") or "blocked"),
            "owner": str(blocker.get("owner") or "workspace-maintainer"),
            "repair": str(blocker.get("repair") or "refresh or resolve the owning authority"),
        }
    else:
        status = "actionable" if invocation else "terminal"
        primary_action = action if invocation else {}
        external_blocker = {}
    identity_input = {
        "revisions": revisions,
        "action": invocation,
        "blocker": external_blocker,
        "terminal_state": inputs.get("terminal_state", ""),
    }
    return {
        "kind": "agentic-workspace/operating-decision/v1",
        "decision_id": f"operating-decision:{_digest(identity_input)[:16]}",
        "status": status,
        "input_revisions": revisions,
        "current_work": _as_dict(inputs.get("current_work")),
        "selected_owner": _as_dict(inputs.get("selected_owner")),
        "terminal_state": str(inputs.get("terminal_state") or "CONTINUE"),
        "primary_action": primary_action,
        "external_blocker": external_blocker,
        "blocked_claim_classes": _as_list(inputs.get("blocked_claim_classes")),
        "provenance": _as_dict(inputs.get("provenance")),
        "replacement_map": {
            "next_action.command": "display rendering only; operation_invocation owns executable identity",
            "actionability.progress_check.proposed_operation": "derived from operation_invocation.operation_id",
            "startup/implement/proof claim gates": "consume operating decision status and blocker reason codes",
        },
        "rule": "This compiler composes admitted specialist outputs and preserves their ownership; it does not infer authority from rendered text.",
    }
