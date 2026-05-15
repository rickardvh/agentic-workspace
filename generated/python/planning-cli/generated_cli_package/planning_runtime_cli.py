from __future__ import annotations

import argparse
import json
import shutil
import sys

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap._source import UpgradeSource, resolve_upgrade_source
from repo_planning_bootstrap.installer import (
    adopt_bootstrap,
    archive_execplan,
    archive_parent_lane_closeout,
    close_planning_item,
    collect_status,
    create_execplan_scaffold,
    create_review_record,
    doctor_bootstrap,
    format_summary_json,
    install_bootstrap,
    list_bundled_skill_files,
    list_default_payload_files,
    list_optional_payload_files,
    list_payload_files,
    planning_handoff,
    planning_reconcile,
    planning_report,
    planning_report_tiny,
    planning_summary,
    promote_todo_item_to_execplan,
    record_delegation_decision,
    record_planning_recovery,
    uninstall_bootstrap,
    upgrade_bootstrap,
    verify_payload,
)
from repo_planning_bootstrap.runtime_projection import (
    _emit,
    _print_handoff,
    _print_reconcile,
    _print_report,
    _print_summary,
)

from . import (
    build_generated_parser as build_generated_cli_package_parser,
)
from . import (
    generated_command_names as generated_cli_package_command_names,
)
from . import (
    generated_operation_contract as generated_cli_package_operation_contract,
)
from . import (
    run_generated_command as run_generated_cli_package_command,
)
from . import (
    supports_generated_command as supports_generated_cli_package_command,
)
from .planning_operation_ir_executor import run_operation_ir


