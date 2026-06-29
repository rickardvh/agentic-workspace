"""Shared projection helpers for workspace runtime payloads.

These helpers are intentionally small and data-only. They are shared by startup,
implement, proof, and report payload builders without owning command semantics.
"""

from __future__ import annotations

from typing import Any


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _workflow_participation_payload(*, surface: str, compact: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/workflow-participation/v1",
        "surface": surface,
        "status": "mandatory",
        "rule": (
            "When Agentic Workspace is enabled, run and follow the routed AW workflow for non-trivial work. "
            "Advisory routing only scopes agent judgment inside that mandatory workflow."
        ),
        "agent_judgment_scope": (
            "The agent owns semantic work-shape, proof-proportionality, and completion judgment only after the "
            "required start/implement route has been consulted and any gates have been followed."
        ),
        "not_permission": [
            "implementation_allowed is not permission to skip AW startup, planning, proof, or closeout routing",
            "advisory-support is not optional workflow participation",
        ],
    }
    if compact:
        return {
            "status": payload["status"],
            "rule": "AW mandatory; advisory guidance and implementation_allowed cannot bypass workflow.",
        }
    return payload


def _authority_boundary_payload(
    *,
    surface: str,
    enforced_by_aw: list[str] | None = None,
    observed_by_aw: list[str] | None = None,
    recommended_by_aw: list[str] | None = None,
    candidate_routes: list[str] | None = None,
    proof_hints: list[str] | None = None,
    agent_owned_decisions: list[str] | None = None,
    human_owned_decisions: list[str] | None = None,
    rule: str | None = None,
) -> dict[str, Any]:
    enforced = [str(item).strip() for item in (enforced_by_aw or []) if str(item).strip()]
    observed = [str(item).strip() for item in (observed_by_aw or []) if str(item).strip()]
    recommended = [str(item).strip() for item in (recommended_by_aw or []) if str(item).strip()]
    routes = [str(item).strip() for item in (candidate_routes or []) if str(item).strip()]
    hints = [str(item).strip() for item in (proof_hints or []) if str(item).strip()]
    agent = [str(item).strip() for item in (agent_owned_decisions or []) if str(item).strip()]
    human = [str(item).strip() for item in (human_owned_decisions or []) if str(item).strip()]
    if enforced:
        authority_class = "hard-gate"
    elif recommended or routes or hints:
        authority_class = "advisory-support"
    elif observed:
        authority_class = "observed-facts"
    else:
        authority_class = "agent-owned"
    return {
        "kind": "agentic-workspace/authority-boundary/v1",
        "surface": surface,
        "authority_class": authority_class,
        "enforced_by_aw": enforced,
        "observed_by_aw": observed,
        "recommended_by_aw": recommended,
        "candidate_routes": routes,
        "proof_hints": hints,
        "agent_owned_decisions": agent,
        "human_owned_decisions": human,
        "reporting_rule": rule
        or (
            "Report AW facts, constraints, and suggestions separately from the agent's semantic decision; "
            "advisory route support is internal to the mandatory enabled-AW workflow."
        ),
    }


def _tiny_action_effect(value: Any, *, include_allowed: bool = True, include_resolution_commands: bool = True) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = [
        "force",
        "blocked_until_reconciled",
        "resolution_selector",
        "resolution_command",
    ]
    if include_resolution_commands:
        keys.append("resolution_commands")
    compact = {key: value[key] for key in keys if key in value}
    if include_allowed and "allowed_now" in value:
        compact["allowed_now"] = value["allowed_now"]
    return compact


def _compact_authority_boundary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}

    def compact_items(key: str, limit: int) -> list[str]:
        return [_compact_authority_text(str(item)) for item in _list_payload(value.get(key))[:limit]]

    compact = {
        "kind": value.get("kind"),
        "surface": value.get("surface"),
        "authority_class": value.get("authority_class"),
        "enforced_by_aw": compact_items("enforced_by_aw", 2),
        "observed_by_aw": compact_items("observed_by_aw", 1),
        "recommended_by_aw": compact_items("recommended_by_aw", 1),
        "candidate_routes": compact_items("candidate_routes", 1),
        "agent_owned_decisions": compact_items("agent_owned_decisions", 1),
    }
    return {key: item for key, item in compact.items() if item not in (None, "", [])}


def _compact_authority_text(text: str) -> str:
    mapping = {
        "whether delegation improves quality or cost without lowering proof": "delegation fit without lowering proof",
        "semantic fit of candidate route to the user's task": "candidate-route semantic fit",
        "whether to stay local when advisory delegation is not followed": "stay-local judgment",
        "semantic work shape": "semantic work shape",
        "proof proportionality": "proof proportionality",
        "whether Planning is needed when no hard blocker applies": "planning need when no hard blocker applies",
        "issue intent or acceptance when task scope is externally owned": "external issue intent or acceptance",
    }
    if text in mapping:
        return mapping[text]
    if len(text) <= 80:
        return text
    return text[:77].rstrip() + "..."
