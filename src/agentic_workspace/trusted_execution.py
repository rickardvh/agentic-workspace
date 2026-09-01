from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

TRUSTED_SHELL_SOURCES = frozenset({"checked-repository-proof-route", "explicit-user-executor-command"})


def _trusted_shell_invocation(command: str) -> tuple[str | list[str], bool]:
    """Select the supported host shell without changing declared command syntax."""
    if os.name != "nt":
        return command, True
    powershell = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
    return [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command], False


def run_trusted_shell(
    command: str,
    *,
    trust_source: str,
    admitted: bool,
    cwd: str | Path,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run shell syntax only after an explicit, reviewable trust admission.

    This is not a sandbox. The command receives the caller's filesystem and
    credential authority. Callers must use argv subprocess execution whenever
    shell parsing is not part of the declared command semantics.
    """
    normalized = str(command or "").strip()
    if not normalized:
        raise ValueError("trusted shell command must not be empty")
    if not admitted or trust_source not in TRUSTED_SHELL_SOURCES:
        raise PermissionError("shell execution requires an admitted repository or explicit-user trust source")
    effective_env = dict(os.environ if env is None else env)
    invocation, use_implicit_shell = _trusted_shell_invocation(normalized)
    return subprocess.run(  # noqa: S602
        invocation,
        cwd=cwd,
        env=effective_env,
        shell=use_implicit_shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def run_argv(
    command: Sequence[str],
    *,
    cwd: str | Path,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    if not command or not all(str(part) for part in command):
        raise ValueError("argv command must contain non-empty arguments")
    effective_env = dict(os.environ if env is None else env)
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=effective_env,
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
