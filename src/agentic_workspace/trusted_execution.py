from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

TRUSTED_SHELL_SOURCES = frozenset({"checked-repository-proof-route", "explicit-user-executor-command"})
POSIX_SHELL_DIALECT = "posix-sh"
POWERSHELL_DIALECT = "powershell"
SUPPORTED_SHELL_DIALECTS = frozenset({POSIX_SHELL_DIALECT, POWERSHELL_DIALECT})


def host_shell_dialect() -> str:
    """Return the one shell dialect this host can execute through the trusted boundary."""
    return POWERSHELL_DIALECT if os.name == "nt" else POSIX_SHELL_DIALECT


def trusted_shell_execution_identity(*, command: str, shell_dialect: str) -> str:
    """Bind stored execution identity to command text and its declared parser."""
    material = json.dumps(
        {"kind": "agentic-workspace/trusted-shell-command/v1", "command": command, "shell_dialect": shell_dialect},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _trusted_shell_invocation(command: str, *, shell_dialect: str) -> list[str]:
    """Build an explicit supported-shell argv without implicit host-shell selection."""
    if shell_dialect not in SUPPORTED_SHELL_DIALECTS:
        raise ValueError(f"unsupported trusted shell dialect: {shell_dialect or '<missing>'}")
    expected = host_shell_dialect()
    if shell_dialect != expected:
        raise ValueError(f"trusted shell dialect {shell_dialect!r} is unsupported on this host; expected {expected!r}")
    if shell_dialect == POSIX_SHELL_DIALECT:
        shell = shutil.which("sh") or "/bin/sh"
        return [shell, "-c", command]
    powershell = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
    return [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command]


def run_trusted_shell(
    command: str,
    *,
    shell_dialect: str,
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
    invocation = _trusted_shell_invocation(normalized, shell_dialect=str(shell_dialect or "").strip())
    return subprocess.run(
        invocation,
        cwd=cwd,
        env=effective_env,
        shell=False,
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
