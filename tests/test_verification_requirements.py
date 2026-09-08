"""One current protocol can constrain its assigned role without granting proof."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.test_native_public_cli import native_cli as native_cli

from agentic_workspace.assignment_source import configuration_requirements
from agentic_workspace.decision import DecisionContractError, direct_task_subject, verification_requirements

MANIFEST = ".agentic-workspace/verification/manifest.toml"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def current(tmp_path):
    path = tmp_path / MANIFEST
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / MANIFEST).read_bytes())
    return {
        "target": str(tmp_path),
        "task": "Evaluate current operating instruction consistency",
        "changed_paths": ["AGENTS.md"],
        "current_work": {"id": "planning:current", "revision": "semantic-work-1"},
        "role": "evaluator",
        "request": None,
    }


def answer(current):
    view = verification_requirements(current)
    request = view["request"]
    request["arguments"]["obligation_ref"] = f"{MANIFEST}#protocols.aw_context_consistency"
    request["arguments"]["judgment"] = {
        "independence_mode": "fresh-context",
        "required_proof_classes": ["worker-check"],
        "reason": "This assigned consistency evaluation needs fresh context and a structured worker check; source authority remains unchanged.",
    }
    return request


def test_actual_protocol_request_flows_into_ordinary_task_requirements(current):
    initial = verification_requirements(current)
    assert initial["status"] == "unresolved"
    assert initial["verification"] is None
    assert "aw_context_consistency" in initial["obligations"]
    request = answer(current)
    projected = verification_requirements({**current, "request": request})
    assert projected["status"] == "resolved"
    assert projected["verification"]["role"] == "evaluator"
    assert projected["verification"]["independence_mode"] == "fresh-context"
    assert projected["selected_obligation"]["protocol"] == initial["obligations"]["aw_context_consistency"]
    assert "No proof" in projected["claim_boundary"]
    task = direct_task_subject(current["task"], current["changed_paths"])
    result = configuration_requirements(
        SimpleNamespace(required_execution_guarantees=()),
        task_identity=task,
        work=current["current_work"],
        target_root=Path(current["target"]),
        task=current["task"],
        changed_paths=current["changed_paths"],
        judgment={
            "task_identity": task,
            "current_work": current["current_work"],
            "role": "evaluator",
            "required_result_classes": ["review"],
            "required_proof_classes": [],
            "verification_identity": None,
            "verification_request": request,
        },
    )
    assert result["status"] == "resolved"
    assert result["requirements"]["independent_context"] is True
    assert result["requirements"]["required_proof_classes"] == ["worker-check"]


@pytest.mark.parametrize("change", ["task", "current_work", "role", "source", "protocol"])
def test_current_role_obligation_rejects_stale_or_mismatched_request(current, change):
    request = answer(current)
    candidate = copy.deepcopy(current)
    if change == "task":
        candidate["task"] = "Implement a different outcome"
    elif change == "current_work":
        candidate["current_work"]["revision"] = "materially-changed"
    elif change == "role":
        candidate["role"] = "executor"
    elif change == "source":
        with (Path(current["target"]) / MANIFEST).open("a") as stream:
            stream.write("\n# Current source changed\n")
    else:
        request["arguments"]["obligation_ref"] = f"{MANIFEST}#protocols.invented"
    with pytest.raises(DecisionContractError):
        verification_requirements({**candidate, "request": request})


def test_request_is_judgment_not_authentication_or_empty_assumption(current):
    request = answer(current)
    request["arguments"]["judgment"] = None
    assert verification_requirements({**current, "request": request})["verification"] is None
    request["arguments"]["authenticated"] = True
    with pytest.raises(DecisionContractError):
        verification_requirements({**current, "request": request})


def test_executor_does_not_inherit_an_evaluator_obligation(current, monkeypatch):
    def unexpected(_):
        raise AssertionError("An executor without a selected obligation must not acquire global evaluator constraints")

    monkeypatch.setattr("agentic_workspace.decision.verification_requirements", unexpected)
    task = direct_task_subject(current["task"], current["changed_paths"])
    result = configuration_requirements(
        SimpleNamespace(required_execution_guarantees=()),
        task_identity=task,
        work=current["current_work"],
        target_root=Path(current["target"]),
        task=current["task"],
        changed_paths=current["changed_paths"],
        judgment={
            "task_identity": task,
            "current_work": current["current_work"],
            "role": "executor",
            "required_result_classes": ["read-only"],
            "required_proof_classes": [],
            "verification_identity": None,
        },
    )
    assert result["status"] == "resolved"
    assert result["requirements"]["independent_context"] is False


def test_node_and_json_requests_preserve_selected_role_and_no_proof(current, shared_core_binary):
    module = (ROOT / "bindings/node/semantic-decision.mjs").as_uri()
    for request, expected in [(None, "unresolved"), (answer(current), "resolved")]:
        context = {**current, "request": request}
        direct = subprocess.run(
            [str(shared_core_binary)], input=json.dumps({"verification_requirements": context}), text=True, capture_output=True, check=True
        )
        node = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                f"import {{verificationRequirements}} from {json.dumps(module)}; console.log(JSON.stringify(verificationRequirements(JSON.parse(process.argv[1]))));",
                json.dumps(context),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        for result in [json.loads(direct.stdout), json.loads(node.stdout)]:
            assert result["status"] == expected
            assert result["role"] == "evaluator"
            assert "No proof" in result["claim_boundary"]
            if request is not None:
                assert result["verification"]["independence_mode"] == "fresh-context"


def test_public_assignment_preview_resolves_current_selected_obligation(current, tmp_path):
    from tests.test_external_operation_clients import _prepare_shared_worktree_assignment

    from agentic_workspace.generated_operations import assignment_export

    _, invocation, _ = _prepare_shared_worktree_assignment(tmp_path, run_id="obligation")
    (tmp_path / ".agentic-workspace/config.local.toml").write_text("""schema_version = 1
