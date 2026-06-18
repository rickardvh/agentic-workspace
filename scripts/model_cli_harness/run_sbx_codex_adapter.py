"""Host-side bridge for running Codex non-interactively in Docker Sandboxes."""

from __future__ import annotations

import argparse
import posixpath
import re
import shlex
import subprocess
import sys
from pathlib import Path


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbx", default="sbx")
    parser.add_argument("--sandbox-name", required=True)
    parser.add_argument("--template")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--share-path", required=True)
    parser.add_argument("--exec-env", action="append", default=[])
    parser.add_argument("--prompt")
    parser.add_argument("--prompt-file")
    args = parser.parse_args(argv)

    prompt = _prompt_from_args(args)
    sandbox_repo = _sandbox_path(args.repo)
    sandbox_share_path = _sandbox_path(args.share_path)
    create_command = [args.sbx, "create", "--name", args.sandbox_name]
    if args.template:
        create_command.extend(["--template", args.template])
    create_command.extend(["codex", args.repo])
    create = _run(create_command, capture=True)
    create_output = f"{create.stdout or ''}\n{create.stderr or ''}".lower()
    if create.returncode != 0 and "already exists" not in create_output:
        return int(create.returncode)
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
        return mkdir
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
    return _returncode(exec_command)


if __name__ == "__main__":
    raise SystemExit(main())
