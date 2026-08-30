"""Deterministic replay for Structured Executor transition inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from kernel import reduce_transition


def replay(
    initial_state: Mapping[str, Any], transition_inputs: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    state = dict(initial_state)
    records: list[dict[str, Any]] = []
    for transition_input in transition_inputs:
        state, record = reduce_transition(state, transition_input)
        records.append(record)
    return state, records


def verify_replay(
    initial_state: Mapping[str, Any],
    transition_inputs: Sequence[Mapping[str, Any]],
    expected_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    state, records = replay(initial_state, transition_inputs)
    if records != list(expected_records):
        raise ValueError("replayed transition identities differ from the recorded sequence")
    return state
