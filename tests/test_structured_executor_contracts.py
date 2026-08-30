from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_ROOT = ROOT / "tools" / "model-cli-harness" / "structured-executor"


def _load_kernel() -> ModuleType:
    spec = importlib.util.spec_from_file_location("structured_executor_kernel", EXECUTOR_ROOT / "kernel.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _artifact(name: str) -> dict[str, str]:
    return {
        "ref": f"artifact:{name}",
        "digest": f"sha256:{'a' * 64}",
        "media_type": "application/json",
    }


def _transition_input(kernel: ModuleType, state: dict[str, object]) -> dict[str, object]:
    return {
        "kind": kernel.TRANSITION_INPUT_KIND,
        "expected_revision": state["revision"],
        "expected_state_digest": state["state_digest"],
        "trigger_ref": _artifact("trigger"),
        "classification": "deterministic",
        "selected_action_ref": None,
        "result": None,
        "observation": {"authoritative_reobservation": True},
        "made_progress": True,
        "budget_delta": {"execution": 0, "semantic": 0, "context_tokens": 0},
        "cost_observations": {"elapsed_ms": 0, "effective_input_tokens": None, "output_tokens": None},
    }


def test_representative_state_and_transition_validate() -> None:
    kernel = _load_kernel()
    state_schema = json.loads((EXECUTOR_ROOT / "contracts" / "state.schema.json").read_text(encoding="utf-8"))
    transition_schema = json.loads((EXECUTOR_ROOT / "contracts" / "transition.schema.json").read_text(encoding="utf-8"))
    state = kernel.initial_state(
        run_id="contract-test",
        task_ref=_artifact("task"),
        execution_budget=2,
        semantic_budget=1,
        context_token_budget=4096,
    )
    jsonschema.Draft202012Validator(state_schema).validate(state)
    transition_input = _transition_input(kernel, state)
    jsonschema.Draft202012Validator(transition_schema).validate(transition_input)
    next_state, record = kernel.reduce_transition(state, transition_input)
    jsonschema.Draft202012Validator(state_schema).validate(next_state)
    jsonschema.Draft202012Validator(transition_schema).validate(record)


def test_fixture_is_canonical_initial_state() -> None:
    kernel = _load_kernel()
    fixture = json.loads((EXECUTOR_ROOT / "fixtures" / "initial-state.json").read_text(encoding="utf-8"))
    expected = kernel.initial_state(
        run_id="fixture-run",
        task_ref=_artifact("task"),
        execution_budget=2,
        semantic_budget=1,
        context_token_budget=4096,
    )
    assert fixture == expected


def test_stale_revision_and_digest_reject_without_mutation() -> None:
    kernel = _load_kernel()
    state = kernel.initial_state(run_id="stale-test", task_ref=_artifact("task"))
    original = copy.deepcopy(state)
    stale_revision = _transition_input(kernel, state)
    stale_revision["expected_revision"] = 1
    with pytest.raises(kernel.TransitionRejected, match="stale state revision"):
        kernel.reduce_transition(state, stale_revision)
    stale_digest = _transition_input(kernel, state)
    stale_digest["expected_state_digest"] = f"sha256:{'f' * 64}"
    with pytest.raises(kernel.TransitionRejected, match="stale state digest"):
        kernel.reduce_transition(state, stale_digest)
    assert state == original


def test_reducer_is_deterministic_and_transition_identity_is_complete() -> None:
    kernel = _load_kernel()
    state = kernel.initial_state(run_id="determinism-test", task_ref=_artifact("task"))
    transition_input = _transition_input(kernel, state)
    first_state, first_record = kernel.reduce_transition(state, transition_input)
    second_state, second_record = kernel.reduce_transition(state, transition_input)
    assert kernel.canonical_json_bytes(first_state) == kernel.canonical_json_bytes(second_state)
    assert first_record == second_record
    assert first_record["before_digest"] == state["state_digest"]
    assert first_record["after_digest"] == first_state["state_digest"]
    assert first_record["transition_id"].startswith("sha256:")
