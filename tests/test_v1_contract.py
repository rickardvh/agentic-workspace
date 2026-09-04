from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from agentic_workspace.decision import compile_source_decision, select_decision_detail
from agentic_workspace.modules import Module, discover_modules, module_contributions, register_module_operations
from agentic_workspace.operating_decision import compile_operating_decision
from agentic_workspace.operations import Operation, OperationContractError, OperationDispatcher, StaleInvocationError


def _planning(state: dict[str, Any]) -> dict[str, Any]:
    actions = []
    if state["status"] == "open":
        actions.append(
            {
                "operation_id": "planning.complete",
                "arguments": {"item": "ship-v1"},
                "effects": ["planning-state"],
                "priority": 10,
            }
        )
    return {
        "owner": "planning",
        "revision": state["revision"],
        "facts": {"status": state["status"]},
        "actions": actions,
        "claims": {"allowed": ["progress"], "blocked": [] if state["status"] == "complete" else ["complete"]},
        "terminal": state["status"] == "complete",
    }


def test_same_source_state_has_one_answer_across_views() -> None:
    decision = compile_source_decision([_planning({"status": "open", "revision": "p1"})], intent={"task": "ship"})
    cli = select_decision_detail(decision, ["status", "primary_action", "claim_boundary"])
    python = select_decision_detail(decision, ["primary_action", "status"])

    assert cli["decision_id"] == python["decision_id"] == decision["decision_id"]
    assert cli["input_revision"] == python["input_revision"] == decision["input_revision"]
    assert cli["values"]["status"] == python["values"]["status"] == "actionable"


def test_canonical_compiler_routes_source_contributions_without_consumer_semantics() -> None:
    contribution = _planning({"status": "open", "revision": "p1"})
    cli = compile_operating_decision(inputs={"consumer": "cli", "task": "ship", "source_contributions": [contribution]})
    python = compile_operating_decision(inputs={"consumer": "python", "task": "ship", "source_contributions": [contribution]})
    assert cli == python


def test_result_reconciles_to_the_next_decision_without_polling() -> None:
    state = {"status": "open", "revision": "p1"}
    calls = 0

    def resolve() -> dict[str, Any]:
        return compile_source_decision([_planning(state)], intent={"task": "ship"})

    def complete(values: dict[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert values == {"item": "ship-v1"}
        state.update(status="complete", revision="p2")
        return {"status": "applied", "effects": ["planning-state"], "value": {"item": values["item"]}}

    dispatcher = OperationDispatcher()
    dispatcher.register(
        Operation(
            "planning.complete",
            {
                "type": "object",
                "properties": {"item": {"type": "string", "minLength": 1}},
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
    assert result["next_decision"]["claim_boundary"] == {"allowed": ["progress"], "blocked": []}
    assert dispatcher.invoke(invocation, resolve_decision=resolve) == result
    assert calls == 1

    with pytest.raises(OperationContractError, match="idempotency key was already used"):
        dispatcher.invoke(
            {**invocation, "arguments": {"item": "different"}},
            resolve_decision=resolve,
        )
    with pytest.raises(OperationContractError, match="idempotency key was already used"):
        dispatcher.invoke(
            {**invocation, "expected_input_revision": "sha256:different"},
            resolve_decision=resolve,
        )


def test_stale_and_invalid_invocations_fail_closed() -> None:
    state = {"status": "open", "revision": "p1"}
    dispatcher = OperationDispatcher()
    dispatcher.register(
        Operation("planning.complete", {"type": "object"}, ("planning-state",), lambda _: {"status": "applied", "effects": []})
    )
    decision = compile_source_decision([_planning(state)])
    stale = {**decision["primary_action"], "expected_input_revision": "sha256:stale"}

    with pytest.raises(StaleInvocationError):
        dispatcher.invoke(stale, resolve_decision=lambda: decision)
    with pytest.raises(OperationContractError):
        dispatcher.invoke({**decision["primary_action"], "effects": []}, resolve_decision=lambda: decision)


@dataclass
class _EntryPoint:
    name: str
    value: Module

    def load(self) -> Module:
        return self.value


def test_out_of_tree_module_uses_the_generic_contribution_and_operation_seam() -> None:
    state = {"revision": "ext1", "pending": True}
    external = Module(
        name="example.external",
        contribute=lambda context: {
            "revision": state["revision"],
            "relevant": context["task"] == "external",
            "actions": [{"operation_id": "example.finish", "arguments": {}, "effects": ["external-state"]}] if state["pending"] else [],
            "terminal": not state["pending"],
        },
        operations=(
            Operation(
                "example.finish",
                {"type": "object", "additionalProperties": False},
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
        return compile_source_decision(module_contributions(modules, context=context), intent=context)

    first = resolve()
    result = dispatcher.invoke(first["primary_action"], resolve_decision=resolve)
    assert dispatcher.operation_ids == ("example.finish",)
    assert result["next_decision"]["status"] == "terminal"


def test_irrelevant_modules_are_absent_from_the_decision() -> None:
    module = Module(
        name="example.external",
        contribute=lambda context: None if context["task"] != "external" else {"revision": "one"},
    )
    contributions = module_contributions([module], context={"task": "direct"})
    assert compile_source_decision(contributions, intent={"task": "direct"})["relevant_owners"] == []
