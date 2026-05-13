from __future__ import annotations

import argparse
import json
import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

from repo_memory_bootstrap import __version__
from repo_memory_bootstrap.generated_cli_package import (
    build_generated_parser as build_generated_cli_package_parser,
)
from repo_memory_bootstrap.generated_cli_package import (
    generated_command_names as generated_cli_package_command_names,
)
from repo_memory_bootstrap.generated_cli_package import (
    generated_operation_contract as generated_cli_package_operation_contract,
)
from repo_memory_bootstrap.generated_cli_package import (
    run_generated_command as run_generated_cli_package_command,
)
from repo_memory_bootstrap.generated_cli_package import (
    supports_generated_command as supports_generated_cli_package_command,
)
from repo_memory_bootstrap.installer import (
    BOOTSTRAP_WORKSPACE_ROOT,
    MANIFEST_PATH,
    RepoDetectionError,
    adopt_bootstrap,
    check_current_memory,
    cleanup_bootstrap_workspace,
    collect_status,
    create_memory_note,
    detect_bootstrap_layout,
    doctor_bootstrap,
    format_actions,
    format_result_json,
    install_bootstrap,
    list_bundled_skills,
    list_payload_files,
    memory_report,
    migrate_layout,
    promotion_report,
    report_routes,
    resolve_target_root,
    resolve_upgrade_source,
    review_routes,
    route_memory,
    search_memory,
    show_current_memory,
    suggest_memory_note_capture,
    sync_memory,
    uninstall_bootstrap,
    upgrade_bootstrap,
    verify_payload,
)
from repo_memory_bootstrap.operation_ir_executor import run_operation_ir


