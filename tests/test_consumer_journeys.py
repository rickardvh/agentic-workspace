"""The existing installed smoke must finish ordinary work, not only launch AW."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from tests.test_native_public_cli import native_cli as native_cli

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/tooling/release"))
import pytest
from consumer_journeys import INDEPENDENT_NOTES, Workspace, check_removed, check_stale_rejection, clean_context_snapshot  # noqa: E402
from first_contact import journey  # noqa: E402


def test_public_first_contact_finishes_task_and_preserves_repository(tmp_path, native_cli):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    journey([str(native_cli)], tmp_path, dict(os.environ))
    assert '"port":8081' in (tmp_path / "settings.json").read_text()
    assert "8081" in (tmp_path / "README.md").read_text()
    assert (tmp_path / "notes.txt").read_text() == "Repository-owned note: keep this file.\n"
    assert (tmp_path / "AGENTS.md").read_text().startswith("Repository-owned instructions:")


def test_removal_cannot_pass_from_final_re_adopted_state():
    before = {**INDEPENDENT_NOTES, "policy.md": b"policy", "notes.txt": b"notes"}
    after = {**before, ".agentic-workspace/skills/workspace-startup/SKILL.md": b"still installed"}
    with pytest.raises(ValueError, match="package foothold"):
        check_removed(before, after)
    after.pop(".agentic-workspace/skills/workspace-startup/SKILL.md")
    check_removed(before, after)
    after["notes.txt"] = b"lost"
    with pytest.raises(ValueError, match="independently owned"):
        check_removed(before, after)


def test_stale_guard_crash_is_not_a_successful_rejection():
    class Broken:
        def files(self):
            return {"policy.md": b"unchanged"}

        def invoke(self, action):
            raise subprocess.CalledProcessError(1, ["missing"], output="")

    with pytest.raises(ValueError):
        check_stale_rejection(Broken(), {})


@pytest.mark.parametrize("name", ["../outside", "/absolute", "nested/../../outside", "..\\outside", "node_modules/tool", ".git/config"])
def test_continuation_rejects_unsafe_transfer_before_writing(name):
    class Consumer:
        def write_file(self, *args):
            pytest.fail("Unsafe snapshot transferred")

    with pytest.raises(ValueError, match="Unsafe continuation"):
        Workspace(Consumer()).restore({name: b"untrusted"})


def test_stalled_export_is_bounded_before_archive_header(monkeypatch):
    import tarfile

    import consumer_journeys

    class Consumer:
        name = "fixture"

        def archive_command(self):
            return [sys.executable, "-c", "import time; time.sleep(60)"]

    monkeypatch.setattr(consumer_journeys, "EXPORT_SECONDS", 0.1)
    started = time.monotonic()
    with pytest.raises((ValueError, tarfile.ReadError)):
        Workspace(Consumer()).files()
    assert time.monotonic() - started < 5


def test_export_failure_keeps_bounded_diagnostic_tail():
    class Consumer:
        name = "fixture"

        def archive_command(self):
            return [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('x'*65536+'EXPORT_CAUSE'); sys.stdout.buffer.write(bytes(10240)); sys.exit(2)",
            ]

    with pytest.raises(ValueError, match="EXPORT_CAUSE") as failure:
        Workspace(Consumer()).files()
    assert len(str(failure.value)) < 4200


def test_clean_context_preserves_selected_meaning_without_disposable_transport():
    plan = ".agentic-workspace/planning/execplans/maintenance.plan.json"
    selection = ".agentic-workspace/local/planning/owner-selection.json"
    before = {"AGENTS.md": b"source", "settings.json": b"8080", ".agentic-workspace/local/.gitignore": b"*"}
    retained = {plan: b'{"next_action":"Create delayed client with retry 7"}'}
    disposable = {
        ".agentic-workspace/local/scratch/task/carrier.json": b'{"kind":"agentic-workspace/operating-carriage/v1"}',
        "arbitrary-name.json": b'{"carriage":{"kind":"agentic-workspace/operating-carriage/v1"}}',
        "delivery.json": b'{"available_sources":["policy.md"]}',
        "helper.py": b"prior transport script",
        ".agentic-workspace/local/planning/request.json": b"prior request",
    }
    intact = {
        **before,
        **retained,
        **disposable,
        "settings.json": b"8081",
        selection: json.dumps({"selected_owner": {"ref": plan}}).encode(),
    }
    transferred = clean_context_snapshot(before, intact, retained)
    assert transferred == {"AGENTS.md": b"source", "settings.json": b"8081", **retained, selection: intact[selection]}
    assert not set(disposable) & transferred.keys()
