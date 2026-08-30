from __future__ import annotations

import importlib
import socket
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


def _input(
    kernel: ModuleType,
    state: dict[str, object],
    *,
    action: str | None = None,
    observation: dict[str, object] | None = None,
    made_progress: bool = True,
) -> dict[str, object]:
    return {
        "kind": kernel.TRANSITION_INPUT_KIND,
        "expected_revision": state["revision"],
        "expected_state_digest": state["state_digest"],
        "trigger_ref": _artifact("trigger"),
        "classification": "deterministic",
        "selected_action_ref": action,
        "result": None,
        "observation": observation or {},
        "made_progress": made_progress,
        "budget_delta": {"execution": 0, "semantic": 0, "context_tokens": 0},
        "cost_observations": {"elapsed_ms": None, "effective_input_tokens": None, "output_tokens": None},
    }


def _observed_state(kernel: ModuleType, *, run_id: str = "safety") -> dict[str, object]:
    state = kernel.initial_state(run_id=run_id, task_ref=_artifact("task"), max_no_progress=2, max_pair_repeats=2)
    state, _ = kernel.reduce_transition(
        state,
        _input(
            kernel,
            state,
            observation={
                "authoritative_reobservation": True,
                "action_candidates": [
                    {
                        "id": "action:one",
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
        ),
    )
    return state


def _initialize_observed_run(kernel: ModuleType, store: ModuleType, run_root: Path, *, run_id: str) -> dict[str, object]:
    initial = kernel.initial_state(run_id=run_id, task_ref=_artifact("task"), max_no_progress=2, max_pair_repeats=2)
    store.initialize_run(run_root, initial)
    observed, record = kernel.reduce_transition(
        initial,
        _input(
            kernel,
            initial,
            observation={
                "authoritative_reobservation": True,
                "action_candidates": [
                    {
                        "id": "action:one",
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
        ),
    )
    store.commit(run_root, observed, record)
    return observed


def test_restart_is_committed_and_blocks_action_until_reobservation(
    modules: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path
) -> None:
    kernel, _, store = modules
    run_root = tmp_path / "run"
    state = _initialize_observed_run(kernel, store, run_root, run_id="restart")
    restarted, restart_record = store.restart(run_root)
    assert restarted["revision"] == state["revision"] + 1
    assert restarted["authoritative_reobservation_required"] is True
    assert restart_record["classification"] == "deterministic"
    with pytest.raises(kernel.TransitionRejected, match="re-observation is required"):
        kernel.reduce_transition(restarted, _input(kernel, restarted, action="action:one"))
    observed, _ = kernel.reduce_transition(
        restarted,
        _input(kernel, restarted, observation={"authoritative_reobservation": True}),
    )
    selected, _ = kernel.reduce_transition(observed, _input(kernel, observed, action="action:one"))
    assert selected["selected_action_ref"] == "action:one"


def test_pending_commit_recovers_interruption_after_log_write(
    modules: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kernel, _, store = modules
    run_root = tmp_path / "run"
    state = _initialize_observed_run(kernel, store, run_root, run_id="recovery")
    next_state, record = kernel.reduce_transition(state, _input(kernel, state, made_progress=True))
    real_save_state = store.save_state
    interrupted = {"raised": False}

    def fail_once(root: Path, payload: dict[str, object]) -> None:
        if payload.get("revision") == next_state["revision"] and not interrupted["raised"]:
            interrupted["raised"] = True
            raise OSError("simulated interruption")
        real_save_state(root, payload)

    monkeypatch.setattr(store, "save_state", fail_once)
    with pytest.raises(OSError, match="simulated interruption"):
        store.commit(run_root, next_state, record)
    assert (run_root / store.PENDING_NAME).exists()
    monkeypatch.setattr(store, "save_state", real_save_state)
    assert store.recover(run_root) is True
    assert store.load_state(run_root) == next_state
    recovered_transitions = store.load_transitions(run_root)
    assert len(recovered_transitions) == 2
    assert recovered_transitions[-1] == record
    assert not (run_root / store.PENDING_NAME).exists()


def test_store_rejects_noninitial_and_cross_lineage_snapshots(modules: tuple[ModuleType, ModuleType, ModuleType], tmp_path: Path) -> None:
    kernel, _, store = modules
    run_root = tmp_path / "run"
    initial = kernel.initial_state(run_id="lineage", task_ref=_artifact("task"))
    advanced, record = kernel.reduce_transition(initial, _input(kernel, initial))
    with pytest.raises(store.StoreError, match="revision zero"):
        store.initialize_run(run_root, advanced)
    store.initialize_run(run_root, initial)
    unrelated = kernel.initial_state(run_id="unrelated", task_ref=_artifact("task"))
    with pytest.raises(store.StoreError, match="proposed state snapshot"):
        store.commit(run_root, unrelated, record)


def test_unknown_action_is_rejected_without_mutating_input(modules: tuple[ModuleType, ModuleType, ModuleType]) -> None:
    kernel, _, _ = modules
    state = _observed_state(kernel, run_id="unknown-action")
    before = kernel.canonical_json_bytes(state)
    with pytest.raises(kernel.TransitionRejected, match="not an admitted candidate"):
        kernel.reduce_transition(state, _input(kernel, state, action="action:missing"))
    assert kernel.canonical_json_bytes(state) == before


def test_no_progress_and_repeated_pair_become_bounded_blocker(modules: tuple[ModuleType, ModuleType, ModuleType]) -> None:
    kernel, _, _ = modules
    state = _observed_state(kernel, run_id="cycle")
    first, _ = kernel.reduce_transition(state, _input(kernel, state, made_progress=False))
    second, _ = kernel.reduce_transition(first, _input(kernel, first, made_progress=False))
    assert second["terminal_disposition"] == {
        "status": "blocked",
        "reason_ref": "structured-executor:no-progress-or-cycle",
        "recovery_action_ref": "structured-executor:authoritative-reobserve",
    }


def test_replay_has_no_model_aw_network_subprocess_or_repository_side_effects(
    modules: tuple[ModuleType, ModuleType, ModuleType], monkeypatch: pytest.MonkeyPatch
) -> None:
    kernel, replay_module, _ = modules
    state = kernel.initial_state(run_id="isolated", task_ref=_artifact("task"))
    transition = _input(kernel, state, observation={"authoritative_reobservation": True})

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"external effect attempted: {args!r} {kwargs!r}")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    final_state, records = replay_module.replay(state, [transition])
    assert final_state["revision"] == 1
    assert len(records) == 1


def test_reducer_source_is_domain_neutral() -> None:
    source = (EXECUTOR_ROOT / "kernel.py").read_text(encoding="utf-8").lower()
    for forbidden in ("operating_decision", "planning", "memory", "verification"):
        assert forbidden not in source