[delegation]
assignment_policy = "required-best-fit"
current_target = "orchestrator"
transport_authority = "manual"
[delegation_targets.orchestrator]
target_id = "host:orchestrator"
target_revision = "1"
strength = "strong"
location = "local"
transports = [{kind="internal"}]
[delegation_targets.worker]
target_id = "host:worker"
target_revision = "1"
strength = "strong"
location = "external"
transports = [{kind="manual"}]
""")
    values = {"task": current["task"], "changed": current["changed_paths"], "dry_run": True}
    initial = assignment_export(values, target=tmp_path, invocation=invocation)
    judgment = initial["preview"]["task_requirements"]["judgment_request"]["arguments"]
    judgment.update(role="evaluator", required_result_classes=["review"])
    unresolved = assignment_export({**values, "task_judgment_json": json.dumps(judgment)}, target=tmp_path, invocation=invocation)
    assert unresolved["status"] == "requirements-required"
    owner = unresolved["preview"]["task_requirements"]["verification_requirements"]
    request = owner["request"]
    request["arguments"].update(answer(current)["arguments"])
    judgment["verification_request"] = request
    resolved = assignment_export({**values, "task_judgment_json": json.dumps(judgment)}, target=tmp_path, invocation=invocation)
    requirements = resolved["preview"]["task_requirements"]
    assert requirements["status"] == "resolved", resolved
    assert requirements["requirements"]["independent_context"] is True
    assert requirements["verification_requirements"]["selected_obligation"]["reference"].endswith("#protocols.aw_context_consistency")
    assert not resolved["mutation_applied"]


def test_native_start_composes_selected_verification_request_with_assignment(current, shared_core_binary, native_cli):
    from tests.test_native_public_cli import consume

    target = Path(current["target"])
    (target / ".agentic-workspace/config.local.toml").write_text(
        'schema_version = 1\n[delegation_targets.worker]\ntarget_id="host:worker"\ntarget_revision="1"\n'
        'strength="strong"\nlocation="external"\ntransports=[{kind="manual"}]\n'
    )
    context = {"target": str(target), "task": current["task"], "changed": current["changed_paths"]}

    def start(request=None):
        return consume("native", shared_core_binary, native_cli, {**context, "request": request})

    offered = start()
    assignment = offered["task_requirements"]["requests"][0]
    assignment["arguments"].update(role="evaluator", required_result_classes=["review"])
    unresolved = start(assignment)
    request = unresolved["task_requirements"]["verification_requirements"]["request"]
    assert request["owner"] == "verification"
    request["arguments"].update(answer(current)["arguments"])
    resolved = start([assignment, request])
    assert resolved["task_requirements"]["result"]["status"] == "resolved"
    assert resolved["task_requirements"]["result"]["requirements"]["independent_context"] is True
    assert resolved["verification"]["evidence"] == []
    assert resolved["verification"]["contribution"] == offered["verification"]["contribution"]
    ordinary = verification_requirements({**current, "current_work": assignment["arguments"]["current_work"]})
    other_request = ordinary["request"]
    other_request["arguments"].update(request["arguments"])
    ordinary = verification_requirements({**current, "current_work": assignment["arguments"]["current_work"], "request": other_request})
    assert ordinary["verification"] == resolved["task_requirements"]["verification_requirements"]["verification"]
    (target / MANIFEST).write_text((target / MANIFEST).read_text() + "\n# Source changed after judgment\n")
    with pytest.raises(AssertionError, match="changed"):
        start([assignment, request])