def _program_name() -> str:
    invoked = sys.argv[0].replace("\\", "/").rsplit("/", 1)[-1]
    if invoked == "agentic-memory":
        return invoked
    return "agentic-memory"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_program_name(),
        description=("Install, route, inspect, and maintain checked-in repository Memory."),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    generated_commands = set(generated_cli_package_command_names())

    install_parser = subparsers.add_parser("install", help="Install bootstrap files into a repository.")
    _add_install_arguments(install_parser)
    init_parser = subparsers.add_parser("init", help="Alias for install, intended for clean bootstrap cases.")
    _add_install_arguments(init_parser)

    adopt_parser = subparsers.add_parser(
        "adopt",
        help="Add bootstrap capability to an existing repository conservatively.",
    )
    _add_target_arguments(adopt_parser)
    adopt_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the adoption plan without writing files.",
    )
    adopt_parser.add_argument(
        "--apply-local-entrypoint",
        action="store_true",
        help="Patch AGENTS.md with the canonical workflow pointer block when needed.",
    )
    _add_project_metadata_arguments(adopt_parser)
    _add_format_argument(adopt_parser)

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade an existing bootstrap install.")
    _add_target_arguments(upgrade_parser)
    upgrade_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the upgrade plan without writing files.",
    )
    upgrade_parser.add_argument("--force", action="store_true", help="Allow replacing customised starter files.")
    upgrade_parser.add_argument(
        "--apply-local-entrypoint",
        action="store_true",
        help="Patch AGENTS.md with the canonical workflow pointer block when needed.",
    )
    _add_project_metadata_arguments(upgrade_parser)
    _add_format_argument(upgrade_parser)

    migrate_parser = subparsers.add_parser(
        "migrate-layout",
        help="Move bootstrap-managed files from the legacy memory layout into `.agentic-workspace/memory/` conservatively.",
    )
    _add_target_arguments(migrate_parser)
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the layout migration plan without writing files.",
    )
    _add_format_argument(migrate_parser)

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove bootstrap-managed files conservatively.")
    _add_target_arguments(uninstall_parser)
    uninstall_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the uninstall plan without writing files.",
    )
    _add_project_metadata_arguments(uninstall_parser)
    _add_format_argument(uninstall_parser)

    if "doctor" not in generated_commands:
        doctor_parser = subparsers.add_parser("doctor", help="Diagnose bootstrap state and recommended remediation.")
        _add_target_arguments(doctor_parser)
        doctor_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Emit broad diagnostic action detail.",
        )
        doctor_parser.add_argument(
            "--strict-doc-ownership",
            action="store_true",
            help="Enforce doc-ownership audits even when the repo manifest has not enabled them.",
        )
        _add_project_metadata_arguments(doctor_parser)
        _add_format_argument(doctor_parser)

    if "status" not in generated_commands:
        status_parser = subparsers.add_parser("status", help="Report whether bootstrap files are present.")
        _add_target_arguments(status_parser)
        status_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Emit broad diagnostic action detail.",
        )
        _add_format_argument(status_parser)

    if "list-files" not in generated_commands:
        list_files_parser = subparsers.add_parser("list-files", help="Preview packaged bootstrap files.")
        _add_target_arguments(list_files_parser)
        _add_format_argument(list_files_parser)

    if "list-skills" not in generated_commands:
        list_skills_parser = subparsers.add_parser("list-skills", help="List bundled bootstrap-lifecycle skills.")
        _add_format_argument(list_skills_parser)

    prompt_parser = subparsers.add_parser(
        "prompt",
        help="Print a canonical agent prompt for install, adopt, populate, upgrade, or uninstall.",
    )
    prompt_subparsers = prompt_parser.add_subparsers(dest="prompt_command", required=True)
    prompt_install_parser = prompt_subparsers.add_parser("install", help="Print the canonical install prompt.")
    _add_target_arguments(prompt_install_parser)
    prompt_adopt_parser = prompt_subparsers.add_parser("adopt", help="Print the canonical adoption prompt.")
    _add_target_arguments(prompt_adopt_parser)
    prompt_populate_parser = prompt_subparsers.add_parser("populate", help="Print the canonical populate prompt.")
    _add_target_arguments(prompt_populate_parser)
    prompt_upgrade_parser = prompt_subparsers.add_parser("upgrade", help="Print the canonical upgrade prompt.")
    _add_target_arguments(prompt_upgrade_parser)
    prompt_uninstall_parser = prompt_subparsers.add_parser("uninstall", help="Print the canonical uninstall prompt.")
    _add_target_arguments(prompt_uninstall_parser)

    current_parser = subparsers.add_parser("current", help="Inspect or check legacy current-memory migration residue.")
    current_subparsers = current_parser.add_subparsers(dest="current_command", required=True)
    current_show_parser = current_subparsers.add_parser("show", help="Show legacy current-memory notes when present.")
    _add_target_arguments(current_show_parser)
    _add_format_argument(current_show_parser)
    current_check_parser = current_subparsers.add_parser("check", help="Check legacy current-memory notes for migration pressure.")
    _add_target_arguments(current_check_parser)
    _add_format_argument(current_check_parser)

    route_parser = subparsers.add_parser(
        "route",
        help="Suggest the smallest relevant durable note set for touched files or surfaces so the agent can read less, not more.",
    )
    _add_target_arguments(route_parser)
    route_parser.add_argument("--files", nargs="*", default=[], help="Touched file paths to route from.")
    route_parser.add_argument(
        "--surface",
        dest="surfaces",
        nargs="*",
        default=[],
        help="Explicit routing surfaces.",
    )
    _add_format_argument(route_parser)

    route_review_parser = subparsers.add_parser(
        "route-review",
        help="Review checked-in routing feedback cases against the current routing result.",
    )
    _add_target_arguments(route_review_parser)
    _add_format_argument(route_review_parser)

    if "route-report" not in generated_commands:
        route_report_parser = subparsers.add_parser(
            "route-report",
            help="Show a compact aggregate routing snapshot derived from checked-in feedback cases and fixtures.",
        )
        _add_target_arguments(route_report_parser)
        route_report_parser.add_argument("--verbose", action="store_true", help="Emit full route-report fixture detail.")
        _add_format_argument(route_report_parser)

    sync_parser = subparsers.add_parser(
        "sync-memory", help="Suggest memory updates for changed work and surface compact upstream improvement candidates."
    )
    _add_target_arguments(sync_parser)
    sync_parser.add_argument("--files", nargs="*", default=[], help="Changed file paths to inspect.")
    sync_parser.add_argument("--notes", nargs="*", default=[], help="Explicit memory notes to review.")
    _add_format_argument(sync_parser)

    if "promotion-report" not in generated_commands:
        promotion_parser = subparsers.add_parser(
            "promotion-report",
            help=(
                "Suggest memory notes that should be promoted into canonical docs or "
                "considered for elimination through skills, scripts, tests, or refactors."
            ),
        )
        _add_target_arguments(promotion_parser)
        promotion_parser.add_argument(
            "--notes",
            nargs="*",
            default=[],
            help="Explicit memory notes to inspect.",
        )
        promotion_parser.add_argument(
            "--mode",
            choices=("all", "remediation"),
            default="all",
            help="Report all candidates or only medium/high-confidence remediation candidates.",
        )
        _add_format_argument(promotion_parser)

    if "report" not in generated_commands:
        report_parser = subparsers.add_parser(
            "report",
            help="Report compact memory module state without broad note-tree inspection first.",
        )
        _add_target_arguments(report_parser)
        report_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Emit broad diagnostic report detail.",
        )
        _add_format_argument(report_parser)

    create_note_parser = subparsers.add_parser(
        "create-note",
        help="Create a minimal Memory note and matching manifest entry.",
    )
    create_note_parser.add_argument("slug")
    create_note_parser.add_argument("--title")
    create_note_parser.add_argument("--folder", default="domains")
    create_note_parser.add_argument("--note-type", default="domain")
    create_note_parser.add_argument("--summary", default="")
    create_note_parser.add_argument("--applies-to", nargs="*", default=[])
    create_note_parser.add_argument("--use-when", nargs="*", default=[])
    create_note_parser.add_argument("--routes-from", nargs="*", default=[])
    create_note_parser.add_argument("--stale-when", nargs="*", default=[])
    create_note_parser.add_argument("--evidence", nargs="*", default=[])
    create_note_parser.add_argument("--memory-role", default="")
    create_note_parser.add_argument("--promotion-target", default="")
    create_note_parser.add_argument("--promotion-trigger", default="")
    create_note_parser.add_argument("--retention-after-promotion", default="")
    create_note_parser.add_argument("--dry-run", action="store_true")
    _add_target_arguments(create_note_parser)
    _add_format_argument(create_note_parser)

    capture_note_parser = subparsers.add_parser(
        "capture-note",
        help="Recommend whether durable learning should update an existing Memory note or create a new one.",
    )
    capture_note_parser.add_argument("slug", nargs="?", default="")
    capture_note_parser.add_argument("--summary", default="")
    capture_note_parser.add_argument("--files", nargs="*", default=[])
    capture_note_parser.add_argument("--surface", dest="surfaces", nargs="*", default=[])
    capture_note_parser.add_argument("--existing-note", default="")
    capture_note_parser.add_argument("--force-new-reason", default="")
    _add_target_arguments(capture_note_parser)
    _add_format_argument(capture_note_parser)

    search_parser = subparsers.add_parser(
        "search",
        help="Search for keywords across all memory notes.",
    )
    _add_target_arguments(search_parser)
    search_parser.add_argument("query", help="Keyword or pattern to search for.")
    _add_format_argument(search_parser)

    verify_parser = subparsers.add_parser("verify-payload", help="Verify the packaged bootstrap payload contract.")
    _add_target_arguments(verify_parser)
    _add_format_argument(verify_parser)

    cleanup_parser = subparsers.add_parser("bootstrap-cleanup", help="Remove the temporary bootstrap workspace.")
    _add_target_arguments(cleanup_parser)
    _add_format_argument(cleanup_parser)

    return parser


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")


def _add_install_arguments(command_parser: argparse.ArgumentParser) -> None:
    _add_target_arguments(command_parser)
    command_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without writing files.",
    )
    command_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite managed files that already exist.",
    )
    _add_project_metadata_arguments(command_parser)
    _add_format_argument(command_parser)


