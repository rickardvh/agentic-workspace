"""Native Memory requires independently admitted whole-lesson absorption."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli
from tests.test_shared_core import _commit_native, _native_archive, _write_native


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_memory_exact_disposition_preserves_sources_and_rejects_drift(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    reference = ".agentic-workspace/memory/repo/decisions/former.md"
    note = tmp_path / reference
    note.parent.mkdir(parents=True)
    note.write_text("A faithful former-source lesson.\n", encoding="utf-8")
    manifest = note.parent.parent / "manifest.toml"
    before = f'version=1\n# Human corpus comment\n[notes."{reference}"]\nroutes_from=["src/**"] # retain\n\n[unrelated]\nvalue="preserve"\n'
    manifest.write_text(before, encoding="utf-8", newline="")
    context = {"target": str(tmp_path), "task": "Assess one former note", "changed": ["src/core.rs"]}

    def call(value: dict | None = None) -> dict:
        return consume(surface, shared_core_binary, native_cli, value or context)

    initial = call()
    request = initial["memory"]["disposition"]["requests"][0]
    request["arguments"].update(disposition="retire", reason="Fixture human determines this note is obsolete and has no future value.")
    proposed = call({**context, "request": request})
    assert manifest.read_text() == before
    assert not (tmp_path / ".agentic-workspace/local").exists()
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    deferred = call({**context, "request": {**answer, "arguments": {**answer["arguments"], "answer": "defer"}}})
    assert deferred["memory"]["disposition"]["status"] == "deferred"
    assert manifest.read_text() == before
    answer["arguments"]["answer"] = "authorize-disposition"  # fixture, not real corpus authorization
    ready = call({**context, "request": answer})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "memory.dispose"
    manifest.write_text(before + "# intervening human edit\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="changed|stale"):
        call({**context, "invocation": action})
    manifest.write_text(before, encoding="utf-8", newline="")
    result = call({**context, "invocation": action})
    assert result["value"]["disposition"] == "retire"
    assert result["value"]["continuing_custody"] is False
    assert "# Human corpus comment\n" in manifest.read_text()
    assert 'routes_from=["src/**"] # retain' in manifest.read_text()
    assert '[unrelated]\nvalue="preserve"\n' in manifest.read_text()
    assert note.read_text() == "A faithful former-source lesson.\n"
    retired = call()
    assert retired["memory"]["selected_notes"] == []
    assert retired["memory"]["suppressed_notes"][0]["status"] == "retire"
    with pytest.raises(AssertionError, match="changed|stale"):
        call({**context, "invocation": action})
    note.write_text("A newly relevant lesson.\n", encoding="utf-8")
    renewed = call()
    assert len(renewed["memory"]["selected_notes"]) == 1
    assert renewed["memory"]["disposition"]["diagnostics"][0]["code"] == "disposition-currentness-lost"

    # Restoring the preimage cannot revive a consumed one-shot answer (ABA).
    note.write_text("A faithful former-source lesson.\n", encoding="utf-8")
    manifest.write_text(before, encoding="utf-8", newline="")
    with pytest.raises(AssertionError, match="consumed"):
        call({**context, "invocation": action})
    manifest.write_text(before.replace("version=1", "version=2"), encoding="utf-8")
    unsupported = call()
    assert unsupported["memory"]["disposition"]["requests"] == []
    assert len(unsupported["memory"]["selected_notes"]) == 1


@pytest.mark.parametrize("parent", ["local", "local/effects"])
def test_memory_disposition_confines_publication_scratch(tmp_path: Path, shared_core_binary: Path, native_cli: Path, parent: str) -> None:
    import subprocess

    target = tmp_path / "target"
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    reference = ".agentic-workspace/memory/repo/decisions/former.md"
    note = target / reference
    note.parent.mkdir(parents=True)
    note.write_text("Useful advisory source.", encoding="utf-8")
    manifest = note.parent.parent / "manifest.toml"
    before = f'version=1\n[notes."{reference}"]\nroutes_from=["src/**"]\n'.encode()
    manifest.write_bytes(before)
    context = {"target": str(target), "task": "Fixture confined disposition", "changed": ["src/core.rs"]}

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value)

    request = call(context)["memory"]["disposition"]["requests"][0]
    answer = call({**context, "request": request})["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-disposition"
    action = call({**context, "request": answer})["decision_packet"]["primary_action"]
    link = target / ".agentic-workspace" / parent
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        linked = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
        assert linked.returncode == 0, linked.stderr
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(AssertionError, match="link|confined|reparse"):
        call({**context, "invocation": action})
    assert list(outside.iterdir()) == []
    assert manifest.read_bytes() == before


@pytest.mark.parametrize("subject", ["note", "fact"])
@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_memory_receiver_needs_current_admitted_whole_lesson(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, subject: str
) -> None:
    _, record = _native_archive(tmp_path)
    reference = ".agentic-workspace/memory/repo/decisions/former.md"
    note = tmp_path / reference
    note.parent.mkdir(parents=True)
    lesson = "Preserve the selected owner's scope and unresolved constraints."
    note.write_text(lesson if subject == "note" else lesson + "\nAnother lesson remains advisory.", encoding="utf-8")
    manifest = note.parent.parent / "manifest.toml"
    manifest.write_text(f'version=1\n[notes."{reference}"]\nroutes_from=["src/**"]\n', encoding="utf-8")
    if subject == "fact":
        import json

        with manifest.open("a", encoding="utf-8") as stream:
            stream.write(
                f'\n[durable_facts."{record["id"]}"]\nsummary={json.dumps(lesson)}\n'
                f'note_ref="{reference}"\nauthority_class="advisory"\nowner="decision-continuity"\n'
            )
    original = manifest.read_bytes(), note.read_bytes()
    config = tmp_path / ".agentic-workspace/config.toml"
    context = {"target": str(tmp_path), "task": "Maintain the former lesson", "changed": ["src/core.rs"]}

    def admit() -> None:
        _write_native(tmp_path / "design/choice.md", record)
        revision = _commit_native(tmp_path)
        config.write_text(
            'schema_version=1\n[modules]\nenabled=["memory"]\n[assurance]\n'
            f'decision_record_target="design"\ndecision_record_revision="{revision}"\n',
            encoding="utf-8",
        )

    def call(value: dict | None = None) -> dict:
        return consume(surface, shared_core_binary, native_cli, value or context, host_path=os.environ["PATH"])

    # These are explicit fixture repository admissions, never approvals of the
    # real corpus. Matching prose alone does not acknowledge its source identity.
    record["consequence"] = lesson
    admit()
    assert call()["memory"]["receiving_admissions"] == []
    record["context"] = [
        {
            "owner": "repository",
            "reference": reference,
            "revision": "sha256:" + hashlib.sha256(note.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        }
    ]
    admit()
    current = call()
    receivers = current["memory"]["receiving_admissions"]
    assert len(receivers) == 1
    assert receivers[0]["receiving_admission"]["id"] == record["id"]
    assert receivers[0]["disposition_authorized"] is False
    assert receivers[0]["completion_authority"] is False
    assert len(current["memory"]["selected_notes"]) == 1
    quiet = call({**context, "changed": ["unrelated.txt"]})
    assert "receiving_admissions" not in quiet["memory"]
    assert "disposition" not in quiet["memory"]
    assert all(not owner.get("operations") for owner in quiet["capability_contract"]["owners"] if owner["owner"] == "memory")
    # Admission of an excerpt cannot hide another lesson in the source.
    note.write_text(lesson + "\nPreserve independent review as well.", encoding="utf-8")
    assert call()["memory"]["receiving_admissions"] == []
    note.write_bytes(original[1])
    authority = tmp_path / "authority.md"
    authority.write_text("The old deciding authority is no longer current.\n", encoding="utf-8")
    stale = call()
    assert stale["memory"]["receiving_admissions"] == []
    assert len(stale["memory"]["selected_notes"]) == 1
    assert (manifest.read_bytes(), note.read_bytes()) == original
    assert not (tmp_path / ".agentic-workspace/local").exists()

    # Full exact promotion is a separate fixture human decision. Receiving
    # admission is necessary but never authorizes this write by itself.
    authority.write_text("Human owner admits this bounded decision.\n", encoding="utf-8")
    current = call()
    request = next(r for r in current["memory"]["disposition"]["requests"] if ("fact" in r["arguments"]) == (subject == "fact"))
    request["arguments"].update(
        disposition="promote",
        reason="Fixture owner authorizes the whole retained lesson's promotion.",
        receiver=receivers[0]["receiving_admission"],
    )
    forged = {**request, "arguments": {**request["arguments"], "receiver": {"id": record["id"]}}}
    with pytest.raises(AssertionError, match="receiving-owner admission"):
        call({**context, "request": forged})
    original_manifest = manifest.read_bytes()
    manifest.write_bytes(
        original_manifest.replace(b'routes_from=["src/**"]', b'routes_from=["src/**"]\ncontradicted_by=["current-policy"]')
    )
    fresh = call()["memory"]["disposition"]["requests"]
    contradiction = next(r for r in fresh if ("fact" in r["arguments"]) == (subject == "fact"))
    contradiction["arguments"] = request["arguments"].copy()
    with pytest.raises(AssertionError, match="contradictions"):
        call({**context, "request": contradiction})
    manifest.write_bytes(original_manifest)
    proposed = call({**context, "request": request})
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-disposition"
    action = call({**context, "request": answer})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    assert result["value"]["disposition"] == "promote"
    admitted = call()["memory"]
    assert len(admitted["selected_notes"]) == (1 if subject == "fact" else 0)
    assert admitted["suppressed_facts" if subject == "fact" else "suppressed_notes"][0]["status"] == "promote"
    assert note.read_bytes() == original[1]
    # Loss of the receiving owner exposes the retained note and blocks effects;
    # neither a historical result nor the manifest's promotion string suffices.
    (tmp_path / "design/choice.md").unlink()
    lost = call()
    assert len(lost["memory"]["selected_notes"]) == 1
    assert lost["decision_packet"]["primary_action"] is None
    assert any(b["code"] == "receiving-decision-source-unavailable" for b in lost["decision_packet"]["blockers"])
