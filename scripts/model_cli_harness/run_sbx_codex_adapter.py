"""Host-side bridge for running Codex non-interactively in Docker Sandboxes."""

from __future__ import annotations

import argparse
import contextlib
import json
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


def _admit_final_response(*, repo: str, share_path: str) -> int:
    host_share_path = Path(share_path)
    if not host_share_path.is_file():
        print(
            "Codex final-response admission skipped: --output-last-message artifact was not written.",
            file=sys.stderr,
            flush=True,
        )
        return 1
    command = [
        sys.executable,
        "-c",
        "from agentic_workspace.cli import main; raise SystemExit(main())",
        "final-response",
        "admit",
        "--target",
        repo,
        "--attempt-file",
        str(host_share_path),
        "--source",
        "codex-sbx-output-last-message",
        "--after-compaction",
        "--format",
        "json",
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)  # noqa: S603
    stdout_text = completed.stdout.strip()
    stderr_text = completed.stderr.strip()
    if stdout_text:
        with host_share_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(stdout_text)
            handle.write("\n")
    if completed.returncode != 0:
        if stdout_text:
            print(stdout_text, file=sys.stdout, flush=True)
        if stderr_text:
            print(stderr_text, file=sys.stderr, flush=True)
        return int(completed.returncode)
    with contextlib.suppress(json.JSONDecodeError):
        payload = json.loads(stdout_text)
        if isinstance(payload, dict) and payload.get("status") == "rejected_auto_resumed":
            print(
                "Codex final-response admission rejected terminal output and executed AW continuation.",
                file=sys.stderr,
                flush=True,
            )
    return 0


def _prompt_from_args(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return ""
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


def _sandbox_prompt_path(prompt_file: str | None) -> str | None:
    if not prompt_file:
        return None
    prompt_name = Path(prompt_file).name or "prompt.txt"
    return posixpath.join(posixpath.sep, "tmp", "agentic-workspace-model-cli-harness", prompt_name)


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
    sandbox_prompt_path = _sandbox_prompt_path(args.prompt_file)
    exec_command = _codex_exec_command(
        args=args,
        prompt=prompt,
        sandbox_repo=sandbox_repo,
        sandbox_share_path=sandbox_share_path,
        sandbox_prompt_path=sandbox_prompt_path,
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
        mkdir_paths = [posixpath.dirname(sandbox_share_path)]
        if sandbox_prompt_path:
            mkdir_paths.append(posixpath.dirname(sandbox_prompt_path))
        mkdir = _returncode(
            [
                args.sbx,
                "exec",
                args.sandbox_name,
                "sh",
                "-lc",
                "mkdir -p " + " ".join(shlex.quote(path) for path in mkdir_paths),
            ]
        )
        if mkdir != 0:
            return_code = mkdir
        elif sandbox_prompt_path and args.prompt_file:
            copy_prompt = _returncode([args.sbx, "cp", args.prompt_file, f"{args.sandbox_name}:{sandbox_prompt_path}"])
            if copy_prompt != 0:
                return_code = copy_prompt
            else:
                return_code = _returncode(exec_command)
        else:
            return_code = _returncode(exec_command)
        if return_code == 0:
            return_code = _admit_final_response(repo=args.repo, share_path=args.share_path)
    finally:
        if not args.keep_sandbox:
            cleanup = _returncode([args.sbx, "rm", "--force", args.sandbox_name])
            if return_code == 0 and cleanup != 0:
                return_code = cleanup
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
