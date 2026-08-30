"""Pure deterministic state reducer for the maintainer-only Structured Executor."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

STATE_KIND = "agentic-workspace/structured-executor-state/v1"
TRANSITION_INPUT_KIND = "agentic-workspace/structured-executor-transition-input/v1"
TRANSITION_KIND = "agentic-workspace/structured-executor-transition/v1"


class TransitionRejected(ValueError):
    """Raised before mutation when a transition is not bound to current state."""


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Return the stable semantic serialization used for every identity."""

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def semantic_digest(payload: Mapping[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(payload)).hexdigest()}"


def state_digest(state: Mapping[str, Any]) -> str:
    semantic_state = {key: value for key, value in state.items() if key != "state_digest"}
    return semantic_digest(semantic_state)


def with_state_digest(state: Mapping[str, Any]) -> dict[str, Any]:
    next_state = copy.deepcopy(dict(state))
    next_state["state_digest"] = state_digest(next_state)
    return next_state


def initial_state(
    *,
    run_id: str,
    task_ref: Mapping[str, Any],
    execution_budget: int = 0,
    semantic_budget: int = 0,
    context_token_budget: int = 0,
    max_no_progress: int = 3,
    max_pair_repeats: int = 2,
) -> dict[str, Any]:
    state = {
        "kind": STATE_KIND,
        "run_id": run_id,
        "revision": 0,
        "state_digest": "",
        "task_ref": copy.deepcopy(dict(task_ref)),
        "domain_snapshot_refs": [],
        "authoritative_reobservation_required": True,
        "decision_points": [],
        "action_candidates": [],
        "selected_action_ref": None,
        "operation_results": [],
        "evidence_refs": [],
        "claim_statuses": [],
        "terminal_disposition": {"status": "continue", "reason_ref": None, "recovery_action_ref": None},
        "budgets": {
            "execution_remaining": execution_budget,
            "semantic_remaining": semantic_budget,
            "context_tokens_remaining": context_token_budget,
        },
        "progress": {
            "no_progress_count": 0,
            "max_no_progress": max_no_progress,
            "max_pair_repeats": max_pair_repeats,
            "recent_state_action_pairs": [],
        },
    }
    return with_state_digest(state)


def _replace_by_identity(current: list[Any], additions: list[Any], identity: str) -> list[Any]:
    merged = {str(item[identity]): copy.deepcopy(item) for item in current}
    for item in additions:
        merged[str(item[identity])] = copy.deepcopy(item)
    return [merged[key] for key in sorted(merged)]


def _apply_observation(state: dict[str, Any], observation: Mapping[str, Any]) -> None:
    list_identities = {
        "domain_snapshot_refs": "domain_ref",
        "decision_points": "id",
        "action_candidates": "id",
        "operation_results": "id",
        "evidence_refs": "id",
        "claim_statuses": "claim_ref",
    }
    for field, identity in list_identities.items():
        if field in observation:
            additions = observation[field]
            if not isinstance(additions, list):
                raise TransitionRejected(f"observation.{field} must be a list")
            state[field] = _replace_by_identity(state[field], additions, identity)
    if "authoritative_reobservation" in observation:
        if observation["authoritative_reobservation"] is not True:
            raise TransitionRejected("authoritative_reobservation must be true when present")
        state["authoritative_reobservation_required"] = False
    if "terminal_disposition" in observation:
        state["terminal_disposition"] = copy.deepcopy(observation["terminal_disposition"])


def _apply_budget_delta(state: dict[str, Any], delta: Mapping[str, Any]) -> None:
    fields = {
        "execution": "execution_remaining",
        "semantic": "semantic_remaining",
        "context_tokens": "context_tokens_remaining",
    }
    for delta_field, state_field in fields.items():
        value = delta.get(delta_field)
        if not isinstance(value, int) or value > 0:
            raise TransitionRejected(f"budget_delta.{delta_field} must be a non-positive integer")
        remaining = int(state["budgets"][state_field]) + value
        if remaining < 0:
            raise TransitionRejected(f"budget_delta.{delta_field} exceeds remaining budget")
        state["budgets"][state_field] = remaining


def _apply_progress(state: dict[str, Any], *, before_digest: str, selected_action_ref: str | None, made_progress: bool) -> None:
    progress = state["progress"]
    pair = f"{before_digest}|{selected_action_ref or 'none'}"
    recent_pairs = [*progress["recent_state_action_pairs"], pair][-16:]
    progress["recent_state_action_pairs"] = recent_pairs
    progress["no_progress_count"] = 0 if made_progress else int(progress["no_progress_count"]) + 1
    pair_repeats = recent_pairs.count(pair)
    if progress["no_progress_count"] >= progress["max_no_progress"] or pair_repeats >= progress["max_pair_repeats"]:
        state["terminal_disposition"] = {
            "status": "blocked",
            "reason_ref": "structured-executor:no-progress-or-cycle",
            "recovery_action_ref": "structured-executor:authoritative-reobserve",
        }


def reduce_transition(state: Mapping[str, Any], transition_input: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate and reduce one transition without mutating either input."""

    if state.get("kind") != STATE_KIND:
        raise TransitionRejected("unsupported state kind")
    if transition_input.get("kind") != TRANSITION_INPUT_KIND:
        raise TransitionRejected("unsupported transition input kind")
    current_digest = state_digest(state)
    if state.get("state_digest") != current_digest:
        raise TransitionRejected("state digest is invalid")
    if transition_input.get("expected_revision") != state.get("revision"):
        raise TransitionRejected("stale state revision")
    if transition_input.get("expected_state_digest") != current_digest:
        raise TransitionRejected("stale state digest")

    next_state = copy.deepcopy(dict(state))
    selected_action_ref = transition_input.get("selected_action_ref")
    if selected_action_ref is not None:
        candidate_ids = {item["id"] for item in next_state["action_candidates"]}
        if selected_action_ref not in candidate_ids:
            raise TransitionRejected("selected action is not an admitted candidate")
        next_state["selected_action_ref"] = selected_action_ref

    result = transition_input.get("result")
    if result is not None:
        if not isinstance(result, Mapping) or not str(result.get("id") or ""):
            raise TransitionRejected("result must carry a stable id")
        next_state["operation_results"] = _replace_by_identity(next_state["operation_results"], [dict(result)], "id")
    observation = transition_input.get("observation") or {}
    if not isinstance(observation, Mapping):
        raise TransitionRejected("observation must be an object")
    _apply_observation(next_state, observation)
    _apply_budget_delta(next_state, transition_input.get("budget_delta") or {})
    _apply_progress(
        next_state,
        before_digest=current_digest,
        selected_action_ref=selected_action_ref,
        made_progress=transition_input.get("made_progress") is True,
    )
    next_state["revision"] = int(state["revision"]) + 1
    next_state = with_state_digest(next_state)

    record_without_id = {
        "kind": TRANSITION_KIND,
        "sequence": next_state["revision"],
        "before_revision": state["revision"],
        "before_digest": current_digest,
        "trigger_ref": copy.deepcopy(transition_input["trigger_ref"]),
        "validation": "accepted",
        "selected_action_ref": selected_action_ref,
        "result_ref": result.get("id") if isinstance(result, Mapping) else None,
        "after_revision": next_state["revision"],
        "after_digest": next_state["state_digest"],
        "classification": transition_input["classification"],
        "cost_observations": copy.deepcopy(transition_input["cost_observations"]),
    }
    record = {**record_without_id, "transition_id": semantic_digest(record_without_id)}
    return next_state, record
