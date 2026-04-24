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
    planning_handoff,
    planning_report,
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
        command_parser.add_argument("--local", action="store_true", help="Set up the workspace in a local, non-tracked directory.")
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
    summary_parser.add_argument("--profile", choices=("compact", "full"), default="compact")
    summary_parser.add_argument("--format", choices=("text", "json"), default="text")

    report_parser = subparsers.add_parser("report", help="Report compact planning module state without reading raw planning files first.")
    report_parser.add_argument("--target")
    report_parser.add_argument("--format", choices=("text", "json"), default="text")

    handoff_parser = subparsers.add_parser("handoff", help="Emit the compact delegated-worker handoff derived from active planning state.")
    handoff_parser.add_argument("--target")
    handoff_parser.add_argument("--format", choices=("text", "json"), default="text")

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
        return _emit(install_bootstrap(target=args.target, dry_run=args.dry_run, force=args.force, local_only=args.local), args.format)
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
        summary_profile = args.profile if args.format == "json" else "full"
        summary = planning_summary(target=args.target, profile=summary_profile)
        if args.format == "json":
            print(format_summary_json(summary))
        else:
            _print_summary(summary)
        return 0
    if args.command == "report":
        report = planning_report(target=args.target)
        if args.format == "json":
            print(json.dumps(report, indent=2))
        else:
            _print_report(report)
        return 0
    if args.command == "handoff":
        handoff = planning_handoff(target=args.target)
        if args.format == "json":
            print(json.dumps(handoff, indent=2))
        else:
            _print_handoff(handoff)
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
        print("Intent-validation contract view:")
        print(f"- Attention count: {counts.get('attention_count', 0)}")
        print(f"- Untracked external open items: {counts.get('untracked_external_open_count', 0)}")
        print(f"- Lower-trust closeouts: {counts.get('lower_trust_closeout_count', 0)}")
        print(f"- External evidence: {external.get('status', 'absent')}")
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
        print(
            "Intent validation: "
            f"{counts.get('attention_count', 0)} attention / "
            f"{counts.get('untracked_external_open_count', 0)} untracked external open / "
            f"{counts.get('lower_trust_closeout_count', 0)} lower-trust closeouts"
        )
        print(f"External intent evidence: {external.get('status', 'absent')}")
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
                "Use an installed `agentic-planning-bootstrap` command if it is already available locally, "
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
                "Use an installed `agentic-planning-bootstrap` command if it is already available locally, "
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
            "`agentic-planning-bootstrap` command with `--non-interactive` when available, and rerun render/check validation. "
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
            "Use an installed `agentic-planning-bootstrap` command if it is already available locally."
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
