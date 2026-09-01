from __future__ import annotations

import os
import shlex
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
    python = f'& "{sys.executable}"' if os.name == "nt" else shlex.quote(sys.executable)
    completed = run_trusted_shell(
        f"{python} -c \"print('first')\" && {python} -c \"print('second')\"",
        trust_source="explicit-user-executor-command",
        admitted=True,
        cwd=tmp_path,
    )

    assert completed.returncode == 0
    assert completed.stdout.splitlines() == ["first", "second"]


def test_trusted_shell_preserves_quoted_multi_token_arguments(tmp_path: Path) -> None:
    test_path = tmp_path / "test_selected_expression.py"
    test_path.write_text(
        "def test_alpha():\n    assert True\n\ndef test_beta():\n    assert True\n\ndef test_other():\n    assert False\n",
        encoding="utf-8",
    )
    completed = run_trusted_shell(
        f"uv run --active pytest \"{test_path}\" -k 'alpha or beta' -q",
        trust_source="checked-repository-proof-route",
        admitted=True,
        cwd=tmp_path,
    )

    assert completed.returncode == 0, completed.stderr
    assert "2 passed, 1 deselected" in completed.stdout
