from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace.decision import compile_source_decision, select_decision_detail
from agentic_workspace.modules import Module, discover_modules, module_contributions, register_module_operations
from agentic_workspace.operating_decision import compile_operating_decision
from agentic_workspace.operations import (
    Operation,
    OperationContractError,
    OperationDispatcher,
    StaleInvocationError,
    UncertainOperationError,
)

ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_CONTRACT = json.loads((ROOT / "tests/vectors/capability_contract.json").read_text(encoding="utf-8"))
for owner in CAPABILITY_CONTRACT["owners"]:
    for operation in owner.get("operations", []):
        if operation["id"] in {"planning.complete", "example.finish"}:
            operation["input_schema"].setdefault("properties", {})["target"] = {"type": "string"}


def _planning(state: dict[str, Any]) -> dict[str, Any]:
    actions = []
    if state["status"] == "open":
        actions.append(
            {
                "dependency_revision": state["revision"],
                "operation_id": "planning.complete",
                "arguments": {"item": "ship-v1", **({"target": state["target"]} if "target" in state else {})},
                "effects": ["planning-state"],
            }
        )
    return {
        "owner": "planning",
        "revision": state["revision"],
        "facts": {"status": state["status"]},
        "actions": actions,
        "claims": {
            "allowed": ["planning-progress", "complete"] if state["status"] == "complete" else ["planning-progress"],
            "blocked": [] if state["status"] == "complete" else ["complete"],
        },
        "settled": state["status"] == "complete",
        "outcome": (
            {"id": "ship", "status": "complete", "claim": "complete", "evidence_revision": state["revision"]}
            if state["status"] == "complete"
            else None
        ),
    }


def _ship_intent() -> dict[str, Any]:
    return {"outcome": {"id": "ship", "owner": "planning", "claim": "complete"}}


def test_same_source_state_has_one_answer_across_views(shared_core_binary: object) -> None:
    decision = compile_source_decision(
        [_planning({"status": "open", "revision": "p1"})], intent=_ship_intent(), capability_contract=CAPABILITY_CONTRACT
    )
    cli = select_decision_detail(decision, ["status", "primary_action", "claim_boundary"])
    python = select_decision_detail(decision, ["primary_action", "status"])

    assert cli["decision_id"] == python["decision_id"] == decision["decision_id"]
    assert cli["input_revision"] == python["input_revision"] == decision["input_revision"]
    assert cli["values"]["status"] == python["values"]["status"] == "actionable"


def test_canonical_compiler_routes_source_contributions_without_consumer_semantics(shared_core_binary: object) -> None:
    contribution = _planning({"status": "open", "revision": "p1"})
    cli = compile_operating_decision(
        inputs={
            "consumer": "cli",
            "source_contributions": [contribution],
            "intent": _ship_intent(),
            "capability_contract": CAPABILITY_CONTRACT,
        }
    )
    python = compile_operating_decision(
        inputs={
            "consumer": "python",
            "source_contributions": [contribution],
            "intent": _ship_intent(),
            "capability_contract": CAPABILITY_CONTRACT,
        }
    )
    assert cli == python


