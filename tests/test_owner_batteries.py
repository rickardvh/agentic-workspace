from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace.builtin_modules import memory_module, planning_module, verification_module
from agentic_workspace.generated_semantics import KINDS, semantic_digest
from agentic_workspace.modules import Module
from agentic_workspace.operations import StaleInvocationError
from agentic_workspace.repository_controls import repository_module
from agentic_workspace.workspace import Workspace


def _decision_invocation(
    decision: dict[str, Any], *, answer: str, arguments: dict[str, Any], intent: dict[str, Any]
) -> dict[str, Any]:
    request = decision["decision_request"]
    response = {
        "id": request["id"],
        "owner": request["owner"],
        "revision": request["revision"],
        "authority": request["authority"],
        "answer": answer,
    }
    return {
        "kind": KINDS["invocation"],
        "operation_id": request["response_operation_id"],
        "arguments": arguments,
        "intent": intent,
        "effects": request["effects"],
        "authority": request["authority"],
        "source_owner": request["owner"],
        "expected_input_revision": decision["input_revision"],
        "decision_response": response,
        "idempotency_key": semantic_digest(
            {"response": response, "arguments": arguments, "input": decision["input_revision"]}
        ),
    }


def test_scoped_markdown_rule_routes_reusable_procedure_and_bounded_configuration(tmp_path: Path) -> None:
    rule = {
        "id": "release-runner",
        "applies": {"task_terms": ["release"]},
        "facts": {"preferred_capability": "trusted-runner"},
        "procedures": [{"id": "release-review", "locator": "docs/release-review.md"}],
        "claims": {"blocked": ["publish"]},
        "decision": {
            "question": "Which trusted runner should publish?",
            "authority": "maintainer",
            "scope": "shared",
            "choices": [{"id": "host", "label": "Maintainer host"}],
        },
    }
    (tmp_path / "AGENTS.md").write_text(
        "# Repository guidance\n\n<!-- agentic-workspace:rule\n" + json.dumps(rule) + "\n-->\n",
        encoding="utf-8",
    )
    workspace = Workspace(tmp_path, modules=[repository_module()])
    assert workspace.start(task="rename variable")["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace").exists()

    intent = {"task": "prepare release", "changed_paths": [], "claims": []}
    decision = workspace.start(intent=intent)
    assert decision["status"] == "decision"
    assert decision["procedures"] == [
        {
            "id": "release-review",
            "owner": "repository",
            "revision": decision["decision_request"]["detail_revision"],
            "locator": "docs/release-review.md",
            "summary": "",
            "authority": "reference-only",
        }
    ]
    invocation = _decision_invocation(
        decision,
        answer="host",
        arguments={
            "target": str(tmp_path),
            "rule_id": "release-runner",
            "rule_revision": decision["decision_request"]["detail_revision"],
            "answer": "host",
            "scope": "shared",
        },
        intent=intent,
    )
    result = workspace.invoke(invocation)
    assert result["next_decision"]["status"] == "terminal"
    assert result["next_decision"]["claim_boundary"]["blocked"] == ["publish"]


def test_open_configuration_judgment_is_deferred_and_stale_answers_fail_closed(tmp_path: Path) -> None:
    rule = {
        "id": "support-owner",
        "decision": {
            "question": "Who owns support exceptions?",
            "authority": "maintainer",
            "scope": "local",
            "allow_open": True,
        },
    }
    path = tmp_path / "AGENTS.md"
    path.write_text(f"<!-- agentic-workspace:rule\n{json.dumps(rule)}\n-->\n", encoding="utf-8")
    workspace = Workspace(tmp_path, modules=[repository_module()])
    intent = {"task": "support", "changed_paths": [], "claims": []}
    deferred = workspace.start(intent=intent)
    assert deferred["decision_request"]["allow_open"] is True
    assert Workspace(tmp_path, modules=[repository_module()]).start(intent=intent) == deferred
    invocation = _decision_invocation(
        deferred,
        answer="release maintainer",
        arguments={
            "target": str(tmp_path),
            "rule_id": "support-owner",
            "rule_revision": deferred["decision_request"]["detail_revision"],
            "answer": "release maintainer",
            "scope": "local",
        },
        intent=intent,
    )
    rule["decision"]["question"] = "Who owns current support exceptions?"
    path.write_text(f"<!-- agentic-workspace:rule\n{json.dumps(rule)}\n-->\n", encoding="utf-8")
    with pytest.raises(StaleInvocationError):
        workspace.invoke(invocation)


