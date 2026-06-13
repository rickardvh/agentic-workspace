"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-verification
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
                'target': getattr(args, 'target', None),
                'changed_paths': getattr(args, 'changed_paths', []),
                'task_text': getattr(args, 'task_text', ''),
                'format': getattr(args, 'format', 'text'),
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
                'target': values.get('target', None),
                'changed_paths': values.get('changed_paths', []),
                'task_text': values.get('task_text', ''),
                'format': values.get('format', 'text'),
            },
        ).get('result')
    return result


def run_operation_values(operation: dict[str, Any], *, initial_values: Mapping[str, Any]) -> dict[str, Any]:
    if operation.get("id") not in {
        'verification.report.report'
    }:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    try:
        return run_operation_steps(
            operation,
            initial_values=dict(initial_values),
            context=PrimitiveContext(cwd=Path.cwd(), roots={
                'verification.contracts': _handle_context_root_verification_contracts(),
            }),
            handlers={
                'path.target_root.resolve': _handle_path_target_root_resolve,
                'verification.report.load': _handle_verification_report_load,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc


def _handle_context_root_verification_contracts() -> Path:
    from .resources import find_resource_root

    return find_resource_root(__file__, [('_contracts', 'operations/verification.report.report.json')])


def _handle_path_target_root_resolve(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .resources import resolve_repo_target_root

    return resolve_repo_target_root(values.get('target'), ('pyproject.toml', 'package.json', 'Cargo.toml', '.hg'))


def _handle_verification_report_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .verification_runtime import verification_report_payload

    return verification_report_payload(changed_paths=values.get('changed_paths'), target_root=values.get('target_root'), task_text=values.get('task_text'))