def test_result_reconciles_to_the_next_decision_without_polling(shared_core_binary: object, tmp_path: Path) -> None:
    state = {"status": "open", "revision": "p1", "target": str(tmp_path)}
    calls = 0
    other = {"owner": "memory", "revision": "m1", "facts": {"advice": "old"}}

    def resolve() -> dict[str, Any]:
        return compile_source_decision([_planning(state), other], intent=_ship_intent(), capability_contract=CAPABILITY_CONTRACT)

    def complete(values: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert values == {"item": "ship-v1", "target": str(tmp_path)}
        state.update(status="complete", revision="p2")
        return {"status": "applied", "effects": ["planning-state"], "value": {"item": values["item"]}}

    dispatcher = OperationDispatcher()
    dispatcher.register(
        Operation(
            "planning.complete",
            {
                "type": "object",
                "properties": {"item": {"type": "string", "minLength": 1}, "target": {"type": "string"}},
                "required": ["item"],
                "additionalProperties": False,
            },
            ("planning-state",),
            complete,
        )
    )
    invocation = resolve()["primary_action"]
    result = dispatcher.invoke(invocation, resolve_decision=resolve)

    assert result["status"] == "applied"
    assert result["next_decision"]["status"] == "terminal"
    assert result["next_decision"]["claim_boundary"] == {"allowed": ["complete", "planning-progress"], "blocked": []}
    assert dispatcher.invoke(invocation, resolve_decision=resolve) == result
    other.update(revision="m2", facts={"advice": "new"})
    replay = dispatcher.invoke(invocation, resolve_decision=resolve)
    assert replay["next_decision"] == resolve()
    assert replay["next_decision"] != result["next_decision"]
    assert {k: v for k, v in replay.items() if k != "next_decision"} == {k: v for k, v in result.items() if k != "next_decision"}
    # A caller cannot mutate the retained effect value through the returned result.
    result["value"]["item"] = "tampered"
    assert dispatcher.invoke(invocation, resolve_decision=resolve)["value"] == {"item": "ship-v1"}
    assert calls == 1

    with pytest.raises(OperationContractError, match="idempotency key was already used"):
        dispatcher.invoke(
            {**invocation, "arguments": {"item": "different", "target": str(tmp_path)}},
            resolve_decision=resolve,
        )
    with pytest.raises(OperationContractError, match="idempotency key was already used"):
        dispatcher.invoke(
            {**invocation, "expected_dependency_revision": "sha256:different"},
            resolve_decision=resolve,
        )


@pytest.mark.parametrize(("crash", "concurrent"), [(False, False), (True, False), (False, True)])
def test_dispatcher_restart_never_forgets_effect_admission(
    shared_core_binary: object, tmp_path: Path, crash: bool, concurrent: bool
) -> None:
    decision = compile_source_decision(
        [_planning({"status": "open", "revision": "p1", "target": str(tmp_path)})], capability_contract=CAPABILITY_CONTRACT
    )
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"decision": decision}))
    program = """
import json, os, sys
from pathlib import Path
from agentic_workspace.operations import Operation, OperationDispatcher
data = json.loads(Path(sys.argv[1]).read_text())
decision = data['decision']
def effect(values):
    marker = Path(values['target']) / 'external-effect'
    with marker.open('a') as stream:
        stream.write('x')
    if sys.argv[2] == 'crash':
        os._exit(9)
    return {'status': 'applied', 'effects': ['planning-state'], 'value': 1}
dispatcher = OperationDispatcher()
dispatcher.register(Operation('planning.complete', {'type': 'object'}, ('planning-state',), effect))
print(json.dumps(dispatcher.invoke(decision['primary_action'], resolve_decision=lambda: decision, custody=data.get('custody'))))
"""
    command = [sys.executable, "-c", program, str(request), "crash" if crash else "complete"]
    if concurrent:
        workers = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        completed = [(worker, worker.communicate(timeout=30)) for worker in workers]
        assert sorted(worker.returncode for worker in workers) == [0, 1]
        worker, (stdout, stderr) = next(item for item in completed if item[0].returncode == 0)
        first = subprocess.CompletedProcess(command, worker.returncode, stdout, stderr)
    else:
        first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode == (9 if crash else 0), first.stderr
    second = subprocess.run([sys.executable, "-c", program, str(request), "complete"], capture_output=True, text=True)
    assert second.returncode != 0
    assert "preserved" in second.stderr
    marker = tmp_path / "external-effect"
    assert marker.read_text() == "x"
    if not crash:
        result = json.loads(first.stdout)
        request.write_text(json.dumps({"decision": decision, "custody": result["custody"]}))
        replay = subprocess.run([sys.executable, "-c", program, str(request), "complete"], capture_output=True, text=True)
        assert replay.returncode == 0, replay.stderr
        assert json.loads(replay.stdout) == result
        assert marker.read_text() == "x"


