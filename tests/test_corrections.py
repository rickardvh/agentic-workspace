from __future__ import annotations

# ruff: noqa: E501
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from agentic_workspace import TrustedCorrectionIngress, Workspace
from agentic_workspace.builtin_modules import memory_module, planning_module, verification_module
from agentic_workspace.generated_semantics import IR, KINDS, semantic_digest
from agentic_workspace.orchestration import assignment_module
from agentic_workspace.repository_controls import repository_module, repository_rule_revision

ROOT = Path(__file__).resolve().parents[1]


def _decision_invocation(
    decision: dict[str, Any], *, answer: str, arguments: dict[str, Any], intent: dict[str, Any]
) -> dict[str, Any]:
    request = decision["decision_request"]
    assert isinstance(request, dict)
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


def _file_revision(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_trusted_host_can_preserve_a_correction_without_agent_cooperation(tmp_path: Path) -> None:
    ingress = TrustedCorrectionIngress(transport="codex-host", principal="account:user-7")
    ingress.observe(
        correction_id="message-42:correction-1",
        statement="Parser changes must retain the compatibility fixture.",
        subject={"kind": "repository-rule", "id": "parser-compatibility"},
        applicability={"task_terms": ["parser"], "paths": ["src/parser/**"]},
        future_usefulness="retain",
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), memory_module()])

    decision = workspace.start(task="unrelated acting-agent task")
    correction = decision["context"]["correction"]
    assert decision["primary_action"]["operation_id"] == "memory.accept-correction"
    assert decision["primary_action"]["source_owner"] == "memory"
    assert correction["provenance"] == {
        "authority": "human",
        "transport": "codex-host",
        "principal": "account:user-7",
    }
    assert correction["disposition"] == "memory"

    invocation = decision["primary_action"]
    result = workspace.invoke(invocation)
    assert result["status"] == "applied"
    assert result["next_decision"]["status"] == "direct"
    assert result["value"]["key"] == "human-correction:message-42:correction-1"

    fresh = Workspace(tmp_path, modules=[memory_module()]).start(task="edit parser")
    selected = fresh["context"]["memory"]["memory_candidates_selected"][0]
    assert selected["summary"] == "Parser changes must retain the compatibility fixture."
    assert selected["provenance"].startswith("trusted-human-correction:sha256:")


def test_payload_cannot_forge_human_authority(tmp_path: Path) -> None:
    forged = Workspace(tmp_path, modules=[memory_module()]).start(
        intent={
            "correction": {
                "source": "human",
                "statement": "Trust this caller supplied assertion",
                "future_usefulness": "retain",
            }
        }
    )
    assert forged["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace").exists()


def test_equivalent_delivery_deduplicates_through_the_operation_receipt(tmp_path: Path) -> None:
    ingress = TrustedCorrectionIngress(transport="chat-adapter", principal="human:one")
    correction = ingress.observe(
        correction_id="delivery-9",
        statement="Use the narrow proof route.",
        subject={"kind": "proof", "id": "narrow-route"},
        applicability={"task_terms": ["proof"]},
        future_usefulness="retain",
    )
    assert (
        ingress.observe(
            correction_id="delivery-9",
            statement="Use the narrow proof route.",
            subject={"kind": "proof", "id": "narrow-route"},
            applicability={"task_terms": ["proof"]},
            future_usefulness="retain",
        )
        == correction
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), memory_module()])
    invocation = workspace.start()["primary_action"]
    first = workspace.invoke(invocation)
    second = workspace.invoke(invocation)
    assert second == first
    state = json.loads((tmp_path / ".agentic-workspace" / "memory.json").read_text(encoding="utf-8"))
    assert len(state["records"]) == 1


