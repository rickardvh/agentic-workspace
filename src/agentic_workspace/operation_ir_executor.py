from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, run_operation_steps


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") not in {"config.report", "defaults.report", "prompt.init", "prompt.uninstall", "prompt.upgrade"}:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    context = PrimitiveContext(cwd=Path.cwd())
    try:
        run_operation_steps(
            operation,
            initial_values={
                "format": getattr(args, "format", "text"),
                "operation_id": operation.get("id"),
                "profile": _diagnostic_profile(args, default="tiny"),
                "adopt": getattr(args, "adopt", False),
                "agent_instructions_file": getattr(args, "agent_instructions_file", None),
                "module": getattr(args, "module", None),
                "non_interactive": getattr(args, "non_interactive", False),
                "prompt_command": getattr(args, "prompt_command", None),
                "preset": getattr(args, "preset", None),
                "section": getattr(args, "section", None),
                "select": getattr(args, "select", None),
                "target": getattr(args, "target", None),
            },
            context=context,
            handlers={
                "workspace.root.resolve": _resolve_workspace_target_root,
                "workspace.config.load": _load_workspace_config,
                "workspace.defaults.load": _load_defaults,
                "workspace.defaults.select": _select_defaults,
                "workspace.selection.resolve": _resolve_workspace_selection,
                "prompt.render": _render_prompt,
                "output.fields.select": _select_fields,
                "output.emit": _emit_workspace_output,
                "workspace.config.emit": _emit_workspace_output,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _resolve_workspace_target_root(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Path:
    from agentic_workspace._runtime_cli import _resolve_target_root, _validate_target_root

    target_root = _resolve_target_root(values.get("target")) if values.get("target") else _resolve_target_root(None)
    _validate_target_root(command_name="config", target_root=target_root)
    return target_root


def _load_workspace_config(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from agentic_workspace import config as config_lib
    from agentic_workspace._runtime_cli import _module_operations, _preset_modules, _validate_descriptor_contract

    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    return config_lib.load_workspace_config(
        target_root=values["target_root"],
        valid_presets=set(_preset_modules(descriptors)),
    )


def _load_defaults(_values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_workspace._runtime_cli import _defaults_payload

    return _defaults_payload()


def _select_defaults(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_workspace._runtime_cli import _select_defaults_section, _select_payload_fields, _tiny_defaults_payload, serialise_value

    payload = values["defaults_payload"]
    section = values.get("section")
    if section is not None:
        payload = _select_defaults_section(payload, section=str(section))
    elif values.get("profile") == "tiny":
        payload = _tiny_defaults_payload(payload)
    select = values.get("select")
    if select is not None:
        payload = _select_payload_fields(payload, select=str(select), source_command="defaults")
    return serialise_value(payload)


def _select_fields(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_workspace._runtime_cli import (
        _compact_config_payload,
        _config_payload,
        _select_payload_fields,
        _tiny_config_payload,
        serialise_value,
    )

    payload = _config_payload(config=values["config"])
    select = values.get("select")
    if select:
        payload = _select_payload_fields(payload, select=str(select), source_command="config")
    elif values.get("profile") == "tiny":
        payload = _tiny_config_payload(payload)
    elif values.get("profile") == "compact":
        payload = _compact_config_payload(payload)
    return serialise_value(payload)


def _resolve_workspace_selection(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_workspace._runtime_cli import _selected_runtime_context

    args = argparse.Namespace(
        target=values.get("target"),
        module=values.get("module"),
        preset=values.get("preset"),
        agent_instructions_file=values.get("agent_instructions_file"),
    )
    target_root, descriptors, config, selected_modules, resolved_preset = _selected_runtime_context(args=args, command_name="prompt")
    return {
        "target_root": target_root,
        "descriptors": descriptors,
        "config": config,
        "selected_modules": selected_modules,
        "resolved_preset": resolved_preset,
    }


def _render_prompt(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_workspace._runtime_cli import _run_prompt_command

    selection = values["selection"]
    prompt_command = values.get("prompt_command")
    if prompt_command is None:
        operation_id = str(values.get("operation_id", ""))
        prompt_command = operation_id.removeprefix("prompt.") if operation_id.startswith("prompt.") else ""
    return _run_prompt_command(
        prompt_command=str(prompt_command),
        target_root=selection["target_root"],
        selected_modules=selection["selected_modules"],
        resolved_preset=selection["resolved_preset"],
        descriptors=selection["descriptors"],
        force_adopt=bool(values.get("adopt", False)),
        non_interactive=bool(values.get("non_interactive", False)),
        config=selection["config"],
    )


def _emit_workspace_output(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> None:
    from agentic_workspace._runtime_cli import _emit_compact_answer_text, _emit_config, _emit_defaults, _emit_payload

    payload = values["result"]
    output_format = str(values.get("format") or "text")
    if isinstance(payload, dict) and payload.get("command") == "prompt":
        _emit_payload(payload=payload, format_name=output_format)
        return
    if output_format == "json":
        print(json.dumps(payload, indent=2))
        return
    if values.get("section") is not None and isinstance(payload, dict):
        _emit_compact_answer_text(payload)
        return
    if "config" in values:
        _emit_config(
            format_name=output_format,
            config=values["config"],
            profile=str(values.get("profile") or "tiny"),
            select=str(values["select"]) if values.get("select") is not None else None,
        )
        return
    _emit_defaults(
        format_name=output_format,
        section=None,
        profile=str(values.get("profile") or "tiny"),
        select=str(values["select"]) if values.get("select") is not None else None,
    )


def _diagnostic_profile(args: argparse.Namespace, *, default: str) -> str:
    from agentic_workspace._runtime_cli import _diagnostic_profile as runtime_diagnostic_profile

    return runtime_diagnostic_profile(args, default=default)
