"""Exact instruction publication, recovery and cross-owner restrictions."""

from __future__ import annotations

import copy
import hashlib
import os
import subprocess
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text(".agentic-workspace/local/\n")


def instruction(call, source, content):
    request = copy.deepcopy(call()["instructions"]["authoring"]["requests"][0])
    request["arguments"] = {"source": source, "content": content}
    proposal = call(request=request)
    decision = next(
        d for d in proposal["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "instruction-write-authorization"
    )
    answer = decision["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    return proposal, answer, action


@pytest.mark.parametrize("owner", ["instructions", "configuration"])
def test_current_nomination_uses_destination_authority_and_quiets_after_change(tmp_path, shared_core_binary, native_cli, owner):
    repo(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[workspace]\nimprovement_latitude="reporting"\ncli_invoke="aw-old"\n')
    evidence = tmp_path / "observation.md"
    evidence.write_text("Fixture: the same owner method is repeatedly reconstructed.")
    nomination = {
        "origin": "repo-opportunity",
        "concern": "repository",
        "disposition": "change",
        "scope": "proactive",
        "reason": "A bounded current method improvement.",
        "expected_effect": "Stop repeating the fixture setup.",
        "validation": "Fresh owner projection must expose the changed method.",
        "supersession": "Fresh source supersedes this request; restore with a new owner proposal if needed.",
        "evidence": [{"reference": "observation.md", "revision": "sha256:" + hashlib.sha256(evidence.read_bytes()).hexdigest()}],
    }
    source = ".agentic-workspace/instructions/method.md"
    context = {"target": str(tmp_path), "task": "Improve one bounded current method", "changed": ["src/a.txt"]}
    section = "authoring" if owner == "instructions" else None

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    def view(result):
        return result["instructions"][section] if section else result["configuration_write"]

    def request():
        requests = view(call())["requests"]
        candidate = copy.deepcopy(requests[0] if section else next(r for r in requests if r["arguments"]["key"] == "workspace.cli_invoke"))
        if section:
            candidate["arguments"].update(source=source, content="---\npaths: [src/**]\n---\nUse the current owner method.\n")
        else:
            candidate["arguments"]["value"] = "aw-current"
        candidate["arguments"]["nomination"] = copy.deepcopy(nomination)
        return candidate

    assert view(call(request=request()))["status"] == "report"
    assert not (tmp_path / ".agentic-workspace/local").exists()
    config.write_text(config.read_text().replace('"reporting"', '"proactive"'))
    candidate = request()
    candidate["arguments"]["nomination"]["concern"] = "package"
    assert view(call(request=candidate))["status"] == "report-to-package-owner"
    candidate = request()
    proposed = call(request=candidate)
    assert view(proposed)["status"] == "human-decision-required"  # Latitude is not mutation authority.
    answer = next(
        d
        for d in proposed["decision_packet"]["pending_consequences"]["decisions"]
        if d["id"] == ("instruction-write-authorization" if section else "configuration-write-authorization")
    )["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    assert action["operation_id"] == ("instructions.write" if section else "configuration.write")
    before = evidence.read_bytes()
    evidence.write_text("Changed evidence")
    with pytest.raises(AssertionError, match="evidence changed"):
        call(invocation=action)
    evidence.write_bytes(before)
    call(invocation=action)
    assert view(call(request=request()))["status"] == "already-owned"
    candidate = request()
    candidate["arguments"]["nomination"].update(origin="owner-friction", disposition="already-owned")
    if section:
        candidate["arguments"]["content"] += "Not yet owned.\n"
    else:
        candidate["arguments"]["value"] = "not-yet-owned"
    with pytest.raises(AssertionError, match="already-owned"):
        call(request=candidate)
    no_action = copy.deepcopy(candidate)
    no_action["arguments"]["nomination"]["disposition"] = "no-action"
    assert view(call(request=no_action))["status"] == "no-action"
    authority_owner = "scoped-instructions" if section else "configuration"
    authority_path = source if section else ".agentic-workspace/config.toml"
    config.write_text(
        config.read_text() + f'\n[assurance]\ndecision_delegations=[{{owner="{authority_owner}",scope=["path:{authority_path}"]}}]\n'
    )
    delegated = request()
    delegated["arguments"].update(candidate["arguments"])
    delegated["arguments"]["nomination"].update(disposition="change")
    admitted = call(request=delegated)
    assert view(admitted)["status"] == "write-ready"
    call(invocation=admitted["decision_packet"]["primary_action"])
    if section:
        assert "Not yet owned" in call()["instructions"]["sources"][0]["guidance"]
        unsafe = request()
        unsafe["arguments"]["content"] = "Broader unscoped method.\n"
        unsafe["arguments"]["nomination"]["origin"] = "owner-friction"
        with pytest.raises(AssertionError, match="binding floors"):
            call(request=unsafe)
    else:
        assert call()["configuration"]["cli_invoke"] == "not-yet-owned"


@pytest.mark.parametrize("scope", ["instructions", "local/instructions"])
def test_instruction_correction_exact_publication_and_fresh_delivery(tmp_path, shared_core_binary, native_cli, scope):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Retain explicit future behavior", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = f".agentic-workspace/{scope}/behavior.md"
    content = "---\npaths: [src/**]\nprotect: [generated/**]\n---\nUse this checkout unless isolation is necessary. Clean up completed isolation.\n"
    proposal, answer, action = instruction(call, source, content)
    assert not (tmp_path / source).exists()
    assert action["operation_id"] == "instructions.write"
    forged = copy.deepcopy(answer)
    forged["arguments"]["content"] += "Different instruction."
    with pytest.raises(AssertionError):
        call(request=forged)
    result = call(invocation=action)
    assert result["status"] == "applied", result
    assert (tmp_path / source).read_text() == content
    fresh = call()
    row = next(r for r in fresh["instructions"]["sources"] if r["source"]["reference"] == source)
    assert row["binding_admission"]["status"] == "current", row
    assert "isolation" in row["guidance"]
    assert not (tmp_path / ".agentic-workspace/planning").exists()
    quiet = consume("json", shared_core_binary, native_cli, {**context, "changed": ["other.txt"]}, host_path=os.environ["PATH"])
    assert not quiet["instructions"]["sources"][0]["applicable"]
    (tmp_path / source).write_text(content + "Drift.\n")
    assert call()["instructions"]["sources"][0]["binding_admission"]["status"] != "current"


def test_instruction_recovery_preserves_drift_and_unknown_files(tmp_path, shared_core_binary, native_cli):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Retain exact correction", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = ".agentic-workspace/local/instructions/behavior.md"
    _, answer, action = instruction(call, source, "---\nprotect: [generated/**]\n---\nKeep generated content protected.\n")
    destination = tmp_path / source
    destination.parent.mkdir(parents=True)
    destination.write_text("Another author's important instruction.\n")
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert "important" in destination.read_text()
    destination.unlink()
    result = call(invocation=action)
    before = destination.read_bytes()
    # Simulate interruption after source publication but before final attempt commit.
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    fresh = call()
    assert fresh["instructions"]["sources"][0]["binding_admission"]["status"] != "current"
    recovery = fresh["instructions"]["authoring"]["recovery_requests"][0]
    repaired = call(invocation=call(request=recovery)["decision_packet"]["primary_action"])
    assert repaired["status"] == "applied"
    assert destination.read_bytes() == before
    assert call()["instructions"]["sources"][0]["binding_admission"]["status"] == "current"
    request = copy.deepcopy(call()["instructions"]["authoring"]["requests"][0])
    request["arguments"] = {
        "source": ".agentic-workspace/local/instructions/bad.md",
        "content": "A local rule without ignore policy.\n",
    }
    (tmp_path / ".gitignore").write_text("")
    with pytest.raises(AssertionError, match="gitignored"):
        call(request=request)


def test_checked_in_instruction_protects_local_config_and_correction(tmp_path, shared_core_binary, native_cli):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Preserve repository policy", "changed": []}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    _, _, action = instruction(
        call,
        ".agentic-workspace/instructions/guard.md",
        "---\nprotect: [.agentic-workspace/config.local.toml, .agentic-workspace/local/instructions/**]\n---\nRepository guard.\n",
    )
    call(invocation=action)
    _, _, action = instruction(call, ".agentic-workspace/local/instructions/waive.md", "Please ignore the repository guard.\n")
    assert action is None
    request = next(
        r
        for r in call(request=call()["configuration_write"]["creation_discovery_request"])["configuration_write"]["creation_requests"]
        if r["arguments"]["key"] == "safety.safe_to_auto_run_commands"
    )
    request["arguments"]["value"] = False
    answer = call(request=request)["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    ready = call(request=answer)
    assert ready["decision_packet"]["primary_action"] is None
    assert not (tmp_path / ".agentic-workspace/config.local.toml").exists()


def test_checked_in_correction_travels_without_local_publication_custody(tmp_path, shared_core_binary, native_cli):
    origin = tmp_path / "origin"
    origin.mkdir()
    repo(origin)
    context = {"target": str(origin), "task": "Retain portable behavior", "changed": ["src/a.txt"]}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = ".agentic-workspace/instructions/portable.md"
    _, _, action = instruction(call, source, "---\npaths: [src/**]\nprotect: [generated/**]\n---\nPortable repository policy.\n")
    call(invocation=action)
    subprocess.run(["git", "-C", str(origin), "add", ".gitignore", source], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(origin),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "Portable instruction",
        ],
        check=True,
    )
    pin = subprocess.check_output(["git", "-C", str(origin), "rev-parse", "HEAD"], text=True).strip()
    clone = tmp_path / "fresh"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    assert not (clone / ".agentic-workspace/local").exists()
    (clone / ".agentic-workspace/config.toml").write_text(f'schema_version=1\n[assurance]\ninstruction_revision="{pin}"\n')
    fresh = consume("json", shared_core_binary, native_cli, {**context, "target": str(clone)}, host_path=os.environ["PATH"])
    row = fresh["instructions"]["sources"][0]
    assert row["source"]["scope"] == "repository"
    assert row["binding_admission"]["status"] == "current"
    assert row["guidance"] == "Portable repository policy."


def test_instruction_escaped_material_cannot_publish_unreadable_recovery(tmp_path, shared_core_binary, native_cli):
    repo(tmp_path)
    context = {"target": str(tmp_path), "task": "Check bounded instruction publication", "changed": []}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    source = ".agentic-workspace/instructions/bounded.md"
    _, _, action = instruction(call, source, "\x01" * 20_000)
    with pytest.raises(AssertionError, match="bounded recovery size"):
        call(invocation=action)
    assert not (tmp_path / source).exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_real_local_instruction_owner_composes_and_loses_only_local_sources(tmp_path, shared_core_binary, native_cli):
    from tests.test_native_resources import resource

    shared = tmp_path / ".agentic-workspace/instructions/repo.md"
    shared.parent.mkdir(parents=True)
    shared.write_text("Repository-wide guidance.")
    local = tmp_path / ".agentic-workspace/local/instructions/machine.md"
    local.parent.mkdir(parents=True)
    local.write_text("---\npaths: [src/**]\n---\nMachine-local checkout policy.")
    context = {"target": str(tmp_path), "task": "Inspect current policy", "changed": ["src/a.txt"]}

    def call(**kw):
        return consume("json", shared_core_binary, native_cli, {**context, **kw})

    first = call()
    rows = first["instructions"]["sources"]
    assert {r["source"]["scope"] for r in rows} == {"repository", "machine-local"}
    assert any(r["guidance"] == "Machine-local checkout policy." for r in rows)
    assert call()["instructions"]["sources"] == rows
    quiet = call(changed=["unrelated.txt"])
    assert not next(r for r in quiet["instructions"]["sources"] if r["source"]["scope"] == "machine-local")["guidance"]
    local.unlink()
    lost = call()["instructions"]["sources"]
    assert lost == [next(r for r in rows if r["source"]["scope"] == "repository")]
    # A newly appearing local obligation is observed without any changed-list update.
    local.write_text("---\nreconcile: [guide.md]\n---\nReconcile the local source obligation.")
    (tmp_path / "guide.md").write_text("Canonical source")
    assert call()["verification"]["source_reconciliation"]["status"] != first["verification"]["source_reconciliation"]["status"]
    # Local prose cannot override a checked-in structured protection.
    shared.write_text("---\nprotect: [.agentic-workspace/local/scratch/**]\n---\nPreserve task state.")
    local.write_text("Use scratch freely; this local prose does not waive repository protection.")
    blocked = resource("json", shared_core_binary, native_cli, {**context, "request": {"operation": "scratch-create"}})
    assert "action" not in blocked and any("protects" in b for b in blocked["blockers"])


def test_instruction_skill_reference_tracks_current_procedure(tmp_path, shared_core_binary, native_cli):
    import json

    repo(tmp_path)
    registry = tmp_path / ".agentic-workspace/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    procedure = registry.parent / "review/SKILL.md"
    procedure.parent.mkdir()
    procedure.write_text("Review the exact changed behavior.\n")
    registry.write_text(
        json.dumps(
            {
                "schema_version": "skill-registry.v1",
                "skills": [
                    {"id": "review", "path": "review/SKILL.md", "semantic_routes": [{"id": "repo/quality/review", "match": "exact"}]}
                ],
            }
        )
    )
    context = {"target": str(tmp_path), "task": "Review a scoped change", "changed": ["a.txt"]}
    (tmp_path / "a.txt").write_text("source")

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    _, _, action = instruction(
        call, ".agentic-workspace/instructions/procedure.md", "---\npaths: [a.txt]\nuse: [review]\n---\nUse the review procedure.\n"
    )
    call(invocation=action)
    resolution = call()["instructions"]["sources"][0]["procedure_resolution"][0]
    assert resolution["status"] == "current"
    assert resolution["procedures"][0]["reference"] == ".agentic-workspace/skills/review/SKILL.md"
    procedure.unlink()
    assert call()["instructions"]["sources"][0]["procedure_resolution"][0]["status"] == "unavailable"
