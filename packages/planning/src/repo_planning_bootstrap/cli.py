from __future__ import annotations

import argparse
import json
import shutil
import sys

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap._source import UpgradeSource, resolve_upgrade_source
from repo_planning_bootstrap.generated_cli_package import (
    build_generated_parser as build_generated_cli_package_parser,
)
from repo_planning_bootstrap.generated_cli_package import (
    generated_command_names as generated_cli_package_command_names,
)
from repo_planning_bootstrap.generated_cli_package import (
    run_generated_command as run_generated_cli_package_command,
)
from repo_planning_bootstrap.generated_cli_package import (
    supports_generated_command as supports_generated_cli_package_command,
)
from repo_planning_bootstrap.installer import (
    adopt_bootstrap,
    archive_execplan,
    archive_parent_lane_closeout,
    collect_status,
    create_execplan_scaffold,
    create_review_record,
    doctor_bootstrap,
    format_actions,
    format_result_json,
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
    uninstall_bootstrap,
    upgrade_bootstrap,
    verify_payload,
)


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
            help="Copy optional planning docs and bundled skills for richer review, intake, recovery, and autopilot workflows.",
        )
        command_parser.add_argument("--format", choices=("text", "json"), default="text")

    adopt_parser = subparsers.add_parser("adopt", help="Conservatively add planning bootstrap files to an existing repository.")
    adopt_parser.add_argument("--target")
    adopt_parser.add_argument("--dry-run", action="store_true")
    adopt_parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Copy optional planning docs and bundled skills without overwriting existing repo-owned files.",
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
        help="Refresh optional planning docs and bundled skills when the repo has enabled richer planning workflows.",
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

    review_parser = subparsers.add_parser("create-review", help="Create a valid planning review record skeleton.")
    review_parser.add_argument("slug")
    review_parser.add_argument("--title", required=True)
    review_parser.add_argument("--target")
    review_parser.add_argument("--scope")
    review_parser.add_argument("--classification", default="review")
    review_parser.add_argument("--render-markdown", action="store_true")
    review_parser.add_argument("--dry-run", action="store_true")
    review_parser.add_argument("--format", choices=("text", "json"), default="text")

    list_files_parser = subparsers.add_parser("list-files")
    list_files_parser.add_argument("--format", choices=("text", "json"), default="text")

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
    return _emit(collect_status(target=args.target), args.format)


def _run_doctor_report_adapter(args: argparse.Namespace) -> int:
    return _emit(doctor_bootstrap(target=args.target), args.format)


def _run_summary_report_adapter(args: argparse.Namespace) -> int:
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


def _run_report_adapter(args: argparse.Namespace) -> int:
    report = planning_report_tiny(target=args.target) if not getattr(args, "verbose", False) else planning_report(target=args.target)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)
    return 0


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
    reconcile = planning_reconcile(target=args.target)
    if args.format == "json":
        print(json.dumps(reconcile, indent=2))
    else:
        _print_reconcile(reconcile)
    return 0


