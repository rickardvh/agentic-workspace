"""Command construction for the bounded installed-consumer actor.

The former host-mounted standalone launcher is retired. Historical records remain
readable; use run_model_cli_harness.py for new execution.
"""

from __future__ import annotations

import argparse
import shlex
import sys


def _codex_exec_command(
    *,
    args: argparse.Namespace,
    prompt: str,
    sandbox_repo: str,
    sandbox_share_path: str,
    sandbox_prompt_path: str | None = None,
) -> list[str]:
    exec_command = [args.sbx, "exec"]
    for env_value in args.exec_env:
        exec_command.extend(["-e", env_value])
    codex_command = [
        "codex",
        "exec",
        "--model",
        args.model,
        "--config",
        'model_reasoning_effort="' + getattr(args, "reasoning_effort", "medium") + '"',
        "--cd",
        sandbox_repo,
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "--output-last-message",
        sandbox_share_path,
        "--json",
    ]
    if sandbox_prompt_path:
        shell_command = " ".join(shlex.quote(part) for part in [*codex_command, "-"])
        shell_command = f"{shell_command} < {shlex.quote(sandbox_prompt_path)}"
        exec_command.extend([args.sandbox_name, "sh", "-lc", shell_command])
        return exec_command
    codex_command.append(prompt)
    exec_command.extend(
        [
            args.sandbox_name,
            *codex_command,
        ]
    )
    return exec_command


def main(argv: list[str] | None = None) -> int:
    print(
        "Retired launcher: use run_model_cli_harness.py run --driver agent --backend sandbox with an exact subject and bounded budget.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