def test_memory_selects_only_applicable_current_advice_and_supports_promotion(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, modules=[memory_module()])
    record = workspace.start(
        intent={
            "memory": {
                "key": "parser-workaround",
                "value": "use strict mode",
                "summary": "Parser needs strict mode",
                "provenance": "issue-42",
                "task_terms": ["parser"],
                "kind": "workaround",
            }
        }
    )
    workspace.invoke(record["primary_action"])

    selected = Workspace(tmp_path, modules=[memory_module()]).start(task="debug parser")
    assert selected["relevant_owners"] == ["memory"]
    assert selected["status"] == "terminal"
    assert selected["resources"] == []
    assert selected["claim_boundary"] == {"allowed": [], "blocked": []}
    assert Workspace(tmp_path, modules=[memory_module()]).start(task="edit CSS")["status"] == "direct"

    disposition = workspace.start(
        intent={
            "memory": {
                "operation": "disposition",
                "key": "parser-workaround",
                "disposition": "promoted",
                "stronger_owner": "repository",
            }
        }
    )
    workspace.invoke(disposition["primary_action"])
    assert Workspace(tmp_path, modules=[memory_module()]).start(task="debug parser")["status"] == "direct"


def test_planning_preserves_semantic_subject_across_status_attempt_transitions(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, modules=[planning_module()])
    shape = {
        "operation": "set",
        "item": "ship",
        "status": "in-progress",
        "outcome": "publish v1",
        "scope": ["src"],
        "constraints": ["preserve API"],
        "dependencies": ["review"],
        "stops": ["proof fails"],
        "proof_claims": ["complete"],
    }
    workspace.invoke(workspace.start(intent={"planning": shape})["primary_action"])
    first = json.loads((tmp_path / ".agentic-workspace" / "planning.json").read_text(encoding="utf-8"))["subject"]
    attempt = {
        "operation": "record-attempt",
        "item": "ship",
        "expected_subject_revision": first["semantic_revision"],
        "attempt_id": "attempt-2",
        "target_id": "worker-b",
        "status": "returned",
        "result_revision": "result-1",
    }
    result = workspace.invoke(workspace.start(intent={"planning": attempt})["primary_action"])
    second = json.loads((tmp_path / ".agentic-workspace" / "planning.json").read_text(encoding="utf-8"))["subject"]
    assert first["semantic_revision"] == second["semantic_revision"]
    assert second["status"] == "integration-pending"
    assert result["next_decision"]["status"] == "decision"
    assert result["next_decision"]["decision_request"]["response_operation_id"] == "planning.reconcile"