def _add_project_metadata_arguments(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--project-name", help="Value used for the <PROJECT_NAME> placeholder.")
    command_parser.add_argument("--project-purpose", help="Value used for the <PROJECT_PURPOSE> placeholder.")
    command_parser.add_argument("--key-repo-docs", help="Value used for the <KEY_REPO_DOCS> placeholder.")
    command_parser.add_argument("--key-subsystems", help="Value used for the <KEY_SUBSYSTEMS> placeholder.")
    command_parser.add_argument(
        "--primary-build-command",
        help="Value used for the <PRIMARY_BUILD_COMMAND> placeholder.",
    )
    command_parser.add_argument(
        "--primary-test-command",
        help="Value used for the <PRIMARY_TEST_COMMAND> placeholder.",
    )
    command_parser.add_argument(
        "--other-key-commands",
        help="Value used for the <OTHER_KEY_COMMANDS> placeholder.",
    )
    command_parser.add_argument(
        "--policy-profile",
        choices=("default", "strict-doc-ownership"),
        default="default",
        help=(
            "Installer policy preset. strict-doc-ownership enables forbid_core_docs_depend_on_memory in .agentic-workspace/memory/repo/manifest.toml."
        ),
    )


def _add_format_argument(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )


def _handle_install(args: argparse.Namespace) -> int:
    result = install_bootstrap(
        target=args.target,
        dry_run=args.dry_run,
        force=args.force,
        project_name=args.project_name,
        project_purpose=args.project_purpose,
        key_repo_docs=args.key_repo_docs,
        key_subsystems=args.key_subsystems,
        primary_build_command=args.primary_build_command,
        primary_test_command=args.primary_test_command,
        other_key_commands=args.other_key_commands,
        policy_profile=args.policy_profile,
    )
    _emit_result(result, output_format=args.format, include_install_summary=True)
    return 0


def _handle_adopt(args: argparse.Namespace) -> int:
    result = adopt_bootstrap(
        target=args.target,
        dry_run=args.dry_run,
        apply_local_entrypoint=args.apply_local_entrypoint,
        project_name=args.project_name,
        project_purpose=args.project_purpose,
        key_repo_docs=args.key_repo_docs,
        key_subsystems=args.key_subsystems,
        primary_build_command=args.primary_build_command,
        primary_test_command=args.primary_test_command,
        other_key_commands=args.other_key_commands,
        policy_profile=args.policy_profile,
    )
    _emit_result(result, output_format=args.format, include_install_summary=True)
    return 0


def _handle_upgrade(args: argparse.Namespace) -> int:
    result = upgrade_bootstrap(
        target=args.target,
        dry_run=args.dry_run,
        force=args.force,
        apply_local_entrypoint=args.apply_local_entrypoint,
        project_name=args.project_name,
        project_purpose=args.project_purpose,
        key_repo_docs=args.key_repo_docs,
        key_subsystems=args.key_subsystems,
        primary_build_command=args.primary_build_command,
        primary_test_command=args.primary_test_command,
        other_key_commands=args.other_key_commands,
        policy_profile=args.policy_profile,
    )
    _emit_result(result, output_format=args.format)
    return 0


def _handle_migrate_layout(args: argparse.Namespace) -> int:
    _emit_result(migrate_layout(target=args.target, dry_run=args.dry_run), output_format=args.format)
    return 0


def _handle_uninstall(args: argparse.Namespace) -> int:
    result = uninstall_bootstrap(
        target=args.target,
        dry_run=args.dry_run,
        project_name=args.project_name,
        project_purpose=args.project_purpose,
        key_repo_docs=args.key_repo_docs,
        key_subsystems=args.key_subsystems,
        primary_build_command=args.primary_build_command,
        primary_test_command=args.primary_test_command,
        other_key_commands=args.other_key_commands,
    )
    _emit_result(result, output_format=args.format)
    return 0


def _handle_doctor(args: argparse.Namespace) -> int:
    if args.format == "json" and not getattr(args, "verbose", False):
        print(json.dumps(_tiny_memory_lifecycle_payload(target=args.target, command="doctor"), indent=2))
        return 0
    result = doctor_bootstrap(
        target=args.target,
        strict_doc_ownership=args.strict_doc_ownership,
        project_name=args.project_name,
        project_purpose=args.project_purpose,
        key_repo_docs=args.key_repo_docs,
        key_subsystems=args.key_subsystems,
        primary_build_command=args.primary_build_command,
        primary_test_command=args.primary_test_command,
        other_key_commands=args.other_key_commands,
    )
    _emit_result(result, output_format=args.format)
    return 0


def _handle_status(args: argparse.Namespace) -> int:
    if args.format == "json" and not getattr(args, "verbose", False):
        print(json.dumps(_tiny_memory_lifecycle_payload(target=args.target, command="status"), indent=2))
        return 0
    result = collect_status(target=args.target)
    _emit_result(result, output_format=args.format)
    return 0


def _handle_list_files(args: argparse.Namespace) -> int:
    _emit_result(list_payload_files(target=args.target), output_format=args.format)
    return 0


def _handle_list_skills(args: argparse.Namespace) -> int:
    _emit_result(list_bundled_skills(), output_format=args.format)
    return 0


def _handle_prompt(args: argparse.Namespace) -> int:
    print(_build_agent_prompt(args.prompt_command, target=args.target))
    return 0


def _handle_current_show(args: argparse.Namespace) -> int:
    _emit_current_view(show_current_memory(target=args.target), output_format=args.format)
    return 0


def _handle_current_check(args: argparse.Namespace) -> int:
    _emit_result(check_current_memory(target=args.target), output_format=args.format)
    return 0


def _handle_route(args: argparse.Namespace) -> int:
    _emit_result(
        route_memory(target=args.target, files=args.files, surfaces=args.surfaces),
        output_format=args.format,
    )
    return 0


def _handle_sync_memory(args: argparse.Namespace) -> int:
    _emit_result(
        sync_memory(target=args.target, files=args.files, notes=args.notes),
        output_format=args.format,
    )
    return 0


def _handle_route_review(args: argparse.Namespace) -> int:
    _emit_result(review_routes(target=args.target), output_format=args.format)
    return 0


def _handle_route_report(args: argparse.Namespace) -> int:
    if args.format == "json" and not getattr(args, "verbose", False):
        print(json.dumps(_tiny_route_report_payload(target=args.target), indent=2))
        return 0
    result = report_routes(target=args.target)
    _emit_result(result, output_format=args.format)
    return 0


def _handle_promotion_report(args: argparse.Namespace) -> int:
    _emit_result(promotion_report(target=args.target, notes=args.notes, mode=args.mode), output_format=args.format)
    return 0


def _handle_report(args: argparse.Namespace) -> int:
    if args.format == "json" and not getattr(args, "verbose", False):
        print(json.dumps(_tiny_memory_report_fast(target=args.target), indent=2))
        return 0
    report = memory_report(target=args.target)
    if not getattr(args, "verbose", False):
        report = _tiny_memory_report(report)
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)
    return 0


