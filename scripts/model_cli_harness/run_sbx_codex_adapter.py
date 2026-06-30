"""Host-side bridge for running Codex non-interactively in Docker Sandboxes."""

from __future__ import annotations

import argparse
import posixpath
import re
import shlex
import subprocess
import sys
from pathlib import Path

WINDOWS_COMMAND_LINE_LIMIT = 32000


def _run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(  # noqa: S603
        command,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if capture:
        if process.stdout:
            print(process.stdout, end="", flush=True)
        if process.stderr:
            print(process.stderr, end="", file=sys.stderr, flush=True)
    return process


def _returncode(command: list[str]) -> int:
    process = _run(command)
    return int(process.returncode)


def _prompt_from_args(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return args.prompt or ""


def _sandbox_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    match = re.match(r"^([A-Za-z]):/(.*)$", normalized)
    if not match:
        return normalized
    return f"/{match.group(1).lower()}/{match.group(2)}"


def _codex_exec_command(
    *,
    args: argparse.Namespace,
    prompt: str,
    sandbox_repo: str,
    sandbox_share_path: str,
) -> list[str]:
    exec_command = [args.sbx, "exec"]
    for env_value in args.exec_env:
        exec_command.extend(["-e", env_value])
    exec_command.extend(
        [
            args.sandbox_name,
            "codex",
            "exec",
            "--model",
            args.model,
            "--cd",
            sandbox_repo,
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--output-last-message",
            sandbox_share_path,
            "--json",
            prompt,
        ]
    )
    return exec_command


def _windows_command_line_length(command: list[str]) -> int:
    return len(subprocess.list2cmdline(command))


def _windows_command_length_error(command: list[str], *, prompt_file: str | None) -> str | None:
    if sys.platform != "win32":
        return None
    command_length = _windows_command_line_length(command)
    if command_length < WINDOWS_COMMAND_LINE_LIMIT:
        return None
    source = f" from prompt file {prompt_file}" if prompt_file else ""
    return (
        "codex-sbx cannot safely pass this large prompt through the Windows command line"
        f"{source}: rendered command is {command_length} characters, limit is {WINDOWS_COMMAND_LINE_LIMIT}. "
        "Refusing before sandbox/model execution. Use the plain codex adapter's file-backed prompt transport "
        "or reduce the prompt until codex-sbx grows in-sandbox prompt-file support."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbx", default="sbx")
    parser.add_argument("--sandbox-name", required=True)
    parser.add_argument("--template")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--share-path", required=True)
    parser.add_argument("--exec-env", action="append", default=[])
    parser.add_argument("--keep-sandbox", action="store_true", help="Leave the named sandbox running for debugging.")
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    args = parser.parse_args(argv)

    prompt = _prompt_from_args(args)
    sandbox_repo = _sandbox_path(args.repo)
    sandbox_share_path = _sandbox_path(args.share_path)
    exec_command = _codex_exec_command(
        args=args,
        prompt=prompt,
        sandbox_repo=sandbox_repo,
        sandbox_share_path=sandbox_share_path,
    )
    command_length_error = _windows_command_length_error(exec_command, prompt_file=args.prompt_file)
    if command_length_error:
        print(command_length_error, file=sys.stderr, flush=True)
        return 2

    create_command = [args.sbx, "create", "--name", args.sandbox_name]
    if args.template:
        create_command.extend(["--template", args.template])
    create_command.extend(["codex", args.repo])
    create = _run(create_command, capture=True)
    create_output = f"{create.stdout or ''}\n{create.stderr or ''}".lower()
    if create.returncode != 0 and "already exists" in create_output:
        remove_stale = _returncode([args.sbx, "rm", "--force", args.sandbox_name])
        if remove_stale != 0:
            return remove_stale
        create = _run(create_command, capture=True)
    if create.returncode != 0:
        return int(create.returncode)

    return_code = 1
    try:
        mkdir = _returncode(
            [
                args.sbx,
                "exec",
                args.sandbox_name,
                "sh",
                "-lc",
                f"mkdir -p {shlex.quote(posixpath.dirname(sandbox_share_path))}",
            ]
        )
        if mkdir != 0:
            return_code = mkdir
        else:
            return_code = _returncode(exec_command)
    finally:
        if not args.keep_sandbox:
            cleanup = _returncode([args.sbx, "rm", "--force", args.sandbox_name])
            if return_code == 0 and cleanup != 0:
                return_code = cleanup
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