def _program_name() -> str:
    invoked = sys.argv[0].replace("\\", "/").rsplit("/", 1)[-1]
    if invoked == "agentic-planning":
        return invoked
    return "agentic-planning"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_program_name(),
        description=("Install, inspect, and maintain checked-in Planning surfaces."),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generated_commands = set(generated_cli_package_command_names())

    for command in ("install", "init"):
        command_parser = subparsers.add_parser(command, help="Install bootstrap files into a repository.")
        command_parser.add_argument("--target")
        command_parser.add_argument("--dry-run", action="store_true")
        command_parser.add_argument("--force", action="store_true")
        command_parser.add_argument("--local", action="store_true", help="Set up the workspace in a local, non-tracked directory.")
        command_parser.add_argument(
            "--include-optional",
            action="store_true",
            help="Copy optional planning docs for richer review, intake, and recovery workflows.",
        )
        command_parser.add_argument("--format", choices=("text", "json"), default="text")

    adopt_parser = subparsers.add_parser("adopt", help="Conservatively add planning bootstrap files to an existing repository.")
    adopt_parser.add_argument("--target")
    adopt_parser.add_argument("--dry-run", action="store_true")
    adopt_parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Copy optional planning docs without overwriting existing repo-owned files.",
    )
    adopt_parser.add_argument("--format", choices=("text", "json"), default="text")

    upgrade_parser = subparsers.add_parser(
        "upgrade",
        help="Refresh package-managed helper surfaces without overwriting repo-owned root planning files.",
    )
    upgrade_parser.add_argument("--target")
    upgrade_parser.add_argument("--dry-run", action="store_true")
    upgrade_parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Refresh optional planning docs when the repo has enabled richer planning workflows.",
    )
    upgrade_parser.add_argument("--format", choices=("text", "json"), default="text")

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove managed bootstrap files when they still match package content.")
    uninstall_parser.add_argument("--target")
    uninstall_parser.add_argument("--dry-run", action="store_true")
    uninstall_parser.add_argument("--format", choices=("text", "json"), default="text")

    for command in ("doctor", "status"):
        if command in generated_commands:
            continue
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--target")
        command_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Emit broad diagnostic output when the command has compact defaults.",
        )
        command_parser.add_argument("--format", choices=("text", "json"), default="text")

    if "summary" not in generated_commands:
        summary_parser = subparsers.add_parser("summary", help="Summarise the active planning surfaces in a machine-readable way.")
        summary_parser.add_argument("--target")
        summary_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Emit broad diagnostic planning detail.",
        )
        summary_parser.add_argument("--task", help="Optional task text used to return a task-scoped compact summary.")
        summary_parser.add_argument("--changed", nargs="*", default=[], help="Optional changed paths used to scope compact summary output.")
        summary_parser.add_argument("--format", choices=("text", "json"), default="text")

    if "report" not in generated_commands:
        report_parser = subparsers.add_parser(
            "report", help="Report compact planning module state without reading raw planning files first."
        )
        report_parser.add_argument("--target")
        report_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Emit broad diagnostic report detail.",
        )
        report_parser.add_argument("--format", choices=("text", "json"), default="text")

    if "reconcile" not in generated_commands:
        reconcile_parser = subparsers.add_parser(
            "reconcile",
            help="Report stale planning state against provider-agnostic external work evidence.",
        )
        reconcile_parser.add_argument("--target")
        reconcile_parser.add_argument(
            "--apply-safe-prune",
            action="store_true",
            help="Apply only reconcile cleanup targets that are already marked safe_to_prune.",
        )
        reconcile_parser.add_argument("--dry-run", action="store_true", help="Preview --apply-safe-prune without writing files.")
        reconcile_parser.add_argument("--format", choices=("text", "json"), default="text")

    if "handoff" not in generated_commands:
        handoff_parser = subparsers.add_parser("handoff", help="Emit the compact delegated-worker handoff derived from active planning state.")
        handoff_parser.add_argument("--target")
        handoff_parser.add_argument("--format", choices=("text", "json"), default="text")

    new_plan_parser = subparsers.add_parser("new-plan", help="Create a schema-valid execplan scaffold and optionally register it.")
    new_plan_parser.add_argument("--id", required=True, help="Stable slug/id for the plan; used as the .plan.json filename.")
    new_plan_parser.add_argument("--title", required=True, help="Human-readable plan title.")
    new_plan_parser.add_argument("--source", default="", help="Optional source reference such as an issue URL or chat-intake summary.")
    new_plan_parser.add_argument("--target")
    state_group = new_plan_parser.add_mutually_exclusive_group()
    state_group.add_argument("--activate", action="store_true", help="Register the new plan in todo.active_items.")
    state_group.add_argument("--queue", action="store_true", help="Register the new plan in todo.queued_items.")
    new_plan_parser.add_argument(
        "--switch-active",
        action="store_true",
        help="When used with --activate, demote existing active items into the queue before registering the new active plan.",
    )
    new_plan_parser.add_argument(
        "--prep-only",
        action="store_true",
        help="Mark this scaffold as a planning-only handoff slice; verify summary, then stop without product scaffolding.",
    )
    new_plan_parser.add_argument("--overwrite", action="store_true", help="Replace an existing scaffold with the same id.")
    new_plan_parser.add_argument("--dry-run", action="store_true")
    new_plan_parser.add_argument("--format", choices=("text", "json"), default="text")

    promote_parser = subparsers.add_parser("promote-to-plan", help="Promote a direct TODO item into an execplan scaffold.")
    promote_parser.add_argument("item_id")
    promote_parser.add_argument("--target")
    promote_parser.add_argument("--plan-slug")
    promote_parser.add_argument("--dry-run", action="store_true")
    promote_parser.add_argument("--format", choices=("text", "json"), default="text")

    archive_parser = subparsers.add_parser(
        "archive-plan",
        help="Close a completed execplan or parent lane after distillation; archive retention is legacy/audit-only.",
    )
    archive_parser.add_argument("plan", nargs="?")
    archive_parser.add_argument("--target")
    archive_parser.add_argument("--dry-run", action="store_true")
    archive_parser.add_argument(
        "--apply-cleanup",
        action="store_true",
        help="Apply narrow cleanup for completed TODO references and Active Handoff residue tied to the archived plan.",
    )
    archive_parser.add_argument(
        "--prepare-closeout",
        action="store_true",
        help="Write package-normalized closeout fields before archive validation runs.",
    )
    archive_parser.add_argument(
        "--retain-archive",
        action="store_true",
        help="Legacy escape hatch: keep a completed execplan record under execplans/archive instead of removing it after distillation.",
    )
    archive_parser.add_argument(
        "--parent-lane-closeout",
        help="Close a parent lane from structured planning state without hand-authoring an execplan record.",
    )
    archive_parser.add_argument(
        "--closure-decision",
        choices=("archive-and-close", "archive-but-keep-lane-open"),
        help="Closeout decision to write when --prepare-closeout is used.",
    )
    archive_parser.add_argument(
        "--intent-satisfied",
        choices=("yes", "no", "true", "false"),
        help="Whether the larger original intent is fully satisfied when --prepare-closeout is used.",
    )
    archive_parser.add_argument("--unsolved-intent", help="Continuation owner for unsolved larger intent.")
    archive_parser.add_argument("--intent-evidence", help="Evidence of intent satisfaction for prepared closeout.")
    archive_parser.add_argument("--closure-reason", help="Why the prepared closure decision is honest.")
    archive_parser.add_argument("--closure-evidence", help="Evidence carried forward by the prepared closure.")
    archive_parser.add_argument("--reopen-trigger", help="Reopen trigger for the prepared closure.")
    archive_parser.add_argument("--discard-summary", help="Closeout distillation discard bucket summary.")
    archive_parser.add_argument("--continuation-summary", help="Closeout distillation continuation bucket summary.")
    archive_parser.add_argument("--format", choices=("text", "json"), default="text")

    close_item_parser = subparsers.add_parser(
        "close-item",
        help="Close completed planning residue by id without hand-editing checked-in state.",
    )
    close_item_parser.add_argument("item")
    close_item_parser.add_argument("--target")
    close_item_parser.add_argument("--reason", default="")
    close_item_parser.add_argument("--issue", default="")
    close_item_parser.add_argument("--dry-run", action="store_true")
    close_item_parser.add_argument("--format", choices=("text", "json"), default="text")

    review_parser = subparsers.add_parser("create-review", help="Create a valid planning review record skeleton.")
    review_parser.add_argument("slug")
    review_parser.add_argument("--title", required=True)
    review_parser.add_argument("--target")
    review_parser.add_argument("--scope")
    review_parser.add_argument("--classification", default="review")
    review_parser.add_argument("--render-markdown", action="store_true")
    review_parser.add_argument("--dry-run", action="store_true")
    review_parser.add_argument("--format", choices=("text", "json"), default="text")

    delegation_parser = subparsers.add_parser(
        "delegation-decision",
        help="Record the delegation route chosen for the active execplan before mechanical lane work proceeds.",
    )
    delegation_parser.add_argument("--target")
    delegation_parser.add_argument("--plan", help="Plan path, slug, or id; defaults to the active execplan.")
    delegation_parser.add_argument(
        "--route",
        required=True,
        choices=(
            "keep-local",
            "delegate-exploration",
            "delegate-implementation",
            "delegate-validation",
            "escalate-review",
            "no-safe-route",
        ),
    )
    delegation_parser.add_argument("--skipped-reason", default="")
    delegation_parser.add_argument("--expected-savings", default="")
    delegation_parser.add_argument("--actual-friction", default="")
    delegation_parser.add_argument("--proof-result", default="")
    delegation_parser.add_argument("--quality-concern", default="")
    delegation_parser.add_argument("--decomposition-adjustment", default="")
    delegation_parser.add_argument("--dry-run", action="store_true")
    delegation_parser.add_argument("--format", choices=("text", "json"), default="text")

    recovery_parser = subparsers.add_parser(
        "record-recovery",
        help="Bless an emergency manual repair to managed planning surfaces with explicit provenance.",
    )
    recovery_parser.add_argument("--target")
    recovery_parser.add_argument("--path", action="append", dest="paths", required=True)
    recovery_parser.add_argument("--reason", required=True)
    recovery_parser.add_argument("--dry-run", action="store_true")
    recovery_parser.add_argument("--format", choices=("text", "json"), default="text")

    list_files_parser = subparsers.add_parser("list-files")
    list_files_parser.add_argument("--format", choices=("text", "json"), default="text")

    if "verify-payload" not in generated_commands:
        verify_parser = subparsers.add_parser("verify-payload")
        verify_parser.add_argument("--format", choices=("text", "json"), default="text")

    prompt_parser = subparsers.add_parser("prompt")
    prompt_parser.add_argument("prompt_command", choices=("install", "adopt"))
    prompt_parser.add_argument("--target")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    generated_result = _run_generated_cli_package_if_supported(argv_list)
    if generated_result is not None:
        return generated_result

    parser = build_parser()
    args = parser.parse_args(argv_list)

    if args.command in {"install", "init"}:
        return _emit(
            install_bootstrap(
                target=args.target,
                dry_run=args.dry_run,
                force=args.force,
                local_only=args.local,
                include_optional=args.include_optional,
            ),
            args.format,
        )
    if args.command == "adopt":
        return _emit(adopt_bootstrap(target=args.target, dry_run=args.dry_run, include_optional=args.include_optional), args.format)
    if args.command == "upgrade":
        return _emit(upgrade_bootstrap(target=args.target, dry_run=args.dry_run, include_optional=args.include_optional), args.format)
    if args.command == "uninstall":
        return _emit(uninstall_bootstrap(target=args.target, dry_run=args.dry_run), args.format)
    if args.command == "doctor":
        return _emit(doctor_bootstrap(target=args.target), args.format)
    if args.command == "status":
        return _emit(collect_status(target=args.target), args.format)
    if args.command == "summary":
        summary_profile = "full" if getattr(args, "verbose", False) or args.format != "json" else "tiny"
        summary = planning_summary(
            target=args.target,
            profile=summary_profile,
            task_text=getattr(args, "task", None),
            changed_paths=list(getattr(args, "changed", []) or []),
        )
        if args.format == "json":
            print(format_summary_json(summary))
        else:
            _print_summary(summary)
        return 0
    if args.command == "report":
        report = planning_report_tiny(target=args.target) if not getattr(args, "verbose", False) else planning_report(target=args.target)
        if args.format == "json":
            print(json.dumps(report, indent=2))
        else:
            _print_report(report)
        return 0
    if args.command == "reconcile":
        reconcile = planning_reconcile(
            target=args.target,
            apply_safe_prune=bool(getattr(args, "apply_safe_prune", False)),
            dry_run=bool(getattr(args, "dry_run", False)),
        )
        if args.format == "json":
            print(json.dumps(reconcile, indent=2))
        else:
            _print_reconcile(reconcile)
        return 0
    if args.command == "handoff":
        handoff = planning_handoff(target=args.target)
        if args.format == "json":
            print(json.dumps(handoff, indent=2))
        else:
            _print_handoff(handoff)
        return 0
    if args.command == "new-plan":
        return _emit(
            create_execplan_scaffold(
                plan_id=args.id,
                title=args.title,
                source=args.source,
                target=args.target,
                activate=args.activate,
                queue=args.queue,
                switch_active=args.switch_active,
                prep_only=args.prep_only,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
            ),
            args.format,
        )
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
        if args.parent_lane_closeout:
            return _emit(
                archive_parent_lane_closeout(
                    args.parent_lane_closeout,
                    target=args.target,
                    dry_run=args.dry_run,
                    intent_satisfied=args.intent_satisfied,
                    intent_evidence=args.intent_evidence,
                    closure_reason=args.closure_reason,
                    closure_evidence=args.closure_evidence,
                    reopen_trigger=args.reopen_trigger,
                    discard_summary=args.discard_summary,
                    continuation_summary=args.continuation_summary,
                ),
                args.format,
            )
        if not args.plan:
            parser.error("archive-plan requires PLAN unless --parent-lane-closeout is used")
        return _emit(
            archive_execplan(
                args.plan,
                target=args.target,
                dry_run=args.dry_run,
                apply_cleanup=args.apply_cleanup,
                prepare_closeout=args.prepare_closeout,
                closure_decision=args.closure_decision,
                intent_satisfied=args.intent_satisfied,
                unsolved_intent=args.unsolved_intent,
                intent_evidence=args.intent_evidence,
                closure_reason=args.closure_reason,
                closure_evidence=args.closure_evidence,
                reopen_trigger=args.reopen_trigger,
                discard_summary=args.discard_summary,
                continuation_summary=args.continuation_summary,
                retain_archive=args.retain_archive,
            ),
            args.format,
        )
    if args.command == "close-item":
        return _emit(
            close_planning_item(
                args.item,
                target=args.target,
                reason=args.reason,
                issue=args.issue,
                dry_run=args.dry_run,
            ),
            args.format,
        )
    if args.command == "create-review":
        return _emit(
            create_review_record(
                slug=args.slug,
                title=args.title,
                target=args.target,
                scope=args.scope,
                classification=args.classification,
                dry_run=args.dry_run,
                render_markdown=args.render_markdown,
            ),
            args.format,
        )
    if args.command == "delegation-decision":
        return _emit(
            record_delegation_decision(
                target=args.target,
                plan=args.plan,
                route=args.route,
                skipped_reason=args.skipped_reason,
                expected_savings=args.expected_savings,
                actual_friction=args.actual_friction,
                proof_result=args.proof_result,
                quality_concern=args.quality_concern,
                decomposition_adjustment=args.decomposition_adjustment,
                dry_run=args.dry_run,
            ),
            args.format,
        )
    if args.command == "record-recovery":
        return _emit(
            record_planning_recovery(
                target=args.target,
                paths=list(args.paths or []),
                reason=args.reason,
                dry_run=args.dry_run,
            ),
            args.format,
        )
    if args.command == "list-files":
        files = list_payload_files()
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "files": files,
                        "default_files": list_default_payload_files(),
                        "optional_files": list_optional_payload_files(),
                        "bundled_skill_files": list_bundled_skill_files(),
                        "optional_enable_commands": [
                            "agentic-planning install --include-optional",
                            "agentic-planning adopt --include-optional",
                            "agentic-planning upgrade --include-optional",
                        ],
                    },
                    indent=2,
                )
            )
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


