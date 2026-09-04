from __future__ import annotations

# ruff: noqa: E501
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace.decision import compile_source_decision
from agentic_workspace.generated_semantics import IR, canonical_serialize, semantic_digest
from agentic_workspace.operations import Operation, OperationDispatcher

ROOT = Path(__file__).resolve().parents[1]


def _node_decision(contributions: list[dict[str, Any]], intent: dict[str, Any]) -> dict[str, Any]:
    module = (ROOT / "typescript" / "dist" / "index.js").as_uri()
    script = (
        f'import {{ compileSourceDecision }} from "{module}"; '
        "const input = JSON.parse(process.argv[1]); "
        "console.log(JSON.stringify(compileSourceDecision(input.contributions, input.intent)));"
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, json.dumps({"contributions": contributions, "intent": intent})],
        capture_output=True,
        text=True,
        check=True,
    )
    value: Any = json.loads(completed.stdout)
    assert isinstance(value, dict)
    return value


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_python_typescript_and_json_semantics_share_one_vector() -> None:
    contributions: list[dict[str, Any]] = [
        {
            "owner": "review",
            "revision": "r1",
            "facts": {"change": "bounded"},
            "resources": [{"id": "checklist", "revision": "one", "locator": "docs/review.md"}],
            "procedures": [{"id": "review", "revision": "one", "locator": "tools/review.md"}],
            "actions": [
                {
                    "operation_id": "review.run",
                    "arguments": {"subject": "change"},
                    "effects": ["review-evidence"],
                    "authority": "review",
                    "priority": 10,
                }
            ],
            "claims": {"blocked": ["complete"]},
        }
    ]
    intent: dict[str, Any] = {"task": "review change"}

    python = compile_source_decision(contributions, intent=intent)
    typescript = _node_decision(contributions, intent)

    assert typescript == python
    assert python["procedures"][0]["authority"] == "reference-only"
    assert python["resources"][0]["authority"] == "read-only"


