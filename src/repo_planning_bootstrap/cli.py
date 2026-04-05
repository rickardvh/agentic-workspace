from __future__ import annotations

import argparse
import json
import shutil

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap.installer import (
    adopt_bootstrap,
    archive_execplan,
    collect_status,
    doctor_bootstrap,
    format_actions,
    format_result_json,
    format_summary_json,
    install_bootstrap,
    list_payload_files,
    planning_summary,
    promote_todo_item_to_execplan,
    uninstall_bootstrap,
    upgrade_bootstrap,
    verify_payload,
)

GIT_REPO_URL = "git+https://github.com/rickardvh/agentic-planning"


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

    for command, help_text in (
        ("upgrade", "Refresh package-managed helper surfaces without overwriting repo-owned root planning files."),
        ("uninstall", "Remove managed bootstrap files when they still match package content."),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--target")
        command_parser.add_argument("--dry-run", action="store_true")
        command_parser.add_argument("--format", choices=("text", "json"), default="text")

    for command in ("doctor", "status"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--target")
        command_parser.add_argument("--format", choices=("text", "json"), default="text")

    summary_parser = subparsers.add_parser("summary", help="Summarise the active planning surfaces in a machine-readable way.")
    summary_parser.add_argument("--target")
    summary_parser.add_argument("--format", choices=("text", "json"), default="text")

    promote_parser = subparsers.add_parser("promote-to-plan", help="Promote a direct TODO item into an execplan scaffold.")
    promote_parser.add_argument("item_id")
    promote_parser.add_argument("--target")
    promote_parser.add_argument("--plan-slug")
    promote_parser.add_argument("--dry-run", action="store_true")
    promote_parser.add_argument("--format", choices=("text", "json"), default="text")

    archive_parser = subparsers.add_parser("archive-plan", help="Archive a completed execplan.")
    archive_parser.add_argument("plan")
    archive_parser.add_argument("--target")
    archive_parser.add_argument("--dry-run", action="store_true")
    archive_parser.add_argument(
        "--apply-cleanup",
        action="store_true",
        help="Apply narrow cleanup for completed TODO references and Active Handoff residue tied to the archived plan.",
    )
    archive_parser.add_argument("--format", choices=("text", "json"), default="text")

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
    if args.command == "upgrade":
        return _emit(upgrade_bootstrap(target=args.target, dry_run=args.dry_run), args.format)
    if args.command == "uninstall":
        return _emit(uninstall_bootstrap(target=args.target, dry_run=args.dry_run), args.format)
    if args.command == "doctor":
        return _emit(doctor_bootstrap(target=args.target), args.format)
    if args.command == "status":
        return _emit(collect_status(target=args.target), args.format)
    if args.command == "summary":
        summary = planning_summary(target=args.target)
        if args.format == "json":
            print(format_summary_json(summary))
        else:
            _print_summary(summary)
        return 0
    if args.command == "promote-to-plan":
        return _emit(
            promote_todo_item_to_execplan(
                args.item_id,
                target=args.target,
                plan_slug=args.plan_slug,
                dry_run=args.dry_run,
            ),
            args.format,
        )
    if args.command == "archive-plan":
        return _emit(
            archive_execplan(
                args.plan,
                target=args.target,
                dry_run=args.dry_run,
                apply_cleanup=args.apply_cleanup,
            ),
            args.format,
        )
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


def _print_summary(summary: dict) -> None:
    print(f"Target: {summary['target_root']}")
    print(f"Mode: {summary['adoption_mode']}")
    print(
        "TODO: "
        f"{summary['todo']['active_count']} active / {summary['todo']['item_count']} items / {summary['todo']['line_count']} lines"
    )
    print(
        "Execplans: "
        f"{summary['execplans']['active_count']} active / {summary['execplans']['archived_count']} archived"
    )
    print(f"Roadmap: {summary['roadmap']['candidate_count']} candidate bullets")
    if summary["todo"]["active_items"]:
        print("Active items:")
        for item in summary["todo"]["active_items"]:
            print(f"- {item['id']}: {item['surface']}")
    if summary["warning_count"]:
        print(f"Warnings: {summary['warning_count']}")
        for warning in summary["warnings"]:
            print(f"- [{warning['warning_class']}] {warning['path']}: {warning['message']}")
    else:
        print("Warnings: none")


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