def _run_generated_cli_package_if_supported(argv: list[str]) -> int | None:
    if not supports_generated_cli_package_command(argv):
        return None
    return run_generated_cli_package_command(argv, _run_generated_cli_operation)


def _run_generated_cli_operation(operation_id: str, args: argparse.Namespace) -> int:
    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is None:
        build_generated_cli_package_parser().error(f"Generated adapter for {args.command} references unsupported operation {operation_id}.")
        raise SystemExit(2)
    return handler(args)


def _run_status_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.status.report"), args)


def _run_doctor_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.doctor.report"), args)


def _run_summary_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.summary.report"), args)


def _run_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.report.report"), args)


def _tiny_report(report: dict) -> dict:
    status = report.get("status", {})
    active = report.get("active", {})
    findings = report.get("findings", [])
    return {
        "kind": report.get("kind", "planning-report/v1"),
        "profile": "tiny",
        "module": report.get("module", "planning"),
        "target_root": report.get("target_root", ""),
        "health": report.get("health", "unknown"),
        "status": status,
        "active": {
            "active_item_count": active.get("active_item_count", 0) if isinstance(active, dict) else 0,
            "active_execplan_count": active.get("active_execplan_count", 0) if isinstance(active, dict) else 0,
        },
        "finding_count": len(findings) if isinstance(findings, list) else 0,
        "findings": findings[:5] if isinstance(findings, list) else [],
        "next_action": report.get("next_action", {}),
        "detail_commands": {
            "full": "agentic-planning report --target . --verbose --format json",
            "summary": "agentic-planning summary --target . --format json",
        },
    }