def test_ir_inventories_semantics_and_exact_platform_primitives() -> None:
    assert IR["decision"]["contribution_dimensions"] == [
        "facts",
        "resources",
        "procedures",
        "decisions",
        "blockers",
        "actions",
        "claims",
        "terminal",
    ]
    assert {operation["id"] for operation in IR["operations"]} == {
        "workspace.remove",
        "workspace.remove-legacy",
        "planning.set",
        "planning.complete",
        "memory.read",
        "memory.record",
        "verification.run",
        "workspace.transfer-ownership",
        "memory.disposition",
        "planning.reconcile",
        "planning.record-attempt",
        "repository.answer",
        "correction.disposition",
        "correction.choose-retention",
        "repository.accept-correction",
        "verification.accept-correction",
        "assignment.accept-correction",
        "planning.accept-correction-failure",
        "memory.accept-correction",
        "assignment.choose",
        "assignment.transfer-retired-policy",
        "assignment.record-evidence",
        "delegation.dispatch",
        "delegation.return",
        "delegation.integrate",
    }
    assert IR["primitive_inventory"]["python"]
    assert IR["primitive_inventory"]["typescript"]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_canonical_identity_is_target_neutral_and_unicode_normalized() -> None:
    value = {"z": [1, True, None], "e\u0301": "e\u0301"}
    module = (ROOT / "typescript" / "dist" / "index.js").as_uri()
    script = (
        f'import {{ canonicalSerialize, semanticDigest }} from "{module}"; '
        "const value = JSON.parse(process.argv[1]); "
        "console.log(JSON.stringify([canonicalSerialize(value), semanticDigest(value)]));"
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script, json.dumps(value)],
        capture_output=True,
        text=True,
        check=True,
    )
    serialized, digest = json.loads(completed.stdout)
    assert serialized == canonical_serialize(value)
    assert digest == semantic_digest(value)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_bounded_decision_is_revision_bound_and_shared_by_both_targets() -> None:
    contributions = [
        {
            "owner": "configuration",
            "revision": "config-7",
            "decisions": [
                {
                    "id": "runner",
                    "question": "Which eligible runner should own this work?",
                    "authority": "maintainer",
                    "response_operation_id": "configuration.answer",
                    "choices": [{"id": "local", "label": "Local"}, {"id": "host", "label": "Host"}],
                }
            ],
        }
    ]
    python = compile_source_decision(contributions)
    assert python["status"] == "decision"
    assert python["primary_action"] is None
    assert python["decision_request"]["revision"] == "config-7"
    assert _node_decision(contributions, {}) == python


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_typescript_module_contract_supports_independent_capability_and_judgment() -> None:
    module = (ROOT / "typescript" / "dist" / "index.js").as_uri()
    script = f'''
import {{ admitModules, compileSourceDecision, moduleContributions }} from "{module}";
const operation = {{ operation_id: "example.answer", input_schema: {{ type: "object" }}, effects: ["example-state"], handler: () => ({{ status: "applied", effects: ["example-state"] }}) }};
const extension = {{
  name: "example",
  api_version: "1.1",
  required_capabilities: ["contribution/decisions"],
  owns: ["example-state"],
  resources: [{{ id: "guide", revision: "g1", locator: "docs/guide.md" }}],
  procedures: [{{ id: "review", revision: "p1", locator: "docs/review.md" }}],
  operations: [operation],
  contribute: () => ({{ revision: "one", decisions: [{{ id: "choice", question: "Choose", authority: "maintainer", response_operation_id: "example.answer", effects: ["example-state"], choices: [{{ id: "yes", label: "Yes" }}] }}] }})
}};
const admitted = admitModules([extension]);
console.log(JSON.stringify(compileSourceDecision(moduleContributions(admitted, {{}}))));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True
    )
    decision = json.loads(completed.stdout)
    assert decision["status"] == "decision"
    assert decision["resources"][0]["owner"] == "example"
    assert decision["procedures"][0]["authority"] == "reference-only"


def test_one_ir_change_regenerates_both_language_targets(tmp_path: Path) -> None:
    source = tmp_path / "source"
    contracts = source / "contracts"
    contracts.mkdir(parents=True)
    original = json.loads((ROOT / "contracts" / "semantic-ir.json").read_text(encoding="utf-8"))
    (contracts / "semantic-ir.json").write_text(json.dumps(original), encoding="utf-8")
    before = tmp_path / "before"
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(ROOT / "scripts" / "generate_contracts.py"),
            "--root",
            str(source),
            "--output-root",
            str(before),
        ],
        cwd=ROOT,
        check=True,
    )
    original["kinds"]["decision"] = "agentic-workspace/operating-decision/example"
    (contracts / "semantic-ir.json").write_text(json.dumps(original), encoding="utf-8")
    after = tmp_path / "after"
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(ROOT / "scripts" / "generate_contracts.py"),
            "--root",
            str(source),
            "--output-root",
            str(after),
        ],
        cwd=ROOT,
        check=True,
    )

    assert (before / "src/agentic_workspace/generated_semantics.py").read_bytes() != (
        after / "src/agentic_workspace/generated_semantics.py"
    ).read_bytes()
    assert (before / "typescript/dist/index.js").read_bytes() != (after / "typescript/dist/index.js").read_bytes()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_generated_dispatchers_share_result_currentness_and_effect_semantics() -> None:
    state = {"revision": "r1", "pending": True}

    def resolve() -> dict[str, Any]:
        return compile_source_decision(
            [
                {
                    "owner": "example",
                    "revision": state["revision"],
                    "actions": [
                        {
                            "operation_id": "example.finish",
                            "arguments": {"value": "done"},
                            "effects": ["example-state"],
                        }
                    ]
                    if state["pending"]
                    else [],
                    "terminal": not state["pending"],
                }
            ]
        )

    def finish(arguments: dict[str, Any]) -> dict[str, Any]:
        state.update(revision="r2", pending=False)
        return {"status": "applied", "effects": ["example-state"], "value": arguments}

    dispatcher = OperationDispatcher()
    dispatcher.register(
        Operation(
            "example.finish",
            {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            ("example-state",),
            finish,
        )
    )
    invocation = resolve()["primary_action"]
    python = dispatcher.invoke(invocation, resolve_decision=resolve)

    module = (ROOT / "typescript" / "dist" / "index.js").as_uri()
    script = f'''
import {{ compileSourceDecision, OperationDispatcher }} from "{module}";
const state = {{ revision: "r1", pending: true }};
const resolve = () => compileSourceDecision([{{ owner: "example", revision: state.revision, actions: state.pending ? [{{ operation_id: "example.finish", arguments: {{ value: "done" }}, effects: ["example-state"] }}] : [], terminal: !state.pending }}]);
const dispatcher = new OperationDispatcher({{ commitCoordinator: {{ run: async (context) => context.execute() }} }});
dispatcher.register({{ operation_id: "example.finish", input_schema: {{ type: "object", properties: {{ value: {{ type: "string" }} }}, required: ["value"], additionalProperties: false }}, effects: ["example-state"], handler: (values) => {{ state.revision = "r2"; state.pending = false; return {{ status: "applied", effects: ["example-state"], value: values }}; }} }});
console.log(JSON.stringify(await dispatcher.invoke(resolve().primary_action, resolve)));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True
    )
    assert json.loads(completed.stdout) == python