def _compact_result_dict(result, *, detail_command: str) -> dict[str, object]:
    payload = result.to_dict()
    actions = payload.get("actions", [])
    compact_actions: list[dict[str, object]] = []
    if isinstance(actions, list):
        for action in actions[:5]:
            if isinstance(action, dict):
                compact_actions.append(
                    {
                        key: action.get(key)
                        for key in ("kind", "path", "detail", "category", "remediation_kind", "memory_action")
                        if action.get(key) not in (None, "")
                    }
                )
    return {
        "target_root": payload.get("target_root", ""),
        "dry_run": payload.get("dry_run", False),
        "mode": payload.get("mode", ""),
        "message": payload.get("message", ""),
        "detected_version": payload.get("detected_version"),
        "bootstrap_version": payload.get("bootstrap_version"),
        "action_count": len(actions) if isinstance(actions, list) else 0,
        "actions": compact_actions,
        "route_summary": payload.get("route_summary", {}),
        "missing_note_hint": payload.get("missing_note_hint", ""),
        "review_summary": payload.get("review_summary", {}),
        "sync_summary": payload.get("sync_summary", {}),
        "detail_command": detail_command,
    }


def _tiny_memory_manifest_counts(*, target_root: Path) -> dict[str, object]:
    manifest_path = target_root / MANIFEST_PATH
    if not manifest_path.exists():
        return {
            "status": "missing",
            "note_count": 0,
            "required_count": 0,
            "optional_count": 0,
            "routing_only_count": 0,
            "path": MANIFEST_PATH.as_posix(),
        }
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {
            "status": "invalid",
            "note_count": 0,
            "required_count": 0,
            "optional_count": 0,
            "routing_only_count": 0,
            "path": MANIFEST_PATH.as_posix(),
        }
    notes = payload.get("notes", {}) if isinstance(payload, dict) else {}
    note_values = list(notes.values()) if isinstance(notes, dict) else []
    required_count = 0
    optional_count = 0
    routing_only_count = 0
    for note in note_values:
        if not isinstance(note, dict):
            continue
        note_map = cast(dict[str, object], note)
        relevance = str(note_map.get("task_relevance", "")).strip().lower()
        if relevance == "required":
            required_count += 1
        elif relevance == "optional":
            optional_count += 1
        if bool(note_map.get("routing_only", False)):
            routing_only_count += 1
    return {
        "status": "present",
        "note_count": len(note_values),
        "required_count": required_count,
        "optional_count": optional_count,
        "routing_only_count": routing_only_count,
        "path": MANIFEST_PATH.as_posix(),
    }


def _tiny_memory_lifecycle_payload(*, target: str | Path | None, command: str) -> dict[str, object]:
    target_root = resolve_target_root(target)
    counts = _tiny_memory_manifest_counts(target_root=target_root)
    health = "healthy" if counts["status"] == "present" else "attention-needed"
    return {
        "target_root": str(target_root),
        "dry_run": command == "doctor",
        "mode": "",
        "message": "Status report" if command == "status" else "Doctor report",
        "health": health,
        "detected_version": None,
        "bootstrap_version": None,
        "action_count": 0 if health == "healthy" else 1,
        "actions": []
        if health == "healthy"
        else [
            {
                "kind": counts["status"],
                "path": counts["path"],
                "detail": "memory manifest is not readable; run full doctor for remediation detail",
            }
        ],
        "active": counts,
        "detail_command": f"agentic-memory {command} --target . --verbose --format json",
    }


def _tiny_memory_report_fast(*, target: str | Path | None) -> dict[str, object]:
    target_root = resolve_target_root(target)
    counts = _tiny_memory_manifest_counts(target_root=target_root)
    health = "healthy" if counts["status"] == "present" else "attention-needed"
    findings = []
    if health != "healthy":
        findings.append(
            {
                "severity": "warning",
                "path": counts["path"],
                "message": "Memory manifest is not readable; run full report for remediation detail.",
            }
        )
    return {
        "kind": "memory-module-report/v1",
        "profile": "tiny",
        "module": "memory",
        "target_root": str(target_root),
        "health": health,
        "status": {
            "detected_version": None,
            "bootstrap_version": None,
            "note_count": counts["note_count"],
            "manifest_status": counts["status"],
        },
        "active": {
            "note_count": counts["note_count"],
            "manifest_note_count": counts["note_count"],
            "required_count": counts["required_count"],
            "optional_count": counts["optional_count"],
            "routing_only_count": counts["routing_only_count"],
        },
        "habitual_pull": {
            "status": "available" if counts["status"] == "present" else "unavailable",
            "read_first": [".agentic-workspace/memory/repo/index.md"],
            "do_not_bulk_read": True,
        },
        "promotion_pressure": {
            "status": "not-evaluated",
            "detail_command": "agentic-memory report --target . --verbose --format json",
        },
        "trust": {"status": "not-evaluated", "detail_command": "agentic-memory report --target . --verbose --format json"},
        "finding_count": len(findings),
        "findings": findings,
        "next_action": {
            "summary": "No immediate memory action." if health == "healthy" else "Run full memory report for remediation detail.",
            "commands": [] if health == "healthy" else ["agentic-memory report --target . --verbose --format json"],
        },
        "detail_commands": {
            "full": "agentic-memory report --target . --verbose --format json",
            "route": "agentic-memory route --target . --files <paths> --format json",
        },
    }


