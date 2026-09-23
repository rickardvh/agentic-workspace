"""The existing installed smoke must finish ordinary work, not only launch AW."""

import os
import subprocess
import sys
from pathlib import Path

from tests.test_native_public_cli import native_cli as native_cli

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/tooling/release"))
import pytest
from consumer_journeys import INDEPENDENT_NOTES, check_removed, check_stale_rejection  # noqa: E402
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