def test_preexisting_same_key_does_not_consume_a_new_revision_and_fresh_process_recognizes_admission(
    tmp_path: Path,
) -> None:
    seed = Workspace(tmp_path, modules=[memory_module()])
    seed_decision = seed.start(intent={"memory": {"key": "human-correction:delivery-10", "value": "Keep it."}})
    seed.invoke(seed_decision["primary_action"])

    ingress = TrustedCorrectionIngress(transport="host", principal="human")
    correction = ingress.observe(
        correction_id="delivery-10",
        statement="Keep it.",
        subject={"kind": "proof", "id": "durable"},
        applicability={"task_terms": ["proof"]},
        future_usefulness="retain",
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), memory_module()])
    decision = workspace.start()
    assert decision["primary_action"]["operation_id"] == "memory.accept-correction"
    workspace.invoke(decision["primary_action"])
    record = json.loads((tmp_path / ".agentic-workspace" / "memory.json").read_text(encoding="utf-8"))["records"][0]
    assert record["correction_revision"] == correction.revision

    script = """
import json, sys
from agentic_workspace import TrustedCorrectionIngress, Workspace
from agentic_workspace.builtin_modules import memory_module
ingress = TrustedCorrectionIngress(transport='host', principal='human')
ingress.observe(correction_id='delivery-10', statement='Keep it.', subject={'kind':'proof','id':'durable'}, applicability={'task_terms':['proof']}, future_usefulness='retain')
print(json.dumps(Workspace(sys.argv[1], modules=[ingress.module(), memory_module()]).start()))
"""
    replay = subprocess.run([sys.executable, "-c", script, str(tmp_path)], capture_output=True, text=True, check=True)
    assert json.loads(replay.stdout)["status"] == "direct"


def test_unrelated_current_repository_evidence_is_rejected_by_the_owner(tmp_path: Path) -> None:
    evidence = _repository_rule(tmp_path)
    ingress = TrustedCorrectionIngress(transport="host", principal="human")
    ingress.observe(
        correction_id="unrelated-owner",
        statement="Claim an unrelated rule enforces this.",
        subject={"kind": "repository-rule", "id": "different-rule"},
        existing_owner=evidence,
        future_usefulness="retain",
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), repository_module()])
    result = workspace.invoke(workspace.start()["primary_action"])
    assert result["status"] == "rejected"
    assert result["value"]["reason"] == "correction-not-enforced-by-owner"


def _repository_rule(tmp_path: Path) -> dict[str, str]:
    rule = {"id": "current-invariant", "facts": {"required": True}}
    (tmp_path / "AGENTS.md").write_text(f"<!-- agentic-workspace:rule\n{json.dumps(rule)}\n-->\n", encoding="utf-8")
    revision = repository_rule_revision(tmp_path, "current-invariant")
    assert revision is not None
    return {"owner": "repository", "ref": "current-invariant", "revision": revision}


@pytest.mark.parametrize(
    ("future_usefulness", "expected"), [("retain", "already-owned"), ("do-not-retain", "no-new-durable-record")]
)
def test_non_memory_dispositions_are_explicit_and_leave_no_correction_archive(
    tmp_path: Path, future_usefulness: str, expected: str
) -> None:
    existing_owner = _repository_rule(tmp_path) if expected == "already-owned" else None
    ingress = TrustedCorrectionIngress(transport="trusted-test-host", principal="human")
    ingress.observe(
        correction_id="bounded-1",
        statement="Keep the current invariant.",
        subject={"kind": "repository-rule", "id": "current-invariant"},
        future_usefulness=future_usefulness,
        existing_owner=existing_owner,
    )
    modules = [ingress.module(), memory_module()]
    if existing_owner:
        modules.append(repository_module())
    workspace = Workspace(tmp_path, modules=modules)
    result = workspace.invoke(workspace.start()["primary_action"])
    assert result["value"]["disposition"] == expected
    assert not (tmp_path / ".agentic-workspace" / "corrections").exists()
    assert not (tmp_path / ".agentic-workspace" / "memory.json").exists()
    assert result["value"]["justification"]


