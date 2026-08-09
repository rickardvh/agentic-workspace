from __future__ import annotations

import sys
from pathlib import Path

import pytest

from agentic_workspace.trusted_execution import run_argv, run_trusted_shell


def test_trusted_shell_refuses_unadmitted_or_unknown_provenance(tmp_path: Path) -> None:
    with pytest.raises(PermissionError, match="requires an admitted"):
        run_trusted_shell("echo unsafe", trust_source="explicit-user-executor-command", admitted=False, cwd=tmp_path)
    with pytest.raises(PermissionError, match="requires an admitted"):
        run_trusted_shell("echo unsafe", trust_source="untrusted-repository", admitted=True, cwd=tmp_path)


def test_argv_execution_does_not_interpret_shell_metacharacters(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    command = [sys.executable, "-c", "import sys; print(sys.argv[1])", f"literal; echo unsafe > {marker}"]

    completed = run_argv(command, cwd=tmp_path)

    assert completed.returncode == 0
    assert "literal; echo unsafe" in completed.stdout
    assert not marker.exists()


def test_explicit_trusted_shell_preserves_declared_shell_semantics(tmp_path: Path) -> None:
    completed = run_trusted_shell(
        f'"{sys.executable}" -c "print(\'first\')" && "{sys.executable}" -c "print(\'second\')"',
        trust_source="explicit-user-executor-command",
        admitted=True,
        cwd=tmp_path,
    )

    assert completed.returncode == 0
    assert completed.stdout.splitlines() == ["first", "second"]