def test_planning_derives_dependency_frontier_and_invalidates_dependent_attempts(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, modules=[planning_module()])
    workspace.invoke(
        workspace.start(
            intent={
                "planning": {
                    "operation": "set",
                    "item": "ship",
                    "status": "in-progress",
                    "dependencies": ["review"],
                    "scope": ["src"],
                }
            }
        )["primary_action"]
    )
    workspace.invoke(
        workspace.start(intent={"planning": {"operation": "set", "item": "review", "status": "in-progress"}})[
            "primary_action"
        ]
    )
    state_path = tmp_path / ".agentic-workspace" / "planning.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["subject"]["id"] == "review"
    assert state["subjects"]["ship"]["readiness"] == "blocked"
    ship_revision = state["subjects"]["ship"]["semantic_revision"]
    attempt_intent = {
        "planning": {
            "operation": "record-attempt",
            "item": "ship",
            "expected_subject_revision": ship_revision,
            "attempt_id": "ship-attempt",
            "target_id": "worker",
            "status": "in-flight",
        }
    }
    stale_attempt = workspace.start(intent=attempt_intent)["primary_action"]
    workspace.invoke(stale_attempt)
    unrun_stale_attempt = workspace.start(
        intent={
            "planning": {
                **attempt_intent["planning"],
                "attempt_id": "unrun-stale-attempt",
            }
        }
    )["primary_action"]

    complete_review = workspace.start(intent={"planning": {"operation": "set", "item": "review", "status": "complete"}})
    result = workspace.invoke(complete_review["primary_action"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["subject"]["id"] == "ship"
    assert state["subjects"]["ship"]["readiness"] == "ready"
    assert state["subjects"]["ship"]["semantic_revision"] != ship_revision
    assert state["attempts"] == []
    assert result["next_decision"] == Workspace(tmp_path, modules=[planning_module()]).start(
        intent=complete_review["primary_action"]["intent"]
    )
    with pytest.raises(StaleInvocationError):
        workspace.invoke(unrun_stale_attempt)


def test_verification_selects_smallest_sufficient_owned_strategy_and_blocks_missing(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, modules=[planning_module(), verification_module()])
    plan = workspace.start(
        intent={
            "planning": {
                "operation": "set",
                "item": "ship",
                "status": "ready-to-complete",
                "outcome": "ship",
                "proof_claims": ["complete"],
            }
        }
    )
    workspace.invoke(plan["primary_action"])
    missing = workspace.start(task="ship", claims=["complete"])
    assert missing["status"] == "blocked"
    assert missing["blockers"][0]["code"] == "missing-proof-strategy"

    (tmp_path / ".agentic-workspace" / "verification.toml").write_text(
        "schema_version = 1\n\n"
        "[[routes]]\nid = 'broad'\nclaims = ['complete']\nbreadth = 100\n"
        f"commands = [['{sys.executable}', '-c', 'raise SystemExit(0)']]\n\n"
        "[[routes]]\nid = 'focused'\nclaims = ['complete']\nbreadth = 1\n"
        f"commands = [['{sys.executable}', '-c', 'raise SystemExit(0)']]\n",
        encoding="utf-8",
    )
    proof = Workspace(tmp_path, modules=[planning_module(), verification_module()]).start(
        task="ship", claims=["complete"]
    )
    assert proof["primary_action"]["arguments"]["route_id"] == "focused"


def test_owner_conclusion_reuse_survives_fresh_workspace_and_invalidates_narrowly(tmp_path: Path) -> None:
    calls = 0
    revision = {"value": "one"}

    def contribute(_: Mapping[str, Any]) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return {"revision": revision["value"], "facts": {"expensive": calls}, "terminal": True}

    module = Module(
        "expensive",
        contribute,
        currentness=lambda _: revision["value"],
    )
    first = Workspace(tmp_path, modules=[module]).start(task="material")
    second = Workspace(tmp_path, modules=[module]).start(task="material")
    assert first == second
    assert calls == 1
    revision["value"] = "two"
    Workspace(tmp_path, modules=[module]).start(task="material")
    assert calls == 2


def test_two_real_owner_conclusions_reuse_and_invalidate_only_their_dependencies(tmp_path: Path) -> None:
    memory = Workspace(tmp_path, modules=[memory_module()])
    memory.invoke(
        memory.start(
            intent={
                "memory": {
                    "key": "parser",
                    "value": "strict",
                    "summary": "strict parser",
                    "task_terms": ["parser"],
                }
            }
        )["primary_action"]
    )
    planning = Workspace(tmp_path, modules=[planning_module()])
    planning.invoke(
        planning.start(intent={"planning": {"operation": "set", "item": "ship", "status": "ready-to-complete"}})[
            "primary_action"
        ]
    )
    policy = tmp_path / ".agentic-workspace" / "verification.toml"
    policy.write_text(
        "schema_version = 1\n\n[[routes]]\nid = 'focused'\nclaims = ['complete']\nbreadth = 1\ncommands = []\n",
        encoding="utf-8",
    )

    calls = {"memory": 0, "verification": 0}
    original_memory = memory_module()
    original_verification = verification_module()

    def count_memory(context: Mapping[str, Any]) -> Mapping[str, Any] | None:
        calls["memory"] += 1
        return original_memory.contribute(context)

    def count_verification(context: Mapping[str, Any]) -> Mapping[str, Any] | None:
        calls["verification"] += 1
        return original_verification.contribute(context)

    counted_memory = replace(original_memory, contribute=count_memory)
    counted_verification = replace(original_verification, contribute=count_verification)
    modules = [counted_memory, counted_verification]
    first = Workspace(tmp_path, modules=modules).start(task="parser ship", claims=["complete"])
    second = Workspace(tmp_path, modules=modules).start(task="parser ship", claims=["complete"])
    assert first == second
    assert calls == {"memory": 1, "verification": 1}

    policy.write_text(policy.read_text(encoding="utf-8") + "# narrower proof revision\n", encoding="utf-8")
    Workspace(tmp_path, modules=modules).start(task="parser ship", claims=["complete"])
    assert calls == {"memory": 1, "verification": 2}
