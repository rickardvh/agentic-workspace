from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace.generated_semantics import IR, KINDS, semantic_digest
from agentic_workspace.modules import Module
from agentic_workspace.operations import Operation, StaleInvocationError
from agentic_workspace.repository_controls import repository_module
from agentic_workspace.workspace import Workspace

ROOT = Path(__file__).resolve().parents[1]


def _write_rules(path: Path, rules: list[dict[str, Any]]) -> None:
    path.write_text(
        "# Repository controls\n\n"
        + "\n".join(f"<!-- agentic-workspace:rule\n{json.dumps(rule)}\n-->" for rule in rules)
        + "\n",
        encoding="utf-8",
    )


def _decision_invocation(
    decision: dict[str, Any], *, answer: str, scope: str, target: Path, intent: dict[str, Any]
) -> dict[str, Any]:
    request = decision["decision_request"]
    response = {
        "id": request["id"],
        "owner": request["owner"],
        "revision": request["revision"],
        "authority": request["authority"],
        "answer": answer,
    }
    arguments = {
        "target": str(target),
        "rule_id": request["id"],
        "rule_revision": request["detail_revision"],
        "answer": answer,
        "scope": scope,
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


def test_ordinary_start_applies_strong_inference_before_human_question(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
    rules = [
        {
            "id": "test-runner",
            "decision": {
                "question": "Which supported test runner should be used?",
                "scope": "shared",
                "choices": [{"id": "pytest", "label": "pytest"}],
                "infer": [{"answer": "pytest", "when": {"path_exists": "pyproject.toml"}}],
            },
        },
        {
            "id": "release-owner",
            "decision": {
                "question": "Who owns release approval?",
                "scope": "shared",
                "allow_open": True,
            },
        },
    ]
    _write_rules(tmp_path / "AGENTS.md", rules)
    workspace = Workspace(tmp_path, modules=[repository_module()])

    inferred = workspace.start(task="first task after install")
    assert inferred["status"] == "actionable"
    assert inferred["primary_action"]["operation_id"] == "repository.answer"
    assert inferred["primary_action"]["arguments"]["answer"] == "pytest"
    assert inferred["primary_action"]["authority"] == "repository-inference"
    next_decision = workspace.invoke(inferred["primary_action"])["next_decision"]
    assert next_decision["status"] == "decision"
    assert next_decision["decision_request"]["id"] == "release-owner"

    stored = json.loads((tmp_path / ".agentic-workspace" / "config.answers.json").read_text(encoding="utf-8"))
    assert stored["test-runner"]["answer"] == "pytest"
    assert stored["test-runner"]["disposition"] == "configured"


def test_fact_inference_is_order_independent_and_conflicts_fail_closed(tmp_path: Path) -> None:
    rules = [
        {
            "id": "a-config",
            "decision": {
                "question": "Which runtime should execute checks?",
                "choices": [{"id": "python", "label": "Python"}],
                "infer": [{"answer": "python", "when": {"fact_equals": {"key": "runtime", "value": "python"}}}],
            },
        },
        {"id": "z-facts", "facts": {"runtime": "python"}},
    ]
    path = tmp_path / "AGENTS.md"
    _write_rules(path, rules)
    inferred = Workspace(tmp_path, modules=[repository_module()]).start()
    assert inferred["primary_action"]["arguments"]["answer"] == "python"

    rules.append({"id": "zz-conflict", "facts": {"runtime": "node"}})
    _write_rules(path, rules)
    blocked = Workspace(tmp_path, modules=[repository_module()]).start()
    assert blocked["status"] == "blocked"
    assert blocked["blockers"][0]["code"] == "repository-control-conflict"


def test_optional_decision_defers_resumes_and_fails_closed_when_stale(tmp_path: Path) -> None:
    rule = {
        "id": "local-provider",
        "decision": {
            "question": "Which local provider should handle optional remote work?",
            "scope": "local",
            "required": False,
            "choices": [{"id": "provider-a", "label": "Provider A"}],
        },
    }
    path = tmp_path / "AGENTS.md"
    _write_rules(path, [rule])
    workspace = Workspace(tmp_path, modules=[repository_module()])
    intent = {"task": "ordinary task", "changed_paths": [], "claims": []}

    decision = workspace.start(intent=intent)
    assert [choice["id"] for choice in decision["decision_request"]["choices"]] == ["provider-a", "defer"]
    deferred = workspace.invoke(
        _decision_invocation(decision, answer="defer", scope="local", target=tmp_path, intent=intent)
    )
    assert deferred["next_decision"]["status"] == "terminal"
    assert deferred["next_decision"]["context"]["repository"]["configuration:local-provider"]["status"] == "deferred"
    assert not (tmp_path / ".agentic-workspace" / "config.answers.json").exists()

    resumed_intent = {**intent, "configuration": {"resume": True}}
    resumed = Workspace(tmp_path, modules=[repository_module()]).start(intent=resumed_intent)
    assert resumed["status"] == "decision"
    stale_invocation = _decision_invocation(
        resumed, answer="provider-a", scope="local", target=tmp_path, intent=resumed_intent
    )

    rule["decision"]["question"] = "Which current local provider should handle optional remote work?"
    _write_rules(path, [rule])
    with pytest.raises(StaleInvocationError):
        workspace.invoke(stale_invocation)
    changed = Workspace(tmp_path, modules=[repository_module()]).start(intent=intent)
    assert changed["status"] == "decision"


def test_only_changed_configuration_revision_is_revisited(tmp_path: Path) -> None:
    rules = [
        {
            "id": "docs-owner",
            "applies": {"task_terms": ["docs"]},
            "decision": {
                "question": "Who owns docs?",
                "scope": "shared",
                "choices": [{"id": "team-a", "label": "Team A"}],
            },
        },
        {
            "id": "release-owner",
            "applies": {"task_terms": ["release"]},
            "decision": {
                "question": "Who owns releases?",
                "scope": "shared",
                "choices": [{"id": "team-b", "label": "Team B"}],
            },
        },
    ]
    path = tmp_path / "AGENTS.md"
    _write_rules(path, rules)
    workspace = Workspace(tmp_path, modules=[repository_module()])
    docs_intent = {"task": "edit docs", "changed_paths": [], "claims": []}
    docs = workspace.start(intent=docs_intent)
    workspace.invoke(_decision_invocation(docs, answer="team-a", scope="shared", target=tmp_path, intent=docs_intent))

    rules[1]["decision"]["question"] = "Who owns current releases?"
    _write_rules(path, rules)
    assert Workspace(tmp_path, modules=[repository_module()]).start(intent=docs_intent)["status"] == "terminal"
    release = Workspace(tmp_path, modules=[repository_module()]).start(task="prepare release")
    assert release["status"] == "decision"
    assert release["decision_request"]["id"] == "release-owner"


def test_independent_module_configuration_and_capability_delta_use_generic_contract(tmp_path: Path) -> None:
    capabilities = {
        "stable": {"revision": "stable-r1", "question": "Choose stable mode"},
    }
    settled: dict[str, dict[str, str]] = {}

    def contribute(_context: Mapping[str, Any]) -> dict[str, Any]:
        pending = [
            (capability_id, value)
            for capability_id, value in sorted(capabilities.items())
            if settled.get(capability_id, {}).get("revision") != value["revision"]
        ]
        decisions = []
        if pending:
            capability_id, value = pending[0]
            decisions.append(
                {
                    "id": capability_id,
                    "question": value["question"],
                    "authority": "capability-owner",
                    "response_operation_id": "example.configure",
                    "effects": ["example-configuration"],
                    "choices": [{"id": "enabled", "label": "Enabled"}],
                }
            )
        return {
            "revision": semantic_digest({"capabilities": capabilities, "settled": settled}),
            "facts": {"settled": dict(settled)},
            "decisions": decisions,
            "terminal": not decisions,
        }

    def configure(arguments: dict[str, Any]) -> dict[str, Any]:
        capability_id = arguments["capability_id"]
        current = capabilities.get(capability_id)
        if current is None or current["revision"] != arguments["capability_revision"]:
            return {"status": "rejected", "effects": [], "value": {"reason": "stale-capability"}}
        settled[capability_id] = {"revision": current["revision"], "answer": arguments["answer"]}
        return {"status": "applied", "effects": ["example-configuration"], "value": settled[capability_id]}

    operation = Operation(
        "example.configure",
        {
            "type": "object",
            "properties": {
                "capability_id": {"type": "string"},
                "capability_revision": {"type": "string"},
                "answer": {"type": "string"},
            },
            "required": ["capability_id", "capability_revision", "answer"],
            "additionalProperties": False,
        },
        ("example-configuration",),
        configure,
    )
    module = Module(
        name="example-capability",
        owns=("example-configuration",),
        contribute=contribute,
        operations=(operation,),
        currentness=lambda _context: semantic_digest({"capabilities": capabilities, "settled": settled}),
    )
    workspace = Workspace(tmp_path, modules=[module])

    first = workspace.start()
    assert first["decision_request"]["owner"] == "example-capability"
    first_request = first["decision_request"]
    first_response = {
        "id": "stable",
        "owner": "example-capability",
        "revision": first_request["revision"],
        "authority": "capability-owner",
        "answer": "enabled",
    }
    first_invocation = {
        "kind": KINDS["invocation"],
        "operation_id": "example.configure",
        "arguments": {"capability_id": "stable", "capability_revision": "stable-r1", "answer": "enabled"},
        "intent": {"task": "", "changed_paths": [], "claims": []},
        "effects": ["example-configuration"],
        "authority": "capability-owner",
        "source_owner": "example-capability",
        "expected_input_revision": first["input_revision"],
        "decision_response": first_response,
        "idempotency_key": semantic_digest({"response": first_response, "input": first["input_revision"]}),
    }
    assert workspace.invoke(first_invocation)["next_decision"]["status"] == "terminal"

    capabilities["new-provider"] = {"revision": "provider-r1", "question": "Choose the new provider posture"}
    changed = Workspace(tmp_path, modules=[module]).start()
    assert changed["decision_request"]["id"] == "new-provider"
    assert changed["context"]["example-capability"]["settled"] == {
        "stable": {"revision": "stable-r1", "answer": "enabled"}
    }


def test_direct_repository_has_no_configuration_ceremony_or_residue(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Plain instructions\n", encoding="utf-8")
    result = Workspace(tmp_path, modules=[repository_module()]).start(task="edit code")
    assert result["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace").exists()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_generated_targets_expose_equal_configuration_semantics() -> None:
    module = (ROOT / "typescript" / "dist" / "index.js").as_uri()
    script = f'import {{ IR }} from "{module}"; console.log(JSON.stringify(IR.configuration));'
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True
    )
    assert json.loads(completed.stdout) == IR["configuration"]
