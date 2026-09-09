"""Ordinary bounded human decisions, not signed-host identity or publication authority."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli
from tests.test_shared_core import _commit_native, _native_archive


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_bounded_decision_capture_recall_and_currentness(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    dependency = tmp_path / "policy.md"
    dependency.write_text("Fixture source constraint, not a delegated authority grant.\n")
    manifest = tmp_path / ".agentic-workspace/memory/repo/manifest.toml"
    manifest.parent.mkdir(parents=True)
    before = 'version=1\n# External author comment\n[unrelated]\nvalue="preserved"\n'
    manifest.write_text(before)
    context = {"target": str(tmp_path), "task": "Deliberate fixture decision", "changed": ["src/core.rs"]}

    def call(**extra: object) -> dict:
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    initial = call()
    request = initial["memory"]["capture"]["requests"][0]
    request["arguments"]["material"] = {
        "id": "fixture:bounded-decision",
        "decision": "Use one explicit source boundary.",
        "consequence": "Preserve this fixture boundary for src/core.rs.",
        "rationale": "A deliberate conformance fixture; no real repository decision is authorized.",
        "alternatives": ["Rejected: inferring deciding authority from publication."],
        "dependency_paths": ["policy.md"],
        "supersedes": [],
    }
    for field in ["authority", "actor", "provenance", "authors"]:
        forged = copy.deepcopy(request)
        forged["arguments"]["material"][field] = {"kind": "human", "id": "forged"}
        with pytest.raises(AssertionError):
            call(request=forged)
    proposed = call(request=request)
    proposal = proposed["memory"]["capture"]["proposal"]
    source = tmp_path / proposal["binding"]["source"]
    assert not source.exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    deferred = copy.deepcopy(answer)
    deferred["arguments"]["answer"] = "defer"
    assert call(request=deferred)["memory"]["capture"]["status"] == "deferred"
    answer["arguments"]["answer"] = "confirm-decision"  # Exact fixture human answer only.
    drifted = copy.deepcopy(answer)
    drifted["arguments"]["material"]["consequence"] = "A different consequence"
    with pytest.raises(AssertionError, match="stale|exact"):
        call(request=drifted)
    with pytest.raises(AssertionError, match="stale|current"):
        call(request=answer, task="Different work")
    action = call(request=answer)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "memory.capture-decision"
    dependency.write_text("Changed source constraint")
    with pytest.raises(AssertionError, match="stale|exact|changed"):
        call(invocation=action)
    dependency.write_text("Fixture source constraint, not a delegated authority grant.\n")
    published = call(invocation=action)
    assert published["value"]["authority_effect"] == "publication-only"
    assert source.read_bytes() == proposal["postimage"].encode()
    assert manifest.read_text().startswith(before)
    fresh = call(task="Fresh session, relevant source")
    states = fresh["decision_packet"]["decision_context"]["states"]
    assert len(states) == 1
    assert states[0]["id"] == "fixture:bounded-decision"
    consequence = fresh["decision_packet"]["decision_context"]["consequences"][0]
    assert consequence["authors"][0]["kind"] == "unattributed"
    assert consequence["authority"]["basis"][0]["owner"] == "bounded-human-answer"
    assert fresh["decision_sources"]["requests"]
    read = fresh["decision_sources"]["requests"][0]
    detail = call(task="Fresh session, relevant source", request=read)
    assert "bounded human answer" in detail["decision_sources"]["response"]["body"]
    quiet = call(task="Unrelated", changed=["src/other.rs"])
    assert not quiet["decision_packet"].get("decision_context", {}).get("states")
    with pytest.raises(AssertionError, match="collision|stale|consumed"):
        call(invocation=action)
    original = source.read_bytes()
    source.unlink()
    lost = call()
    assert any(b["code"] == "receiving-decision-source-unavailable" for b in lost["decision_packet"]["blockers"])
    source.write_bytes(original)
    manifest_original = manifest.read_bytes()
    manifest.write_bytes(manifest_original.replace(b"native_decision = true", b"native_decision = false"))
    lost = call()
    assert any(b["code"] == "decision-declaration-currentness-lost" for b in lost["decision_packet"]["blockers"])
    manifest.write_bytes(manifest_original)
    source.write_bytes(original + b"\nchanged")
    stale = call()
    assert any(b["code"] == "receiving-decision-source-unavailable" for b in stale["decision_packet"]["blockers"])
    source.write_bytes(original)
    dependency.write_text("A materially different constraint")
    stale = call()
    assert stale["decision_packet"]["decision_context"]["states"][0]["status"] == "stale"
    assert not stale["decision_packet"]["decision_context"]["consequences"]
    assert stale["decision_sources"]["requests"]
    assert source.read_bytes() == original
    admission = stale["decision_sources"]["requests"][0]["arguments"]
    replacement = call()["memory"]["capture"]["requests"][0]
    replacement["arguments"]["material"] = {
        **request["arguments"]["material"],
        "id": "fixture:reconciled-decision",
        "supersedes": [{"id": admission["id"], "material_revision": admission["material_revision"], "scope": ["path:src/core.rs"]}],
    }
    answer = call(request=replacement)["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "confirm-decision"
    call(invocation=call(request=answer)["decision_packet"]["primary_action"])
    reconciled = call()["decision_packet"]["decision_context"]
    assert [row["id"] for row in reconciled["consequences"]] == ["fixture:reconciled-decision"]
    assert source.read_bytes() == original
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text('schema_version=1\n[assurance]\ndecision_record_target="docs/decisions"\n')
    promoted_owner = call()
    assert promoted_owner["memory"]["capture"]["status"] == "stronger-owner-required"
    assert not promoted_owner["decision_packet"]["decision_context"]["consequences"]
    assert any(row["status"] == "stale" for row in promoted_owner["decision_packet"]["decision_context"]["states"])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_fallback_defers_to_configured_repository_owner(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[assurance]\ndecision_record_target="docs/decisions"\n')
    result = consume(surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Fixture", "changed": ["a.rs"]})
    assert result["memory"]["capture"]["status"] == "stronger-owner-required"
    assert result["memory"]["capture"]["requests"] == []
    assert not (tmp_path / ".agentic-workspace/memory").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_supersession_preserves_rationale_and_narrows_only_admitted_scope(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = {"target": str(tmp_path), "task": "Fixture supersession", "changed": ["src/a.rs", "src/b.rs"]}

    def call(**extra: object) -> dict:
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    def capture(identity: str, supersedes: list) -> dict:
        request = call()["memory"]["capture"]["requests"][0]
        request["arguments"]["material"] = {
            "id": identity,
            "decision": f"Fixture choice {identity}",
            "consequence": f"Fixture consequence {identity}",
            "rationale": f"Retained rationale for {identity}",
            "alternatives": [],
            "dependency_paths": [],
            "supersedes": supersedes,
        }
        proposed = call(request=request)
        answer = proposed["decision_packet"]["decision_request"]["response_request"]
        answer["arguments"]["answer"] = "confirm-decision"
        action = call(request=answer)["decision_packet"]["primary_action"]
        call(invocation=action)
        return proposed["memory"]["capture"]["proposal"]

    first = capture("fixture:old", [])
    admission = call()["decision_sources"]["requests"][0]["arguments"]
    second = capture(
        "fixture:new", [{"id": admission["id"], "material_revision": admission["material_revision"], "scope": ["path:src/a.rs"]}]
    )
    current = call()["decision_packet"]["decision_context"]
    old = next(row for row in current["consequences"] if row["id"] == "fixture:old")
    assert old["scope"] == ["path:src/b.rs"]
    assert (tmp_path / first["binding"]["source"]).read_text() == first["postimage"]
    assert (tmp_path / second["binding"]["source"]).exists()
    relevant = call(task="Fresh narrower work", changed=["src/a.rs"])["decision_packet"]["decision_context"]
    assert [row["id"] for row in relevant["consequences"]] == ["fixture:new"]
    assert not call(changed=["src/a.rs.extra"])["decision_packet"].get("decision_context", {}).get("consequences")
    context["changed"] = ["src/a.rs", "src/c.rs"]
    admission = next(row for row in call()["decision_sources"]["requests"] if row["arguments"]["id"] == "fixture:new")["arguments"]
    capture("fixture:expanded", [{"id": admission["id"], "material_revision": admission["material_revision"], "scope": ["path:src/a.rs"]}])
    expanded = call(task="Fresh expansion scope", changed=["src/c.rs"])["decision_packet"]["decision_context"]
    assert [row["id"] for row in expanded["consequences"]] == ["fixture:expanded"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_unadmitted_archive_names_do_not_block_unrelated_work(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    archive = tmp_path / ".agentic-workspace/memory/repo/decisions"
    archive.mkdir(parents=True)
    for index in range(65):
        (archive / f"native-unowned-{index}.md").write_text("Unrelated advisory source, no deciding authority.\n")
    result = consume(
        surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Unrelated direct work", "changed": ["other.rs"]}
    )
    assert result["decision_packet"]["status"] == "direct"
    assert not result["decision_packet"].get("decision_context", {}).get("consequences")
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_supersession_retains_git_admitted_ancestor_locator(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    _native_archive(tmp_path)
    archive = tmp_path / ".agentic-workspace/memory/repo/decisions"
    archive.mkdir(parents=True)
    former = archive / "owner-chosen-name.md"
    former.write_bytes((tmp_path / "design/choice.md").read_bytes())
    original = former.read_bytes()
    revision = _commit_native(tmp_path)
    (tmp_path / ".agentic-workspace/config.toml").write_text(
        'schema_version=1\n[modules]\nenabled=["memory"]\n[assurance]\n'
        f'decision_record_fallback={{archive=".agentic-workspace/memory/repo/decisions",admitted_revision="{revision}"}}\n'
    )
    context = {"target": str(tmp_path), "task": "Fixture mixed-source supersession", "changed": ["src/core.rs", "src/new.rs"]}

    def call(**extra: object) -> dict:
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    current = call()
    admission = current["decision_sources"]["requests"][0]["arguments"]
    request = current["memory"]["capture"]["requests"][0]
    request["arguments"]["material"] = {
        "id": "fixture:native-successor",
        "decision": "A fixture successor to the Git-admitted choice",
        "consequence": "Use the fixture successor",
        "rationale": "Keep the exact former source and admitted basis",
        "alternatives": [],
        "dependency_paths": [],
        "supersedes": [{"id": admission["id"], "material_revision": admission["material_revision"], "scope": ["path:src/core.rs"]}],
    }
    answer = call(request=request)["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "confirm-decision"
    call(invocation=call(request=answer)["decision_packet"]["primary_action"])
    for changed in [["src/core.rs"], ["src/new.rs"]]:
        fresh = call(task="Fresh relevant session", changed=changed)["decision_packet"]["decision_context"]
        assert [row["id"] for row in fresh["consequences"]] == ["fixture:native-successor"]
    assert former.read_bytes() == original
