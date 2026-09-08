"""The optional Python command and source launcher cannot regain CLI semantics."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]
PYTHON_CLI = [sys.executable, "-c", "from agentic_workspace.cli import main; raise SystemExit(main())"]
SOURCE_CLI = [sys.executable, str(ROOT / "scripts/run_agentic_workspace.py")]


@pytest.mark.parametrize("condition", ["current", "future-reader", "retired-command"])
def test_python_launchers_preserve_native_command_admission(tmp_path, shared_core_binary, native_cli, condition):
    target = tmp_path / "target with spaces"
    target.mkdir()
    retained = target / "unrelated.txt"
    retained.write_text("Preserve unrelated work.")
    if condition == "future-reader":
        config = target / ".agentic-workspace/config.toml"
        config.parent.mkdir()
        config.write_text("schema_version=1\n[cli_compatibility]\nminimum_reader_epoch=999\n")
    command = "config" if condition == "retired-command" else "start"
    args = [command, "--target", str(target), "--task", "Inspect the bounded source", "--format", "json"]
    env = {**os.environ, "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)}

    def run(prefix):
        return subprocess.run([*prefix, *args], cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True, check=False)

    expected = run([str(native_cli)])
    assert expected.returncode == (2 if condition == "retired-command" else 0)
    if condition == "future-reader":
        blocked = json.loads(expected.stdout)
        assert blocked["status"] == "blocked" and blocked["managed_state_interpreted"] is False
    for launcher in [PYTHON_CLI, SOURCE_CLI]:
        actual = run(launcher)
        assert (actual.returncode, actual.stdout, actual.stderr) == (expected.returncode, expected.stdout, expected.stderr)
    assert retained.read_text() == "Preserve unrelated work."
    assert not (target / ".agentic-workspace/local").exists()


def test_missing_paired_cli_has_no_generated_or_installed_package_fallback(tmp_path, shared_core_binary):
    core = tmp_path / shared_core_binary.name
    shutil.copy2(shared_core_binary, core)
    target = tmp_path / "target"
    target.mkdir()
    env = {**os.environ, "AGENTIC_WORKSPACE_CORE_BINARY": str(core)}
    args = ["start", "--target", str(target), "--task", "Inspect current sources", "--format", "json"]
    for launcher in [PYTHON_CLI, SOURCE_CLI]:
        result = subprocess.run([*launcher, *args], cwd=ROOT, env=env, text=True, encoding="utf-8", capture_output=True, check=False)
        assert result.returncode == 2 and not result.stdout
        assert "native Agentic Workspace CLI is unavailable" in result.stderr
    assert list(target.iterdir()) == []

    # A source runner resolves its own artifact helper even when another Python
    # package is earlier on the import path. That package must not be imported.
    foreign = tmp_path / "foreign/agentic_workspace"
    foreign.mkdir(parents=True)
    (foreign / "__init__.py").write_text("raise AssertionError('foreign semantic host imported')")
    result = subprocess.run(
        [*SOURCE_CLI, *args],
        cwd=tmp_path,
        env={**env, "PYTHONPATH": str(foreign.parent)},
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2 and "native Agentic Workspace CLI is unavailable" in result.stderr
    assert "foreign semantic host" not in result.stderr and list(target.iterdir()) == []
