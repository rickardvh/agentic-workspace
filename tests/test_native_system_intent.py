"""Governing-source reads preserve source authority without granting alignment."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli

MIRROR = ".agentic-workspace/system-intent/intent.toml"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_real_governing_sources_are_lazy_exact_and_not_alignment(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[system_intent]\nsources=["SYSTEM_INTENT.md","README.md"]\npreferred_source="SYSTEM_INTENT.md"\n')
    for reference in ("SYSTEM_INTENT.md", "README.md", MIRROR):
        path = tmp_path / reference
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / reference).read_bytes())
    context = {"target": str(tmp_path), "task": "Inspect current intent"}
    result = consume(surface, shared_core_binary, native_cli, context)
    owner = result["system_intent"]
    assert owner["preferred_source"] == "SYSTEM_INTENT.md"
    assert owner["interpretation"]["status"] == "retained"
    assert owner["interpretation"]["alignment"] == "unresolved-owner-judgment"
    assert len(json.dumps(owner)) < 16000
    assert "governing_intents =" not in json.dumps(owner)
    request = next(r for r in owner["requests"] if r["arguments"]["reference"] == MIRROR)
    read = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["system_intent"]["response"]
    assert read["text"] == (tmp_path / MIRROR).read_bytes().decode("utf-8")
    assert "governing_intents" in read["text"]
    assert "grants no alignment" in read["authority_boundary"]
    for projection in ("compact", "carried"):
        delivered = consume(surface, shared_core_binary, native_cli, {**context, "request": request, "projection": projection})
        visible = delivered["view"] if projection == "carried" else delivered
        projected_read = visible["decision_packet"]["material"]["system-intent"]
        delivery = projected_read.pop("delivery")
        assert delivery["status"] == "included"
        assert delivery["extent"] == "whole-source"
        assert delivery["authority"] == "presentation-only; no semantic satisfaction"
        assert delivery["reference"].startswith("sha256:")
        assert projected_read == read
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {**context, "task": "A different task", "request": request})
    forged = json.loads(json.dumps(request))
    forged["arguments"]["reference"] = "secret.txt"
    with pytest.raises(AssertionError, match="outside current declared"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": forged})
    original_config = config.read_bytes()
    config.write_text(config.read_text().replace('preferred_source="SYSTEM_INTENT.md"', 'preferred_source="README.md"'))
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    config.write_bytes(original_config)
    with (tmp_path / "SYSTEM_INTENT.md").open("ab") as f:
        f.write(b"\nChanged governing source\n")
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    current = consume(surface, shared_core_binary, native_cli, context)["system_intent"]
    assert "retained-interpretation-source-currentness-unproven" in current["gaps"]
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_governing_source_absence_is_quiet_and_missing_declaration_is_not_waived(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    (tmp_path / "README.md").write_text("Unrelated generic repository prose")
    context = {"target": str(tmp_path), "task": "Describe the repository"}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert quiet["system_intent"]["status"] == "absent"
    assert quiet["system_intent"]["requests"] == []
    assert "boundary" not in quiet["system_intent"]["reconciliation"]
    assert quiet["decision_packet"]["status"] == "direct"
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[system_intent]\nsources=["missing.md"]\npreferred_source="missing.md"\n')
    blocked = consume(surface, shared_core_binary, native_cli, context)
    assert blocked["system_intent"]["gaps"] == ["governing-source-unavailable:missing.md"]
    assert blocked["decision_packet"]["blockers"]
    assert not (tmp_path / MIRROR).exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("condition", ["unreviewed", "invalid"])
def test_existing_interpretation_uncertainty_is_preserved(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, condition: str
) -> None:
    mirror = tmp_path / MIRROR
    mirror.parent.mkdir(parents=True)
    text = (ROOT / MIRROR).read_text(encoding="utf-8")
    text = text.replace("needs_review = false", "needs_review = true") if condition == "unreviewed" else "unparseable retained authority"
    mirror.write_text(text, encoding="utf-8")
    context = {"target": str(tmp_path), "task": "Inspect retained intent"}
    result = consume(surface, shared_core_binary, native_cli, context)
    gap = "retained-interpretation-review-unresolved" if condition == "unreviewed" else "retained-interpretation-invalid-or-unavailable"
    assert gap in result["system_intent"]["gaps"]
    assert result["decision_packet"]["blockers"]
    assert mirror.read_text(encoding="utf-8") == text
    request = result["system_intent"]["requests"][0]
    read = consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    assert read["system_intent"]["response"]["text"] == mirror.read_bytes().decode("utf-8")
    assert read["system_intent"]["gaps"] == result["system_intent"]["gaps"]
    with pytest.raises(AssertionError, match="one current request"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": [request, request]})


def test_retained_intent_reconciliation_requires_exact_judgment_and_authority(tmp_path, shared_core_binary, native_cli):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(".agentic-workspace/local/\n")
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[system_intent]\nsources=["SYSTEM_INTENT.md"]\npreferred_source="SYSTEM_INTENT.md"\n')
    governing = tmp_path / "SYSTEM_INTENT.md"
    governing.write_text("Preserve human why; keep tools quiet.\n", encoding="utf-8")
    mirror = tmp_path / MIRROR
    mirror.parent.mkdir()
    old = 'schema_version=1\nkind="agentic-workspace/system-intent/v1"\nsummary="Older interpretation"\nneeds_review=false\n'
    mirror.write_text(old)
    context = {"target": str(tmp_path), "task": "Reconcile retained interpretation"}

    def call(**extra):
        return consume("native", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    stale = call()["system_intent"]
    assert "retained-interpretation-source-currentness-unproven" in stale["gaps"]
    read = next(r for r in stale["requests"] if r["arguments"]["reference"] == "SYSTEM_INTENT.md")
    assert call(request=read)["system_intent"]["response"]["text"] == governing.read_bytes().decode()
    request = copy.deepcopy(stale["reconciliation"]["requests"][0])
    assert call(request=request)["system_intent"]["reconciliation"]["status"] == "semantic-judgment-required"
    post = (
        old.replace("Older interpretation", "Preserve human why through quiet tools")
        + 'preferred_source="SYSTEM_INTENT.md"\n[[source_records]]\npath="SYSTEM_INTENT.md"\npresent=true\nsha256="'
        + hashlib.sha256(governing.read_text().encode()).hexdigest()
        + '"\n'
    )
    request["arguments"].update(
        content=post, judgment="revised", reason="The previous summary omitted human why and quietness; both are now explicit."
    )
    proposed = call(request=request)
    assert proposed["system_intent"]["reconciliation"]["status"] == "owner-decision-required"
    assert proposed["decision_packet"]["primary_action"] is None
    assert proposed["system_intent"]["gaps"] == stale["gaps"]
    assert mirror.read_text() == old
    answer = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "intent-write-authorization")[
        "response_request"
    ]
    answer["arguments"]["answer"] = "defer"
    assert call(request=answer)["system_intent"]["gaps"] == stale["gaps"]
    answer["arguments"]["answer"] = "authorize-write"
    ready = call(request=answer)
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "system-intent.write"
    # A changed retained interpretation or policy invalidates the accepted proposal too.
    for source in (mirror, config):
        original = source.read_bytes()
        source.write_bytes(
            original + (b'\n[workspace]\ncli_invoke="different-aw"\n' if source == config else b"\n# Concurrent owner change\n")
        )
        with pytest.raises(AssertionError):
            call(request=answer)
        source.write_bytes(original)
    before = governing.read_bytes()
    governing.write_bytes(before + b"New human intent\n")
    for extra in ({"request": answer}, {"invocation": action}):
        with pytest.raises(AssertionError):
            call(**extra)
    assert mirror.read_text() == old
    governing.write_bytes(before)
    forged = copy.deepcopy(answer)
    forged["arguments"]["content"] = post.replace("quiet tools", "loud tools")
    with pytest.raises(AssertionError, match="exact semantic proposal"):
        call(request=forged)
    result = call(invocation=action)
    assert result["status"] == "applied"
    assert mirror.read_text() == post
    current = call()["system_intent"]
    assert current["interpretation"]["source_currentness"] == "matched"
    assert current["interpretation"]["alignment"] == "unresolved-owner-judgment"  # No automatic larger-task alignment claim.
    assert current["gaps"] == []
    assert current["reconciliation"]["requests"] == []
    assert "boundary" not in current["reconciliation"]
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "Unrelated HEAD",
        ],
        check=True,
    )
    assert call()["system_intent"]["revision"] == current["revision"]
    # Interrupted outcome recovery confirms the exact source; it does not republish.
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    recovery = call()["system_intent"]["reconciliation"]["recovery_requests"][0]
    governing.write_bytes(before + b"New human intent\n")
    with pytest.raises(AssertionError):
        call(request=recovery)
    governing.write_bytes(before)
    repaired = call(invocation=call(request=recovery)["decision_packet"]["primary_action"])
    assert repaired["status"] == "applied"
    assert mirror.read_text() == post
    assert call()["system_intent"]["reconciliation"]["recovery_requests"] == []

    # Committed historical bytes cannot suppress a fresh current publication,
    # including a later return to the same source preimage in this effect store.
    for preimage in (old + "\n# another source state\n", old):
        mirror.write_text(preimage)
        request = call()["system_intent"]["reconciliation"]["requests"][0]
        request["arguments"].update(content=post, judgment="revised", reason="Restore the faithful current interpretation.")
        proposed = call(request=request)
        answer = next(
            d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "intent-write-authorization"
        )["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        restored = call(invocation=call(request=answer)["decision_packet"]["primary_action"])
        assert restored["effect_outcome"]["status"] == "committed"
        assert mirror.read_text() == post
        current = call()["system_intent"]
        read_mirror = next(r for r in current["requests"] if r["arguments"]["reference"] == MIRROR)
        request = call(request=read_mirror)["system_intent"]["reconciliation"]["requests"][0]
        request["arguments"].update(content=post, judgment="faithful", reason="The exact current interpretation is already present.")
        noop = call(request=request)
        assert noop["system_intent"]["reconciliation"]["status"] == "already-current"
        assert noop["decision_packet"]["primary_action"] is None

    # An accepted answer cannot waive another owner's path protection.
    from tests.test_native_instruction_write import instruction

    _, _, guard = instruction(
        call, ".agentic-workspace/instructions/guard.md", f"---\nprotect: [{MIRROR}]\n---\nPreserve the interpretation.\n"
    )
    call(invocation=guard)
    governing.write_bytes(before + b"Preserve repository ownership too.\n")
    request = call()["system_intent"]["reconciliation"]["requests"][0]
    request["arguments"].update(
        content=post.replace(
            hashlib.sha256(before.decode().replace("\r\n", "\n").encode()).hexdigest(),
            hashlib.sha256(governing.read_text().encode()).hexdigest(),
        ),
        judgment="faithful",
        reason="The retained summary still represents human why; ownership is preserved.",
    )
    proposed = call(request=request)
    answer = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "intent-write-authorization")[
        "response_request"
    ]
    answer["arguments"]["answer"] = "authorize-write"
    blocked = call(request=answer)
    assert blocked["decision_packet"]["primary_action"] is None
    assert any("protected" in b["code"] for b in blocked["decision_packet"]["blockers"])
    assert mirror.read_text() == post


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_matched_interpretation_can_be_semantically_corrected(tmp_path, shared_core_binary, native_cli, surface):
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('[system_intent]\nsources=["SYSTEM_INTENT.md"]\n')
    governing = tmp_path / "SYSTEM_INTENT.md"
    governing.write_text("Preserve specific architectural constraints.\n", encoding="utf-8")
    mirror = tmp_path / MIRROR
    mirror.parent.mkdir()
    original = (
        'schema_version=1\nkind="agentic-workspace/system-intent/v1"\n'
        'summary="Generic summary"\nneeds_review=false\npreferred_source="SYSTEM_INTENT.md"\n'
        '[[source_records]]\npath="SYSTEM_INTENT.md"\npresent=true\nsha256="'
        + hashlib.sha256(governing.read_text().encode()).hexdigest()
        + '"\n'
    )
    mirror.write_text(original, encoding="utf-8")
    context = {"target": str(tmp_path), "task": "Correct semantic interpretation"}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    quiet = call()["system_intent"]
    assert quiet["interpretation"]["source_currentness"] == "matched"
    assert quiet["gaps"] == []
    assert quiet["reconciliation"]["requests"] == []
    governing_read = next(r for r in quiet["requests"] if r["arguments"]["reference"] == "SYSTEM_INTENT.md")
    assert call(request=governing_read)["system_intent"]["reconciliation"]["requests"] == []
    retained_read = next(r for r in quiet["requests"] if r["arguments"]["reference"] == MIRROR)
    selected = call(request=retained_read)["system_intent"]
    edit = selected["reconciliation"]["requests"][0]
    corrected = original.replace("Generic summary", "Preserve specific architectural constraints")
    edit["arguments"].update(content=corrected, judgment="revised", reason="The matching mirror lost specific source meaning.")
    proposed = call(request=edit)
    assert mirror.read_text() == original
    answer = next(d for d in proposed["decision_packet"]["pending_consequences"]["decisions"] if d["id"] == "intent-write-authorization")[
        "response_request"
    ]
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    assert call(invocation=action)["status"] == "applied"
    assert mirror.read_text() == corrected
    current = call()["system_intent"]
    assert current["interpretation"]["source_currentness"] == "matched"
    assert current["interpretation"]["alignment"] == "unresolved-owner-judgment"
    assert current["reconciliation"]["requests"] == []
