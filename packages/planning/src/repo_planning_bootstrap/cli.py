from __future__ import annotations

import argparse
import json
import shutil

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap._source import UpgradeSource, resolve_upgrade_source
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
    print(f"TODO: {summary['todo']['active_count']} active / {summary['todo']['item_count']} items / {summary['todo']['line_count']} lines")
    print(f"Execplans: {summary['execplans']['active_count']} active / {summary['execplans']['archived_count']} archived")
    print(f"Roadmap: {summary['roadmap']['candidate_count']} candidate bullets")
    planning_record = summary.get("planning_record", {})
    if planning_record.get("status") == "present":
        task = planning_record.get("task", {})
        print("Planning record:")
        print(f"- Task: {task.get('id', '')}: {task.get('surface', '')}")
        print(f"- Requested outcome: {planning_record['requested_outcome']}")
        print(f"- Next action: {planning_record['next_action']}")
        print(f"- Continuation owner: {planning_record['continuation_owner']}")
        print(f"- Proof expectations: {', '.join(planning_record['proof_expectations'])}")
    elif planning_record:
        print(f"Planning record: {planning_record.get('status')} ({planning_record.get('reason', 'no compact record available')})")
    active_contract = summary.get("active_contract", {})
    if active_contract.get("status") == "present":
        print("Active contract view:")
        print(f"- TODO item: {active_contract['todo_item']['id']}: {active_contract['todo_item']['surface']}")
    elif active_contract:
        print(f"Active contract view: {active_contract.get('status')} ({active_contract.get('reason', 'no compact contract available')})")
    resumable_contract = summary.get("resumable_contract", {})
    if resumable_contract.get("status") == "present":
        print("Resumable contract view:")
        print(f"- Next action: {resumable_contract['current_next_action']}")
    elif resumable_contract:
        print(
            "Resumable contract view: "
            f"{resumable_contract.get('status')} ({resumable_contract.get('reason', 'no resumable contract available')})"
        )
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
    source = resolve_upgrade_source(target)
    runner = _preferred_runner(source)
    target_args = f" --target {target}" if target else ""
    if command == "install":
        if runner is None:
            return (
                "No pinned remote runner is published for this bootstrap version yet. "
                "Use an installed `agentic-planning-bootstrap` command if it is already available locally, "
                "or publish a tagged release before relying on remote `prompt install` workflows."
            )
        return (
            f"Run `{runner} install{target_args}`. "
            "Then customise `AGENTS.md`, prune starter placeholders, and run "
            "`python scripts/render_agent_docs.py` plus "
            "`python scripts/check/check_maintainer_surfaces.py` inside the target repo."
        )
    if command == "adopt":
        if runner is None:
            return (
                "No pinned remote runner is published for this bootstrap version yet. "
                "Use an installed `agentic-planning-bootstrap` command if it is already available locally, "
                "or publish a tagged release before relying on remote `prompt adopt` workflows."
            )
        return (
            f"Run `{runner} adopt{target_args}` conservatively. "
            "Do not overwrite repo-owned planning files unless the user asks for it. "
            "Afterwards run `python scripts/render_agent_docs.py` and "
            "`python scripts/check/check_maintainer_surfaces.py` inside the target repo."
        )
    if command == "upgrade":
        upgrade_guidance = (
            f"Use the checked-in `bootstrap-upgrade` skill under `{_managed_skills_path(target)}/`. "
            "It should use the repo's `.agentic-workspace/planning/UPGRADE-SOURCE.toml`, prefer an installed "
            "`agentic-planning-bootstrap` command when available, and rerun render/check validation. "
            "If `doctor` still flags older active execplans, reconcile those plans to the current contract by "
            "adding or refreshing `Intent Continuity`, `Required Continuation`, `Delegated Judgment`, "
            "`Active Milestone`, and `Execution Summary` instead of treating the upgrade as broken."
        )
        if runner is None:
            return upgrade_guidance
        return upgrade_guidance + f" If a local install is unavailable, fall back to `{runner} upgrade --target <repo>`."
    if runner is None:
        return (
            "No pinned remote runner is published for this bootstrap version yet. "
            "Use an installed `agentic-planning-bootstrap` command if it is already available locally."
        )
    return (
        f"Run `{runner} adopt{target_args}` conservatively. "
        "Do not overwrite repo-owned planning files unless the user asks for it. "
        "Afterwards run `python scripts/render_agent_docs.py` and "
        "`python scripts/check/check_maintainer_surfaces.py` inside the target repo."
    )


def _preferred_runner(source: UpgradeSource) -> str | None:
    if source.source_type == "none" or not source.source_ref:
        return None
    if source.source_type == "local":
        return _runner_command_for_local_source(source.source_ref)
    if shutil.which("uvx"):
        return f"uvx --from {source.source_ref} agentic-planning-bootstrap"
    if shutil.which("pipx"):
        return f"pipx run --spec {source.source_ref} agentic-planning-bootstrap"
    return f"uvx --from {source.source_ref} agentic-planning-bootstrap"


def _managed_skills_path(target: str | None) -> str:
    target_root = target or "./repo"
    return f"{target_root}/skills"


def _runner_command_for_local_source(source_ref: str) -> str:
    if shutil.which("uvx"):
        return f"uvx --from {source_ref} agentic-planning-bootstrap"
    if shutil.which("pipx"):
        return f"pipx run --spec {source_ref} agentic-planning-bootstrap"
    return f"uvx --from {source_ref} agentic-planning-bootstrap"
