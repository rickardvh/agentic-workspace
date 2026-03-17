from __future__ import annotations

import argparse

from repo_memory_bootstrap.installer import (
    RepoDetectionError,
    adopt_bootstrap,
    collect_status,
    doctor_bootstrap,
    format_actions,
    format_result_json,
    install_bootstrap,
    list_payload_files,
    upgrade_bootstrap,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-memory-bootstrap",
        description="Install and upgrade the repository memory bootstrap.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install bootstrap files into a repository.")
    _add_install_arguments(install_parser)
    init_parser = subparsers.add_parser("init", help="Alias for install, intended for clean bootstrap cases.")
    _add_install_arguments(init_parser)

    adopt_parser = subparsers.add_parser("adopt", help="Add bootstrap capability to an existing repository conservatively.")
    _add_target_arguments(adopt_parser)
    adopt_parser.add_argument("--dry-run", action="store_true", help="Show the adoption plan without writing files.")
    adopt_parser.add_argument(
        "--apply-local-entrypoint",
        action="store_true",
        help="Patch AGENTS.md with the canonical workflow pointer block when needed.",
    )
    adopt_parser.add_argument("--project-name", help="Value used for the <PROJECT_NAME> placeholder.")
    _add_format_argument(adopt_parser)

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade an existing bootstrap install.")
    _add_target_arguments(upgrade_parser)
    upgrade_parser.add_argument("--dry-run", action="store_true", help="Show the upgrade plan without writing files.")
    upgrade_parser.add_argument("--force", action="store_true", help="Allow replacing customised starter files.")
    upgrade_parser.add_argument(
        "--apply-local-entrypoint",
        action="store_true",
        help="Patch AGENTS.md with the canonical workflow pointer block when needed.",
    )
    upgrade_parser.add_argument("--project-name", help="Value used for the <PROJECT_NAME> placeholder.")
    _add_format_argument(upgrade_parser)

    doctor_parser = subparsers.add_parser("doctor", help="Diagnose bootstrap state and recommended remediation.")
    _add_target_arguments(doctor_parser)
    doctor_parser.add_argument("--project-name", help="Value used for the <PROJECT_NAME> placeholder.")
    _add_format_argument(doctor_parser)

    status_parser = subparsers.add_parser("status", help="Report whether bootstrap files are present.")
    _add_target_arguments(status_parser)
    _add_format_argument(status_parser)

    list_files_parser = subparsers.add_parser("list-files", help="Preview packaged bootstrap files and local templates.")
    _add_target_arguments(list_files_parser)
    _add_format_argument(list_files_parser)

    return parser


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")


def _add_install_arguments(command_parser: argparse.ArgumentParser) -> None:
    _add_target_arguments(command_parser)
    command_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    command_parser.add_argument("--force", action="store_true", help="Overwrite managed files that already exist.")
    command_parser.add_argument("--project-name", help="Value used for the <PROJECT_NAME> placeholder.")
    _add_format_argument(command_parser)


def _add_format_argument(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command in {"install", "init"}:
            result = install_bootstrap(
                target=getattr(args, "target", None),
                dry_run=getattr(args, "dry_run", False),
                force=getattr(args, "force", False),
                project_name=getattr(args, "project_name", None),
            )
            _emit_result(result, output_format=args.format, include_install_summary=True)
            return 0

        if args.command == "adopt":
            result = adopt_bootstrap(
                target=args.target,
                dry_run=args.dry_run,
                apply_local_entrypoint=args.apply_local_entrypoint,
                project_name=args.project_name,
            )
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "upgrade":
            result = upgrade_bootstrap(
                target=args.target,
                dry_run=args.dry_run,
                force=args.force,
                apply_local_entrypoint=args.apply_local_entrypoint,
                project_name=args.project_name,
            )
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "doctor":
            result = doctor_bootstrap(target=args.target, project_name=args.project_name)
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "status":
            result = collect_status(target=args.target)
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "list-files":
            result = list_payload_files(target=args.target)
            _emit_result(result, output_format=args.format)
            return 0
    except RepoDetectionError as exc:
        print(f"Error: {exc}")
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


def _emit_result(result, *, output_format: str, include_install_summary: bool = False) -> None:
    if output_format == "json":
        print(format_result_json(result))
        return

    print(f"Target: {result.target_root}")
    print(result.message)
    if result.detected_version is None:
        print(f"Detected version: none (payload version {result.bootstrap_version})")
    else:
        print(f"Detected version: {result.detected_version} (payload version {result.bootstrap_version})")
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")
    if include_install_summary:
        _print_install_summary(result)


def _print_install_summary(result) -> None:
    counts = result.counts()
    summary = ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
    print(f"Summary: {summary}")
    print("Next steps:")
    print("- Review placeholders and repository-specific details in AGENTS.md and TODO.md.")
    print("- Review the shared workflow rules in memory/system/WORKFLOW.md.")
    print("- Run agentic-memory-bootstrap doctor --target <repo> before upgrading an older install.")
    print("- Create a local .agent-work/ directory from the packaged templates if you want disposable task notes.")
    print("- Run python scripts/check/check_memory_freshness.py after customising memory notes.")
