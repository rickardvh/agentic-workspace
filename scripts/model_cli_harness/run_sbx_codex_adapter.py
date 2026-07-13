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
from typing import Any

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


def _admission_metadata_path(share_path: str) -> Path:
    return Path(f"{share_path}.admission.json")


def _admit_final_response(*, repo: str, share_path: str) -> dict[str, Any]:
    host_share_path = Path(share_path)
    if not host_share_path.is_file():
        print(
            "Codex final-response admission skipped: --output-last-message artifact was not written.",
            file=sys.stderr,
            flush=True,
        )
        return {"exit_code": 1, "payload": {}, "metadata_path": str(_admission_metadata_path(share_path))}
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
    payload: dict[str, Any] = {}
    if stdout_text:
        with contextlib.suppress(json.JSONDecodeError):
            loaded = json.loads(stdout_text)
            if isinstance(loaded, dict):
                payload = loaded
        metadata_path = _admission_metadata_path(share_path)
        with metadata_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(stdout_text)
            handle.write("\n")
    if completed.returncode != 0:
        if stdout_text:
            print(stdout_text, file=sys.stdout, flush=True)
        if stderr_text:
            print(stderr_text, file=sys.stderr, flush=True)
        return {"exit_code": int(completed.returncode), "payload": payload, "metadata_path": str(_admission_metadata_path(share_path))}
    if payload.get("status") == "rejected_auto_resumed":
        print(
            "Codex final-response admission rejected terminal output and executed AW continuation.",
            file=sys.stderr,
            flush=True,
        )
    return {"exit_code": 0, "payload": payload, "metadata_path": str(_admission_metadata_path(share_path))}


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


def _continuation_prompt(
    *, original_prompt: str, sandbox_prompt_path: str | None, admission_payload: dict[str, Any], slice_index: int
) -> str:
    original_prompt_hint = (
        original_prompt
        if original_prompt.strip()
        else f"The original prompt was file-backed in this sandbox at {sandbox_prompt_path}."
        if sandbox_prompt_path
        else "Continue the original task from repository state and AW checkpoint evidence."
    )
    return (
        "Agentic Workspace rejected the previous terminal final response because work remains in CONTINUE.\n"
        "Do not stop or emit a terminal final yet. Continue the same objective through the next safe in-scope slice.\n\n"
        f"Original objective:\n{original_prompt_hint}\n\n"
        f"Admission result after slice {slice_index}:\n{json.dumps(admission_payload, indent=2, sort_keys=True)}\n\n"
        "Read the repository and .agentic-workspace/local/chat-checkpoint.json as needed. "
        "Only emit a terminal final when the outcome is DELIVERED, genuinely BLOCKED, or USER_PAUSED."
    )


def _copy_continuation_prompt_to_sandbox(
    *, args: argparse.Namespace, prompt_text: str, share_path: str, slice_index: int
) -> tuple[int, str]:
    host_prompt = Path(f"{share_path}.continuation-{slice_index}.txt")
    host_prompt.write_text(prompt_text, encoding="utf-8", newline="\n")
    sandbox_prompt_path = posixpath.join(
        posixpath.sep,
        "tmp",
        "agentic-workspace-model-cli-harness",
        f"continuation-{slice_index}.txt",
    )
    copy_code = _returncode([args.sbx, "cp", str(host_prompt), f"{args.sandbox_name}:{sandbox_prompt_path}"])
    return copy_code, sandbox_prompt_path


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
    parser.add_argument(
        "--max-admission-slices",
        type=int,
        default=0,
        help=(
            "Deprecated compatibility flag. Admission slices are not capped by the adapter because a fixed slice "
            "budget is not an authorized terminal outcome while final-response admission remains CONTINUE."
        ),
    )
    args = parser.parse_args(argv)

    prompt = _prompt_from_args(args)
    sandbox_repo = _sandbox_path(args.repo)
    sandbox_share_path = _sandbox_path(args.share_path)
    sandbox_prompt_path = _sandbox_prompt_path(args.prompt_file)
    max_admission_slices = max(0, int(args.max_admission_slices or 0))

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
        else:
            return_code = 0
        if return_code == 0 and sandbox_prompt_path and args.prompt_file:
            copy_prompt = _returncode([args.sbx, "cp", args.prompt_file, f"{args.sandbox_name}:{sandbox_prompt_path}"])
            if copy_prompt != 0:
                return_code = copy_prompt
        if return_code != 0:
            return return_code

        current_prompt = prompt
        current_sandbox_prompt_path = sandbox_prompt_path
        slice_index = 1
        while True:
            exec_command = _codex_exec_command(
                args=args,
                prompt=current_prompt,
                sandbox_repo=sandbox_repo,
                sandbox_share_path=sandbox_share_path,
                sandbox_prompt_path=current_sandbox_prompt_path,
            )
            command_length_error = _windows_command_length_error(
                exec_command,
                prompt_file=args.prompt_file if slice_index == 1 and current_sandbox_prompt_path else None,
            )
            if command_length_error:
                print(command_length_error, file=sys.stderr, flush=True)
                return_code = 2
                break
            return_code = _returncode(exec_command)
            if return_code != 0:
                break
            admission = _admit_final_response(repo=args.repo, share_path=args.share_path)
            return_code = int(admission["exit_code"])
            if return_code != 0:
                break
            admission_payload = admission["payload"] if isinstance(admission["payload"], dict) else {}
            if admission_payload.get("status") != "rejected_auto_resumed":
                break
            if max_admission_slices and slice_index == max_admission_slices:
                print(
                    "Codex final-response admission reached the configured compatibility slice budget; "
                    "continuing because a slice cap is not an authorized terminal outcome.",
                    file=sys.stderr,
                    flush=True,
                )
            continuation_prompt = _continuation_prompt(
                original_prompt=prompt,
                sandbox_prompt_path=sandbox_prompt_path,
                admission_payload=admission_payload,
                slice_index=slice_index,
            )
            copy_code, current_sandbox_prompt_path = _copy_continuation_prompt_to_sandbox(
                args=args,
                prompt_text=continuation_prompt,
                share_path=args.share_path,
                slice_index=slice_index + 1,
            )
            if copy_code != 0:
                return_code = copy_code
                break
            current_prompt = ""
            slice_index += 1
    finally:
        if not args.keep_sandbox:
            cleanup = _returncode([args.sbx, "rm", "--force", args.sandbox_name])
            if return_code == 0 and cleanup != 0:
                return_code = cleanup
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
