"""Atomic local persistence for Structured Executor evaluation runs."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from kernel import canonical_json_bytes, semantic_digest, state_digest

MARKER_NAME = ".aw-scratch.toml"
STATE_NAME = "state.json"
TRANSITIONS_NAME = "transitions.jsonl"
ARTIFACTS_NAME = "artifacts"


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
    expected_sequence = len(transitions) + 1
    if transition.get("sequence") != expected_sequence:
        raise StoreError("transition sequence is not contiguous")
    if transitions and transitions[-1].get("after_digest") != transition.get("before_digest"):
        raise StoreError("transition lineage is not contiguous")
    save_transitions(run_root, [*transitions, transition])
    save_state(run_root, state)
