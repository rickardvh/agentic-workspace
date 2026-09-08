"""Self-sufficient current read-only handoffs, never reviewer authentication."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest
from tests.test_native_npm_routes import packed as packed
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

BASE = 'schema_version=1\n[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="manual"\n[delegation_targets.local]\nstrength="weak"\ntransports=[{kind="internal"}]\n[delegation_targets.expert]\nstrength="strong"\ntransports=[{kind="manual"}]\n'


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_capsule_and_typed_return_without_parent_context(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(BASE)
    dependency = tmp_path / "dependency.md"
    dependency.write_text("Domain rule: blå means blue.\n", encoding="utf-8", newline="\n")
    context = {"target": str(tmp_path), "task": "Explain the supplied domain rule in English; return findings only.", "changed": []}

    def call(request=None, **updates):
        return consume(surface, shared_core_binary, native_cli, {**context, **updates, **({"request": request} if request else {})})

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    before = call(task)
    manual = next(
        r
        for r in before["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
        if r["configuration"]["id"] == "expert:manual"
    )
    assert not manual["eligible"]
    inputs = before["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"].update(
        input_refs=["dependency.md"], complete=False, reason="The named domain rule is the complete input for this bounded explanation."
    )
    inputs = call(inputs)["task_requirements"]["handoff_inputs"]["requests"][0]
    inputs[-1]["arguments"]["complete"] = True
    offered = call(inputs)
    assert "blå means" not in json.dumps(offered, ensure_ascii=False)
    assessment = offered["task_requirements"]["assignment"]["requests"][0]
    assessment[-1]["arguments"].update(
        alternative="expert:manual", reason="The configured expert is preferred for this domain explanation."
    )
    current = call(assessment)
    assert current["task_requirements"]["assignment"]["result"]["status"] == "assigned-nonlocal-handoff-required"
    export = current["task_requirements"]["handoff"]["requests"][0]
    exported = call(export)["task_requirements"]["handoff"]
    packet = exported["packet"]
    worker = packet["worker_context"]
    assert worker["intent"]["outcome"] == context["task"]
    assert worker["inputs"]["capsule"] == [
        {
            "reference": "dependency.md",
            "revision": "sha256:" + hashlib.sha256(dependency.read_bytes()).hexdigest(),
            "content": "Domain rule: blå means blue.\n",
        }
    ]
    assert worker["effects"]["allowed"] == ["read-provided-inputs", "return-observations"]
    assert worker["proof"]["worker_authority"] is False
    assert worker["inputs"]["task_requirements"]["requirements"]["required_result_classes"] == ["read-only"]
    reentry = copy.deepcopy(worker["return_contract"]["reentry"])
    returned = {
        **worker["return_contract"]["required_identity"],
        "kind": "agentic-workspace/delegated-return/v1",
        "result_delivery": "unapplied-patch",
        "changed_paths": [],
        "patch": "",
        "summary": "The supplied Swedish word means blue.",
        "stop_conditions_hit": [],
    }
    reentry["request"][-1]["arguments"]["returned"] = returned
    # Fresh process consumes only this sealed packet's explicit re-entry context.
    admitted = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **reentry})
    observed = admitted["task_requirements"]["handoff"]["observation"]
    assert observed["status"] == "current-unproven-observation"
    assert observed["proof_current"] is False and observed["authenticated_reviewer"] is False
    assert any(b["code"] == "current-nonlocal-assignment-handoff-required" for b in admitted["decision_packet"]["blockers"])
    assert not (tmp_path / ".agentic-workspace/local").exists()
    wrong = copy.deepcopy(reentry)
    wrong["request"][-1]["arguments"]["returned"]["target"] = "other"
    with pytest.raises(AssertionError, match="match"):
        consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **wrong})
    mutation = copy.deepcopy(reentry)
    mutation["request"][-1]["arguments"]["returned"]["patch"] = "invented diff"
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), **mutation})
    dependency.write_text("Changed domain rule.\n")
    with pytest.raises(AssertionError, match="changed|stale"):
        call(export)
    assert source.read_text() == BASE


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_missing_or_unreviewed_inputs_never_construct_manual_assignment(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(BASE)
    context = {"target": str(tmp_path), "task": "Explain a bounded supplied rule", "changed": []}

    def call(request=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **({"request": request} if request else {})})

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    offered = call(task)
    request = offered["task_requirements"]["handoff_inputs"]["requests"][0]
    request[-1]["arguments"].update(input_refs=["missing.md"], reason="This named input is necessary.", complete=True)
    with pytest.raises(AssertionError, match="observed|changed"):
        call(request)
    request[-1]["arguments"]["complete"] = False
    missing = call(request)
    assert "missing" in str(missing["task_requirements"]["handoff_inputs"]["gaps"])
    complete = missing["task_requirements"]["handoff_inputs"]["requests"][0]
    complete[-1]["arguments"]["complete"] = True
    still_missing = call(complete)
    manual = next(
        r
        for r in still_missing["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
        if r["configuration"]["id"] == "expert:manual"
    )
    assert not manual["eligible"]
    assert any(b["code"] == "current-binding-assignment-required" for b in still_missing["decision_packet"]["blockers"])
    (tmp_path / "missing.md").write_text("The required rule is now supplied.")
    with pytest.raises(AssertionError, match="changed"):
        call(complete)
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_readonly_handoff_does_not_gain_mutation_capability(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(BASE)
    context = {"target": str(tmp_path), "task": "Prepare a bounded file change", "changed": []}

    def call(request=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **({"request": request} if request else {})})

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["unapplied-patch"]
    request = call(task)["task_requirements"]["handoff_inputs"]["requests"][0]
    request[-1]["arguments"].update(reason="The task description is the complete input.", complete=False)
    current = call(request)["task_requirements"]["handoff_inputs"]["requests"][0]
    current[-1]["arguments"]["complete"] = True
    result = call(current)
    manual = next(
        r
        for r in result["task_requirements"]["execution_configurations"]["configurations"]["candidates"]
        if r["configuration"]["id"] == "expert:manual"
    )
    assert not manual["eligible"] and "result-class-unavailable" in manual["reasons"]
    assert result["task_requirements"]["handoff"]["requests"] == []
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["json", "python", "typescript"])
def test_shared_seal_preserves_only_exact_known_unicode_checksum(tmp_path, shared_core_binary, surface):
    import os
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    packet = {
        "assignment_id": "a",
        "assignment_revision": "revision",
        "run_id": "r",
        "target": "worker",
        "assignment_identity": {"human_intent": "Explain blå", "allowed_paths": []},
        "return_contract": {"required_fields": ["assignment_revision"]},
    }

    def call(action, value):
        payload = {"action": action, "packet": value}
        env = {**os.environ, "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)}
        if surface == "json":
            command = [str(shared_core_binary)]
            stdin = json.dumps({"assignment_packet": payload})
        elif surface == "python":
            command = [
                sys.executable,
                "-c",
                "import json,sys; from agentic_workspace.decision import assignment_packet; print(json.dumps(assignment_packet(json.loads(sys.argv[1]))))",
                json.dumps(payload),
            ]
            stdin = None
        else:
            module = (root / "bindings/node/semantic-decision.mjs").as_uri()
            command = [
                "node",
                "--input-type=module",
                "-e",
                f"import {{assignmentPacket}} from {json.dumps(module)}; console.log(JSON.stringify(assignmentPacket(JSON.parse(process.argv[1]))));",
                json.dumps(payload),
            ]
            stdin = None
        result = subprocess.run(command, input=stdin, text=True, encoding="utf-8", capture_output=True, env=env, cwd=root)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    sealed = call("seal", packet)
    blank = copy.deepcopy(sealed)
    blank["packet_integrity"] = ""
    for contract in [blank["return_contract"], blank["worker_context"]["return_contract"]]:
        contract["required_identity"]["packet_integrity"] = ""

    def checksum(ascii_only):
        return (
            "sha256:"
            + hashlib.sha256(json.dumps(blank, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_only).encode()).hexdigest()
        )

    assert sealed["packet_integrity"] == checksum(True)
    legacy = copy.deepcopy(sealed)
    legacy["packet_integrity"] = checksum(False)
    for contract in [legacy["return_contract"], legacy["worker_context"]["return_contract"]]:
        contract["required_identity"]["packet_integrity"] = legacy["packet_integrity"]
    assert call("integrity", legacy)["integrity"] == legacy["packet_integrity"]
    assert call("seal", legacy)["packet_integrity"] == sealed["packet_integrity"]
    changed = copy.deepcopy(legacy)
    changed["assignment_identity"]["human_intent"] = "Other work"
    assert call("integrity", changed)["integrity"] != legacy["packet_integrity"]
    unknown = copy.deepcopy(legacy)
    unknown["packet_integrity"] = "sha256:unknown-codec"
    assert call("integrity", unknown)["integrity"] != "sha256:unknown-codec"


def test_real_packed_packet_owner_without_python_or_checkout(packed, tmp_path):
    import os
    import shutil
    import subprocess

    node = shutil.which("node")
    assert node
    module = (packed / "src/native/semantic-decision.mjs").as_uri()
    payload = {
        "action": "seal",
        "packet": {
            "assignment_id": "a",
            "assignment_revision": "r",
            "run_id": "one",
            "target": "manual",
            "assignment_identity": {"human_intent": "A bounded explanation"},
            "return_contract": {},
        },
    }
    environment = {key: value for key, value in os.environ.items() if key != "AGENTIC_WORKSPACE_CORE_BINARY"}
    environment["PATH"] = ""
    result = subprocess.run(
        [
            node,
            "--input-type=module",
            "-e",
            f"import {{assignmentPacket}} from {json.dumps(module)}; console.log(JSON.stringify(assignmentPacket(JSON.parse(process.argv[1]))));",
            json.dumps(payload),
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    packet = json.loads(result.stdout)
    assert packet["worker_context"]["intent"]["outcome"] == "A bounded explanation"
    assert packet["return_contract"]["required_identity"]["packet_integrity"] == packet["packet_integrity"]
    assert packet["worker_context"]["proof"]["worker_authority"] is False