def test_deterministic_owner_failure_routes_to_planning_owner_and_stale_evidence_blocks(tmp_path: Path) -> None:
    evidence = _repository_rule(tmp_path)
    ingress = TrustedCorrectionIngress(transport="trusted-test-host", principal="human")
    ingress.observe(
        correction_id="repair-1",
        statement="The enforced invariant was skipped.",
        subject={"kind": "repository-rule", "id": "current-invariant"},
        future_usefulness="retain",
        deterministic_owner_failure=evidence,
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), memory_module(), planning_module()])
    decision = workspace.start()
    assert decision["primary_action"]["operation_id"] == "planning.accept-correction-failure"
    assert decision["primary_action"]["source_owner"] == "planning"
    result = workspace.invoke(decision["primary_action"])
    assert result["next_decision"]["context"]["planning"]["active"]["id"] == "correction-repair:repair-1"
    assert not (tmp_path / ".agentic-workspace" / "memory.json").exists()

    stale = TrustedCorrectionIngress(transport="trusted-test-host", principal="human")
    stale.observe(
        correction_id="repair-2",
        statement="Another claimed failure.",
        subject={"kind": "repository-rule", "id": "current-invariant"},
        deterministic_owner_failure={**evidence, "revision": "sha256:" + "0" * 64},
    )
    stale_workspace = Workspace(tmp_path, modules=[stale.module(), planning_module()])
    rejected = stale_workspace.invoke(stale_workspace.start()["primary_action"])
    assert rejected["status"] == "rejected"
    assert rejected["value"]["reason"] == "owner-failure-not-established"


def _verification_evidence(tmp_path: Path) -> dict[str, str]:
    policy = tmp_path / ".agentic-workspace" / "verification.toml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        "schema_version = 1\n\n[[routes]]\nid = 'focused'\nclaims = ['complete']\nbreadth = 1\ncommands = []\n",
        encoding="utf-8",
    )
    return {"owner": "verification", "ref": "focused", "revision": _file_revision(policy)}


def test_verification_owner_accepts_only_its_current_exact_route(tmp_path: Path) -> None:
    evidence = _verification_evidence(tmp_path)
    ingress = TrustedCorrectionIngress(transport="host", principal="human")
    ingress.observe(
        correction_id="verification-owned",
        statement="Use the focused verification route.",
        subject={"kind": "verification-route", "id": "focused"},
        existing_owner=evidence,
        future_usefulness="retain",
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), verification_module()])
    action = workspace.start()["primary_action"]
    assert action["operation_id"] == "verification.accept-correction"
    result = workspace.invoke(action)
    assert result["status"] == "unchanged"
    assert result["value"]["owner"] == "verification"
    assert result["next_decision"]["status"] == "direct"


@pytest.mark.parametrize("evidence_kind", ["policy", "evidence"])
def test_assignment_owner_accepts_current_policy_or_target_evidence(tmp_path: Path, evidence_kind: str) -> None:
    local = tmp_path / ".agentic-workspace" / "local"
    local.mkdir(parents=True)
    if evidence_kind == "policy":
        path = local / "delegation.json"
        path.write_text(json.dumps({"schema_version": 1, "routes": []}), encoding="utf-8")
        evidence = {"owner": "assignment", "ref": "policy", "revision": _file_revision(path)}
        subject = {"kind": "delegation-policy", "id": "policy"}
    else:
        record = {"id": "worker-proof", "target": "worker-a", "capabilities": ["python"]}
        (local / "target-evidence.json").write_text(
            json.dumps({"schema_version": 1, "records": [record]}), encoding="utf-8"
        )
        evidence = {"owner": "assignment", "ref": "worker-proof", "revision": semantic_digest(record)}
        subject = {"kind": "delegation-evidence", "id": "worker-proof"}
        (local / "delegation.json").write_text(json.dumps({"schema_version": 1, "routes": []}), encoding="utf-8")
    ingress = TrustedCorrectionIngress(transport="host", principal="human")
    ingress.observe(
        correction_id=f"assignment-owned-{evidence_kind}",
        statement="Keep the current assignment constraint.",
        subject=subject,
        existing_owner=evidence,
        future_usefulness="retain",
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), assignment_module()])
    action = workspace.start()["primary_action"]
    assert action["operation_id"] == "assignment.accept-correction"
    result = workspace.invoke(action)
    assert result["status"] == "unchanged"
    assert result["value"]["owner"] == "assignment"


def test_non_repository_owner_failure_routes_to_planning_repair(tmp_path: Path) -> None:
    evidence = _verification_evidence(tmp_path)
    ingress = TrustedCorrectionIngress(transport="host", principal="human")
    ingress.observe(
        correction_id="verification-repair",
        statement="The focused route was skipped.",
        subject={"kind": "verification-route", "id": "focused"},
        deterministic_owner_failure=evidence,
        future_usefulness="retain",
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), planning_module()])
    action = workspace.start()["primary_action"]
    assert action["operation_id"] == "planning.accept-correction-failure"
    result = workspace.invoke(action)
    assert result["status"] == "applied"
    assert result["value"]["outcome"].startswith("Repair deterministic verification owner failure")