def _tiny_route_report_payload(*, target: str | Path | None) -> dict[str, object]:
    target_root = resolve_target_root(target)
    feedback_path = target_root / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md"
    fixtures_root = target_root / "tests" / "fixtures" / "routing"
    fixture_count = len(list(fixtures_root.glob("*.json"))) if fixtures_root.exists() else 0
    feedback_present = feedback_path.exists()
    return {
        "target_root": str(target_root),
        "dry_run": True,
        "message": "Routing report",
        "health": "healthy",
        "route_report_summary": {
            "feedback": {"status": "present" if feedback_present else "missing", "path": feedback_path.as_posix()},
            "fixtures": {"status": "present" if fixture_count else "missing", "fixture_count": fixture_count},
            "detail": "Run full route-report for fixture evaluation and feedback-case matching.",
        },
        "detail_command": "agentic-memory route-report --target . --verbose --format json",
    }


def _tiny_memory_report(report: dict[str, object]) -> dict[str, object]:
    findings = report.get("findings", [])
    active = report.get("active", {})
    if isinstance(active, dict):
        active_map = cast(dict[str, object], active)
        active = {
            key: active_map.get(key)
            for key in ("note_count", "manifest_note_count", "required_count", "optional_count", "routing_only_count")
            if key in active_map
        }
    habitual_pull = report.get("habitual_pull", {})
    if isinstance(habitual_pull, dict):
        habitual_pull_map = cast(dict[str, object], habitual_pull)
        habitual_pull = {
            key: habitual_pull_map.get(key) for key in ("status", "read_first", "max_notes", "do_not_bulk_read") if key in habitual_pull_map
        }
    trust = report.get("trust", {})
    if isinstance(trust, dict):
        trust_map = cast(dict[str, object], trust)
        trust = {key: trust_map.get(key) for key in ("status", "attention_count", "finding_count", "detail_command") if key in trust_map}
    return {
        "kind": report.get("kind", "memory-report/v1"),
        "profile": "tiny",
        "module": report.get("module", "memory"),
        "target_root": report.get("target_root", ""),
        "health": report.get("health", "unknown"),
        "status": report.get("status", {}),
        "active": active,
        "habitual_pull": habitual_pull,
        "promotion_pressure": report.get("promotion_pressure", {}),
        "trust": trust,
        "finding_count": len(findings) if isinstance(findings, list) else 0,
        "findings": findings[:5] if isinstance(findings, list) else [],
        "next_action": report.get("next_action", {}),
        "detail_commands": {
            "full": "agentic-memory report --target . --verbose --format json",
            "route": "agentic-memory route --target . --files <paths> --format json",
        },
    }


def _handle_create_note(args: argparse.Namespace) -> int:
    _emit_result(
        create_memory_note(
            slug=args.slug,
            title=args.title,
            target=args.target,
            folder=args.folder,
            note_type=args.note_type,
            summary=args.summary,
            applies_to=args.applies_to,
            use_when=args.use_when,
            routes_from=args.routes_from,
            stale_when=args.stale_when,
            evidence=args.evidence,
            memory_role=args.memory_role,
            promotion_target=args.promotion_target,
            promotion_trigger=args.promotion_trigger,
            retention_after_promotion=args.retention_after_promotion,
            dry_run=args.dry_run,
        ),
        output_format=args.format,
    )
    return 0


def _handle_capture_note(args: argparse.Namespace) -> int:
    payload = suggest_memory_note_capture(
        slug=args.slug,
        target=args.target,
        summary=args.summary,
        files=args.files,
        surfaces=args.surfaces,
        existing_note=args.existing_note,
        force_new_reason=args.force_new_reason,
    )
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(f"Recommended action: {payload.get('recommended_action', 'unknown')}")
        print(f"Reason: {payload.get('reason', '')}")
        commands = payload.get("commands", [])
        for command in commands if isinstance(commands, list) else []:
            print(f"Command: {command}")
    return 0


def _handle_search(args: argparse.Namespace) -> int:
    _emit_result(
        search_memory(target=args.target, query=args.query),
        output_format=args.format,
    )
    return 0


def _handle_verify_payload(args: argparse.Namespace) -> int:
    _emit_result(verify_payload(target=args.target), output_format=args.format)
    return 0


def _handle_bootstrap_cleanup(args: argparse.Namespace) -> int:
    _emit_result(cleanup_bootstrap_workspace(target=args.target), output_format=args.format)
    return 0


COMMAND_HANDLERS = {
    "install": _handle_install,
    "init": _handle_install,
    "adopt": _handle_adopt,
    "upgrade": _handle_upgrade,
    "migrate-layout": _handle_migrate_layout,
    "uninstall": _handle_uninstall,
    "doctor": _handle_doctor,
    "status": _handle_status,
    "list-files": _handle_list_files,
    "list-skills": _handle_list_skills,
    "prompt": _handle_prompt,
    "current:show": _handle_current_show,
    "current:check": _handle_current_check,
    "route": _handle_route,
    "route-review": _handle_route_review,
    "route-report": _handle_route_report,
    "sync-memory": _handle_sync_memory,
    "promotion-report": _handle_promotion_report,
    "report": _handle_report,
    "create-note": _handle_create_note,
    "capture-note": _handle_capture_note,
    "search": _handle_search,
    "verify-payload": _handle_verify_payload,
    "bootstrap-cleanup": _handle_bootstrap_cleanup,
}


