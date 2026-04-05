from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from agentic_workspace import __version__

MODULE_ORDER = ("memory", "planning")


@dataclass(frozen=True)
class ModuleDescriptor:
    name: str
    description: str
    commands: dict[str, Callable[..., Any]]
    detector: Callable[[Path], bool]


class ModuleSelectionError(ValueError):
    """Raised when the orchestrator cannot resolve a safe default module set."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-workspace",
        description="Workspace-level lifecycle orchestrator for selected agentic-workspace modules.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    modules_parser = subparsers.add_parser("modules", help="List workspace modules available to the orchestrator.")
    _add_format_argument(modules_parser)

    install_parser = subparsers.add_parser("install", help="Install selected modules into a repository.")
    _add_shared_arguments(install_parser)
    install_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    install_parser.add_argument("--force", action="store_true", help="Allow module installers to overwrite managed files when supported.")

    for command in ("adopt", "upgrade", "uninstall"):
        command_parser = subparsers.add_parser(command, help=f"Run `{command}` for the selected modules.")
        _add_shared_arguments(command_parser)
        command_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")

    for command in ("doctor", "status"):
        command_parser = subparsers.add_parser(command, help=f"Run `{command}` for the selected modules.")
        _add_shared_arguments(command_parser)

    return parser


def _add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--module",
        dest="modules",
        action="append",
        choices=MODULE_ORDER,
        help="Module to operate on. Repeat to target multiple modules. Defaults to all available modules.",
    )
    parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")
    _add_format_argument(parser)


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "modules":
        _emit_modules(format_name=args.format)
        return 0

    descriptors = _module_operations()
    try:
        selected_modules = _selected_modules(args.command, args.modules, args.target, descriptors)
    except ModuleSelectionError as exc:
        parser.error(str(exc))
    reports = [_invoke_module_command(args.command, module_name, descriptors[module_name], args) for module_name in selected_modules]
    _emit_reports(command_name=args.command, reports=reports, format_name=args.format)
    return 0


def _module_operations() -> dict[str, ModuleDescriptor]:
    from repo_memory_bootstrap.installer import (
        adopt_bootstrap as memory_adopt_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        collect_status as memory_collect_status,
    )
    from repo_memory_bootstrap.installer import (
        doctor_bootstrap as memory_doctor_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        install_bootstrap as memory_install_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        uninstall_bootstrap as memory_uninstall_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        upgrade_bootstrap as memory_upgrade_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        adopt_bootstrap as planning_adopt_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        collect_status as planning_collect_status,
    )
    from repo_planning_bootstrap.installer import (
        doctor_bootstrap as planning_doctor_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        install_bootstrap as planning_install_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        uninstall_bootstrap as planning_uninstall_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        upgrade_bootstrap as planning_upgrade_bootstrap,
    )

    return {
        "memory": ModuleDescriptor(
            name="memory",
            description="Durable repository knowledge bootstrap and maintenance.",
            commands={
                "install": lambda *, target, dry_run, force: memory_install_bootstrap(target=target, dry_run=dry_run, force=force),
                "adopt": lambda *, target, dry_run: memory_adopt_bootstrap(target=target, dry_run=dry_run),
                "upgrade": lambda *, target, dry_run: memory_upgrade_bootstrap(target=target, dry_run=dry_run),
                "uninstall": lambda *, target, dry_run: memory_uninstall_bootstrap(target=target, dry_run=dry_run),
                "doctor": lambda *, target: memory_doctor_bootstrap(target=target),
                "status": lambda *, target: memory_collect_status(target=target),
            },
            detector=lambda target_root: (target_root / "memory" / "index.md").exists()
            and (target_root / ".agentic-workspace" / "memory").exists(),
        ),
        "planning": ModuleDescriptor(
            name="planning",
            description="Repo-native execution planning bootstrap and maintenance.",
            commands={
                "install": lambda *, target, dry_run, force: planning_install_bootstrap(target=target, dry_run=dry_run, force=force),
                "adopt": lambda *, target, dry_run: planning_adopt_bootstrap(target=target, dry_run=dry_run),
                "upgrade": lambda *, target, dry_run: planning_upgrade_bootstrap(target=target, dry_run=dry_run),
                "uninstall": lambda *, target, dry_run: planning_uninstall_bootstrap(target=target, dry_run=dry_run),
                "doctor": lambda *, target: planning_doctor_bootstrap(target=target),
                "status": lambda *, target: planning_collect_status(target=target),
            },
            detector=lambda target_root: (target_root / "TODO.md").exists()
            and (target_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists(),
        ),
    }


def _selected_modules(
    command_name: str,
    module_args: list[str] | None,
    target: str | None,
    descriptors: dict[str, ModuleDescriptor],
) -> list[str]:
    if not module_args:
        if command_name in {"install", "adopt"}:
            return [module_name for module_name in MODULE_ORDER if module_name in descriptors]

        target_root = _resolve_target_root(target)
        detected = [
            module_name
            for module_name in MODULE_ORDER
            if module_name in descriptors and descriptors[module_name].detector(target_root)
        ]
        if detected:
            return detected
        raise ModuleSelectionError(
            "No installed modules were detected for this maintenance command. Use --module to target a module explicitly."
        )

    selected: list[str] = []
    for module_name in module_args:
        if module_name not in selected and module_name in descriptors:
            selected.append(module_name)
    return selected


def _resolve_target_root(target: str | None) -> Path:
    return Path(target).resolve() if target else Path.cwd().resolve()


def _invoke_module_command(command_name: str, module_name: str, descriptor: ModuleDescriptor, args: argparse.Namespace) -> dict[str, Any]:
    command = descriptor.commands[command_name]
    kwargs: dict[str, Any] = {"target": args.target}
    if command_name == "install":
        kwargs["dry_run"] = args.dry_run
        kwargs["force"] = args.force
    elif command_name in {"adopt", "upgrade", "uninstall"}:
        kwargs["dry_run"] = args.dry_run

    result = command(**kwargs)
    return {
        "module": module_name,
        "message": result.message,
        "target_root": Path(result.target_root),
        "dry_run": bool(result.dry_run),
        "actions": [_serialise_action(action) for action in result.actions],
        "warnings": [_serialise_value(warning) for warning in getattr(result, "warnings", [])],
    }


def _serialise_action(action: Any) -> dict[str, Any]:
    if is_dataclass(action):
        return {key: _serialise_value(value) for key, value in asdict(action).items()}
    return {key: _serialise_value(value) for key, value in vars(action).items()}


def _serialise_value(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {key: _serialise_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_serialise_value(item) for item in value]
    return value


def _emit_modules(*, format_name: str) -> None:
    descriptors = _module_operations()
    payload = {
        "modules": [
            {
                "name": descriptor.name,
                "description": descriptor.description,
                "commands": sorted(descriptor.commands),
            }
            for descriptor in descriptors.values()
        ]
    }
    if format_name == "json":
        print(json.dumps(payload, indent=2))
        return
    for module_data in payload["modules"]:
        print(f"{module_data['name']}: {module_data['description']}")
        print(f"  commands: {', '.join(module_data['commands'])}")


def _emit_reports(*, command_name: str, reports: list[dict[str, Any]], format_name: str) -> None:
    if format_name == "json":
        payload = _serialise_value({"command": command_name, "reports": reports})
        print(json.dumps(payload, indent=2))
        return

    target_root = reports[0]["target_root"] if reports else Path.cwd()
    print(f"Target: {target_root}")
    print(f"Command: {command_name}")
    print(f"Modules: {', '.join(report['module'] for report in reports)}")
    for report in reports:
        print(f"[{report['module']}] {report['message']}")
        for action in report["actions"]:
            detail = f" ({action['detail']})" if action.get("detail") else ""
            print(f"- {action['kind']}: {_display_path(action['path'], report['target_root'])}{detail}")
        if report["warnings"]:
            print("Warnings:")
            for warning in report["warnings"]:
                warning_path = warning.get("path", ".")
                warning_message = warning.get("message", "")
                warning_class = warning.get("warning_class", "warning")
                print(f"- [{warning_class}] {warning_path}: {warning_message}")


def _display_path(path_value: str, target_root: Path) -> str:
    path = Path(path_value)
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()
