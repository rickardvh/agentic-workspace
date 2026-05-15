"""Generated runtime-backed Python command adapter.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from typing import Any

# DO NOT EDIT DIRECTLY.
# Command/interface changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Runtime behavior changes belong in hand-written operation/primitive implementation code.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py


def _load_generated_json(name: str) -> Any:
    parts = tuple(part for part in name.replace('\\', '/').split('/') if part)
    try:
        return json.loads(files(__package__).joinpath(*parts).read_text(encoding="utf-8"))
    except (AttributeError, FileNotFoundError, ModuleNotFoundError, TypeError):
        return json.loads(Path(__file__).parent.joinpath(*parts).read_text(encoding="utf-8"))


GENERATED_COMMAND_PACKAGE: dict[str, Any] = _load_generated_json("command_package.json")

_GENERATED_ADAPTER_COMMANDS: list[dict[str, Any]] = _load_generated_json("adapter_commands.json")
_GENERATED_COMMANDS_BY_NAME: dict[str, dict[str, Any]] = {
    str(command["interface"]["name"]): command for command in _GENERATED_ADAPTER_COMMANDS
}

_GENERATED_OPERATION_PATHS_BY_ID: dict[str, str] = {}

_GENERATED_MATURITY_ID = 'weak-agent-safe-adapter'
_GENERATED_WEAK_AGENT_ROUTING = 'allowed-read-only'
_GENERATED_RUNNABLE = True

RuntimeHandler = Callable[[str, argparse.Namespace], int]


def generated_maturity() -> dict[str, object]:
    return {
        "id": _GENERATED_MATURITY_ID,
        "runnable": _GENERATED_RUNNABLE,
        "weak_agent_routing": _GENERATED_WEAK_AGENT_ROUTING,
    }


def generated_weak_agent_routing() -> str:
    return _GENERATED_WEAK_AGENT_ROUTING


def generated_command_names() -> tuple[str, ...]:
    return tuple(sorted(_GENERATED_COMMANDS_BY_NAME))


def _interface_operation_ref(interface: dict[str, Any], inherited_operation_id: str, inherited_operation_path: str) -> tuple[str, str]:
    operation_ref = interface.get("operation_ref", {})
    if isinstance(operation_ref, dict):
        return str(operation_ref.get("id", inherited_operation_id)), str(operation_ref.get("path", inherited_operation_path))
    return inherited_operation_id, inherited_operation_path


def _interface_operation_paths_by_id(interface: dict[str, Any], inherited_operation_id: str, inherited_operation_path: str) -> dict[str, str]:
    operation_id, operation_path = _interface_operation_ref(interface, inherited_operation_id, inherited_operation_path)
    paths = {operation_id: operation_path}
    for subcommand in interface.get("subcommands", []):
        if isinstance(subcommand, dict):
            paths.update(_interface_operation_paths_by_id(subcommand, operation_id, operation_path))
    return paths


_GENERATED_OPERATION_PATHS_BY_ID.update(
    {
        operation_id: operation_path
        for command in _GENERATED_ADAPTER_COMMANDS
        for operation_id, operation_path in _interface_operation_paths_by_id(
            command["interface"],
            str(command["operation_id"]),
            str(command["operation_path"]),
        ).items()
    }
)


def generated_operation_ids() -> tuple[str, ...]:
    return tuple(sorted(_GENERATED_OPERATION_PATHS_BY_ID))


def generated_operation_contract(operation_id: str) -> dict[str, Any]:
    operation_path = _GENERATED_OPERATION_PATHS_BY_ID[str(operation_id)]
    return _load_generated_json(operation_path)


def supports_generated_command(argv: list[str] | tuple[str, ...]) -> bool:
    return bool(argv) and str(argv[0]) in _GENERATED_COMMANDS_BY_NAME


def _option_type(option_spec: dict[str, Any]) -> Any:
    if option_spec.get("type") == "integer":
        return int
    return None


def _add_option(parser: argparse.ArgumentParser, option_spec: dict[str, Any], *, suppress_default: bool = False) -> None:
    kwargs: dict[str, Any] = {}
    action = option_spec.get("action")
    if isinstance(action, str):
        kwargs["action"] = action
    if "choices" in option_spec:
        kwargs["choices"] = tuple(option_spec["choices"])
    if suppress_default:
        kwargs["default"] = argparse.SUPPRESS
    elif "default" in option_spec:
        kwargs["default"] = option_spec["default"]
    if "nargs" in option_spec:
        kwargs["nargs"] = option_spec["nargs"]
    option_type = _option_type(option_spec)
    if option_type is not None:
        kwargs["type"] = option_type
    if option_spec.get("required") is True:
        kwargs["required"] = True
    help_text = option_spec.get("help")
    if isinstance(help_text, str):
        kwargs["help"] = help_text
    parser.add_argument(*option_spec["flags"], **kwargs)


def _add_interface_options(
    parser: argparse.ArgumentParser,
    interface: dict[str, Any],
    inherited_option_names: frozenset[str] = frozenset(),
) -> frozenset[str]:
    option_names: set[str] = set()
    for argument in interface.get("arguments", []):
        kwargs: dict[str, Any] = {}
        if "nargs" in argument:
            kwargs["nargs"] = argument["nargs"]
        if "default" in argument:
            kwargs["default"] = argument["default"]
        if "choices" in argument:
            kwargs["choices"] = tuple(argument["choices"])
        help_text = argument.get("help")
        if isinstance(help_text, str):
            kwargs["help"] = help_text
        parser.add_argument(str(argument["name"]), **kwargs)
    for option in interface.get("options", []):
        option_name = str(option.get("name", ""))
        if option_name:
            option_names.add(option_name)
        _add_option(parser, option, suppress_default=option_name in inherited_option_names)
    return frozenset(option_names)


def _set_generated_operation_id(parser: argparse.ArgumentParser, operation_id: str) -> None:
    parser.set_defaults(_generated_operation_id=operation_id)


def _add_interface_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    interface: dict[str, Any],
    operation_id: str,
    inherited_option_names: frozenset[str] = frozenset(),
) -> None:
    command_parser = subparsers.add_parser(
        str(interface["name"]),
        help=str(interface["help"]),
        description=str(interface["help"]),
    )
    nested_operation_ref = interface.get("operation_ref", {})
    if isinstance(nested_operation_ref, dict):
        operation_id = str(nested_operation_ref.get("id", operation_id))
    _set_generated_operation_id(command_parser, operation_id)
    option_names = _add_interface_options(command_parser, interface, inherited_option_names)
    subcommands = interface.get("subcommands", [])
    if not subcommands:
        return
    subcommand_dest = str(interface.get("subcommand_dest", "subcommand"))
    child_subparsers = command_parser.add_subparsers(
        dest=subcommand_dest,
        required=bool(interface.get("subcommands_required", True)),
    )
    child_inherited_option_names = inherited_option_names | option_names
    for subcommand in subcommands:
        _add_interface_command(child_subparsers, subcommand, operation_id, child_inherited_option_names)


def build_generated_parser() -> argparse.ArgumentParser:
    epilog = (
        f"Weak-agent routing: {_GENERATED_WEAK_AGENT_ROUTING}\n"
        "Recovery: use one of the supported generated commands or route back to the canonical Python CLI."
    )
    parser = argparse.ArgumentParser(prog="agentic-workspace", description="", epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in _GENERATED_ADAPTER_COMMANDS:
        interface = command["interface"]
        _add_interface_command(subparsers, interface, str(command["operation_id"]))
    return parser


def run_generated_command(argv: list[str] | tuple[str, ...], runtime_handler: RuntimeHandler) -> int:
    parser = build_generated_parser()
    args = parser.parse_args(list(argv))
    operation_id = str(getattr(args, "_generated_operation_id"))
    return runtime_handler(operation_id, args)


def _run_runtime_handler(operation_id: str, args: argparse.Namespace) -> int:
    from .workspace_runtime_cli import _GENERATED_RUNTIME_HANDLERS

    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is None:
        build_generated_parser().error(
            f"Generated adapter for {getattr(args, 'command', operation_id)} references unsupported operation {operation_id}."
        )
    return handler(args)


def main(argv: list[str] | None = None) -> int:
    import sys
    from .workspace_runtime_cli import main as runtime_main

    argv_list = list(sys.argv[1:] if argv is None else argv)
    if argv_list and argv_list[0] in {'-h', '--help'}:
        build_generated_parser().parse_args(argv_list)
        return 0
    if supports_generated_command(argv_list):
        try:
            return run_generated_command(argv_list, _run_runtime_handler)
        except Exception as exc:
            if exc.__class__.__name__.endswith('UsageError') or exc.__class__.__name__ == 'RepoDetectionError':
                build_generated_parser().error(str(exc))
            raise

    # Compatibility fallback for package commands that have not entered command_package_ir yet.
    return runtime_main(argv_list)