def _command_key(args: argparse.Namespace) -> str:
    if args.command == "current":
        return f"current:{args.current_command}"
    return args.command


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    try:
        generated_result = _run_generated_cli_package_if_supported(argv_list)
        if generated_result is not None:
            return generated_result
    except RepoDetectionError as exc:
        build_generated_cli_package_parser().error(_repo_detection_error_message(exc))

    parser = build_parser()
    args = parser.parse_args(argv_list)

    try:
        handler = COMMAND_HANDLERS.get(_command_key(args))
        if handler is None:
            parser.error(f"Unknown command: {args.command}")
        return handler(args)
    except RepoDetectionError as exc:
        parser.error(_repo_detection_error_message(exc))


def _run_generated_cli_package_if_supported(argv: list[str]) -> int | None:
    if not supports_generated_cli_package_command(argv):
        return None
    return run_generated_cli_package_command(argv, _run_generated_cli_operation)


def _repo_detection_error_message(exc: RepoDetectionError) -> str:
    return f"{exc} Retry with --target . when the current directory is the intended repository."


def _run_generated_cli_operation(operation_id: str, args: argparse.Namespace) -> int:
    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is not None:
        result = handler(args)
        return 0 if result is None else result
    build_generated_cli_package_parser().error(f"Generated adapter for {args.command} references unsupported operation {operation_id}.")
    raise SystemExit(2)


def _handle_generated_doctor(args: argparse.Namespace) -> int | None:
    for name in (
        "project_name",
        "project_purpose",
        "key_repo_docs",
        "key_subsystems",
        "primary_build_command",
        "primary_test_command",
        "other_key_commands",
    ):
        if not hasattr(args, name):
            setattr(args, name, None)
    if not hasattr(args, "policy_profile"):
        args.policy_profile = "default"
    return _handle_doctor(args)


def _run_doctor_report_adapter(args: argparse.Namespace) -> int | None:
    return _handle_generated_doctor(args)


def _run_list_files_report_adapter(args: argparse.Namespace) -> int | None:
    return run_operation_ir(generated_cli_package_operation_contract("memory.list-files.report"), args)


def _run_list_skills_report_adapter(args: argparse.Namespace) -> int | None:
    return run_operation_ir(generated_cli_package_operation_contract("memory.list-skills.report"), args)


def _run_promotion_report_adapter(args: argparse.Namespace) -> int | None:
    return _handle_promotion_report(args)


def _run_report_adapter(args: argparse.Namespace) -> int | None:
    return _handle_report(args)


def _run_route_report_adapter(args: argparse.Namespace) -> int | None:
    return _handle_route_report(args)


def _run_status_report_adapter(args: argparse.Namespace) -> int | None:
    return _handle_status(args)


_GENERATED_RUNTIME_HANDLERS = {
    "memory.doctor.report": _run_doctor_report_adapter,
    "memory.list-files.report": _run_list_files_report_adapter,
    "memory.list-skills.report": _run_list_skills_report_adapter,
    "memory.promotion-report.report": _run_promotion_report_adapter,
    "memory.report.report": _run_report_adapter,
    "memory.route-report.report": _run_route_report_adapter,
    "memory.status.report": _run_status_report_adapter,
}


def _emit_result(result, *, output_format: str, include_install_summary: bool = False) -> None:
    if output_format == "json":
        print(format_result_json(result))
        return

    print(f"Target: {result.target_root}")
    print(result.message)
    if result.route_summary:
        print(
            "Route summary: "
            f"notes={result.route_summary.get('routed_note_count', 0)}, "
            f"required={result.route_summary.get('required_count', 0)}, "
            f"optional={result.route_summary.get('optional_count', 0)}, "
            f"exceeded_target={result.route_summary.get('exceeded_target', 'no')}"
        )
        if result.route_summary.get("justification"):
            print(f"Route justification: {result.route_summary['justification']}")
        if result.route_summary.get("warning"):
            print(f"Route warning: {result.route_summary['warning']}")
    if result.missing_note_hint:
        print(f"Routing feedback: {result.missing_note_hint}")
    if result.review_summary:
        print(
            "Route review: "
            f"reviewed={result.review_summary.get('reviewed_case_count', 0)}, "
            f"still_missed={result.review_summary.get('still_missed_count', 0)}, "
            f"still_over_routed={result.review_summary.get('still_over_routed_count', 0)}, "
            f"unresolved={result.review_summary.get('unresolved_case_count', 0)}"
        )
    if result.sync_summary:
        primary = result.sync_summary.get("primary_note", {})
        summary = result.sync_summary.get("summary", "")
        if summary:
            print(f"Sync summary: {summary}")
        if isinstance(primary, dict) and primary.get("path"):
            print(f"Primary note: {primary.get('path')} ({primary.get('action', 'review')})")
    if result.route_report_summary:
        feedback = result.route_report_summary.get("feedback", {})
        fixtures = result.route_report_summary.get("fixtures", {})
        missed_note = result.route_report_summary.get("missed_note", {})
        over_routing = result.route_report_summary.get("over_routing", {})
        working_set = result.route_report_summary.get("working_set", {})
        startup_cost = result.route_report_summary.get("startup_cost", {})
        print("Feedback cases:")
        print(
            f"  total={feedback.get('total_feedback_case_count', 0)}, "
            f"reviewed={feedback.get('reviewed_feedback_case_count', 0)}, "
            f"unresolved={feedback.get('unresolved_feedback_case_count', 0)}, "
            f"externalized={feedback.get('externalized_case_count', 0)}, "
            f"missed_note_cases={feedback.get('missed_note_case_count', 0)}, "
            f"still_missed={feedback.get('still_missed_count', 0)}, "
            f"over_routing_cases={feedback.get('over_routing_case_count', 0)}, "
            f"still_over_routed={feedback.get('still_over_routed_count', 0)}, "
            f"open={feedback.get('open_case_count', 0)}, "
            f"tuned={feedback.get('tuned_case_count', 0)}, "
            f"rejected={feedback.get('rejected_case_count', 0)}"
        )
        if result.route_report_summary.get("feedback_guidance"):
            print(f"  note: {result.route_report_summary['feedback_guidance']}")
        print("Fixture coverage:")
        print(
            f"  fixtures={fixtures.get('fixture_count', 0)}, "
            f"passing={fixtures.get('passing_fixture_count', 0)}, "
            f"failing={fixtures.get('failing_fixture_count', 0)}, "
            f"invalid={fixtures.get('invalid_fixture_count', 0)}"
        )
        if result.route_report_summary.get("fixture_guidance"):
            print(f"  note: {result.route_report_summary['fixture_guidance']}")
        print("Missed-note summary:")
        print(
            f"  feedback_cases={missed_note.get('feedback_case_count', 0)}, "
            f"still_failing_feedback={missed_note.get('still_failing_feedback_case_count', 0)}, "
            f"fixtures={missed_note.get('fixture_case_count', 0)}, "
            f"failing_fixtures={missed_note.get('failing_fixture_count', 0)}, "
            f"fixture_failure_rate={missed_note.get('fixture_failure_rate', 0)}"
        )
        print("Over-routing summary:")
        print(
            f"  feedback_cases={over_routing.get('feedback_case_count', 0)}, "
            f"still_failing_feedback={over_routing.get('still_failing_feedback_case_count', 0)}, "
            f"fixtures={over_routing.get('fixture_case_count', 0)}, "
            f"failing_fixtures={over_routing.get('failing_fixture_count', 0)}, "
            f"fixture_failure_rate={over_routing.get('fixture_failure_rate', 0)}"
        )
        print("Working-set pressure:")
        print(
            f"  average={working_set.get('average_routed_note_count', 0)}, "
            f"average_required={working_set.get('average_required_note_count', 0)}, "
            f"average_optional={working_set.get('average_optional_note_count', 0)}, "
            f"max={working_set.get('max_routed_note_count', 0)}, "
            f"over_target={working_set.get('fixture_count_exceeding_target', 0)}, "
            f"over_strong_warning={working_set.get('fixture_count_exceeding_strong_warning', 0)}"
        )
        print("Startup cost:")
        print(
            f"  average_lines={startup_cost.get('average_routed_line_count', 0)}, max_lines={startup_cost.get('max_routed_line_count', 0)}"
        )
    if result.detected_version is None:
        print(f"Detected version: none (payload version {result.bootstrap_version})")
    else:
        print(f"Detected version: {result.detected_version} (payload version {result.bootstrap_version})")
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")
    if include_install_summary:
        _print_install_summary(result)


