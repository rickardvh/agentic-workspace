from __future__ import annotations

import argparse

from repo_memory_bootstrap.installer import (
    BOOTSTRAP_WORKSPACE_ROOT,
    RepoDetectionError,
    adopt_bootstrap,
    check_current_memory,
    collect_status,
    doctor_bootstrap,
    format_actions,
    format_result_json,
    install_bootstrap,
    list_bundled_skills,
    list_payload_files,
    route_memory,
    show_current_memory,
    sync_memory,
    upgrade_bootstrap,
    verify_payload,
)

GIT_REPO_URL = "git+https://github.com/Tenfifty/agentic-memory"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-memory-bootstrap",
        description="Install and upgrade a repository memory and lightweight coordination bootstrap.",
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
    _add_project_metadata_arguments(adopt_parser)
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
    _add_project_metadata_arguments(upgrade_parser)
    _add_format_argument(upgrade_parser)

    doctor_parser = subparsers.add_parser("doctor", help="Diagnose bootstrap state and recommended remediation.")
    _add_target_arguments(doctor_parser)
    _add_project_metadata_arguments(doctor_parser)
    _add_format_argument(doctor_parser)

    status_parser = subparsers.add_parser("status", help="Report whether bootstrap files are present.")
    _add_target_arguments(status_parser)
    _add_format_argument(status_parser)

    list_files_parser = subparsers.add_parser("list-files", help="Preview packaged bootstrap files.")
    _add_target_arguments(list_files_parser)
    _add_format_argument(list_files_parser)

    list_skills_parser = subparsers.add_parser("list-skills", help="List bundled bootstrap-lifecycle skills.")
    _add_format_argument(list_skills_parser)

    prompt_parser = subparsers.add_parser("prompt", help="Print a canonical agent prompt for install, adopt, populate, or upgrade.")
    prompt_subparsers = prompt_parser.add_subparsers(dest="prompt_command", required=True)
    prompt_install_parser = prompt_subparsers.add_parser("install", help="Print the canonical install prompt.")
    _add_target_arguments(prompt_install_parser)
    prompt_adopt_parser = prompt_subparsers.add_parser("adopt", help="Print the canonical adoption prompt.")
    _add_target_arguments(prompt_adopt_parser)
    prompt_populate_parser = prompt_subparsers.add_parser("populate", help="Print the canonical populate prompt.")
    _add_target_arguments(prompt_populate_parser)
    prompt_upgrade_parser = prompt_subparsers.add_parser("upgrade", help="Print the canonical upgrade prompt.")
    _add_target_arguments(prompt_upgrade_parser)

    current_parser = subparsers.add_parser("current", help="Inspect or check the current-memory surface.")
    current_subparsers = current_parser.add_subparsers(dest="current_command", required=True)
    current_show_parser = current_subparsers.add_parser("show", help="Show current-memory notes.")
    _add_target_arguments(current_show_parser)
    _add_format_argument(current_show_parser)
    current_check_parser = current_subparsers.add_parser("check", help="Check current-memory notes.")
    _add_target_arguments(current_check_parser)
    _add_format_argument(current_check_parser)

    route_parser = subparsers.add_parser("route", help="Suggest relevant memory notes for touched files or surfaces.")
    _add_target_arguments(route_parser)
    route_parser.add_argument("--files", nargs="*", default=[], help="Touched file paths to route from.")
    route_parser.add_argument("--surface", dest="surfaces", nargs="*", default=[], help="Explicit routing surfaces.")
    _add_format_argument(route_parser)

    sync_parser = subparsers.add_parser("sync-memory", help="Suggest memory updates for changed work.")
    _add_target_arguments(sync_parser)
    sync_parser.add_argument("--files", nargs="*", default=[], help="Changed file paths to inspect.")
    sync_parser.add_argument("--notes", nargs="*", default=[], help="Explicit memory notes to review.")
    _add_format_argument(sync_parser)

    verify_parser = subparsers.add_parser("verify-payload", help="Verify the packaged bootstrap payload contract.")
    _add_target_arguments(verify_parser)
    _add_format_argument(verify_parser)

    return parser


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")


def _add_install_arguments(command_parser: argparse.ArgumentParser) -> None:
    _add_target_arguments(command_parser)
    command_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    command_parser.add_argument("--force", action="store_true", help="Overwrite managed files that already exist.")
    _add_project_metadata_arguments(command_parser)
    _add_format_argument(command_parser)


