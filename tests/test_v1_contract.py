from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from agentic_workspace.decision import compile_source_decision, select_decision_detail
from agentic_workspace.generated_semantics import KINDS, semantic_digest
from agentic_workspace.modules import (
    Module,
    admit_modules,
    discover_modules,
    module_contributions,
    register_module_operations,
)
from agentic_workspace.operations import (
    InterruptedOperationError,
    Operation,
    OperationContractError,
    OperationDispatcher,
    StaleInvocationError,
)


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
        Operation(
            "planning.complete", {"type": "object"}, ("planning-state",), lambda _: {"status": "applied", "effects": []}
        )
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
            "actions": [{"operation_id": "example.finish", "arguments": {}, "effects": ["external-state"]}]
            if state["pending"]
            else [],
            "terminal": not state["pending"],
        },
        operations=(
            Operation(
                "example.finish",
                {"type": "object", "additionalProperties": False},
                ("external-state",),
                lambda _: (
                    state.update(revision="ext2", pending=False) or {"status": "applied", "effects": ["external-state"]}
                ),
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


def test_capability_first_module_admission_resources_and_removal() -> None:
    resource = {"id": "guide", "revision": "g1", "locator": "docs/guide.md", "summary": "bounded context"}
    procedure = {"id": "review", "revision": "p1", "locator": "tools/review.md", "summary": "review procedure"}
    module = Module(
        name="example.read",
        api_version="1.0",
        owns=("example-domain",),
        resources=(resource,),
        procedures=(procedure,),
        contribute=lambda context: (
            {"revision": "one", "facts": {"selected": True}, "terminal": True} if context["task"] == "example" else None
        ),
    )

    decision = compile_source_decision(module_contributions([module], context={"task": "example"}))
    assert decision["resources"][0]["owner"] == "example.read"
    assert decision["procedures"][0]["authority"] == "reference-only"
    assert decision["status"] == "terminal"
    assert compile_source_decision(module_contributions([module], context={"task": "other"}))["status"] == "direct"
    assert compile_source_decision(module_contributions([], context={"task": "example"}))["status"] == "direct"


def test_module_compatibility_and_owned_domain_conflicts_fail_closed() -> None:
    def contribution(_: Mapping[str, Any]) -> dict[str, str]:
        return {"revision": "one"}

    with pytest.raises(ValueError, match="incompatible module API"):
        admit_modules([Module("future", contribution, api_version="2.0")])
    with pytest.raises(ValueError, match="owned domain conflict"):
        admit_modules(
            [
                Module("one", contribution, owns=("shared",)),
                Module("two", contribution, owns=("shared",)),
            ]
        )
    assert admit_modules([Module("additive", contribution, required_capabilities=("contribution/facts",))])
    with pytest.raises(ValueError, match="unsupported required module semantics.*upgrade agentic-workspace"):
        admit_modules([Module("future", contribution, required_capabilities=("future/required",))])


def test_interrupted_effect_is_recovered_without_blind_reexecution() -> None:
    state: dict[str, Any] = {"pending": True, "revision": "one", "calls": 0}
    journal: dict[str, Any] = {}

    def resolve() -> dict[str, Any]:
        return compile_source_decision(
            [
                {
                    "owner": "example",
                    "revision": state["revision"],
                    "actions": [{"operation_id": "example.apply", "arguments": {}, "effects": ["example-state"]}]
                    if state["pending"]
                    else [],
                    "terminal": not state["pending"],
                }
            ]
        )

    def apply(_: dict[str, Any]) -> dict[str, Any]:
        state.update(pending=False, revision="two", calls=state["calls"] + 1)
        return {"status": "applied", "effects": ["example-state"], "value": {"done": True}}

    writes = 0

    def interrupted_writer(_: str, value: dict[str, Any]) -> None:
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("fault after effect")
        journal.clear()
        journal.update(value)

    operation = Operation(
        "example.apply",
        {"type": "object", "additionalProperties": False},
        ("example-state",),
        apply,
        lambda _: (
            {"status": "applied", "effects": ["example-state"], "value": {"done": True}}
            if not state["pending"]
            else None
        ),
    )
    first = OperationDispatcher(journal_writer=interrupted_writer)
    first.register(operation)
    invocation = resolve()["primary_action"]
    with pytest.raises(OSError, match="fault after effect"):
        first.invoke(invocation, resolve_decision=resolve)

    replay = OperationDispatcher(journal_loader=lambda _: journal or None, journal_clearer=lambda _: journal.clear())
    replay.register(operation)
    result = replay.invoke(invocation, resolve_decision=resolve)
    assert result["next_decision"]["status"] == "terminal"
    assert state["calls"] == 1
    assert journal == {}


def test_interrupted_unrecoverable_effect_blocks_with_exact_owner_route() -> None:
    decision = compile_source_decision(
        [
            {
                "owner": "external",
                "revision": "one",
                "actions": [{"operation_id": "external.run", "arguments": {}, "effects": ["external"]}],
            }
        ]
    )
    invocation = decision["primary_action"]
    dispatcher = OperationDispatcher(
        journal_loader=lambda _: {
            "phase": "prepared",
            "request": {
                "operation_id": "external.run",
                "arguments": {},
                "revision": invocation["expected_input_revision"],
                "source_owner": "external",
                "decision_response": None,
            },
        }
    )
    dispatcher.register(Operation("external.run", {"type": "object"}, ("external",), lambda _: {}))
    with pytest.raises(InterruptedOperationError, match="recover through owner external"):
        dispatcher.invoke(invocation, resolve_decision=lambda: decision)


def test_bounded_decision_answer_is_current_and_admitted_by_its_owner() -> None:
    state = {"revision": "one", "answer": None}

    def resolve() -> dict[str, Any]:
        return compile_source_decision(
            [
                {
                    "owner": "configuration",
                    "revision": state["revision"],
                    "decisions": [
                        {
                            "id": "runner",
                            "question": "Which runner?",
                            "authority": "maintainer",
                            "response_operation_id": "configuration.answer",
                            "effects": ["configuration-state"],
                            "choices": [{"id": "local", "label": "Local"}],
                        }
                    ]
                    if state["answer"] is None
                    else [],
                    "facts": {"answer": state["answer"]},
                    "terminal": state["answer"] is not None,
                }
            ]
        )

    request = resolve()["decision_request"]
    response = {
        "id": request["id"],
        "owner": request["owner"],
        "revision": request["revision"],
        "authority": request["authority"],
        "answer": "local",
    }
    invocation = {
        "kind": KINDS["invocation"],
        "operation_id": "configuration.answer",
        "arguments": {"answer": "local"},
        "effects": ["configuration-state"],
        "expected_input_revision": resolve()["input_revision"],
        "source_owner": "configuration",
        "decision_response": response,
        "idempotency_key": semantic_digest({"response": response, "input_revision": resolve()["input_revision"]}),
    }
    operation = Operation(
        "configuration.answer",
        {
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
            "additionalProperties": False,
        },
        ("configuration-state",),
        lambda values: (
            state.update(revision="two", answer=values["answer"])
            or {"status": "applied", "effects": ["configuration-state"], "value": values}
        ),
    )
    dispatcher = OperationDispatcher()
    dispatcher.register(operation)
    result = dispatcher.invoke(invocation, resolve_decision=resolve)
    assert result["next_decision"]["status"] == "terminal"

    state.update(revision="three", answer=None)
    stale_dispatcher = OperationDispatcher()
    stale_dispatcher.register(operation)
    with pytest.raises(StaleInvocationError, match="source state changed"):
        stale_dispatcher.invoke(invocation, resolve_decision=resolve)
