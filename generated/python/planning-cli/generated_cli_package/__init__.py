"""Generated runtime-backed Python command adapter.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
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
    try:
        return json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))
    except (AttributeError, FileNotFoundError, ModuleNotFoundError, TypeError):
        return json.loads(Path(__file__).with_name(name).read_text(encoding="utf-8"))


GENERATED_COMMAND_PACKAGE: dict[str, Any] = _load_generated_json("command_package.json")

_GENERATED_ADAPTER_COMMANDS: list[dict[str, Any]] = _load_generated_json("adapter_commands.json")
_GENERATED_COMMANDS_BY_NAME: dict[str, dict[str, Any]] = {
    str(command["interface"]["name"]): command for command in _GENERATED_ADAPTER_COMMANDS
}

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


def generated_operation_ids() -> tuple[str, ...]:
    return tuple(sorted(str(command["operation_id"]) for command in _GENERATED_ADAPTER_COMMANDS))


def supports_generated_command(argv: list[str] | tuple[str, ...]) -> bool:
    return bool(argv) and str(argv[0]) in _GENERATED_COMMANDS_BY_NAME


def _option_type(option_spec: dict[str, Any]) -> Any:
    if option_spec.get("type") == "integer":
        return int
    return None


def _add_option(parser: argparse.ArgumentParser, option_spec: dict[str, Any]) -> None:
    kwargs: dict[str, Any] = {}
    action = option_spec.get("action")
    if isinstance(action, str):
        kwargs["action"] = action
    if "choices" in option_spec:
        kwargs["choices"] = tuple(option_spec["choices"])
    if "default" in option_spec:
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


def build_generated_parser() -> argparse.ArgumentParser:
    epilog = (
        f"Weak-agent routing: {_GENERATED_WEAK_AGENT_ROUTING}\n"
        "Recovery: use one of the supported generated commands or route back to the canonical Python CLI."
    )
    parser = argparse.ArgumentParser(prog="agentic-planning", description="", epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in _GENERATED_ADAPTER_COMMANDS:
        interface = command["interface"]
        command_parser = subparsers.add_parser(
            str(interface["name"]),
            help=str(interface["help"]),
            description=str(interface["help"]),
        )
        command_parser.set_defaults(_generated_operation_id=command["operation_id"])
        for option in interface.get("options", []):
            _add_option(command_parser, option)
    return parser


def run_generated_command(argv: list[str] | tuple[str, ...], runtime_handler: RuntimeHandler) -> int:
    parser = build_generated_parser()
    args = parser.parse_args(list(argv))
    operation_id = str(getattr(args, "_generated_operation_id"))
    return runtime_handler(operation_id, args)
