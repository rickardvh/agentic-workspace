from __future__ import annotations

import argparse

from repo_memory_bootstrap.installer import (
    RepoDetectionError,
    collect_status,
    format_actions,
    install_bootstrap,
    list_payload_files,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-memory-bootstrap",
        description="Install the repository memory bootstrap into an existing repo.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install bootstrap files into a repository.")
    _add_install_arguments(install_parser)
    init_parser = subparsers.add_parser("init", help="Alias for install, intended for clean bootstrap cases.")
    _add_install_arguments(init_parser)

    status_parser = subparsers.add_parser("status", help="Report whether bootstrap files are present.")
    status_parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")

    list_files_parser = subparsers.add_parser("list-files", help="Preview packaged bootstrap files and local templates.")
    list_files_parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")

    return parser


def _add_install_arguments(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")
    command_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    command_parser.add_argument("--force", action="store_true", help="Overwrite managed files that already exist.")
    command_parser.add_argument("--project-name", help="Value used for the <PROJECT_NAME> placeholder.")


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
            print(f"Target: {result.target_root}")
            print(result.message)
            for line in format_actions(result.actions, result.target_root):
                print(f"- {line}")
            _print_install_summary(result)
            return 0

        if args.command == "status":
            result = collect_status(target=args.target)
            print(f"Target: {result.target_root}")
            print(result.message)
            for line in format_actions(result.actions, result.target_root):
                print(f"- {line}")
            return 0

        if args.command == "list-files":
            result = list_payload_files(target=args.target)
            print(f"Target: {result.target_root}")
            print(result.message)
            for line in format_actions(result.actions, result.target_root):
                print(f"- {line}")
            return 0
    except RepoDetectionError as exc:
        print(f"Error: {exc}")
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


def _print_install_summary(result) -> None:
    counts = result.counts()
    summary = ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
    print(f"Summary: {summary}")
    print("Next steps:")
    print("- Review placeholders and repository-specific details in AGENTS.md and TODO.md.")
    print("- Review the shared workflow rules in memory/system/WORKFLOW.md.")
    print("- Create a local .agent-work/ directory from the packaged templates if you want disposable task notes.")
    print("- Run python scripts/check/check_memory_freshness.py after customizing memory notes.")