_GENERATED_RUNTIME_HANDLERS = {
    "planning.doctor.report": _run_doctor_report_adapter,
    "planning.reconcile.report": _run_reconcile_report_adapter,
    "planning.report.report": _run_report_adapter,
    "planning.status.report": _run_status_report_adapter,
    "planning.summary.report": _run_summary_report_adapter,
}


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
        f"TODO: {summary['todo']['active_count']} active / "
        f"{summary['todo'].get('queued_count', 0)} queued / "
        f"{summary['todo']['item_count']} items / {summary['todo']['line_count']} lines"
    )
    print(
        f"Execplans: {summary['execplans']['active_count']} active / "
        f"{summary['execplans'].get('completed_count', 0)} completed / "
        f"{summary['execplans']['archived_count']} archived"
    )
    print(f"Roadmap: {summary['roadmap'].get('lane_count', 0)} candidate lanes / {summary['roadmap']['candidate_count']} candidate bullets")
    planning_surface_health = summary.get("planning_surface_health", {})
    if isinstance(planning_surface_health, dict) and planning_surface_health:
        print("Planning-surface health:")
        print(f"- Status: {planning_surface_health.get('status', 'unknown')}")
        print(f"- Warning count: {planning_surface_health.get('warning_count', 0)}")
        print(f"- Recommended next action: {planning_surface_health.get('recommended_next_action', '')}")
        for warning in planning_surface_health.get("warnings", [])[:3]:
            print(f"- [{warning.get('warning_class', '')}] {warning.get('path', '')}: {warning.get('message', '')}")
    ownership_review = summary.get("ownership_review", {})
    if ownership_review.get("status") == "present":
        print("Ownership review:")
        print(f"- Package-owned roots: {', '.join(ownership_review.get('package_owned_roots', []))}")
        print(f"- Repo-owned surfaces: {', '.join(ownership_review.get('repo_owned_surfaces', []))}")
        print(f"- Minimal repo hook: {ownership_review.get('minimal_repo_hook', '')}")
    hierarchy_contract = summary.get("hierarchy_contract", {})
    if hierarchy_contract.get("status") == "present":
        parent_lane = hierarchy_contract.get("parent_lane", {})
        active_chunk = hierarchy_contract.get("active_chunk", {})
        proof_state = hierarchy_contract.get("proof_state", {})
        print("Planning hierarchy view:")
        if parent_lane.get("id") or parent_lane.get("title"):
            lane_label = parent_lane.get("title") or parent_lane.get("id", "")
            if parent_lane.get("id") and parent_lane.get("title"):
                lane_label = f"{parent_lane['id']}: {parent_lane['title']}"
            print(f"- Parent lane: {lane_label}")
        else:
            print("- Parent lane: unspecified")
        active_chunk_label = active_chunk.get("milestone_id", "") or active_chunk.get("todo_id", "")
        active_chunk_scope = active_chunk.get("milestone_scope", "")
        print(f"- Active chunk: {active_chunk_label}: {active_chunk_scope}")
        near_term_queue = hierarchy_contract.get("near_term_queue", [])
        if near_term_queue:
            next_queued = near_term_queue[0]
            print(f"- Near-term queue: {next_queued.get('id', '')}: {next_queued.get('surface', '')}")
        print(f"- Next likely chunk: {hierarchy_contract.get('next_likely_chunk', '')}")
        print(f"- Proof achieved now: {proof_state.get('proof_achieved_now', '')}")
        print(f"- Validation still needed: {proof_state.get('validation_still_needed', '')}")
    elif hierarchy_contract:
        print(
            "Planning hierarchy view: "
            f"{hierarchy_contract.get('status')} ({hierarchy_contract.get('reason', 'no hierarchy projection available')})"
        )
    planning_record = summary.get("planning_record", {})
    if planning_record.get("status") == "present":
        task = planning_record.get("task", {})
        print("Planning record:")
        print(f"- Task: {task.get('id', '')}: {task.get('surface', '')}")
        print(f"- Requested outcome: {planning_record['requested_outcome']}")
        print(f"- Next action: {planning_record['next_action']}")
        print(f"- Continuation owner: {planning_record['continuation_owner']}")
        print(f"- Proof expectations: {', '.join(planning_record['proof_expectations'])}")
        proof_report = planning_record.get("proof_report", {})
        if proof_report:
            proof_evidence = proof_report.get('evidence for "proof achieved" state', "")
            print(f"- Proof achieved now: {proof_report.get('proof achieved now', '')}")
            print(f'- Evidence for "Proof achieved" state: {proof_evidence}')
        intent_satisfaction = planning_record.get("intent_satisfaction", {})
        if intent_satisfaction:
            print(f"- Was original intent fully satisfied?: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
            print(f"- Unsolved intent passed to: {intent_satisfaction.get('unsolved intent passed to', '')}")
        closure_check = planning_record.get("closure_check", {})
        if closure_check:
            print(f"- Closure decision: {closure_check.get('closure decision', '')}")
            print(f"- Larger-intent status: {closure_check.get('larger-intent status', '')}")
        intent_interpretation = planning_record.get("intent_interpretation", {})
        if intent_interpretation:
            print(f"- Literal request: {intent_interpretation.get('literal request', '')}")
            print(f"- Inferred intended outcome: {intent_interpretation.get('inferred intended outcome', '')}")
        execution_bounds = planning_record.get("execution_bounds", {})
        if execution_bounds:
            print(f"- Allowed paths: {execution_bounds.get('allowed paths', '')}")
            print(f"- Max changed files: {execution_bounds.get('max changed files', '')}")
        stop_conditions = planning_record.get("stop_conditions", {})
        if stop_conditions:
            print(f"- Stop when: {stop_conditions.get('stop when', '')}")
        execution_run = planning_record.get("execution_run", {})
        if execution_run:
            print(f"- Execution run status: {execution_run.get('run status', '')}")
            print(f"- Execution run next step: {execution_run.get('next step', '')}")
        finished_run_review = planning_record.get("finished_run_review", {})
        if finished_run_review:
            print(f"- Finished-run review: {finished_run_review.get('review status', '')}")
            print(f"- Intent served: {finished_run_review.get('intent served', '')}")
        tool_verification = planning_record.get("tool_verification", {})
        required_tools = tool_verification.get("required_tools", [])
        if required_tools:
            print(f"- Required tools: {', '.join(required_tools)}")
    elif planning_record:
        print(f"Planning record: {planning_record.get('status')} ({planning_record.get('reason', 'no compact record available')})")
    completed_execplans = summary.get("execplans", {}).get("completed_execplans", [])
    if completed_execplans:
        print("Completed execplans awaiting archive:")
        for item in completed_execplans:
            print(f"- {item.get('path', '')}: {item.get('status', '')}")
            proof_report = item.get("proof_report", {})
            if proof_report:
                print(f"  - Proof achieved now: {proof_report.get('proof achieved now', '')}")
            intent_satisfaction = item.get("intent_satisfaction", {})
            if intent_satisfaction:
                print(f"  - Intent satisfied: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
            closure_check = item.get("closure_check", {})
            if closure_check:
                print(f"  - Closure decision: {closure_check.get('closure decision', '')}")
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
    follow_through_contract = summary.get("follow_through_contract", {})
    if follow_through_contract.get("status") == "present":
        print("Follow-through contract view:")
        print(f"- Enabled: {follow_through_contract['what_this_slice_enabled']}")
        print(f"- Next likely slice: {follow_through_contract['next_likely_slice']}")
    elif follow_through_contract:
        print(
            "Follow-through contract view: "
            f"{follow_through_contract.get('status')} ({follow_through_contract.get('reason', 'no follow-through contract available')})"
        )
    context_budget_contract = summary.get("context_budget_contract", {})
    if context_budget_contract.get("status") == "present":
        print("Context budget contract view:")
        print(f"- Live working set: {context_budget_contract.get('live_working_set', '')}")
        print(f"- Recoverable later: {context_budget_contract.get('recoverable_later', '')}")
        print(f"- Pre-work config pull: {context_budget_contract.get('pre_work_config_pull', '')}")
        print(f"- Pre-work memory pull: {context_budget_contract.get('pre_work_memory_pull', '')}")
        print(f"- Shift triggers: {context_budget_contract.get('context_shift_triggers', '')}")
    elif context_budget_contract:
        print(
            "Context budget contract view: "
            f"{context_budget_contract.get('status')} ({context_budget_contract.get('reason', 'no context-budget contract available')})"
        )
    intent_interpretation_contract = summary.get("intent_interpretation_contract", {})
    if intent_interpretation_contract.get("status") == "present":
        print("Intent-interpretation contract view:")
        print(f"- Literal request: {intent_interpretation_contract.get('literal_request', '')}")
        print(f"- Inferred intended outcome: {intent_interpretation_contract.get('inferred_intended_outcome', '')}")
    elif intent_interpretation_contract:
        print(
            "Intent-interpretation contract view: "
            f"{intent_interpretation_contract.get('status')} ({intent_interpretation_contract.get('reason', 'no intent-interpretation contract available')})"
        )
    execution_run_contract = summary.get("execution_run_contract", {})
    if execution_run_contract.get("status") == "present":
        print("Execution-run contract view:")
        print(f"- Run status: {execution_run_contract.get('run_status', '')}")
        print(f"- Executor: {execution_run_contract.get('executor', '')}")
        print(f"- Changed surfaces: {execution_run_contract.get('changed_surfaces', '')}")
        print(f"- Next step: {execution_run_contract.get('next_step', '')}")
    elif execution_run_contract:
        print(
            "Execution-run contract view: "
            f"{execution_run_contract.get('status')} ({execution_run_contract.get('reason', 'no execution-run contract available')})"
        )
    finished_run_review_contract = summary.get("finished_run_review_contract", {})
    if finished_run_review_contract.get("status") == "present":
        print("Finished-run review contract view:")
        print(f"- Review status: {finished_run_review_contract.get('review_status', '')}")
        print(f"- Scope respected: {finished_run_review_contract.get('scope_respected', '')}")
        print(f"- Intent served: {finished_run_review_contract.get('intent_served', '')}")
        print(f"- Config compliance: {finished_run_review_contract.get('config_compliance', '')}")
        print(f"- Config trust: {finished_run_review_contract.get('config_trust', '')}")
    elif finished_run_review_contract:
        print(
            "Finished-run review contract view: "
            f"{finished_run_review_contract.get('status')} ({finished_run_review_contract.get('reason', 'no finished-run review contract available')})"
        )
    intent_validation_contract = summary.get("intent_validation_contract", {})
    if intent_validation_contract.get("status") == "present":
        counts = intent_validation_contract.get("counts", {})
        external = intent_validation_contract.get("external_evidence", {})
        current_external = intent_validation_contract.get("current_external_work", {})
        historical_audit = intent_validation_contract.get("historical_audit_references", {})
        print("Intent-validation contract view:")
        print(f"- Attention count: {counts.get('attention_count', 0)}")
        print(f"- Untracked external open items: {counts.get('untracked_external_open_count', 0)}")
        print(f"- Lower-trust closeouts: {counts.get('lower_trust_closeout_count', 0)}")
        print(f"- External evidence: {external.get('status', 'absent')}")
        print(
            "- Current external work: "
            f"{current_external.get('status', 'absent')} "
            f"({current_external.get('open_count', 0)} open / {current_external.get('closed_count', 0)} closed)"
        )
        print(
            "- Historical audit references: "
            f"{historical_audit.get('status', 'absent')} "
            f"({historical_audit.get('follow_up_open_count', 0)} follow-up open)"
        )
        print(f"- Recommended next action: {intent_validation_contract.get('recommended_next_action', '')}")
    elif intent_validation_contract:
        print(
            "Intent-validation contract view: "
            f"{intent_validation_contract.get('status')} ({intent_validation_contract.get('reason', 'no intent-validation contract available')})"
        )
    finished_work_inspection_contract = summary.get("finished_work_inspection_contract", {})
    if finished_work_inspection_contract.get("status") == "present":
        counts = finished_work_inspection_contract.get("counts", {})
        evidence = finished_work_inspection_contract.get("evidence", {})
        print("Finished-work inspection contract view:")
        print(f"- Archived closeouts: {counts.get('archived_closeout_count', 0)}")
        print(f"- Likely premature closeouts: {counts.get('likely_premature_closeout_count', 0)}")
        print(f"- Partial archived lanes: {counts.get('partial_count', 0)}")
        print(f"- Optional evidence: {evidence.get('status', 'absent')}")
        print(f"- Recommended next action: {finished_work_inspection_contract.get('recommended_next_action', '')}")
    elif finished_work_inspection_contract:
        print(
            "Finished-work inspection contract view: "
            f"{finished_work_inspection_contract.get('status')} ({finished_work_inspection_contract.get('reason', 'no finished-work inspection contract available')})"
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


def _print_report(report: dict) -> None:
    print(f"Target: {report['target_root']}")
    print("Command: report")
    print(f"Health: {report['health']}")
    status = report.get("status", {})
    if isinstance(status, dict):
        print(
            "Status: "
            f"{status.get('active_todo_count', 0)} active TODO / "
            f"{status.get('queued_todo_count', 0)} queued TODO / "
            f"{status.get('active_execplan_count', 0)} active execplans / "
            f"{status.get('completed_execplan_count', 0)} completed execplans / "
            f"{status.get('roadmap_lane_count', 0)} roadmap lanes / "
            f"{status.get('roadmap_candidate_count', 0)} roadmap candidates"
        )
    next_action = report.get("next_action", {})
    if isinstance(next_action, dict) and next_action.get("summary"):
        print(f"Next action: {next_action['summary']}")
    ownership_review = report.get("ownership_review", {})
    if isinstance(ownership_review, dict) and ownership_review.get("status") == "present":
        print(
            "Ownership review: "
            f"{len(ownership_review.get('repo_owned_surfaces', []))} repo-owned / "
            f"{len(ownership_review.get('package_owned_roots', []))} package-owned roots"
        )
    active = report.get("active", {})
    if isinstance(active, dict):
        hierarchy_contract = active.get("hierarchy_contract", {})
        if isinstance(hierarchy_contract, dict) and hierarchy_contract.get("status") == "present":
            parent_lane = hierarchy_contract.get("parent_lane", {})
            active_chunk = hierarchy_contract.get("active_chunk", {})
            lane_label = parent_lane.get("id") or parent_lane.get("title") or "unspecified"
            print(f"Hierarchy: {lane_label} -> {active_chunk.get('milestone_id', '') or active_chunk.get('todo_id', '')}")
        context_budget_contract = active.get("context_budget_contract", {})
        if isinstance(context_budget_contract, dict) and context_budget_contract.get("status") == "present":
            print(f"Live working set: {context_budget_contract.get('live_working_set', '')}")
            print(f"Pre-work config pull: {context_budget_contract.get('pre_work_config_pull', '')}")
            print(f"Pre-work memory pull: {context_budget_contract.get('pre_work_memory_pull', '')}")
        planning_record = active.get("planning_record", {})
        if isinstance(planning_record, dict) and planning_record.get("status") == "present":
            proof_report = planning_record.get("proof_report", {})
            intent_satisfaction = planning_record.get("intent_satisfaction", {})
            closure_check = planning_record.get("closure_check", {})
            if proof_report:
                print(f"Proof report: {proof_report.get('proof achieved now', '')}")
            if intent_satisfaction:
                print(f"Intent satisfaction: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
            if closure_check:
                print(f"Closure decision: {closure_check.get('closure decision', '')}")
        intent_interpretation_contract = active.get("intent_interpretation_contract", {})
        if isinstance(intent_interpretation_contract, dict) and intent_interpretation_contract.get("status") == "present":
            print(f"Intent interpretation: {intent_interpretation_contract.get('interpretation_distance', '')}")
        execution_run_contract = active.get("execution_run_contract", {})
        if isinstance(execution_run_contract, dict) and execution_run_contract.get("status") == "present":
            print(f"Execution run: {execution_run_contract.get('run_status', '')}")
            print(f"Changed surfaces: {execution_run_contract.get('changed_surfaces', '')}")
        finished_run_review_contract = active.get("finished_run_review_contract", {})
        if isinstance(finished_run_review_contract, dict) and finished_run_review_contract.get("status") == "present":
            print(f"Finished-run review: {finished_run_review_contract.get('review_status', '')}")
    intent_validation = report.get("intent_validation", {})
    if isinstance(intent_validation, dict) and intent_validation.get("status") == "present":
        counts = intent_validation.get("counts", {})
        external = intent_validation.get("external_evidence", {})
        current_external = intent_validation.get("current_external_work", {})
        historical_audit = intent_validation.get("historical_audit_references", {})
        print(
            "Intent validation: "
            f"{counts.get('attention_count', 0)} attention / "
            f"{counts.get('untracked_external_open_count', 0)} untracked external open / "
            f"{counts.get('lower_trust_closeout_count', 0)} lower-trust closeouts"
        )
        print(f"External intent evidence: {external.get('status', 'absent')}")
        print(
            "Current external work: "
            f"{current_external.get('status', 'absent')} "
            f"({current_external.get('open_count', 0)} open / {current_external.get('closed_count', 0)} closed)"
        )
        print(
            "Historical audit references: "
            f"{historical_audit.get('status', 'absent')} "
            f"({historical_audit.get('follow_up_open_count', 0)} follow-up open)"
        )
    finished_work_inspection = report.get("finished_work_inspection", {})
    if isinstance(finished_work_inspection, dict) and finished_work_inspection.get("status") == "present":
        counts = finished_work_inspection.get("counts", {})
        evidence = finished_work_inspection.get("evidence", {})
        print(
            "Finished-work inspection: "
            f"{counts.get('attention_count', 0)} attention / "
            f"{counts.get('likely_premature_closeout_count', 0)} likely premature / "
            f"{counts.get('partial_count', 0)} partial archived lanes"
        )
        print(f"Finished-work evidence: {evidence.get('status', 'absent')}")
    completed_execplans = report.get("completed_execplans", [])
    if completed_execplans:
        print(f"Completed execplans awaiting archive: {len(completed_execplans)}")
        for item in completed_execplans:
            print(f"- {item.get('path', '')}: {item.get('status', '')}")
            proof_report = item.get("proof_report", {})
            if proof_report:
                print(f"  Proof report: {proof_report.get('proof achieved now', '')}")
            intent_satisfaction = item.get("intent_satisfaction", {})
            if intent_satisfaction:
                print(f"  Intent satisfaction: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
            closure_check = item.get("closure_check", {})
            if closure_check:
                print(f"  Closure decision: {closure_check.get('closure decision', '')}")
    findings = report.get("findings", [])
    if findings:
        print("Findings:")
        for finding in findings:
            path = f"{finding['path']}: " if finding.get("path") else ""
            print(f"- {path}{finding.get('message', '')}")


def _print_reconcile(reconcile: dict) -> None:
    print(f"Target: {reconcile['target_root']}")
    print("Command: reconcile")
    print(f"Status: {reconcile['status']}")
    external = reconcile.get("external_work_state", {})
    if isinstance(external, dict):
        print(
            "Current external work: "
            f"{external.get('status', 'absent')} / "
            f"{external.get('open_count', 0)} open / "
            f"{external.get('closed_count', 0)} closed / "
            f"{external.get('untracked_open_count', 0)} untracked open"
        )
    historical = reconcile.get("historical_audit_references", {})
    if isinstance(historical, dict):
        print(
            "Historical audit references: "
            f"{historical.get('status', 'absent')} / "
            f"{historical.get('follow_up_open_count', 0)} follow-up open / "
            f"{historical.get('needs_audit_count', 0)} need audit"
        )
    stale = reconcile.get("stale_forward_state", {})
    if isinstance(stale, dict):
        completed = stale.get("completed_live_execplans", [])
        closed_lanes = stale.get("closed_roadmap_lanes", [])
        print(f"Completed live execplans: {len(completed) if isinstance(completed, list) else 0}")
        print(f"Closed roadmap lanes: {len(closed_lanes) if isinstance(closed_lanes, list) else 0}")
    recommendations = reconcile.get("recommendations", [])
    if isinstance(recommendations, list) and recommendations:
        print("Recommendations:")
        for item in recommendations:
            print(f"- {item}")


def _print_handoff(handoff: dict) -> None:
    print(f"Target: {handoff['target_root']}")
    contract = handoff.get("handoff_contract", {})
    if contract.get("status") != "present":
        reason = contract.get("reason", "no delegated handoff is available")
        print(f"Handoff: unavailable ({reason})")
        return

    task = contract.get("task", {})
    print("Delegated handoff:")
    print(f"- Task: {task.get('id', '')}: {task.get('surface', '')}")
    parent_lane = contract.get("parent_lane", {})
    lane_label = parent_lane.get("id") or parent_lane.get("title")
    if lane_label:
        print(f"- Parent lane: {lane_label}")
    print(f"- Next action: {contract.get('next_action', '')}")
    print(f"- Read first: {', '.join(contract.get('read_first', []))}")
    print(f"- Write scope: {', '.join(contract.get('owned_write_scope', []))}")
    print(f"- Proof: {', '.join(contract.get('proof_expectations', []))}")
    references = contract.get("references", [])
    if references:
        rendered = []
        for reference in references:
            if not isinstance(reference, dict):
                continue
            target = str(reference.get("target", "")).strip()
            if not target:
                continue
            rendered.append(
                f"{reference.get('kind', 'artifact')}:{target}"
                + (f" ({reference.get('role', 'context')})" if reference.get("role") else "")
            )
        if rendered:
            print(f"- References: {', '.join(rendered)}")
    review_residue = contract.get("review_residue", [])
    if review_residue:
        rendered_reviews = []
        for review in review_residue:
            if not isinstance(review, dict):
                continue
            title = str(review.get("title", "")).strip()
            target = str(review.get("target", "")).strip()
            finding_count = review.get("finding_count", 0)
            if not title and not target:
                continue
            rendered_reviews.append(f"{title or target} ({finding_count} findings)")
        if rendered_reviews:
            print(f"- Review residue: {', '.join(rendered_reviews)}")
    capability_posture = contract.get("capability_posture", {})
    if isinstance(capability_posture, dict) and capability_posture:
        print(
            "- Capability posture: "
            f"{capability_posture.get('execution class', '')} / "
            f"{capability_posture.get('recommended strength', '')} / "
            f"{capability_posture.get('preferred location', '')}"
        )
        print(f"- Capability why: {capability_posture.get('why', '')}")
    intent_interpretation = contract.get("intent_interpretation", {})
    if isinstance(intent_interpretation, dict) and intent_interpretation.get("status") == "present":
        print(f"- Literal request: {intent_interpretation.get('literal_request', '')}")
        print(f"- Interpreted outcome: {intent_interpretation.get('inferred_intended_outcome', '')}")
    execution_bounds = contract.get("execution_bounds", {})
    if isinstance(execution_bounds, dict) and execution_bounds:
        print(f"- Allowed paths: {execution_bounds.get('allowed paths', '')}")
        print(f"- Max changed files: {execution_bounds.get('max changed files', '')}")
    stop_conditions = contract.get("stop_conditions", {})
    if isinstance(stop_conditions, dict) and stop_conditions:
        print(f"- Stop when: {stop_conditions.get('stop when', '')}")
    context_budget = contract.get("context_budget", {})
    if isinstance(context_budget, dict) and context_budget.get("status") == "present":
        print(f"- Live working set: {context_budget.get('live_working_set', '')}")
        print(f"- Pre-work config pull: {context_budget.get('pre_work_config_pull', '')}")
        print(f"- Pre-work memory pull: {context_budget.get('pre_work_memory_pull', '')}")
        print(f"- Shift triggers: {context_budget.get('context_shift_triggers', '')}")
    worker_contract = contract.get("worker_contract", {})
    print(f"- Allowed methods: {', '.join(worker_contract.get('allowed_execution_methods', []))}")
    print(f"- Worker owns by default: {', '.join(worker_contract.get('worker_owns_by_default', []))}")
    return_with = contract.get("return_with", {})
    if isinstance(return_with, dict):
        print(f"- Return with execution-run fields: {', '.join(return_with.get('execution_run_fields', []))}")
        print(f"- Return with execution-summary fields: {', '.join(return_with.get('execution_summary_fields', []))}")


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
