"""Stronger repository capture uses the same bounded deciding-answer boundary."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli
from tests.test_shared_core import _commit_native


def repository(root: Path):
    archive = root / "docs/decisions"
    archive.mkdir(parents=True)
    (archive / "README.md").write_bytes((ROOT / "docs/decisions/README.md").read_bytes())
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    revision = _commit_native(root)
    config = root / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(f'schema_version=1\n[assurance]\ndecision_record_target="docs/decisions"\ndecision_record_revision="{revision}"\n')
    text = (ROOT / "docs/decisions/shared-semantic-authority.md").read_text()
    original = json.loads(text.split("```aw-decision\n")[1].split("\n```", 1)[0])
    material = {
        "id": original["id"],
        "decision": original["decision"],
        "consequence": original["consequence"],
        "rationale": text.split("## Rationale and alternatives\n\n")[1].split("\n##", 1)[0],
        "alternatives": ["Rejected parallel handwritten semantic runtimes."],
        "dependency_paths": ["docs/decisions/README.md"],
        "supersedes": [],
    }
    context = {
        "target": str(root),
        "task": "Preserve the actual shared semantic boundary",
        "changed": ["crates/agentic-workspace-core/src/lib.rs"],
    }
    return context, material


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("disposition", ["retain", "no-retention"])
def test_repository_material_targets_stronger_owner_without_memory(tmp_path, shared_core_binary, native_cli, surface, disposition):
    context, material = repository(tmp_path)

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    initial = call()
    assert initial["memory"]["capture"]["status"] == "stronger-owner-required"
    request = initial["decision_sources"]["capture"]["requests"][0]
    request["arguments"] = {"material": material, "disposition": disposition}
    proposed = call(request=request)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "confirm-decision"
    ready = call(request=answer)
    if disposition == "no-retention":
        assert ready["decision_sources"]["capture"]["status"] == "no-retention"
        assert ready["decision_packet"]["primary_action"] is None
        assert not (tmp_path / ".agentic-workspace/local").exists()
        assert list((tmp_path / "docs/decisions").iterdir()) == [tmp_path / "docs/decisions/README.md"]
        return
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "decision-continuity.capture-decision"
    call(invocation=action)
    source = tmp_path / action["arguments"]["binding"]["source"]
    assert source.read_bytes() == proposed["decision_sources"]["capture"]["proposal"]["postimage"].encode()
    assert not (tmp_path / ".agentic-workspace/memory").exists()
    fresh = call(task="Fresh affected session")
    consequences = fresh["decision_packet"]["decision_context"]["consequences"]
    assert len(consequences) == 1
    assert consequences[0]["source"]["owner"] == "repository"
    assert consequences[0]["authority"]["basis"][0]["owner"] == "bounded-human-answer"
    request = fresh["decision_sources"]["requests"][0]
    detail = call(task="Fresh affected session", request=request)
    assert detail["decision_sources"]["response"]["authority_effect"] == "no-new-authority"
    quiet = call(task="Unrelated", changed=["unrelated.txt"])
    assert not quiet["decision_packet"].get("decision_context", {}).get("consequences")


def capture_answer(call, material, **arguments):
    request = call()["decision_sources"]["capture"]["requests"][0]
    request["arguments"] = {"material": material, **arguments}
    proposed = call(request=request)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "confirm-decision"
    return answer


@pytest.mark.parametrize("disposition", ["retain", "no-retention"])
@pytest.mark.parametrize("answer_value", ["confirm-decision", "defer"])
def test_repository_answer_requires_exact_issued_request(tmp_path, shared_core_binary, native_cli, disposition, answer_value):
    context, material = repository(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    answer = capture_answer(call, material, disposition=disposition)
    answer["id"] = "client-made-up-answer"
    answer["arguments"]["answer"] = answer_value
    with pytest.raises(AssertionError, match="exact owner-issued bounded request"):
        call(request=answer)
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("filename", ["decision-unrelated.prepared.json", "decision-" + "a" * 64 + ".prepared.json"])
def test_repository_discovery_preserves_unrelated_malformed_residue(tmp_path, shared_core_binary, native_cli, filename):
    context, material = repository(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    directory = tmp_path / ".agentic-workspace/local/effects"
    directory.mkdir(parents=True)
    residue = directory / filename
    residue.write_bytes(b"{broken")
    quiet = call(changed=["elsewhere.txt"])
    assert quiet["decision_packet"]["status"] == "direct"
    assert residue.read_bytes() == b"{broken"
    action = call(request=capture_answer(call, material))["decision_packet"]["primary_action"]
    call(invocation=action)
    assert call()["decision_packet"]["decision_context"]["consequences"]


def test_repository_relevant_malformed_custody_cannot_silently_drop_consequence(tmp_path, shared_core_binary, native_cli):
    context, material = repository(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    action = call(request=capture_answer(call, material))["decision_packet"]["primary_action"]
    call(invocation=action)
    marker = next((tmp_path / ".agentic-workspace/local/effects").glob("decision-*.prepared.json"))
    marker.write_bytes(b"{broken")
    fresh = call()
    assert not fresh["decision_packet"].get("decision_context", {}).get("consequences")
    assert any(b["code"] == "receiving-decision-source-unavailable" for b in fresh["decision_packet"]["blockers"])
    quiet = call(changed=["elsewhere.txt"])
    assert quiet["decision_packet"]["status"] == "direct"
    assert marker.read_bytes() == b"{broken"


@pytest.mark.parametrize("stage", ["prepared", "published"])
def test_repository_capture_recovery_keeps_original_answer(tmp_path, shared_core_binary, native_cli, stage):
    context, material = repository(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    answer = capture_answer(call, material)
    action = call(request=answer)["decision_packet"]["primary_action"]
    done = call(invocation=action)
    source = tmp_path / action["arguments"]["binding"]["source"]
    before = source.read_bytes()
    (tmp_path / done["custody"]["committed"]["path"]).unlink()
    if stage == "prepared":
        source.unlink()
    fresh = call()
    retries = fresh["decision_sources"]["capture"]["requests"][1:]
    assert len(retries) == 1
    retry = call(request=retries[0])["decision_packet"]["primary_action"]
    call(invocation=retry)
    assert source.read_bytes() == before
    assert call()["decision_packet"]["decision_context"]["consequences"][0]["id"] == material["id"]
    assert not (tmp_path / ".agentic-workspace/memory").exists()


@pytest.mark.parametrize("change", ["source", "missing", "convention"])
def test_repository_publication_cannot_outlive_source_owner_currentness(tmp_path, shared_core_binary, native_cli, change):
    context, material = repository(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    action = call(request=capture_answer(call, material))["decision_packet"]["primary_action"]
    call(invocation=action)
    source = tmp_path / action["arguments"]["binding"]["source"]
    if change == "missing":
        source.unlink()
    else:
        target = source if change == "source" else tmp_path / "docs/decisions/README.md"
        target.write_bytes(target.read_bytes() + b"\nChanged owner source.\n")
    fresh = call()
    assert not fresh["decision_packet"].get("decision_context", {}).get("consequences")
    assert any(b["code"] == "receiving-decision-source-unavailable" for b in fresh["decision_packet"]["blockers"])


def test_repository_publication_preserves_scope_protection(tmp_path, shared_core_binary, native_cli):
    context, material = repository(tmp_path)
    instruction = tmp_path / ".agentic-workspace/instructions/archive.md"
    instruction.parent.mkdir()
    instruction.write_text("---\npaths: [docs/decisions/**]\nprotect: [docs/decisions/**]\n---\nKeep the canonical archive protected.\n")
    revision = _commit_native(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(config.read_text() + f'instruction_revision="{revision}"\n')

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    answer = capture_answer(call, material)
    ready = call(request=answer)
    assert ready["decision_packet"]["primary_action"] is None
    assert any("protected-decision-write" in b["code"] for b in ready["decision_packet"]["blockers"])
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_repository_publication_bounds_escaped_carrier_before_admission(tmp_path, shared_core_binary, native_cli):
    context, material = repository(tmp_path)
    material["rationale"] = "r" * 8192
    material["alternatives"] = ["a" * 8188 + f"{i:03}" for i in range(16)]

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    answer = capture_answer(call, material)
    action = call(request=answer)["decision_packet"]["primary_action"]
    with pytest.raises(AssertionError, match="bounded recovery size"):
        call(invocation=action)
    assert not (tmp_path / ".agentic-workspace/local").exists()
    assert not list((tmp_path / "docs/decisions").glob("native-*"))


def test_repository_identity_collision_and_forged_authorship_are_rejected(tmp_path, shared_core_binary, native_cli):
    import copy

    context, material = repository(tmp_path)

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    request = call()["decision_sources"]["capture"]["requests"][0]
    request["arguments"]["material"] = material
    for field in ["actor", "authority", "provenance", "authors"]:
        forged = copy.deepcopy(request)
        forged["arguments"]["material"][field] = "trusted-human"
        with pytest.raises(AssertionError):
            call(request=forged)
    # Even an unadmitted archive source owns its bytes and cannot silently
    # acquire a same-ID competing canonical record through capture.
    source = tmp_path / "docs/decisions/existing.md"
    source.write_bytes((ROOT / "docs/decisions/shared-semantic-authority.md").read_bytes())
    before = source.read_bytes()
    with pytest.raises(AssertionError, match="identity already exists"):
        call(request=request)
    assert source.read_bytes() == before
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_repository_capture_is_independent_of_memory_enablement(tmp_path, shared_core_binary, native_cli):
    context, material = repository(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(config.read_text() + "\n[modules]\nenabled=[]\n")

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    answer = capture_answer(call, material)
    call(invocation=call(request=answer)["decision_packet"]["primary_action"])
    assert call()["decision_packet"]["decision_context"]["consequences"][0]["source"]["owner"] == "repository"
    assert not (tmp_path / ".agentic-workspace/memory").exists()


def test_repository_capture_obeys_current_startup_and_workspace_ceilings(tmp_path, shared_core_binary, native_cli):
    context, material = repository(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text(config.read_text() + '\n[workspace]\nagent_instructions_file="AGENTS.md"\n')
    (tmp_path / "AGENTS.md").write_text("Observe the current repository owner boundary.\n")

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra})

    answer = capture_answer(call, material)
    guarded = call(request=answer)
    assert guarded["decision_packet"]["primary_action"] is None
    assert any(
        "effect:decision-source" in b["affects"]
        for b in guarded["decision_packet"]["blockers"]
        if b["code"] == "configured-startup-source-read-required"
    )
    read = guarded["startup_adapter"]["requests"][0]
    permitted = call(request=[answer, read])
    assert permitted["decision_packet"]["primary_action"]["operation_id"] == "decision-continuity.capture-decision"
    config.write_text(config.read_text() + "enabled=false\n")
    blocked = call()
    assert any(b["code"] == "workspace-disabled" for b in blocked["decision_packet"]["blockers"])
    with pytest.raises(AssertionError):
        call(invocation=permitted["decision_packet"]["primary_action"])
    assert not list((tmp_path / "docs/decisions").glob("native-*"))
