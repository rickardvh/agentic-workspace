from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, Sequence

HOST_IDENTITY_ENV = "CODEX_THREAD_ID"
AW_IDENTITY_ENV = "AW_SESSION_LOGICAL_IDENTITY"
DEFAULT_AW_INVOKE = "agentic-workspace"


def _target_from_args(args: Sequence[str]) -> Path:
    for index, value in enumerate(args):
        if value == "--target" and index + 1 < len(args):
            return Path(args[index + 1]).resolve()
        if value.startswith("--target="):
            return Path(value.split("=", 1)[1]).resolve()
    return Path.cwd().resolve()


def _configured_invocation(target: Path) -> str:
    for relative in (
        Path(".agentic-workspace/config.local.toml"),
        Path(".agentic-workspace/config.toml"),
    ):
        path = target / relative
        if not path.is_file():
            continue
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        workspace = payload.get("workspace") if isinstance(payload, dict) else None
        invocation = str(workspace.get("cli_invoke") or "").strip() if isinstance(workspace, dict) else ""
        if invocation:
            return invocation
    return DEFAULT_AW_INVOKE


def _command_tokens(invocation: str) -> list[str]:
    return shlex.split(invocation, posix=True)


def _dry_run_payload(*, target: Path, invocation: str, aw_args: list[str], identity_source: str) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/agent-aid-codex-session-identity/v1",
        "status": "would-run",
        "target": target.as_posix(),
        "command": [*_command_tokens(invocation), *aw_args],
        "identity_bridge": {
            "source": identity_source,
            "destination": AW_IDENTITY_ENV,
            "raw_identity_exposed": False,
        },
        "authority": "Invocation adapter only; the selected AW command retains its ordinary mutation and proof authority.",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the configured AW invocation with the Codex thread identity mapped to AW's portable session identity."
    )
    parser.add_argument("--dry-run", action="store_true", help="Show the command and identity mapping without invoking AW.")
    parser.add_argument("aw_args", nargs=argparse.REMAINDER, help="Arguments for the configured AW invocation, normally after --.")
    parsed = parser.parse_args(list(argv) if argv is not None else None)
    aw_args = list(parsed.aw_args)
    if aw_args[:1] == ["--"]:
        aw_args = aw_args[1:]
    if not aw_args:
        parser.error("provide AW arguments after --")

    existing_identity = os.environ.get(AW_IDENTITY_ENV, "").strip()
    host_identity = os.environ.get(HOST_IDENTITY_ENV, "").strip()
    identity = existing_identity or host_identity
    identity_source = AW_IDENTITY_ENV if existing_identity else HOST_IDENTITY_ENV if host_identity else ""
    if not identity:
        print(
            json.dumps(
                {
                    "kind": "agentic-workspace/agent-aid-codex-session-identity/v1",
                    "status": "identity-unavailable",
                    "required_source": HOST_IDENTITY_ENV,
                    "accepted_existing_destination": AW_IDENTITY_ENV,
                    "rule": "Do not invent a session identity from branch, task text, PID, or timestamps.",
                }
            ),
            file=sys.stderr,
        )
        return 2

    target = _target_from_args(aw_args)
    invocation = _configured_invocation(target)
    if parsed.dry_run:
        print(json.dumps(_dry_run_payload(target=target, invocation=invocation, aw_args=aw_args, identity_source=identity_source), indent=2))
        return 0

    env = os.environ.copy()
    env[AW_IDENTITY_ENV] = identity
    completed = subprocess.run([*_command_tokens(invocation), *aw_args], cwd=target, env=env, check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