def _add_project_metadata_arguments(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument("--project-name", help="Value used for the <PROJECT_NAME> placeholder.")
    command_parser.add_argument("--project-purpose", help="Value used for the <PROJECT_PURPOSE> placeholder.")
    command_parser.add_argument("--key-repo-docs", help="Value used for the <KEY_REPO_DOCS> placeholder.")
    command_parser.add_argument("--key-subsystems", help="Value used for the <KEY_SUBSYSTEMS> placeholder.")
    command_parser.add_argument("--primary-build-command", help="Value used for the <PRIMARY_BUILD_COMMAND> placeholder.")
    command_parser.add_argument("--primary-test-command", help="Value used for the <PRIMARY_TEST_COMMAND> placeholder.")
    command_parser.add_argument("--other-key-commands", help="Value used for the <OTHER_KEY_COMMANDS> placeholder.")


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
                project_purpose=getattr(args, "project_purpose", None),
                key_repo_docs=getattr(args, "key_repo_docs", None),
                key_subsystems=getattr(args, "key_subsystems", None),
                primary_build_command=getattr(args, "primary_build_command", None),
                primary_test_command=getattr(args, "primary_test_command", None),
                other_key_commands=getattr(args, "other_key_commands", None),
            )
            _emit_result(result, output_format=args.format, include_install_summary=True)
            return 0

        if args.command == "adopt":
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
            )
            _emit_result(result, output_format=args.format, include_install_summary=True)
            return 0

        if args.command == "upgrade":
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
            )
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "doctor":
            result = doctor_bootstrap(
                target=args.target,
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

        if args.command == "status":
            result = collect_status(target=args.target)
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "list-files":
            result = list_payload_files(target=args.target)
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "list-skills":
            result = list_bundled_skills()
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "prompt":
            print(_build_agent_prompt(args.prompt_command, target=args.target))
            return 0

        if args.command == "current":
            if args.current_command == "show":
                _emit_current_view(show_current_memory(target=args.target), output_format=args.format)
                return 0
            if args.current_command == "check":
                _emit_result(check_current_memory(target=args.target), output_format=args.format)
                return 0

        if args.command == "route":
            result = route_memory(target=args.target, files=args.files, surfaces=args.surfaces)
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "sync-memory":
            result = sync_memory(target=args.target, files=args.files, notes=args.notes)
            _emit_result(result, output_format=args.format)
            return 0

        if args.command == "verify-payload":
            result = verify_payload(target=args.target)
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
    print("- Review repository-specific details in AGENTS.md and the current-memory notes.")
    print(f"- Use the temporary bootstrap skills under {bootstrap_skills_path} to finish install or upgrade review, then remove memory/bootstrap/ when that work is complete.")
    print("- Review the checked-in core memory skills under memory/skills/ and add repo-specific sibling skills there when a local memory workflow is worth reusing.")
    print("- Keep memory/current/project-state.md as a short overview note, not a task list.")
    print("- Populate memory/current/task-context.md only when active work would benefit from a short checked-in continuation note.")
    print("- Confirm the repo's chosen task system separately; this bootstrap does not install one.")
    if _created_current_memory_notes(result):
        print(f"- If current-memory files were created, use the `populate` skill under {bootstrap_skills_path} to fill them conservatively before cleanup.")
    print("- Run agentic-memory-bootstrap doctor --target <repo> before upgrading an older install.")
    print("- Run python scripts/check/check_memory_freshness.py after customising memory notes.")


def _created_current_memory_notes(result) -> bool:
    current_paths = {"memory/current/project-state.md", "memory/current/task-context.md"}
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
    target_root = target or "/path/to/repo"
    runner = _git_runner_command()
    pipx_runner = _pipx_git_runner_command()
    target_args = _target_args(target)
    bootstrap_skills = _bootstrap_skills_path(target)

    if command == "install":
        return (
            f"Run `{runner} init{target_args}` or `{pipx_runner} init{target_args}`. "
            f"Next, use the `install` skill at `{bootstrap_skills}` to finish installation conservatively. "
            "If new current-memory files were created, use `populate` from the same path before cleanup. "
            f"When installation is complete, use `cleanup` at `{bootstrap_skills}` to remove the temporary bootstrap workspace and point out the checked-in core memory skills under `{target_root}/memory/skills`."
        )
    if command == "adopt":
        return (
            f"Run `{runner} adopt{target_args}` or `{pipx_runner} adopt{target_args}`. "
            f"Next, use the `install` skill at `{bootstrap_skills}` to finish installation conservatively. "
            "If new current-memory files were created, use `populate` from the same path before cleanup. "
            f"When installation is complete, use `cleanup` at `{bootstrap_skills}` to remove the temporary bootstrap workspace and point out the checked-in core memory skills under `{target_root}/memory/skills`."
        )
    if command == "populate":
        return (
            f"Run `{runner} current show{target_args}` or `{pipx_runner} current show{target_args}`. "
            f"Next, use the `populate` skill at `{bootstrap_skills}` to fill the current-memory notes conservatively from existing repo docs and visible repo state. "
            "Populate `memory/current/task-context.md` only when there is clearly active work worth preserving across sessions."
        )
    if command == "upgrade":
        return (
            f"Run `{runner} upgrade{target_args}` or `{pipx_runner} upgrade{target_args}`. "
            f"Next, use the `upgrade` skill at `{bootstrap_skills}` to finish the upgrade review conservatively. "
            f"When the upgrade is complete, use `cleanup` at `{bootstrap_skills}` to remove the temporary bootstrap workspace."
        )
    raise ValueError(f"Unknown prompt command: {command}")


def _git_runner_command() -> str:
    return f"uvx --from {GIT_REPO_URL} agentic-memory-bootstrap"


def _pipx_git_runner_command() -> str:
    return f"pipx run --spec {GIT_REPO_URL} agentic-memory-bootstrap"


def _target_args(target: str | None) -> str:
    if not target:
        return ""
    return f" --target {target}"


def _bootstrap_skills_path(target: str | None) -> str:
    target_root = target or "/path/to/repo"
    return f"{target_root}/{BOOTSTRAP_WORKSPACE_ROOT.as_posix()}/skills"
