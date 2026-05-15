"""Generated runtime-backed Python command adapter.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import difflib
import importlib
import json
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from typing import Any

# DO NOT EDIT DIRECTLY.
# Command/interface changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Runtime behavior changes belong in hand-written operation/primitive implementation code.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from agentic_workspace.workspace_runtime_primitives import __version__ as __version__
from agentic_workspace.workspace_runtime_primitives import _authority_marker_for_path as _authority_marker_for_path
from agentic_workspace.workspace_runtime_primitives import _command_with_cli_invoke as _command_with_cli_invoke
from agentic_workspace.workspace_runtime_primitives import _command_suggestions as _command_suggestions
from agentic_workspace.workspace_runtime_primitives import _compact_contract_answer as _compact_contract_answer
from agentic_workspace.workspace_runtime_primitives import _defaults_payload as _defaults_payload
from agentic_workspace.workspace_runtime_primitives import _friction_response_order_payload as _friction_response_order_payload
from agentic_workspace.workspace_runtime_primitives import _implement_payload as _implement_payload
from agentic_workspace.workspace_runtime_primitives import _invoke_module_command as _invoke_module_command
from agentic_workspace.workspace_runtime_primitives import _improvement_boundary_test_payload as _improvement_boundary_test_payload
from agentic_workspace.workspace_runtime_primitives import _improvement_latitude_payload as _improvement_latitude_payload
from agentic_workspace.workspace_runtime_primitives import _load_workspace_config as _load_workspace_config
from agentic_workspace.workspace_runtime_primitives import _module_operations as _module_operations
from agentic_workspace.workspace_runtime_primitives import _module_registry as _module_registry
from agentic_workspace.workspace_runtime_primitives import _MODULE_REGISTRY_ENTRIES as _MODULE_REGISTRY_ENTRIES
from agentic_workspace.workspace_runtime_primitives import _optimization_bias_payload as _optimization_bias_payload
from agentic_workspace.workspace_runtime_primitives import _ordered_module_names as _ordered_module_names
from agentic_workspace.workspace_runtime_primitives import _planning_module_argv as _planning_module_argv
from agentic_workspace.workspace_runtime_primitives import _ownership_payload as _ownership_payload
from agentic_workspace.workspace_runtime_primitives import _PREFLIGHT_STRICT_GATE_POLICY as _PREFLIGHT_STRICT_GATE_POLICY
from agentic_workspace.workspace_runtime_primitives import _product_managed_enclave_payload as _product_managed_enclave_payload
from agentic_workspace.workspace_runtime_primitives import _repo_directed_improvement_evidence_threshold_payload as _repo_directed_improvement_evidence_threshold_payload
from agentic_workspace.workspace_runtime_primitives import _reporting_schema_payload as _reporting_schema_payload
from agentic_workspace.workspace_runtime_primitives import _resolve_option_choices as _resolve_option_choices
from agentic_workspace.workspace_runtime_primitives import _resolve_option_default as _resolve_option_default
from agentic_workspace.workspace_runtime_primitives import _resolve_option_type as _resolve_option_type
from agentic_workspace.workspace_runtime_primitives import _resolved_option_help as _resolved_option_help
from agentic_workspace.workspace_runtime_primitives import _runtime_resolution_payload as _runtime_resolution_payload
from agentic_workspace.workspace_runtime_primitives import _run_report_command as _run_report_command
from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_command as _run_lifecycle_command
from agentic_workspace.workspace_runtime_primitives import _selected_modules as _selected_modules
from agentic_workspace.workspace_runtime_primitives import _setup_finding_class_payload as _setup_finding_class_payload
from agentic_workspace.workspace_runtime_primitives import _start_payload as _start_payload
from agentic_workspace.workspace_runtime_primitives import _validation_friction_payload as _validation_friction_payload
from agentic_workspace.workspace_runtime_primitives import _validate_selected_module_contract as _validate_selected_module_contract
from agentic_workspace.workspace_runtime_primitives import _workflow_artifact_profile_payload as _workflow_artifact_profile_payload
from agentic_workspace.workspace_runtime_primitives import _workspace_agents_template as _workspace_agents_template
from agentic_workspace.workspace_runtime_primitives import _workspace_self_adaptation_guardrail_payload as _workspace_self_adaptation_guardrail_payload
from agentic_workspace.workspace_runtime_primitives import _workspace_self_adaptation_payload as _workspace_self_adaptation_payload
from agentic_workspace.workspace_runtime_primitives import DEFAULT_IMPROVEMENT_LATITUDE as DEFAULT_IMPROVEMENT_LATITUDE
from agentic_workspace.workspace_runtime_primitives import DEFAULT_OPTIMIZATION_BIAS as DEFAULT_OPTIMIZATION_BIAS
from agentic_workspace.workspace_runtime_primitives import DEFAULT_PREFLIGHT_MAX_AGE_SECONDS as DEFAULT_PREFLIGHT_MAX_AGE_SECONDS
from agentic_workspace.workspace_runtime_primitives import DEFAULT_WORKFLOW_ARTIFACT_PROFILE as DEFAULT_WORKFLOW_ARTIFACT_PROFILE
from agentic_workspace.workspace_runtime_primitives import HIGH_RISK_COMMANDS as HIGH_RISK_COMMANDS
from agentic_workspace.workspace_runtime_primitives import MEMORY_POINTER_BLOCK as MEMORY_POINTER_BLOCK
from agentic_workspace.workspace_runtime_primitives import MEMORY_WORKFLOW_MARKER_END as MEMORY_WORKFLOW_MARKER_END
from agentic_workspace.workspace_runtime_primitives import MEMORY_WORKFLOW_MARKER_START as MEMORY_WORKFLOW_MARKER_START
from agentic_workspace.workspace_runtime_primitives import MIXED_AGENT_LOCAL_OVERRIDE_FIELDS as MIXED_AGENT_LOCAL_OVERRIDE_FIELDS
from agentic_workspace.workspace_runtime_primitives import MODULE_COMMAND_ARGS as MODULE_COMMAND_ARGS
from agentic_workspace.workspace_runtime_primitives import MODULE_UPGRADE_SOURCE_PATHS as MODULE_UPGRADE_SOURCE_PATHS
from agentic_workspace.workspace_runtime_primitives import ModuleDescriptor as ModuleDescriptor
from agentic_workspace.workspace_runtime_primitives import ModuleSelectionError as ModuleSelectionError
from agentic_workspace.workspace_runtime_primitives import ModuleResultContract as ModuleResultContract
from agentic_workspace.workspace_runtime_primitives import PREFLIGHT_TOKEN_PREFIX as PREFLIGHT_TOKEN_PREFIX
from agentic_workspace.workspace_runtime_primitives import RootAgentsCleanupBlock as RootAgentsCleanupBlock
from agentic_workspace.workspace_runtime_primitives import SETUP_FINDING_PROMOTION_THRESHOLD as SETUP_FINDING_PROMOTION_THRESHOLD
from agentic_workspace.workspace_runtime_primitives import SETUP_FINDINGS_KIND as SETUP_FINDINGS_KIND
from agentic_workspace.workspace_runtime_primitives import SETUP_FINDINGS_PATH as SETUP_FINDINGS_PATH
from agentic_workspace.workspace_runtime_primitives import SUBSYSTEM_INTENT_KIND as SUBSYSTEM_INTENT_KIND
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_DELEGATION_OUTCOMES as SUPPORTED_DELEGATION_OUTCOMES
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS as SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_DELEGATION_TARGET_STRENGTHS as SUPPORTED_DELEGATION_TARGET_STRENGTHS
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_HANDOFF_SUFFICIENCY as SUPPORTED_HANDOFF_SUFFICIENCY
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_IMPROVEMENT_LATITUDES as SUPPORTED_IMPROVEMENT_LATITUDES
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_OPTIMIZATION_BIASES as SUPPORTED_OPTIMIZATION_BIASES
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_REVIEW_BURDENS as SUPPORTED_REVIEW_BURDENS
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_SETUP_FINDING_CLASSES as SUPPORTED_SETUP_FINDING_CLASSES
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_WORKFLOW_ARTIFACT_PROFILES as SUPPORTED_WORKFLOW_ARTIFACT_PROFILES
from agentic_workspace.workspace_runtime_primitives import SUPPORTED_WORKFLOW_OBLIGATION_STAGES as SUPPORTED_WORKFLOW_OBLIGATION_STAGES
from agentic_workspace.workspace_runtime_primitives import SYSTEM_INTENT_MIRROR_KIND as SYSTEM_INTENT_MIRROR_KIND
from agentic_workspace.workspace_runtime_primitives import WORKSPACE_AGENTS_PATH as WORKSPACE_AGENTS_PATH
from agentic_workspace.workspace_runtime_primitives import WORKSPACE_HANDOFF_SURFACES as WORKSPACE_HANDOFF_SURFACES
from agentic_workspace.workspace_runtime_primitives import WORKSPACE_PAYLOAD_FILES as WORKSPACE_PAYLOAD_FILES
from agentic_workspace.workspace_runtime_primitives import WORKSPACE_POINTER_BLOCK as WORKSPACE_POINTER_BLOCK
from agentic_workspace.workspace_runtime_primitives import datetime as datetime
from agentic_workspace.workspace_runtime_primitives import subprocess as subprocess
from agentic_workspace.workspace_runtime_primitives import timedelta as timedelta
from agentic_workspace.workspace_runtime_primitives import timezone as timezone

_RUNTIME_EXPORT_SOURCES = (
    ('agentic_workspace.workspace_runtime_primitives', '__version__', '__version__'),
    ('agentic_workspace.workspace_runtime_primitives', '_authority_marker_for_path', '_authority_marker_for_path'),
    ('agentic_workspace.workspace_runtime_primitives', '_command_with_cli_invoke', '_command_with_cli_invoke'),
    ('agentic_workspace.workspace_runtime_primitives', '_command_suggestions', '_command_suggestions'),
    ('agentic_workspace.workspace_runtime_primitives', '_compact_contract_answer', '_compact_contract_answer'),
    ('agentic_workspace.workspace_runtime_primitives', '_defaults_payload', '_defaults_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_friction_response_order_payload', '_friction_response_order_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_implement_payload', '_implement_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_invoke_module_command', '_invoke_module_command'),
    ('agentic_workspace.workspace_runtime_primitives', '_improvement_boundary_test_payload', '_improvement_boundary_test_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_improvement_latitude_payload', '_improvement_latitude_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_load_workspace_config', '_load_workspace_config'),
    ('agentic_workspace.workspace_runtime_primitives', '_module_operations', '_module_operations'),
    ('agentic_workspace.workspace_runtime_primitives', '_module_registry', '_module_registry'),
    ('agentic_workspace.workspace_runtime_primitives', '_MODULE_REGISTRY_ENTRIES', '_MODULE_REGISTRY_ENTRIES'),
    ('agentic_workspace.workspace_runtime_primitives', '_optimization_bias_payload', '_optimization_bias_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_ordered_module_names', '_ordered_module_names'),
    ('agentic_workspace.workspace_runtime_primitives', '_planning_module_argv', '_planning_module_argv'),
    ('agentic_workspace.workspace_runtime_primitives', '_ownership_payload', '_ownership_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_PREFLIGHT_STRICT_GATE_POLICY', '_PREFLIGHT_STRICT_GATE_POLICY'),
    ('agentic_workspace.workspace_runtime_primitives', '_product_managed_enclave_payload', '_product_managed_enclave_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_repo_directed_improvement_evidence_threshold_payload', '_repo_directed_improvement_evidence_threshold_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_reporting_schema_payload', '_reporting_schema_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolve_option_choices', '_resolve_option_choices'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolve_option_default', '_resolve_option_default'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolve_option_type', '_resolve_option_type'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolved_option_help', '_resolved_option_help'),
    ('agentic_workspace.workspace_runtime_primitives', '_runtime_resolution_payload', '_runtime_resolution_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_run_report_command', '_run_report_command'),
    ('agentic_workspace.workspace_runtime_primitives', '_run_lifecycle_command', '_run_lifecycle_command'),
    ('agentic_workspace.workspace_runtime_primitives', '_selected_modules', '_selected_modules'),
    ('agentic_workspace.workspace_runtime_primitives', '_setup_finding_class_payload', '_setup_finding_class_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_start_payload', '_start_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_validation_friction_payload', '_validation_friction_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_validate_selected_module_contract', '_validate_selected_module_contract'),
    ('agentic_workspace.workspace_runtime_primitives', '_workflow_artifact_profile_payload', '_workflow_artifact_profile_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_workspace_agents_template', '_workspace_agents_template'),
    ('agentic_workspace.workspace_runtime_primitives', '_workspace_self_adaptation_guardrail_payload', '_workspace_self_adaptation_guardrail_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_workspace_self_adaptation_payload', '_workspace_self_adaptation_payload'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_IMPROVEMENT_LATITUDE', 'DEFAULT_IMPROVEMENT_LATITUDE'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_OPTIMIZATION_BIAS', 'DEFAULT_OPTIMIZATION_BIAS'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_PREFLIGHT_MAX_AGE_SECONDS', 'DEFAULT_PREFLIGHT_MAX_AGE_SECONDS'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_WORKFLOW_ARTIFACT_PROFILE', 'DEFAULT_WORKFLOW_ARTIFACT_PROFILE'),
    ('agentic_workspace.workspace_runtime_primitives', 'HIGH_RISK_COMMANDS', 'HIGH_RISK_COMMANDS'),
    ('agentic_workspace.workspace_runtime_primitives', 'MEMORY_POINTER_BLOCK', 'MEMORY_POINTER_BLOCK'),
    ('agentic_workspace.workspace_runtime_primitives', 'MEMORY_WORKFLOW_MARKER_END', 'MEMORY_WORKFLOW_MARKER_END'),
    ('agentic_workspace.workspace_runtime_primitives', 'MEMORY_WORKFLOW_MARKER_START', 'MEMORY_WORKFLOW_MARKER_START'),
    ('agentic_workspace.workspace_runtime_primitives', 'MIXED_AGENT_LOCAL_OVERRIDE_FIELDS', 'MIXED_AGENT_LOCAL_OVERRIDE_FIELDS'),
    ('agentic_workspace.workspace_runtime_primitives', 'MODULE_COMMAND_ARGS', 'MODULE_COMMAND_ARGS'),
    ('agentic_workspace.workspace_runtime_primitives', 'MODULE_UPGRADE_SOURCE_PATHS', 'MODULE_UPGRADE_SOURCE_PATHS'),
    ('agentic_workspace.workspace_runtime_primitives', 'ModuleDescriptor', 'ModuleDescriptor'),
    ('agentic_workspace.workspace_runtime_primitives', 'ModuleSelectionError', 'ModuleSelectionError'),
    ('agentic_workspace.workspace_runtime_primitives', 'ModuleResultContract', 'ModuleResultContract'),
    ('agentic_workspace.workspace_runtime_primitives', 'PREFLIGHT_TOKEN_PREFIX', 'PREFLIGHT_TOKEN_PREFIX'),
    ('agentic_workspace.workspace_runtime_primitives', 'RootAgentsCleanupBlock', 'RootAgentsCleanupBlock'),
    ('agentic_workspace.workspace_runtime_primitives', 'SETUP_FINDING_PROMOTION_THRESHOLD', 'SETUP_FINDING_PROMOTION_THRESHOLD'),
    ('agentic_workspace.workspace_runtime_primitives', 'SETUP_FINDINGS_KIND', 'SETUP_FINDINGS_KIND'),
    ('agentic_workspace.workspace_runtime_primitives', 'SETUP_FINDINGS_PATH', 'SETUP_FINDINGS_PATH'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUBSYSTEM_INTENT_KIND', 'SUBSYSTEM_INTENT_KIND'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_DELEGATION_OUTCOMES', 'SUPPORTED_DELEGATION_OUTCOMES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS', 'SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_DELEGATION_TARGET_STRENGTHS', 'SUPPORTED_DELEGATION_TARGET_STRENGTHS'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_HANDOFF_SUFFICIENCY', 'SUPPORTED_HANDOFF_SUFFICIENCY'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_IMPROVEMENT_LATITUDES', 'SUPPORTED_IMPROVEMENT_LATITUDES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_OPTIMIZATION_BIASES', 'SUPPORTED_OPTIMIZATION_BIASES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_REVIEW_BURDENS', 'SUPPORTED_REVIEW_BURDENS'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_SETUP_FINDING_CLASSES', 'SUPPORTED_SETUP_FINDING_CLASSES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_WORKFLOW_ARTIFACT_PROFILES', 'SUPPORTED_WORKFLOW_ARTIFACT_PROFILES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_WORKFLOW_OBLIGATION_STAGES', 'SUPPORTED_WORKFLOW_OBLIGATION_STAGES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SYSTEM_INTENT_MIRROR_KIND', 'SYSTEM_INTENT_MIRROR_KIND'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_AGENTS_PATH', 'WORKSPACE_AGENTS_PATH'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_HANDOFF_SURFACES', 'WORKSPACE_HANDOFF_SURFACES'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_PAYLOAD_FILES', 'WORKSPACE_PAYLOAD_FILES'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_POINTER_BLOCK', 'WORKSPACE_POINTER_BLOCK'),
    ('agentic_workspace.workspace_runtime_primitives', 'datetime', 'datetime'),
    ('agentic_workspace.workspace_runtime_primitives', 'subprocess', 'subprocess'),
    ('agentic_workspace.workspace_runtime_primitives', 'timedelta', 'timedelta'),
    ('agentic_workspace.workspace_runtime_primitives', 'timezone', 'timezone'),
)


def _sync_runtime_export_patches() -> None:
    for module_name, source_name, exported_name in _RUNTIME_EXPORT_SOURCES:
        value = globals().get(exported_name)
        module = importlib.import_module(module_name)
        if getattr(module, source_name, None) is not value:
            setattr(module, source_name, value)


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

_GENERATED_MATURITY_ID = 'mutation-capable-adapter'
_GENERATED_WEAK_AGENT_ROUTING = 'allowed-mutation-with-review'
_GENERATED_RUNNABLE = True

RuntimeHandler = Callable[[str, argparse.Namespace], int]
_GENERATED_RUNTIME_HANDLERS: dict[str, RuntimeHandler] = {}


class GeneratedArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        if 'invalid choice' in message and 'command' in message:
            unknown = _extract_unknown_command(message)
            suggestions = difflib.get_close_matches(unknown, generated_command_names(), n=1, cutoff=0.55)
            if suggestions:
                message = f"{message}\nDid you mean: {', '.join(suggestions)}?"
            if 'start' in _GENERATED_COMMANDS_BY_NAME and 'preflight' in _GENERATED_COMMANDS_BY_NAME:
                message = (
                    f"{message}\nStartup tip: run '{self.prog} start --task \"<task>\" --format json' "
                    f"for normal startup or '{self.prog} preflight --format json' to recover a compact takeover context."
                )
        super().error(message)


def _extract_unknown_command(message: str) -> str:
    prefix = "invalid choice: '"
    if prefix not in message:
        return ''
    return message.split(prefix, 1)[1].split("'", 1)[0]


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


def generated_cli_package_command_names() -> tuple[str, ...]:
    return generated_command_names()


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
    parser = GeneratedArgumentParser(prog="agentic-workspace", description="", epilog=epilog, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.0-generated')
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in _GENERATED_ADAPTER_COMMANDS:
        interface = command["interface"]
        _add_interface_command(subparsers, interface, str(command["operation_id"]))
    return parser


def build_parser() -> argparse.ArgumentParser:
    return build_generated_parser()


def build_generated_cli_package_parser() -> argparse.ArgumentParser:
    return build_generated_parser()


def run_generated_command(argv: list[str] | tuple[str, ...], runtime_handler: RuntimeHandler) -> int:
    parser = build_generated_parser()
    args = parser.parse_args(list(argv))
    operation_id = str(getattr(args, "_generated_operation_id"))
    return runtime_handler(operation_id, args)


def _run_command_module(operation_id: str, args: argparse.Namespace) -> int:
    from .commands import GENERATED_COMMAND_HANDLERS

    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id) or GENERATED_COMMAND_HANDLERS.get(operation_id)
    if handler is None:
        build_generated_parser().error(
            f"Generated adapter for {getattr(args, 'command', operation_id)} references unsupported operation {operation_id}."
        )
    _sync_runtime_export_patches()
    return handler(args)


def main(argv: list[str] | None = None) -> int:
    import sys

    argv_list = list(sys.argv[1:] if argv is None else argv)
    if argv_list and argv_list[0] in {'-h', '--help', '--version'}:
        build_generated_parser().parse_args(argv_list)
        return 0
    if supports_generated_command(argv_list):
        try:
            return run_generated_command(argv_list, _run_command_module)
        except Exception as exc:
            if exc.__class__.__name__.endswith('UsageError') or exc.__class__.__name__ == 'RepoDetectionError':
                build_generated_parser().error(str(exc))
            raise

    build_generated_parser().parse_args(argv_list)
    return 0
