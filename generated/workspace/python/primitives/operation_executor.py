"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import contextlib
import io
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .primitive_executor import (
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
    values = run_operation_values(
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
                'review_burden': getattr(args, 'review_burden', None),
                'section': getattr(args, 'section', None),
                'select': getattr(args, 'select', None),
                'sync': getattr(args, 'sync', False),
                'target': getattr(args, 'target', None),
                'task_class': getattr(args, 'task_class', None),
                'scope_class': getattr(args, 'scope_class', None),
                'operation': getattr(args, 'operation', 'submit'),
                'predecessor_id': getattr(args, 'predecessor_id', None),
                'authority': getattr(args, 'authority', 'local-outcome-ledger'),
                'confidence': getattr(args, 'confidence', 'medium'),
                'source_type': getattr(args, 'source_type', None),
                'source_ref': getattr(args, 'source_ref', None),
                'producer_class': getattr(args, 'producer_class', None),
                'route_outcome': getattr(args, 'route_outcome', None),
                'assignment_route': getattr(args, 'assignment_route', None),
                'proof_observation': getattr(args, 'proof_observation', None),
                'review_observation': getattr(args, 'review_observation', None),
                'handoff_burden': getattr(args, 'handoff_burden', None),
                'repair_burden': getattr(args, 'repair_burden', None),
                'retry_burden': getattr(args, 'retry_burden', None),
                'restart_burden': getattr(args, 'restart_burden', None),
                'expected_burden': getattr(args, 'expected_burden', None),
                'observed_burden': getattr(args, 'observed_burden', None),
                'scope_drift': getattr(args, 'scope_drift', 'none'),
                'contradiction_state': getattr(args, 'contradiction_state', 'none'),
                'uncertainty_state': getattr(args, 'uncertainty_state', None),
                'idempotency_key': getattr(args, 'idempotency_key', None),
        },
    )
    emitted = values.get('emitted')
    if isinstance(emitted, str):
        print(emitted, end='')
    return 0


def run_operation_callable(operation: dict[str, Any], values: Mapping[str, Any]) -> object:
    with contextlib.redirect_stdout(io.StringIO()):
        result = run_operation_values(
            operation,
            initial_values={
                "operation_id": operation.get("id"),
                'format': values.get('format', 'text'),
                'verbose': values.get('verbose', False),
                'adopt': values.get('adopt', False),
                'agent_instructions_file': values.get('agent_instructions_file', None),
                'delegation_target': values.get('delegation_target', None),
                'escalation_required': values.get('escalation_required', False),
                'handoff_sufficiency': values.get('handoff_sufficiency', None),
                'module': values.get('module', None),
                'non_interactive': values.get('non_interactive', False),
                'outcome': values.get('outcome', None),
                'prompt_command': values.get('prompt_command', None),
                'review_burden': values.get('review_burden', None),
                'section': values.get('section', None),
                'select': values.get('select', None),
                'sync': values.get('sync', False),
                'target': values.get('target', None),
                'task_class': values.get('task_class', None),
                'scope_class': values.get('scope_class', None),
                'operation': values.get('operation', 'submit'),
                'predecessor_id': values.get('predecessor_id', None),
                'authority': values.get('authority', 'local-outcome-ledger'),
                'confidence': values.get('confidence', 'medium'),
                'source_type': values.get('source_type', None),
                'source_ref': values.get('source_ref', None),
                'producer_class': values.get('producer_class', None),
                'route_outcome': values.get('route_outcome', None),
                'assignment_route': values.get('assignment_route', None),
                'proof_observation': values.get('proof_observation', None),
                'review_observation': values.get('review_observation', None),
                'handoff_burden': values.get('handoff_burden', None),
                'repair_burden': values.get('repair_burden', None),
                'retry_burden': values.get('retry_burden', None),
                'restart_burden': values.get('restart_burden', None),
                'expected_burden': values.get('expected_burden', None),
                'observed_burden': values.get('observed_burden', None),
                'scope_drift': values.get('scope_drift', 'none'),
                'contradiction_state': values.get('contradiction_state', 'none'),
                'uncertainty_state': values.get('uncertainty_state', None),
                'idempotency_key': values.get('idempotency_key', None),
            },
        ).get('result')
    return result


def run_operation_values(operation: dict[str, Any], *, initial_values: Mapping[str, Any]) -> dict[str, Any]:
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
        return run_operation_steps(
            operation,
            initial_values=dict(initial_values),
            context=PrimitiveContext(cwd=Path.cwd(), roots={}),
            handlers={
                'workspace.target-root.resolve': _handle_workspace_target_root_resolve,
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
                'output.emit': _handle_output_emit,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc


def _handle_workspace_target_root_resolve(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _resolve_workspace_operation_target_root

    return _resolve_workspace_operation_target_root(values, arguments, context)


def _handle_workspace_config_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _load_workspace_operation_config

    return _load_workspace_operation_config(values, arguments, context)


def _handle_workspace_defaults_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _load_workspace_operation_defaults

    return _load_workspace_operation_defaults(values, arguments, context)


def _handle_workspace_defaults_select(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _select_workspace_operation_defaults

    return _select_workspace_operation_defaults(values, arguments, context)


def _handle_workspace_selection_resolve(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _resolve_workspace_operation_selection

    return _resolve_workspace_operation_selection(values, arguments, context)


def _handle_prompt_render(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _render_workspace_operation_prompt

    return _render_workspace_operation_prompt(values, arguments, context)


def _handle_delegation_outcome_append(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _append_workspace_operation_delegation_outcome

    return _append_workspace_operation_delegation_outcome(values, arguments, context)


def _handle_system_intent_config_resolve(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _load_workspace_operation_system_intent_config

    return _load_workspace_operation_system_intent_config(values, arguments, context)


def _handle_system_intent_source_metadata_refresh(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _refresh_workspace_operation_system_intent_metadata

    return _refresh_workspace_operation_system_intent_metadata(values, arguments, context)


def _handle_system_intent_mirror_read_or_create(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _read_or_create_workspace_operation_system_intent_mirror

    return _read_or_create_workspace_operation_system_intent_mirror(values, arguments, context)


def _handle_system_intent_result_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _emit_workspace_operation_output

    return _emit_workspace_operation_output(values, arguments, context)


def _handle_output_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .workspace_runtime import _emit_workspace_operation_output

    return _emit_workspace_operation_output(values, arguments, context)