def _run_reconcile_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.reconcile.report"), args)


def _run_handoff_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.handoff.report"), args)


def _run_verify_payload_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.verify-payload.report"), args)


def _run_close_item_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.close-item.lifecycle"), args)


def _run_create_review_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.create-review.lifecycle"), args)


_GENERATED_RUNTIME_HANDLERS = {
    "planning.close-item.lifecycle": _run_close_item_lifecycle_adapter,
    "planning.create-review.lifecycle": _run_create_review_lifecycle_adapter,
    "planning.doctor.report": _run_doctor_report_adapter,
    "planning.handoff.report": _run_handoff_report_adapter,
    "planning.reconcile.report": _run_reconcile_report_adapter,
    "planning.report.report": _run_report_adapter,
    "planning.status.report": _run_status_report_adapter,
    "planning.summary.report": _run_summary_report_adapter,
    "planning.verify-payload.report": _run_verify_payload_report_adapter,
}


def _build_prompt(command: str, target: str | None) -> str:
    source = resolve_upgrade_source(target)
    runner = _preferred_runner(source)
    target_args = f" --target {target}" if target else ""
    non_interactive_args = " --non-interactive"
    if command == "install":
        if runner is None:
            return (
                "No pinned remote runner is published for this bootstrap version yet. "
                "Use an installed `agentic-planning` command if it is already available locally, "
                "or publish a tagged release before relying on remote `prompt install` workflows."
            )
        return (
            f"Run `{runner} install{target_args}{non_interactive_args}`. "
            "Then customise `AGENTS.md`, prune starter placeholders, and run "
            "`agentic-workspace doctor --target ./repo --modules planning --format json` inside the target repo."
        )
    if command == "adopt":
        if runner is None:
            return (
                "No pinned remote runner is published for this bootstrap version yet. "
                "Use an installed `agentic-planning` command if it is already available locally, "
                "or publish a tagged release before relying on remote `prompt adopt` workflows."
            )
        return (
            f"Run `{runner} adopt{target_args}{non_interactive_args}` conservatively. "
            "Do not overwrite repo-owned planning files unless the user asks for it. "
            "Afterwards run `agentic-workspace doctor --target ./repo --modules planning --format json` inside the target repo."
        )
    if command == "upgrade":
        upgrade_guidance = (
            f"Use the checked-in `bootstrap-upgrade` skill under `{_managed_skills_path(target)}/`. "
            "It should use the repo's `.agentic-workspace/planning/UPGRADE-SOURCE.toml`, prefer an installed "
            "`agentic-planning` command with `--non-interactive` when available, and rerun render/check validation. "
            "If `doctor` still flags older active execplans, reconcile those plans to the current contract by "
            "adding or refreshing `Intent Continuity`, `Required Continuation`, `Delegated Judgment`, "
            "`Active Milestone`, and `Execution Summary` instead of treating the upgrade as broken."
        )
        if runner is None:
            return upgrade_guidance
        return upgrade_guidance + f" If a local install is unavailable, fall back to `{runner} upgrade --target <repo> --non-interactive`."
    if runner is None:
        return (
            "No pinned remote runner is published for this bootstrap version yet. "
            "Use an installed `agentic-planning` command if it is already available locally."
        )
    return (
        f"Run `{runner} adopt{target_args}{non_interactive_args}` conservatively. "
        "Do not overwrite repo-owned planning files unless the user asks for it. "
        "Afterwards run `agentic-workspace doctor --target ./repo --modules planning --format json` inside the target repo."
    )


def _preferred_runner(source: UpgradeSource) -> str | None:
    if source.source_type == "none" or not source.source_ref:
        return None
    if source.source_type == "local":
        return _runner_command_for_local_source(source.source_ref)
    if shutil.which("uvx"):
        return f"uvx --from {source.source_ref} agentic-planning"
    if shutil.which("pipx"):
        return f"pipx run --spec {source.source_ref} agentic-planning"
    return f"uvx --from {source.source_ref} agentic-planning"


def _managed_skills_path(target: str | None) -> str:
    target_root = target or "./repo"
    return f"{target_root}/skills"


def _runner_command_for_local_source(source_ref: str) -> str:
    if shutil.which("uvx"):
        return f"uvx --from {source_ref} agentic-planning"
    if shutil.which("pipx"):
        return f"pipx run --spec {source_ref} agentic-planning"
    return f"uvx --from {source_ref} agentic-planning"