def test_read_only_dispatch_has_no_durable_ceremony(shared_core_binary: object, tmp_path: Path) -> None:
    contract = deepcopy(CAPABILITY_CONTRACT)
    for owner in contract["owners"]:
        for operation in owner.get("operations", []):
            if operation["id"] == "planning.complete":
                operation["effects"] = []
    contribution = _planning({"status": "open", "revision": "p1", "target": str(tmp_path)})
    contribution["actions"][0]["effects"] = []
    decision = compile_source_decision([contribution], capability_contract=contract)
    dispatcher = OperationDispatcher()
    dispatcher.register(
        Operation("planning.complete", {"type": "object"}, (), lambda _: {"status": "unchanged", "effects": [], "value": 1})
    )
    result = dispatcher.invoke(decision["primary_action"], resolve_decision=lambda: decision)
    assert result["value"] == 1
    assert "custody" not in result
    assert list(tmp_path.iterdir()) == []


def test_stale_and_invalid_invocations_fail_closed(shared_core_binary: object, tmp_path: Path) -> None:
    state = {"status": "open", "revision": "p1", "target": str(tmp_path)}
    dispatcher = OperationDispatcher()
    dispatcher.register(
        Operation("planning.complete", {"type": "object"}, ("planning-state",), lambda _: {"status": "applied", "effects": []})
    )
    decision = compile_source_decision([_planning(state)], capability_contract=CAPABILITY_CONTRACT)
    stale = {**decision["primary_action"], "expected_dependency_revision": "sha256:stale"}

    with pytest.raises(StaleInvocationError):
        dispatcher.invoke(stale, resolve_decision=lambda: decision)
    with pytest.raises(OperationContractError):
        dispatcher.invoke({**decision["primary_action"], "effects": []}, resolve_decision=lambda: decision)


def test_effectful_callback_without_owner_target_is_not_invoked(shared_core_binary: object) -> None:
    decision = compile_source_decision([_planning({"status": "open", "revision": "p1"})], capability_contract=CAPABILITY_CONTRACT)
    calls = []
    dispatcher = OperationDispatcher()
    dispatcher.register(Operation("planning.complete", {"type": "object"}, ("planning-state",), lambda values: calls.append(values) or {}))
    with pytest.raises(StaleInvocationError, match="owner-derived target"):
        dispatcher.invoke(decision["primary_action"], resolve_decision=lambda: decision)
    assert calls == []


@dataclass
class _EntryPoint:
    name: str
    value: Module

    def load(self) -> Module:
        return self.value


def test_out_of_tree_module_uses_the_generic_contribution_and_operation_seam(shared_core_binary: object, tmp_path: Path) -> None:
    state = {"revision": "ext1", "pending": True}
    external = Module(
        name="example.external",
        contribute=lambda context: {
            "revision": state["revision"],
            "relevant": context["task"] == "external",
            "actions": [
                {
                    "dependency_revision": state["revision"],
                    "operation_id": "example.finish",
                    "arguments": {"target": str(tmp_path)},
                    "effects": ["external-state"],
                }
            ]
            if state["pending"]
            else [],
            "settled": not state["pending"],
            "claims": {"allowed": ["external-complete"] if not state["pending"] else []},
            "outcome": (
                {"id": "external", "status": "complete", "claim": "external-complete", "evidence_revision": state["revision"]}
                if not state["pending"]
                else None
            ),
        },
        operations=(
            Operation(
                "example.finish",
                {"type": "object", "properties": {"target": {"type": "string"}}, "additionalProperties": False},
                ("external-state",),
                lambda _: state.update(revision="ext2", pending=False) or {"status": "applied", "effects": ["external-state"]},
            ),
        ),
    )
    modules = discover_modules(entry_points=[_EntryPoint("external", external)])
    dispatcher = OperationDispatcher()
    register_module_operations(dispatcher, modules)

    def resolve() -> dict[str, Any]:
        context = {"task": "external"}
        intent = {"outcome": {"id": "external", "owner": "example.external", "claim": "external-complete"}}
        return compile_source_decision(
            module_contributions(modules, context=context), intent=intent, capability_contract=CAPABILITY_CONTRACT
        )

    first = resolve()
    result = dispatcher.invoke(first["primary_action"], resolve_decision=resolve)
    assert dispatcher.operation_ids == ("example.finish",)
    assert result["next_decision"]["status"] == "terminal"
    assert result["custody"]["attempt"]["owner"] == "example.external"
    assert (tmp_path / result["custody"]["committed"]["path"]).is_file()


