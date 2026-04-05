from __future__ import annotations

import argparse
import json
import shutil

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap.installer import (
    adopt_bootstrap,
    collect_status,
    doctor_bootstrap,
    format_actions,
    format_result_json,
    install_bootstrap,
    list_payload_files,
    verify_payload,
)


GIT_REPO_URL = "git+https://github.com/Tenfifty/agentic-planning"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-planning-bootstrap",
        description="Install and maintain a lightweight checked-in planning bootstrap for execution.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("install", "init"):
        command_parser = subparsers.add_parser(command, help="Install bootstrap files into a repository.")
        command_parser.add_argument("--target")
        command_parser.add_argument("--dry-run", action="store_true")
        command_parser.add_argument("--force", action="store_true")
        command_parser.add_argument("--format", choices=("text", "json"), default="text")

    adopt_parser = subparsers.add_parser("adopt", help="Conservatively add planning bootstrap files to an existing repository.")
    adopt_parser.add_argument("--target")
    adopt_parser.add_argument("--dry-run", action="store_true")
    adopt_parser.add_argument("--format", choices=("text", "json"), default="text")

    for command in ("doctor", "status"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--target")
        command_parser.add_argument("--format", choices=("text", "json"), default="text")

    list_files_parser = subparsers.add_parser("list-files")
    list_files_parser.add_argument("--format", choices=("text", "json"), default="text")

    verify_parser = subparsers.add_parser("verify-payload")
    verify_parser.add_argument("--format", choices=("text", "json"), default="text")

    prompt_parser = subparsers.add_parser("prompt")
    prompt_parser.add_argument("prompt_command", choices=("install", "adopt"))
    prompt_parser.add_argument("--target")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in {"install", "init"}:
        return _emit(install_bootstrap(target=args.target, dry_run=args.dry_run, force=args.force), args.format)
    if args.command == "adopt":
        return _emit(adopt_bootstrap(target=args.target, dry_run=args.dry_run), args.format)
    if args.command == "doctor":
        return _emit(doctor_bootstrap(target=args.target), args.format)
    if args.command == "status":
        return _emit(collect_status(target=args.target), args.format)
    if args.command == "list-files":
        files = list_payload_files()
        if args.format == "json":
            print(json.dumps({"files": files}, indent=2))
        else:
            for path in files:
                print(path)
        return 0
    if args.command == "verify-payload":
        return _emit(verify_payload(), args.format)
    if args.command == "prompt":
        print(_build_prompt(args.prompt_command, args.target))
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


def _emit(result, output_format: str) -> int:
    if output_format == "json":
        print(format_result_json(result))
        return 0
    print(f"Target: {result.target_root}")
    print(result.message)
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- [{warning['warning_class']}] {warning['path']}: {warning['message']}")
    return 0


def _build_prompt(command: str, target: str | None) -> str:
    runner = _preferred_runner()
    target_args = f" --target {target}" if target else ""
    if command == "install":
        return (
            f"Run `{runner} install{target_args}`. "
            "Then customise `AGENTS.md`, prune starter placeholders, and run "
            "`python scripts/render_agent_docs.py` plus `make plan-check`."
        )
    return (
        f"Run `{runner} adopt{target_args}` conservatively. "
        "Do not overwrite repo-owned planning files unless the user asks for it. "
        "Afterwards run `python scripts/render_agent_docs.py` and `make plan-check`."
    )


def _preferred_runner() -> str:
    if shutil.which("uvx"):
        return f"uvx --from {GIT_REPO_URL} agentic-planning-bootstrap"
    if shutil.which("pipx"):
        return f"pipx run --spec {GIT_REPO_URL} agentic-planning-bootstrap"
    return f"uvx --from {GIT_REPO_URL} agentic-planning-bootstrap"
