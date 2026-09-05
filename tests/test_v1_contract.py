from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
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
            }
        )
    contribution = {
        "owner": "planning",
        "revision": state["revision"],
        "facts": {"status": state["status"]},
        "actions": actions,
        "claims": {"allowed": ["progress", "complete"], "blocked": [] if state["status"] == "complete" else ["complete"]},
        "settled": state["status"] == "complete",
    }
    if state["status"] == "complete":
        contribution["outcome"] = {
            "id": "ship-v1",
            "status": "complete",
            "claim": "complete",
            "evidence_revision": state["revision"],
        }
    return contribution


def _ship_intent() -> dict[str, Any]:
    return {"task": "ship", "outcome": {"id": "ship-v1", "owner": "planning", "claim": "complete"}}


def test_same_source_state_has_one_answer_across_views() -> None:
    decision = compile_source_decision([_planning({"status": "open", "revision": "p1"})], intent=_ship_intent())
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
        return compile_source_decision([_planning(state)], intent=_ship_intent())

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
    assert result["next_decision"]["claim_boundary"] == {"allowed": ["complete", "progress"], "blocked": []}
    assert result["next_decision"]["terminal_authority"]["owner"] == "planning"
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
            "claims": {"allowed": ["external-complete"] if not state["pending"] else []},
            "settled": not state["pending"],
            **(
                {
                    "outcome": {
                        "id": "external",
                        "status": "complete",
                        "claim": "external-complete",
                        "evidence_revision": state["revision"],
                    }
                }
                if not state["pending"]
                else {}
            ),
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
        context = {"task": "external", "outcome": {"id": "external", "owner": "example.external", "claim": "external-complete"}}
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


@pytest.mark.parametrize("owner", ["memory", "repository", "workspace", "assignment", "verification", "planning"])
def test_owner_local_quiescence_does_not_terminalize_the_task(owner: str) -> None:
    contribution = {
        "owner": owner,
        "revision": "one",
        "settled": True,
        "facts": {"selected": True},
        "claims": {"allowed": ["complete"] if owner == "verification" else []},
    }
    decision = compile_source_decision([contribution], intent={"task": "implement"})

    assert decision["status"] == "direct"
    assert decision["terminal_authority"] is None
    assert decision["owner_states"] == [{"owner": owner, "settled": True}]


def test_explicit_outcome_authority_must_be_current_claim_safe_and_without_residual_work() -> None:
    complete = _planning({"status": "complete", "revision": "p2"})
    assert compile_source_decision([complete], intent=_ship_intent())["status"] == "terminal"

    stale = {**complete, "outcome": {**complete["outcome"], "evidence_revision": "p1"}}
    assert compile_source_decision([stale], intent=_ship_intent())["status"] == "direct"

    residual = {**complete, "outcome": {**complete["outcome"], "residual_work": ["publish"]}}
    assert compile_source_decision([residual], intent=_ship_intent())["status"] == "direct"

    blocked = {**complete, "claims": {"allowed": ["complete"], "blocked": ["complete"]}}
    assert compile_source_decision([blocked], intent=_ship_intent())["status"] == "direct"


def test_legacy_terminal_and_self_ranked_actions_fail_closed() -> None:
    with pytest.raises(ValueError, match="terminal is obsolete"):
        compile_source_decision([{"owner": "memory", "revision": "one", "terminal": True}])
    with pytest.raises(ValueError, match="priority is obsolete"):
        compile_source_decision(
            [
                {
                    "owner": "module",
                    "revision": "one",
                    "actions": [{"operation_id": "module.act", "priority": 1}],
                }
            ]
        )


def test_multiple_actions_preserve_exact_alternatives_without_priority_choreography() -> None:
    contributions = [
        {"owner": owner, "revision": "one", "actions": [{"operation_id": operation, "arguments": {"owner": owner}}]}
        for owner, operation in (("zeta", "zeta.act"), ("alpha", "alpha.act"))
    ]
    decision = compile_source_decision(reversed(contributions))

    assert decision["status"] == "blocked"
    assert [item["source_owner"] for item in decision["blockers"][0]["alternatives"]] == ["alpha", "zeta"]


def test_python_and_typescript_project_the_same_terminality_semantics() -> None:
    payload = {"contributions": [_planning({"status": "complete", "revision": "p2"})], "intent": _ship_intent()}
    script = (
        'import { compileSourceDecision } from "./generated/workspace/typescript/src/semanticDecision.mjs";'
        'let text=""; for await (const chunk of process.stdin) text += chunk;'
        "process.stdout.write(JSON.stringify(compileSourceDecision(JSON.parse(text).contributions, JSON.parse(text).intent)));"
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=Path(__file__).resolve().parents[1],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )

    assert json.loads(completed.stdout) == compile_source_decision(payload["contributions"], intent=payload["intent"])


def test_source_decision_projections_are_current() -> None:
    completed = subprocess.run(
        [
            "uv",
            "run",
            "--frozen",
            "--active",
            "--no-sync",
            "python",
            "scripts/generate/generate_source_decision.py",
            "--check",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_portable_program_change_alters_both_executable_projections(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "source"
    contract = source / "src/agentic_workspace/contracts/source_decision_ir.json"
    contract.parent.mkdir(parents=True)
    authority = json.loads((root / "src/agentic_workspace/contracts/source_decision_ir.json").read_text(encoding="utf-8"))
    program = authority["executable_authority"]["compile_source_decision"]
    authority["executable_authority"]["compile_source_decision"] = json.loads(json.dumps(program).replace('"direct"', '"waiting"'))
    contract.write_text(json.dumps(authority), encoding="utf-8")
    output = tmp_path / "output"
    subprocess.run(
        [
            "uv",
            "run",
            "--frozen",
            "--active",
            "--no-sync",
            "python",
            "scripts/generate/generate_source_decision.py",
            "--root",
            str(source),
            "--output-root",
            str(output),
        ],
        cwd=root,
        check=True,
    )

    python_result = subprocess.run(
        [
            "uv",
            "run",
            "--frozen",
            "--active",
            "--no-sync",
            "python",
            "-c",
            (
                "import importlib.util; "
                f"spec=importlib.util.spec_from_file_location('projected_decision', {str(output / 'generated/workspace/python/semantic_decision.py')!r}); "
                "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
                "print(module.compile_source_decision([])['status'])"
            ),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    module = (output / "generated/workspace/typescript/src/semanticDecision.mjs").as_uri()
    typescript_result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            f'import {{ compileSourceDecision }} from "{module}"; console.log(compileSourceDecision([]).status);',
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert python_result.stdout.strip() == typescript_result.stdout.strip() == "waiting"


def test_generator_contains_only_portable_engine_not_reducer_policy() -> None:
    generator = (Path(__file__).resolve().parents[1] / "scripts/generate/generate_source_decision.py").read_text(encoding="utf-8")

    assert "multiple current actions require" not in generator
    assert 'status = "blocked" if blockers' not in generator