def _emit_current_view(result, *, output_format: str) -> None:
    if output_format == "json":
        print(format_result_json(result))
        return

    print(f"Target: {result.target_root}")
    if result.detected_version is None:
        print(f"Detected version: none (payload version {result.bootstrap_version})")
    else:
        print(f"Detected version: {result.detected_version} (payload version {result.bootstrap_version})")
    for note in result.notes:
        print(f"\n[{note.path.as_posix()}]")
        if not note.exists:
            print("(missing)")
            continue
        print(note.content.rstrip())


def _print_install_summary(result) -> None:
    counts = result.counts()
    summary = ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
    print(f"Summary: {summary}")
    bootstrap_skills_path = result.target_root / BOOTSTRAP_WORKSPACE_ROOT / "skills"
    print("Next steps:")
    print(
        "- Review repository-specific details in AGENTS.md, then use "
        "`.agentic-workspace/memory/skills/memory-router/` for day-to-day note selection."
    )
    print(
        f"- Use the temporary bootstrap skills under {bootstrap_skills_path} to finish install "
        "or adopt lifecycle work, then run `agentic-memory bootstrap-cleanup --target "
        "<repo>` when that work is complete."
    )
    print("- Treat `.agentic-workspace/memory/` as the bootstrap-managed surface, and keep repo-specific memory procedures outside it.")
    print("- Keep .agentic-workspace/memory/repo/current/project-state.md as a short overview note, not a task list.")
    print(
        "- Populate .agentic-workspace/memory/repo/current/task-context.md only when active work would benefit from "
        "short checked-in continuation compression, not a shadow planner."
    )
    print("- Use `.agentic-workspace/memory/skills/memory-refresh/` after code or docs changes that may have shifted durable memory.")
    print("- Confirm the repo's active planning/status surface separately; this bootstrap does not install one.")
    if _created_current_memory_notes(result):
        print(
            f"- If current-memory files were created, use the `populate` skill under "
            f"{bootstrap_skills_path} to fill them conservatively before cleanup."
        )
    print("- Run `agentic-workspace doctor --target <repo> --format json` before upgrading an older install.")
    print(
        "- Run `agentic-workspace report --target <repo> --format json` after customising memory notes or when recurring friction should stay visible."
    )


def _print_report(report: dict[str, object]) -> None:
    print(f"Target: {report['target_root']}")
    print("Command: report")
    print(f"Health: {report['health']}")
    status = cast(dict[str, Any], report.get("status", {}))
    if isinstance(status, dict):
        print(
            "Status: "
            f"{status.get('note_count', 0)} notes / "
            f"{status.get('current_note_count', 0)} current notes / "
            f"version {status.get('detected_version', 'unknown')}"
        )
    trust = cast(dict[str, Any], report.get("trust", {}))
    if isinstance(trust, dict):
        state_counts = cast(dict[str, Any], trust.get("state_counts", {}))
        print(
            "Trust: "
            f"{trust.get('manual_review_count', 0)} manual-review / "
            f"{trust.get('warning_count', 0)} warning / "
            f"{trust.get('promotion_candidate_count', 0)} promotion candidates"
        )
        if isinstance(state_counts, dict) and state_counts:
            print(
                "Trust states: "
                f"{state_counts.get('supported', 0)} supported / "
                f"{state_counts.get('questionable', 0)} questionable / "
                f"{state_counts.get('stale', 0)} stale / "
                f"{state_counts.get('elimination_candidate', 0)} elimination-biased"
            )
    recurring_friction = cast(dict[str, Any], report.get("recurring_friction", {}))
    if isinstance(recurring_friction, dict) and recurring_friction.get("status") == "present":
        print(
            "Recurring friction: "
            f"{recurring_friction.get('entry_count', 0)} entries / "
            f"{recurring_friction.get('promotion_pressure_count', 0)} promotion-pressure / "
            f"{recurring_friction.get('structure_warning_count', 0)} structure warnings"
        )
    usefulness_audit = cast(dict[str, Any], report.get("usefulness_audit", {}))
    if isinstance(usefulness_audit, dict) and usefulness_audit.get("summary"):
        print(f"Usefulness: {usefulness_audit['summary']}")
    habitual_pull = cast(dict[str, Any], report.get("habitual_pull", {}))
    if isinstance(habitual_pull, dict) and habitual_pull.get("summary"):
        print(f"Habitual pull: {habitual_pull['summary']}")
    next_action = cast(dict[str, Any], report.get("next_action", {}))
    if isinstance(next_action, dict) and next_action.get("summary"):
        print(f"Next action: {next_action['summary']}")
        commands = cast(list[str], next_action.get("commands", []))
        if isinstance(commands, list) and commands:
            print("Commands:")
            for command in commands:
                print(f"- {command}")
    findings = report.get("findings", [])
    if isinstance(findings, list) and findings:
        print("Findings:")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            f_dict = cast(dict[str, Any], finding)
            path = f"{f_dict['path']}: " if f_dict.get("path") else ""
            print(f"- {f_dict.get('severity', 'info')}: {path}{f_dict.get('message', '')}")


