from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, run_operation_steps


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") not in {
        "config.report",
        "defaults.report",
        "delegation-outcome.append",
        "prompt.init",
        "prompt.uninstall",
        "prompt.upgrade",
        "system-intent.sync",
    }:
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
                "delegation_target": getattr(args, "delegation_target", None),
                "escalation_required": getattr(args, "escalation_required", False),
                "handoff_sufficiency": getattr(args, "handoff_sufficiency", None),
                "module": getattr(args, "module", None),
                "non_interactive": getattr(args, "non_interactive", False),
                "outcome": getattr(args, "outcome", None),
                "prompt_command": getattr(args, "prompt_command", None),
                "preset": getattr(args, "preset", None),
                "review_burden": getattr(args, "review_burden", None),
                "section": getattr(args, "section", None),
                "select": getattr(args, "select", None),
                "sync": getattr(args, "sync", False),
                "target": getattr(args, "target", None),
                "task_class": getattr(args, "task_class", None),
            },
            context=context,
            handlers={
                "workspace.root.resolve": _resolve_workspace_target_root,
                "workspace.config.load": _load_workspace_config,
                "workspace.defaults.load": _load_defaults,
                "workspace.defaults.select": _select_defaults,
                "workspace.selection.resolve": _resolve_workspace_selection,
                "prompt.render": _render_prompt,
                "delegation.outcome.append": _append_delegation_outcome,
                "system_intent.config.resolve": _load_system_intent_config,
                "system_intent.source_metadata.refresh": _refresh_system_intent_metadata,
                "system_intent.mirror.read_or_create": _read_or_create_system_intent_mirror,
                "system_intent.result.emit": _emit_workspace_output,
                "output.fields.select": _select_fields,
                "output.emit": _emit_workspace_output,
                "workspace.config.emit": _emit_workspace_output,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _resolve_workspace_target_root(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Path:
    from agentic_command_generation.workspace_runtime_cli import _resolve_target_root, _validate_target_root

    target_root = _resolve_target_root(values.get("target")) if values.get("target") else _resolve_target_root(None)
    _validate_target_root(command_name="config", target_root=target_root)
    return target_root


def _load_workspace_config(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from agentic_command_generation.workspace_runtime_cli import _module_operations, _preset_modules, _validate_descriptor_contract
    from agentic_workspace import config as config_lib

    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    return config_lib.load_workspace_config(
        target_root=values["target_root"],
        valid_presets=set(_preset_modules(descriptors)),
    )


def _load_defaults(_values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_command_generation.workspace_runtime_cli import _defaults_payload

    return _defaults_payload()


def _select_defaults(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_command_generation.workspace_runtime_cli import (
        _select_defaults_section,
        _select_payload_fields,
        _tiny_defaults_payload,
        serialise_value,
    )

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
    from agentic_command_generation.workspace_runtime_cli import (
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
    from agentic_command_generation.workspace_runtime_cli import _selected_runtime_context

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
    from agentic_command_generation.workspace_runtime_cli import _run_prompt_command

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


def _append_delegation_outcome(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_command_generation.workspace_runtime_cli import _record_delegation_outcome

    return _record_delegation_outcome(
        target_root=values["target_root"],
        delegation_target=str(values.get("delegation_target") or ""),
        task_class=str(values.get("task_class") or ""),
        outcome=str(values.get("outcome") or ""),
        handoff_sufficiency=str(values.get("handoff_sufficiency") or ""),
        review_burden=str(values.get("review_burden") or ""),
        escalation_required=bool(values.get("escalation_required", False)),
    )


def _load_system_intent_config(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from agentic_command_generation.workspace_runtime_cli import _module_operations, _preset_modules, _validate_descriptor_contract
    from agentic_workspace import config as config_lib

    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    return config_lib.load_workspace_config(target_root=values["target_root"], valid_presets=set(_preset_modules(descriptors)))


def _refresh_system_intent_metadata(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    if not values.get("sync"):
        return None
    from agentic_command_generation.workspace_runtime_cli import _system_intent_command_payload

    return _system_intent_command_payload(target_root=values["target_root"], config=values["system_intent_config"], sync=True)


def _read_or_create_system_intent_mirror(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    if values.get("result") is not None:
        return values["result"]
    from agentic_command_generation.workspace_runtime_cli import _system_intent_command_payload

    return _system_intent_command_payload(target_root=values["target_root"], config=values["system_intent_config"], sync=False)


def _emit_workspace_output(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> None:
    from agentic_command_generation.workspace_runtime_cli import (
        _emit_compact_answer_text,
        _emit_config,
        _emit_defaults,
        _emit_payload,
        serialise_value,
    )

    payload = values["result"]
    output_format = str(values.get("format") or "text")
    if isinstance(payload, dict) and payload.get("command") == "prompt":
        _emit_payload(payload=payload, format_name=output_format)
        return
    if isinstance(payload, dict) and payload.get("kind") == "workspace-system-intent/v1":
        if output_format == "json":
            print(json.dumps(serialise_value(payload), indent=2))
        else:
            _emit_system_intent_payload_text(payload)
        return
    if isinstance(payload, dict) and payload.get("kind") == "agentic-workspace/delegation-outcomes/v1":
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


def _emit_system_intent_payload_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: {payload['command']}")
    print(f"Sync requested: {payload['sync_requested']}")
    print(f"Source declaration surface: {payload['source_declaration_surface']}")
    print(f"Compiled declaration surface: {payload['mirror_surface']}")
    print(f"Workflow surface: {payload['workflow_surface']}")
    declaration = payload["source_declaration"]
    print(f"Sources: {', '.join(declaration['sources']) or 'none'} ({declaration['sources_source']})")
    print(f"Preferred source: {declaration['preferred_source'] or 'none'} ({declaration['preferred_source_source']})")
    mirror = payload["mirror"]
    print(f"Compiled declaration status: {mirror.get('status', 'unknown')}")
    if mirror.get("summary"):
        print(f"Compiled declaration summary: {mirror['summary']}")
    if payload["actions"]:
        print("Actions:")
        for action in payload["actions"]:
            print(f"- {action['kind']}: {action['path']} ({action['detail']})")
    print(f"Next action: {payload['next_action']['summary']}")
    for command in payload["next_action"]["commands"]:
        print(f"- {command}")


def _diagnostic_profile(args: argparse.Namespace, *, default: str) -> str:
    from agentic_command_generation.workspace_runtime_cli import _diagnostic_profile as runtime_diagnostic_profile

    return runtime_diagnostic_profile(args, default=default)