def test_irrelevant_modules_are_absent_from_the_decision(shared_core_binary: object) -> None:
    module = Module(
        name="example.external",
        contribute=lambda context: None if context["task"] != "external" else {"revision": "one"},
    )
    contributions = module_contributions([module], context={"task": "direct"})
    assert compile_source_decision(contributions)["relevant_owners"] == []


def test_dependency_change_is_rejected_before_effect_and_repeat_is_owner_authorized(shared_core_binary: object, tmp_path: Path) -> None:
    state = {"status": "open", "revision": "proof-1", "target": str(tmp_path)}
    advice = "advice-1"
    generation = ""
    calls = 0

    def resolve() -> dict[str, Any]:
        contribution = _planning(state)
        contribution["revision"] = advice
        contribution["actions"][0]["effect_generation"] = generation
        return compile_source_decision([contribution], capability_contract=CAPABILITY_CONTRACT)

    def effect(_: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"status": "applied", "effects": ["planning-state"]}

    dispatcher = OperationDispatcher()
    dispatcher.register(Operation("planning.complete", {"type": "object"}, ("planning-state",), effect))
    first = resolve()["primary_action"]
    state["revision"] = "proof-2"
    with pytest.raises(StaleInvocationError):
        dispatcher.invoke(first, resolve_decision=resolve)
    assert calls == 0
    current = resolve()["primary_action"]
    advice = "advice-2"
    dispatcher.invoke(current, resolve_decision=resolve)
    assert calls == 1
    advice = "advice-3"
    dispatcher.invoke(resolve()["primary_action"], resolve_decision=resolve)
    assert calls == 1
    state["revision"] = "proof-3"
    dispatcher.invoke(resolve()["primary_action"], resolve_decision=resolve)
    assert calls == 1
    generation = "owner-authorized-repeat-2"
    dispatcher.invoke(resolve()["primary_action"], resolve_decision=resolve)
    assert calls == 2


def test_committed_effect_survives_unavailable_post_effect_view(shared_core_binary: object, tmp_path: Path) -> None:
    state = {"status": "open", "revision": "p1", "target": str(tmp_path)}
    calls = 0
    fail_resolution = False

    def resolve() -> dict[str, Any]:
        if fail_resolution:
            raise RuntimeError("source currently unavailable")
        return compile_source_decision([_planning(state)], capability_contract=CAPABILITY_CONTRACT)

    def effect(_: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls, fail_resolution
        calls += 1
        state.update(status="complete", revision="p2")
        fail_resolution = True
        return {"status": "applied", "effects": ["planning-state"], "value": {"committed": True}}

    dispatcher = OperationDispatcher()
    dispatcher.register(Operation("planning.complete", {"type": "object"}, ("planning-state",), effect))
    invocation = resolve()["primary_action"]
    result = dispatcher.invoke(invocation, resolve_decision=resolve)
    assert result["status"] == "applied"
    assert result["continuation_status"] == "unavailable"
    assert result["next_decision"] is None
    with pytest.raises(OperationContractError, match="current operation semantics"):
        dispatcher.invoke(invocation, resolve_decision=resolve)
    assert calls == 1
    fail_resolution = False
    replay = dispatcher.invoke(invocation, resolve_decision=resolve)
    assert replay["value"] == result["value"]
    assert replay["continuation_status"] == "current"
    assert replay["next_decision"] == resolve()
    assert calls == 1


def test_failed_effect_attempt_cannot_be_blindly_retried(shared_core_binary: object, tmp_path: Path) -> None:
    decision = compile_source_decision(
        [_planning({"status": "open", "revision": "p1", "target": str(tmp_path)})], capability_contract=CAPABILITY_CONTRACT
    )
    calls = 0

    def effect(_: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise RuntimeError("process may already have effected")

    dispatcher = OperationDispatcher()
    dispatcher.register(Operation("planning.complete", {"type": "object"}, ("planning-state",), effect))
    for _ in range(2):
        with pytest.raises(UncertainOperationError) as failure:
            dispatcher.invoke(decision["primary_action"], resolve_decision=lambda: decision)
        assert failure.value.admission["disposition"] == "uncertain"
        assert failure.value.admission["owner"] == "planning"
        assert failure.value.admission["effects"] == ["planning-state"]
    assert calls == 1
