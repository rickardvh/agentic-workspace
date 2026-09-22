"""Atomic local persistence for Structured Executor evaluation runs."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from kernel import TRANSITION_INPUT_KIND, canonical_json_bytes, reduce_transition, semantic_digest, state_digest

MARKER_NAME = ".aw-scratch.toml"
STATE_NAME = "state.json"
TRANSITIONS_NAME = "transitions.jsonl"
ARTIFACTS_NAME = "artifacts"
PENDING_NAME = "pending-commit.json"


class StoreError(ValueError):
    """Raised when persisted state cannot be admitted safely."""


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def initialize_run(run_root: Path, state: Mapping[str, Any]) -> None:
    if state.get("revision") != 0:
        raise StoreError("run initialization requires revision zero")
    run_root.mkdir(parents=True, exist_ok=True)
    marker = b'kind = "agentic-workspace/structured-executor-scratch/v1"\n'
    _atomic_write(run_root / MARKER_NAME, marker)
    (run_root / ARTIFACTS_NAME).mkdir(exist_ok=True)
    save_state(run_root, state)
    if not (run_root / TRANSITIONS_NAME).exists():
        _atomic_write(run_root / TRANSITIONS_NAME, b"")


def save_state(run_root: Path, state: Mapping[str, Any]) -> None:
    if state.get("state_digest") != state_digest(state):
        raise StoreError("refusing to persist state with an invalid digest")
    _atomic_write(run_root / STATE_NAME, canonical_json_bytes(state) + b"\n")


def load_state(run_root: Path) -> dict[str, Any]:
    try:
        state = json.loads((run_root / STATE_NAME).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError("state snapshot is missing or malformed") from exc
    if not isinstance(state, dict) or state.get("state_digest") != state_digest(state):
        raise StoreError("state snapshot digest is invalid")
    return state


def write_artifact(run_root: Path, payload: Mapping[str, Any]) -> dict[str, str]:
    encoded = canonical_json_bytes(payload)
    digest = semantic_digest(payload)
    artifact_path = run_root / ARTIFACTS_NAME / f"{digest.removeprefix('sha256:')}.json"
    if artifact_path.exists() and artifact_path.read_bytes() != encoded + b"\n":
        raise StoreError("content-addressed artifact collision")
    if not artifact_path.exists():
        _atomic_write(artifact_path, encoded + b"\n")
    return {"ref": f"artifact:{digest}", "digest": digest, "media_type": "application/json"}


def load_transitions(run_root: Path) -> list[dict[str, Any]]:
    path = run_root / TRANSITIONS_NAME
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StoreError(f"transition line {line_number} is malformed") from exc
        if not isinstance(record, dict):
            raise StoreError(f"transition line {line_number} is not an object")
        records.append(record)
    return records


def save_transitions(run_root: Path, transitions: Sequence[Mapping[str, Any]]) -> None:
    payload = b"".join(canonical_json_bytes(record) + b"\n" for record in transitions)
    _atomic_write(run_root / TRANSITIONS_NAME, payload)


def commit(run_root: Path, state: Mapping[str, Any], transition: Mapping[str, Any]) -> None:
    transitions = load_transitions(run_root)
    current_state = load_state(run_root)
    expected_sequence = len(transitions) + 1
    if transition.get("sequence") != expected_sequence:
        raise StoreError("transition sequence is not contiguous")
    if transitions and transitions[-1].get("after_digest") != transition.get("before_digest"):
        raise StoreError("transition lineage is not contiguous")
    if (
        transition.get("before_revision") != current_state.get("revision")
        or transition.get("before_digest") != current_state.get("state_digest")
    ):
        raise StoreError("transition does not extend the current state snapshot")
    if (
        transition.get("after_revision") != state.get("revision")
        or transition.get("after_digest") != state.get("state_digest")
    ):
        raise StoreError("transition does not describe the proposed state snapshot")
    pending = {"kind": "agentic-workspace/structured-executor-pending-commit/v1", "state": state, "transition": transition}
    _atomic_write(run_root / PENDING_NAME, canonical_json_bytes(pending) + b"\n")
    save_transitions(run_root, [*transitions, transition])
    save_state(run_root, state)
    (run_root / PENDING_NAME).unlink(missing_ok=True)


def recover(run_root: Path) -> bool:
    pending_path = run_root / PENDING_NAME
    if not pending_path.exists():
        return False
    try:
        pending = json.loads(pending_path.read_text(encoding="utf-8"))
        pending_state = pending["state"]
        pending_transition = pending["transition"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise StoreError("pending commit is malformed") from exc
    if pending.get("kind") != "agentic-workspace/structured-executor-pending-commit/v1":
        raise StoreError("pending commit kind is unsupported")
    transitions = load_transitions(run_root)
    sequence = pending_transition.get("sequence")
    if len(transitions) == sequence - 1:
        if transitions and transitions[-1].get("after_digest") != pending_transition.get("before_digest"):
            raise StoreError("pending transition does not extend current lineage")
        save_transitions(run_root, [*transitions, pending_transition])
    elif len(transitions) != sequence or transitions[-1] != pending_transition:
        raise StoreError("pending transition conflicts with current log")
    current_state = load_state(run_root)
    if current_state.get("state_digest") == pending_transition.get("before_digest"):
        save_state(run_root, pending_state)
    elif current_state != pending_state:
        raise StoreError("pending state conflicts with current snapshot")
    pending_path.unlink(missing_ok=True)
    return True


def restart(run_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    recover(run_root)
    state = load_state(run_root)
    trigger_payload = {"kind": "structured-executor/restart/v1", "run_id": state["run_id"], "revision": state["revision"]}
    trigger_ref = write_artifact(run_root, trigger_payload)
    transition_input = {
        "kind": TRANSITION_INPUT_KIND,
        "expected_revision": state["revision"],
        "expected_state_digest": state["state_digest"],
        "trigger_ref": trigger_ref,
        "classification": "deterministic",
        "selected_action_ref": None,
        "result": None,
        "observation": {"require_authoritative_reobservation": True},
        "made_progress": True,
        "budget_delta": {"execution": 0, "semantic": 0, "context_tokens": 0},
        "cost_observations": {"elapsed_ms": None, "effective_input_tokens": None, "output_tokens": None},
    }
    restarted_state, record = reduce_transition(state, transition_input)
    commit(run_root, restarted_state, record)
    return restarted_state, record