def _created_current_memory_notes(result) -> bool:
    current_paths = {
        ".agentic-workspace/memory/repo/current/project-state.md",
        ".agentic-workspace/memory/repo/current/task-context.md",
    }
    for action in result.actions:
        if action.kind not in {"created", "copied", "would create", "would copy"}:
            continue
        try:
            relative = action.path.relative_to(result.target_root).as_posix()
        except ValueError:
            relative = action.path.as_posix()
        if relative in current_paths:
            return True
    return False


def _build_agent_prompt(command: str, *, target: str | None) -> str:
    target_root = target or "./repo"
    source = resolve_upgrade_source(target)
    runner = _preferred_git_runner_command(source)
    target_args = _target_args(target)
    bootstrap_skills = _bootstrap_skills_path(target)
    upgrade_runner = _upgrade_runner_command(target)

    if command == "install":
        return (
            "Do not ask the user to install or clone anything locally first. "
            f"Run `{runner} init{target_args}`. "
            f"Next, use the `install` skill at `{bootstrap_skills}` to finish installation conservatively. "
            f"When installation is complete, run `{runner} bootstrap-cleanup{target_args}` and point out "
            f"that `{target_root}/.agentic-workspace/memory/` is the bootstrap-managed surface while repo-specific "
            "memory notes stay under `.agentic-workspace/memory/repo/`."
        )
    if command == "adopt":
        return (
            "Do not ask the user to install or clone anything locally first. "
            f"Run `{runner} adopt{target_args}`. "
            f"Next, use the `install` skill at `{bootstrap_skills}` to finish installation conservatively. "
            f"When installation is complete, run `{runner} bootstrap-cleanup{target_args}` and point out "
            f"that `{target_root}/.agentic-workspace/memory/` is the bootstrap-managed surface while repo-specific "
            "memory notes stay under `.agentic-workspace/memory/repo/`."
        )
    if command == "populate":
        return (
            f"Run `{runner} current show{target_args}`. "
            "Treat any shared `project-state.md` or `task-context.md` output as migration residue. "
            "Move durable facts into normal Memory notes or canonical docs, active state into planning/status, "
            "and transient context into local-only scratch before deleting those legacy files."
        )
    if command == "upgrade":
        return (
            "Do not ask the user to install or clone anything locally first. "
            f"Use the checked-in `memory-upgrade` skill under `{_managed_skills_path(target)}/`. "
            "It should use the recorded upgrade source automatically, run the packaged upgrade flow for this "
            "repo, prefer the installed `agentic-memory` CLI when available, otherwise fall back to "
            f"`{upgrade_runner} upgrade --target <repo>`, and report any conservative manual-review items."
        )
    if command == "uninstall":
        return (
            f"Run `{runner} uninstall{target_args}`. "
            "Review any manual-review items before removing repo-local memory content. "
            "If bundled product skills are available, use `bootstrap-uninstall` to finish the uninstall conservatively."
        )
    raise ValueError(f"Unknown prompt command: {command}")


def _uvx_git_runner_command() -> str:
    source = resolve_upgrade_source(None)
    return f"uvx --from {source['source_ref']} agentic-memory"


def _pipx_git_runner_command() -> str:
    source = resolve_upgrade_source(None)
    return f"pipx run --spec {source['source_ref']} agentic-memory"


def _preferred_git_runner_command(source: dict[str, str | int | Path | None]) -> str:
    source_ref = str(source["source_ref"])
    if shutil.which("uvx"):
        return f"uvx --from {source_ref} agentic-memory"
    if shutil.which("pipx"):
        return f"pipx run --spec {source_ref} agentic-memory"
    return f"uvx --from {source_ref} agentic-memory"


def _upgrade_runner_command(target: str | None) -> str:
    source = resolve_upgrade_source(target)
    if source["source_type"] == "local":
        return _runner_command_for_local_source(str(source["source_ref"]))
    return _preferred_git_runner_command(source)


def _target_args(target: str | None) -> str:
    if not target:
        return ""
    return f" --target {target}"


def _bootstrap_skills_path(target: str | None) -> str:
    target_root = target or "./repo"
    return f"{target_root}/{BOOTSTRAP_WORKSPACE_ROOT.as_posix()}/skills"


def _managed_skills_path(target: str | None) -> str:
    target_root = target or "./repo"
    if target and Path(target).exists():
        if detect_bootstrap_layout(Path(target).resolve()) == "legacy":
            return f"{target_root}/memory/skills"
    return f"{target_root}/.agentic-workspace/memory/skills"


def _runner_command_for_local_source(source_ref: str) -> str:
    if shutil.which("uvx"):
        return f"uvx --from {source_ref} agentic-memory"
    if shutil.which("pipx"):
        return f"pipx run --spec {source_ref} agentic-memory"
    return f"uvx --from {source_ref} agentic-memory"
