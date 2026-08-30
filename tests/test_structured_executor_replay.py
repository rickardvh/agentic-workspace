from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_ROOT = ROOT / "tools" / "model-cli-harness" / "structured-executor"


@pytest.fixture
def modules() -> tuple[ModuleType, ModuleType, ModuleType]:
    sys.path.insert(0, str(EXECUTOR_ROOT))
    try:
        return (
            importlib.import_module("kernel"),
            importlib.import_module("replay"),
            importlib.import_module("store"),
        )
    finally:
        sys.path.remove(str(EXECUTOR_ROOT))


def _artifact(name: str) -> dict[str, str]:
    return {"ref": f"artifact:{name}", "digest": f"sha256:{'a' * 64}", "media_type": "application/json"}


def _inputs(kernel: ModuleType, state: dict[str, object]) -> list[dict[str, object]]:
    first = {
        "kind": kernel.TRANSITION_INPUT_KIND,
        "expected_revision": state["revision"],
        "expected_state_digest": state["state_digest"],
        "trigger_ref": _artifact("observation"),
        "classification": "deterministic",
        "selected_action_ref": None,
        "result": None,
        "observation": {
            "authoritative_reobservation": True,
            "action_candidates": [
                {
                    "id": "action:inspect",
                    "owner_ref": "domain:fixture",
                    "action_kind": "inspect",
                    "capability_ref": "capability:read",
                    "required_input_refs": [],
                    "effects": ["read"],
                    "precondition_refs": [],
                    "expected_result_kind": "observation",
                    "source_revision": "fixture:1",
                    "selection_kind": "deterministic",
                }
            ],
        },
        "made_progress": True,
        "budget_delta": {"execution": 0, "semantic": 0, "context_tokens": 0},
        "cost_observations": {"elapsed_ms": 0, "effective_input_tokens": None, "output_tokens": None},
    }
    after_first, _ = kernel.reduce_transition(state, first)
    second = {
        "kind": kernel.TRANSITION_INPUT_KIND,
        "expected_revision": after_first["revision"],
        "expected_state_digest": after_first["state_digest"],
        "trigger_ref": _artifact("selection"),
        "classification": "deterministic",
        "selected_action_ref": "action:inspect",
        "result": {
            "id": "result:inspect",
            "kind": "observation",
            "status": "succeeded",
            "artifact_ref": _artifact("result"),
            "source_revision": "fixture:1",
        },
        "observation": {},
        "made_progress": True,
        "budget_delta": {"execution": -1, "semantic": 0, "context_tokens": 0},
        "cost_observations": {"elapsed_ms": 1, "effective_input_tokens": None, "output_tokens": None},
    }
    return [first, second]


def test_replay_is_byte_stable_and_record_verification_fails_closed(modules: tuple[ModuleType, ModuleType, ModuleType]) -> None:
    kernel, replay_module, _ = modules
    state = kernel.initial_state(run_id="replay", task_ref=_artifact("task"), execution_budget=2)
    inputs = _inputs(kernel, state)
    first_state, first_records = replay_module.replay(state, inputs)
    second_state, second_records = replay_module.replay(state, inputs)
    assert kernel.canonical_json_bytes(first_state) == kernel.canonical_json_bytes(second_state)
    assert first_records == second_records
    assert first_state["state_digest"] == "sha256:9e1d8041e38620b1cb773101c0a0335cfeddd00db32a29e31f8dc8e2886daf93"
    assert [record["transition_id"] for record in first_records] == [
        "sha256:b23d7b697ae0f7706f61e4baa62a9938c5ed87cc5b7cd88bc68e60fd06a77c91",
        "sha256:20208a039b7f907c76887f7f3cdd26e6e45e5c776dcde1af5d709590469e8a96",
    ]
    assert replay_module.verify_replay(state, inputs, first_records) == first_state
    changed = [dict(first_records[0]), dict(first_records[1])]
    changed[1]["transition_id"] = f"sha256:{'f' * 64}"
    with pytest.raises(ValueError, match="identities differ"):
        replay_module.verify_replay(state, inputs, changed)


def test_store_writes_atomic_snapshot_artifacts_and_contiguous_log(
    modules: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path
) -> None:
    kernel, replay_module, store = modules
    state = kernel.initial_state(run_id="store", task_ref=_artifact("task"), execution_budget=2)
    run_root = tmp_path / "run"
    store.initialize_run(run_root, state)
    artifact_ref = store.write_artifact(run_root, {"bounded": "payload"})
    assert artifact_ref["digest"].startswith("sha256:")
    final_state, records = replay_module.replay(state, _inputs(kernel, state))
    intermediate_state, _ = kernel.reduce_transition(state, _inputs(kernel, state)[0])
    store.commit(run_root, intermediate_state, records[0])
    store.commit(run_root, final_state, records[1])
    assert store.load_state(run_root) == final_state
    assert store.load_transitions(run_root) == records
    assert not list(run_root.rglob("*.tmp"))


def test_malformed_or_noncontiguous_persistence_fails_closed(modules: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path) -> None:
    kernel, replay_module, store = modules
    state = kernel.initial_state(run_id="fail-closed", task_ref=_artifact("task"), execution_budget=2)
    run_root = tmp_path / "run"
    store.initialize_run(run_root, state)
    final_state, records = replay_module.replay(state, _inputs(kernel, state))
    bad = dict(records[0])
    bad["sequence"] = 2
    with pytest.raises(store.StoreError, match="not contiguous"):
        store.commit(run_root, final_state, bad)
    (run_root / store.STATE_NAME).write_text("{partial", encoding="utf-8")
    with pytest.raises(store.StoreError, match="missing or malformed"):
        store.load_state(run_root)


def test_maintainer_cli_validates_and_replays_fixture(tmp_path: Path, modules: tuple[ModuleType, ModuleType, ModuleType]) -> None:
    kernel, _, _ = modules
    state = kernel.initial_state(run_id="cli", task_ref=_artifact("task"), execution_budget=2)
    state_path = tmp_path / "state.json"
    inputs_path = tmp_path / "inputs.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    inputs_path.write_text(json.dumps(_inputs(kernel, state)), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(EXECUTOR_ROOT / "structured_executor.py"),
            "replay",
            "--initial-state",
            str(state_path),
            "--transitions",
            str(inputs_path),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["final_state"]["revision"] == 2
    assert len(payload["transitions"]) == 2
