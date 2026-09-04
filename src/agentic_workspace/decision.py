from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any


class DecisionContractError(ValueError):
    """Raised when a source owner contributes an invalid decision fragment."""


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _strings(value: object, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise DecisionContractError(f"{field} must be a list of non-empty strings")
    return [item for item in value if isinstance(item, str)]


def normalize_contribution(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize the only semantic input accepted by the v1 reducer."""

    owner = str(value.get("owner") or "").strip()
    revision = str(value.get("revision") or "").strip()
    if not owner or not revision:
        raise DecisionContractError("a contribution requires owner and revision")

    blockers = value.get("blockers", [])
    actions = value.get("actions", [])
    if not isinstance(blockers, list) or any(not isinstance(item, Mapping) for item in blockers):
        raise DecisionContractError(f"{owner}.blockers must be a list of objects")
    if not isinstance(actions, list) or any(not isinstance(item, Mapping) for item in actions):
        raise DecisionContractError(f"{owner}.actions must be a list of objects")

    normalized_actions: list[dict[str, Any]] = []
    typed_actions = [dict(item) for item in actions if isinstance(item, Mapping)]
    for index, item in enumerate(typed_actions):
        operation_id = str(item.get("operation_id") or "").strip()
        if not operation_id:
            raise DecisionContractError(f"{owner}.actions[{index}].operation_id is required")
        arguments = item.get("arguments", {})
        if not isinstance(arguments, Mapping):
            raise DecisionContractError(f"{owner}.actions[{index}].arguments must be an object")
        priority = item.get("priority", 0)
        if not isinstance(priority, int):
            raise DecisionContractError(f"{owner}.actions[{index}].priority must be an integer")
        normalized_actions.append(
            {
                "operation_id": operation_id,
                "arguments": dict(arguments),
                "effects": _strings(item.get("effects"), field=f"{owner}.actions[{index}].effects"),
                "authority": str(item.get("authority") or owner),
                "priority": priority,
            }
        )

    normalized_blockers: list[dict[str, str]] = []
    typed_blockers = [dict(item) for item in blockers if isinstance(item, Mapping)]
    for index, item in enumerate(typed_blockers):
        code = str(item.get("code") or "").strip()
        message = str(item.get("message") or "").strip()
        if not code or not message:
            raise DecisionContractError(f"{owner}.blockers[{index}] requires code and message")
        blocker = {"code": code, "message": message, "owner": str(item.get("owner") or owner)}
        recovery = str(item.get("recovery") or "").strip()
        if recovery:
            blocker["recovery"] = recovery
        normalized_blockers.append(blocker)

    claims = value.get("claims", {})
    if not isinstance(claims, Mapping):
        raise DecisionContractError(f"{owner}.claims must be an object")

    facts = value.get("facts", {})
    if not isinstance(facts, Mapping):
        raise DecisionContractError(f"{owner}.facts must be an object")

    return {
        "owner": owner,
        "revision": revision,
        "relevant": value.get("relevant", True) is not False,
        "facts": dict(facts),
        "blockers": normalized_blockers,
        "actions": normalized_actions,
        "claims": {
            "allowed": _strings(claims.get("allowed"), field=f"{owner}.claims.allowed"),
            "blocked": _strings(claims.get("blocked"), field=f"{owner}.claims.blocked"),
        },
        "terminal": value.get("terminal", False) is True,
    }


def compile_source_decision(
    contributions: Iterable[Mapping[str, Any]],
    *,
    intent: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reduce current source-owner contributions to one operating answer.

    Rendering consumers are intentionally not an input. A CLI, Python client, or
    other transport may select detail after this function returns, but cannot
    influence identity, action, status, or claim authority.
    """

    normalized = [normalize_contribution(item) for item in contributions]
    relevant = sorted((item for item in normalized if item["relevant"]), key=lambda item: item["owner"])
    owners = [item["owner"] for item in relevant]
    if len(owners) != len(set(owners)):
        raise DecisionContractError("each source owner may contribute at most once")

    source_input = {
        "intent": dict(intent or {}),
        "sources": [
            {
                "owner": item["owner"],
                "revision": item["revision"],
                "facts": item["facts"],
                "blockers": item["blockers"],
                "actions": item["actions"],
                "claims": item["claims"],
                "terminal": item["terminal"],
            }
            for item in relevant
        ],
    }
    input_revision = _digest(source_input)

    blockers = [blocker for item in relevant for blocker in item["blockers"]]
    actions = [(item["owner"], action) for item in relevant for action in item["actions"]]
    primary_action: dict[str, Any] | None = None

    if not blockers and actions:
        actions.sort(key=lambda pair: (-pair[1]["priority"], pair[0], pair[1]["operation_id"]))
        top_priority = actions[0][1]["priority"]
        tied = [pair for pair in actions if pair[1]["priority"] == top_priority]
        if len(tied) > 1:
            blockers.append(
                {
                    "code": "ambiguous-action",
                    "message": "multiple source owners proposed equally authoritative actions",
                    "owner": "operating-decision",
                    "recovery": "reconcile the competing source owners",
                }
            )
        else:
            owner, action = actions[0]
            primary_action = {
                "kind": "agentic-workspace/operation-invocation/v1",
                "operation_id": action["operation_id"],
                "arguments": action["arguments"],
                "effects": action["effects"],
                "authority": action["authority"],
                "source_owner": owner,
                "expected_input_revision": input_revision,
                "idempotency_key": _digest(
                    {
                        "operation_id": action["operation_id"],
                        "arguments": action["arguments"],
                        "input_revision": input_revision,
                    }
                ),
            }

    allowed_claims = sorted({claim for item in relevant for claim in item["claims"]["allowed"]})
    blocked_claims = sorted({claim for item in relevant for claim in item["claims"]["blocked"]})
    allowed_claims = [claim for claim in allowed_claims if claim not in blocked_claims]
    if blockers:
        status = "blocked"
        primary_action = None
    elif primary_action:
        status = "actionable"
    elif relevant and all(item["terminal"] for item in relevant):
        status = "terminal"
    else:
        status = "direct"

    semantic_answer = {
        "input_revision": input_revision,
        "status": status,
        "primary_action": primary_action,
        "blockers": blockers,
        "claim_boundary": {"allowed": allowed_claims, "blocked": blocked_claims},
        "relevant_owners": owners,
    }
    return {
        "kind": "agentic-workspace/operating-decision/v1",
        "decision_id": "operating-decision:" + _digest(semantic_answer).removeprefix("sha256:")[:16],
        **semantic_answer,
    }


def select_decision_detail(decision: Mapping[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    """Create a non-authoritative view without recompiling semantic state."""

    selected = {field: decision[field] for field in fields if field in decision}
    return {
        "kind": "agentic-workspace/decision-view/v1",
        "decision_id": decision.get("decision_id"),
        "input_revision": decision.get("input_revision"),
        "authoritative": False,
        "values": selected,
    }