@pytest.mark.parametrize(
    ("answer", "next_operation", "has_memory"),
    [("retain", "memory.accept-correction", True), ("no-new-durable-record", "correction.disposition", False)],
)
def test_unspecified_correction_resolves_once_then_runs_the_selected_owner_operation(
    tmp_path: Path, answer: str, next_operation: str, has_memory: bool
) -> None:
    ingress = TrustedCorrectionIngress(transport="host", principal="human")
    correction = ingress.observe(
        correction_id=f"bounded-{answer}",
        statement="A bounded correction with no inferred future scope.",
        subject={"kind": "fact", "id": "bounded"},
    )
    workspace = Workspace(tmp_path, modules=[ingress.module(), memory_module()])
    intent: dict[str, Any] = {}
    decision = workspace.start(intent=intent)
    assert decision["status"] == "decision"
    request = decision["decision_request"]
    invocation = _decision_invocation(
        decision,
        answer=answer,
        arguments={
            "target": str(tmp_path),
            "correction_id": correction.correction_id,
            "correction_revision": correction.revision,
            "answer": answer,
        },
        intent=intent,
    )
    resolved = workspace.invoke(invocation)
    assert resolved["next_decision"]["primary_action"]["operation_id"] == next_operation
    final = workspace.invoke(resolved["next_decision"]["primary_action"])
    assert final["next_decision"]["status"] == "direct"
    assert (tmp_path / ".agentic-workspace" / "memory.json").exists() is has_memory
    assert request["detail_revision"] == correction.revision


def test_no_signal_has_no_first_line_or_durable_tax(tmp_path: Path) -> None:
    ingress = TrustedCorrectionIngress(transport="host", principal="human")
    assert Workspace(tmp_path, modules=[ingress.module(), memory_module()]).start()["status"] == "direct"
    assert not (tmp_path / ".agentic-workspace").exists()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_generated_typescript_has_constructible_trusted_ingress_and_owner_handoff() -> None:
    module = (ROOT / "typescript" / "dist" / "index.js").as_uri()
    script = f'''
import {{ createTrustedCorrectionIngress, validateCorrectionAdmission, moduleContributions, compileSourceDecision, OperationDispatcher }} from "{module}";
let state = {{ records: [] }};
let ingress;
const memory = {{
  name: "memory", owns: ["memory-state"], claims: [],
  operations: [{{ operation_id: "memory.accept-correction", input_schema: {{ type: "object" }}, effects: ["memory-state"], accepted_handoffs: ["correction"], handler: (args) => {{ if (!validateCorrectionAdmission("memory", args, {{ state_revision: "memory-r1" }})) return {{ status: "rejected", effects: [], value: {{ reason: "invalid" }} }}; state.records.push(args); return {{ status: "applied", effects: ["memory-state"], value: {{ correction_revision: args.correction_revision }} }}; }} }}],
  contribute: () => null
}};
ingress = createTrustedCorrectionIngress({{ transport: "ts-host", principal: "human" }});
const correction = ingress.observe({{ correction_id: "ts-1", statement: "Keep parity.", subject: {{ kind: "rule", id: "parity" }}, applicability: {{ task_terms: ["parity"] }}, future_usefulness: "retain" }});
const modules = [ingress.module(), memory];
const resolve = () => compileSourceDecision(moduleContributions(modules, {{ target: ".", owner_revisions: {{ memory: "memory-r1" }} }}));
const decision = resolve();
const dispatcher = new OperationDispatcher({{ commitCoordinator: {{ run: async (context) => context.execute() }}, handoffNotifier: (source, operation, args, outcome) => ingress.module().handoff_complete(operation, args, outcome) }});
dispatcher.register(memory.operations[0]);
const result = await dispatcher.invoke(decision.primary_action, resolve);
const rejected = validateCorrectionAdmission("memory", decision.primary_action.arguments, {{ state_revision: "other" }});
console.log(JSON.stringify({{ correction, decision, result, state, rejected }}));
'''
    completed = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    typescript = json.loads(completed.stdout)
    assert typescript["correction"]["provenance"] == {
        "authority": "human",
        "transport": "ts-host",
        "principal": "human",
    }
    assert typescript["decision"]["primary_action"]["source_owner"] == "memory"
    assert typescript["result"]["next_decision"]["status"] == "direct"
    assert typescript["state"]["records"][0]["correction"]["statement"] == "Keep parity."
    assert typescript["rejected"] is False
    assert IR["correction"]["ingress"] == "trusted-host-capability"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for cross-target conformance")
