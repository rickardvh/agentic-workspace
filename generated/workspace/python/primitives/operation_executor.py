"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from command_generation.primitive_executor import (
    PrimitiveContext,
    PrimitiveExecutionError,
    run_operation_steps,
)

# DO NOT EDIT DIRECTLY.
# Operation executor binding changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") not in {
        'config.report',
        'defaults.report',
        'delegation-outcome.append',
        'prompt.init',
        'prompt.uninstall',
        'prompt.upgrade',
        'system-intent.sync'
    }:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    try:
        run_operation_steps(
            operation,
            initial_values={
                "operation_id": operation.get("id"),
                'format': getattr(args, 'format', 'text'),
                'verbose': getattr(args, 'verbose', False),
                'adopt': getattr(args, 'adopt', False),
                'agent_instructions_file': getattr(args, 'agent_instructions_file', None),
                'delegation_target': getattr(args, 'delegation_target', None),
                'escalation_required': getattr(args, 'escalation_required', False),
                'handoff_sufficiency': getattr(args, 'handoff_sufficiency', None),
                'module': getattr(args, 'module', None),
                'non_interactive': getattr(args, 'non_interactive', False),
                'outcome': getattr(args, 'outcome', None),
                'prompt_command': getattr(args, 'prompt_command', None),
                'preset': getattr(args, 'preset', None),
                'review_burden': getattr(args, 'review_burden', None),
                'section': getattr(args, 'section', None),
                'select': getattr(args, 'select', None),
                'sync': getattr(args, 'sync', False),
                'target': getattr(args, 'target', None),
                'task_class': getattr(args, 'task_class', None),
            },
            context=PrimitiveContext(cwd=Path.cwd(), roots={}),
            handlers={
                'workspace.root.resolve': _handle_workspace_root_resolve,
                'workspace.config.load': _handle_workspace_config_load,
                'workspace.defaults.load': _handle_workspace_defaults_load,
                'workspace.defaults.select': _handle_workspace_defaults_select,
                'workspace.selection.resolve': _handle_workspace_selection_resolve,
                'prompt.render': _handle_prompt_render,
                'delegation.outcome.append': _handle_delegation_outcome_append,
                'system_intent.config.resolve': _handle_system_intent_config_resolve,
                'system_intent.source_metadata.refresh': _handle_system_intent_source_metadata_refresh,
                'system_intent.mirror.read_or_create': _handle_system_intent_mirror_read_or_create,
                'system_intent.result.emit': _handle_system_intent_result_emit,
                'output.fields.select': _handle_output_fields_select,
                'output.emit': _handle_output_emit,
                'workspace.config.emit': _handle_workspace_config_emit,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _handle_workspace_root_resolve(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _resolve_workspace_operation_target_root

    return _resolve_workspace_operation_target_root(values, arguments, context)


def _handle_workspace_config_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_config

    return _load_workspace_operation_config(values, arguments, context)


def _handle_workspace_defaults_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_defaults

    return _load_workspace_operation_defaults(values, arguments, context)


def _handle_workspace_defaults_select(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _select_workspace_operation_defaults

    return _select_workspace_operation_defaults(values, arguments, context)


def _handle_workspace_selection_resolve(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _resolve_workspace_operation_selection

    return _resolve_workspace_operation_selection(values, arguments, context)


def _handle_prompt_render(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _render_workspace_operation_prompt

    return _render_workspace_operation_prompt(values, arguments, context)


def _handle_delegation_outcome_append(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _append_workspace_operation_delegation_outcome

    return _append_workspace_operation_delegation_outcome(values, arguments, context)


def _handle_system_intent_config_resolve(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_system_intent_config

    return _load_workspace_operation_system_intent_config(values, arguments, context)


def _handle_system_intent_source_metadata_refresh(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _refresh_workspace_operation_system_intent_metadata

    return _refresh_workspace_operation_system_intent_metadata(values, arguments, context)


def _handle_system_intent_mirror_read_or_create(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _read_or_create_workspace_operation_system_intent_mirror

    return _read_or_create_workspace_operation_system_intent_mirror(values, arguments, context)


def _handle_system_intent_result_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _emit_workspace_operation_output

    return _emit_workspace_operation_output(values, arguments, context)


def _handle_output_fields_select(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _select_workspace_operation_fields

    return _select_workspace_operation_fields(values, arguments, context)


def _handle_output_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _emit_workspace_operation_output

    return _emit_workspace_operation_output(values, arguments, context)


def _handle_workspace_config_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _emit_workspace_operation_output

    return _emit_workspace_operation_output(values, arguments, context)
