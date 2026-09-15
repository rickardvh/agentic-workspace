"""Selected skill mechanics consume fresh owners and preserve their boundaries."""

import json
import subprocess
import sys
from pathlib import Path

from tests.test_native_public_cli import native_cli as native_cli

SCRIPT = Path(__file__).resolve().parents[1] / ".agentic-workspace/skills/workspace-intent-discovery/prepare.py"


def test_preference_preparation_and_currentness(tmp_path, native_cli):
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    local = root / "config.local.toml"
    shared = root / "config.toml"

    def run(procedure="intent", judgment="ambiguous", *extra):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--native-cli",
                str(native_cli),
                "--target",
                str(tmp_path),
                "--task",
                "Choose an outcome",
                "--procedure",
                procedure,
                "--judgment",
                judgment,
                *extra,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    for mode, posture in [
        ("ask-first", "await-human-answer"),
        ("suggest", "surface-question-and-safe-assumptions"),
        ("auto-continue", "state-bounded-interpretation"),
    ]:
        local.write_text(f'[clarification]\nmode="{mode}"\n')
        assert run()["posture"] == posture
        assert run(judgment="clear")["posture"] == "direct"
        assert run(judgment="required-decision")["posture"] == "await-required-owner"
    prepared = run()
    (tmp_path / "unrelated.md").write_text("Unrelated work")
    assert run("intent", "ambiguous", "--expected-revision", prepared["revision"])["status"] == "prepared"
    local.write_text('[clarification]\nmode="ask-first"\n')
    assert run("intent", "ambiguous", "--expected-revision", prepared["revision"])["status"] == "stale"
    for latitude, expected in [
        ("none", "no-action"),
        ("reporting", "report"),
        ("conservative", "prepare-current-owner-proposal"),
        ("proactive", "prepare-current-owner-proposal"),
    ]:
        shared.write_text(f'[workspace]\nimprovement_latitude="{latitude}"\n')
        assert run("improvement")["posture"] == expected
        assert run("improvement", "clear")["posture"] == "no-action"
        assert run("improvement", "required-decision")["posture"] == "await-required-owner"
        expected = "prepare-current-owner-proposal" if latitude == "proactive" else "no-action" if latitude == "none" else "report"
        assert run("improvement", "ambiguous", "--scope", "proactive")["posture"] == expected
    shared.write_text('[workspace]\nimprovement_latitude="balanced"\n')
    assert run()["status"] == "unavailable"
    assert not (root / "local").exists()


def test_planning_preparation_exposes_current_policy_without_creating_work(tmp_path, native_cli):
    directory = tmp_path / ".agentic-workspace/instructions"
    directory.mkdir(parents=True)
    policy = directory / "planning.md"
    policy.write_text("Use durable Planning for accepted cross-session work.\n")
    command = [
        sys.executable,
        str(SCRIPT),
        "--native-cli",
        str(native_cli),
        "--target",
        str(tmp_path),
        "--task",
        "Continue accepted work",
        "--procedure",
        "planning",
        "--judgment",
        "clear",
    ]
    first = json.loads(subprocess.check_output(command, text=True))
    assert "accepted cross-session" in json.dumps(first["instructions"])
    policy.write_text("Keep this task direct; no durable continuity is needed.\n")
    second = json.loads(subprocess.check_output(command, text=True))
    assert "Keep this task direct" in json.dumps(second["instructions"])
    assert first["revision"] != second["revision"]
    assert first["effects"] == second["effects"] == []
    assert not (tmp_path / ".agentic-workspace/planning").exists()