def test_generated_typescript_routes_named_owners_and_bounded_retention() -> None:
    module = (ROOT / "typescript" / "dist" / "index.js").as_uri()
    script = f'''
import {{ createTrustedCorrectionIngress, validateCorrectionAdmission, moduleContributions, compileSourceDecision, OperationDispatcher, semanticDigest }} from "{module}";
const ingress = createTrustedCorrectionIngress({{ transport: "ts-host", principal: "human" }});
const ownerRevision = "sha256:" + "a".repeat(64);
ingress.observe({{ correction_id: "ts-verification", statement: "Use focused proof.", subject: {{ kind: "verification-route", id: "focused" }}, future_usefulness: "retain", existing_owner: {{ owner: "verification", ref: "focused", revision: ownerRevision }} }});
const ownerDecision = compileSourceDecision(moduleContributions([ingress.module(), {{ name: "verification", owns: [], claims: [], operations: [{{ operation_id: "verification.accept-correction", input_schema: {{ type: "object" }}, effects: [], accepted_handoffs: ["correction"], handler: () => ({{ status: "unchanged", effects: [], value: {{}} }}) }}], contribute: () => null }}], {{ target: "." }}));
const ownerValid = validateCorrectionAdmission("verification", ownerDecision.primary_action.arguments, {{ owner_ref: "focused", owner_revision: ownerRevision }});

async function resolveRetention(answer) {{
  const bounded = createTrustedCorrectionIngress({{ transport: "ts-host", principal: "human" }});
  bounded.observe({{ correction_id: `ts-${{answer}}`, statement: "Bounded correction.", subject: {{ kind: "fact", id: "bounded" }} }});
  const memory = {{ name: "memory", owns: [], claims: [], operations: [{{ operation_id: "memory.accept-correction", input_schema: {{ type: "object" }}, effects: ["memory-state"], accepted_handoffs: ["correction"], handler: () => ({{ status: "applied", effects: ["memory-state"], value: {{}} }}) }}], contribute: () => null }};
  const modules = [bounded.module(), memory];
  const resolve = () => compileSourceDecision(moduleContributions(modules, {{ target: "." }}));
  const decision = resolve();
  const request = decision.decision_request;
  const arguments_ = {{ target: ".", correction_id: `ts-${{answer}}`, correction_revision: request.detail_revision, answer }};
  const response = {{ id: request.id, owner: request.owner, revision: request.revision, authority: request.authority, answer }};
  const invocation = {{ kind: "agentic-workspace/operation-invocation/v1", operation_id: request.response_operation_id, arguments: arguments_, intent: {{}}, effects: request.effects, authority: request.authority, source_owner: request.owner, expected_input_revision: decision.input_revision, decision_response: response, idempotency_key: semanticDigest({{ response, arguments: arguments_, input: decision.input_revision }}) }};
  const dispatcher = new OperationDispatcher({{ commitCoordinator: {{ run: async (context) => context.execute() }} }});
  for (const operation of bounded.module().operations) dispatcher.register(operation);
  return (await dispatcher.invoke(invocation, resolve)).next_decision.primary_action.operation_id;
}}
console.log(JSON.stringify({{ ownerOperation: ownerDecision.primary_action.operation_id, ownerValid, retain: await resolveRetention("retain"), discard: await resolveRetention("no-new-durable-record") }}));
'''
    completed = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {
        "ownerOperation": "verification.accept-correction",
        "ownerValid": True,
        "retain": "memory.accept-correction",
        "discard": "correction.disposition",
    }
