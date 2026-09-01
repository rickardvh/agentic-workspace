from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import pytest

from agentic_workspace.trusted_execution import (
    host_shell_dialect,
    run_argv,
    run_trusted_shell,
    trusted_shell_execution_identity,
)


@pytest.mark.parametrize(
    ("dialect", "trust_source", "admitted", "error"),
    [
        (host_shell_dialect(), "explicit-user-executor-command", False, PermissionError),
        (host_shell_dialect(), "untrusted-repository", True, PermissionError),
        ("", "checked-repository-proof-route", True, ValueError),
        ("cmd", "checked-repository-proof-route", True, ValueError),
        ("posix-sh" if os.name == "nt" else "powershell", "checked-repository-proof-route", True, ValueError),
    ],
    ids=["unadmitted", "unknown-source", "missing-dialect", "unknown-dialect", "host-mismatch"],
)
def test_trusted_shell_refuses_unadmitted_or_unsupported_execution(
    tmp_path: Path, dialect: str, trust_source: str, admitted: bool, error: type[Exception]
) -> None:
    with pytest.raises(error):
        run_trusted_shell(
            "echo unsafe",
            shell_dialect=dialect,
            trust_source=trust_source,
            admitted=admitted,
            cwd=tmp_path,
        )


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
        shell_dialect=host_shell_dialect(),
        trust_source="explicit-user-executor-command",
        admitted=True,
        cwd=tmp_path,
    )

    assert completed.returncode == 0
    assert completed.stdout.splitlines() == ["first", "second"]
    assert trusted_shell_execution_identity(command="echo safe", shell_dialect="posix-sh") != (
        trusted_shell_execution_identity(command="echo safe", shell_dialect="powershell")
    )


def test_trusted_shell_preserves_quoted_multi_token_arguments(tmp_path: Path) -> None:
    test_path = tmp_path / "test_selected_expression.py"
    test_path.write_text(
        "def test_alpha():\n    assert True\n\ndef test_beta():\n    assert True\n\ndef test_other():\n    assert False\n",
        encoding="utf-8",
    )
    completed = run_trusted_shell(
        f"uv run --active pytest \"{test_path}\" -k 'alpha or beta' -q",
        shell_dialect=host_shell_dialect(),
        trust_source="checked-repository-proof-route",
        admitted=True,
        cwd=tmp_path,
    )

    assert completed.returncode == 0, completed.stderr
    assert "2 passed, 1 deselected" in completed.stdout
