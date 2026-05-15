"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
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
        'memory.capture-note.report',
        'memory.doctor.report',
        'memory.list-files.report',
        'memory.list-skills.report',
        'memory.promotion-report.report',
        'memory.report.report',
        'memory.route-report.report',
        'memory.route.report',
        'memory.search.report',
        'memory.status.report',
        'memory.sync-memory.report'
    }:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    try:
        run_operation_steps(
            operation,
            initial_values={
                "operation_id": operation.get("id"),
                'target': getattr(args, 'target', None),
                'format': getattr(args, 'format', 'text'),
                'verbose': getattr(args, 'verbose', False),
                'strict_doc_ownership': getattr(args, 'strict_doc_ownership', False),
                'project_name': getattr(args, 'project_name', None),
                'project_purpose': getattr(args, 'project_purpose', None),
                'key_repo_docs': getattr(args, 'key_repo_docs', None),
                'key_subsystems': getattr(args, 'key_subsystems', None),
                'primary_build_command': getattr(args, 'primary_build_command', None),
                'primary_test_command': getattr(args, 'primary_test_command', None),
                'other_key_commands': getattr(args, 'other_key_commands', None),
                'notes': getattr(args, 'notes', None),
                'files': getattr(args, 'files', []),
                'surface': getattr(args, 'surface', []),
                'mode': getattr(args, 'mode', None),
                'slug': getattr(args, 'slug', ''),
                'summary': getattr(args, 'summary', ''),
                'existing_note': getattr(args, 'existing_note', ''),
                'force_new_reason': getattr(args, 'force_new_reason', ''),
                'query': getattr(args, 'query', ''),
            },
            context=PrimitiveContext(cwd=Path.cwd(), roots={
                'memory.package-payload': _handle_context_root_memory_package_payload(),
                'memory.package-skills': _handle_context_root_memory_package_skills(),
            }),
            handlers={
                'path.target_root.resolve': _handle_path_target_root_resolve,
                'memory.bootstrap.doctor.load': _handle_memory_bootstrap_doctor_load,
                'memory.bootstrap.status.load': _handle_memory_bootstrap_status_load,
                'memory.capture_note.load': _handle_memory_capture_note_load,
                'memory.promotion_report.load': _handle_memory_promotion_report_load,
                'memory.report.load': _handle_memory_report_load,
                'memory.route.load': _handle_memory_route_load,
                'memory.route_report.load': _handle_memory_route_report_load,
                'memory.search.load': _handle_memory_search_load,
                'memory.sync_memory.load': _handle_memory_sync_memory_load,
                'payload.assemble': _handle_payload_assemble,
                'output.emit': _handle_output_emit,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _handle_context_root_memory_package_payload() -> Path:
    from repo_memory_bootstrap._installer_paths import payload_root

    return payload_root()


def _handle_context_root_memory_package_skills() -> Path:
    from repo_memory_bootstrap._installer_paths import skills_root

    return skills_root()


def _handle_path_target_root_resolve(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _resolve_memory_target_root

    return _resolve_memory_target_root(values, arguments, context)


def _handle_memory_bootstrap_doctor_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _load_memory_bootstrap_doctor

    return _load_memory_bootstrap_doctor(values, arguments, context)


def _handle_memory_bootstrap_status_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _load_memory_bootstrap_status

    return _load_memory_bootstrap_status(values, arguments, context)


def _handle_memory_capture_note_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import suggest_memory_note_capture

    return suggest_memory_note_capture(existing_note=values.get('existing_note'), files=values.get('files'), force_new_reason=values.get('force_new_reason'), slug=values.get('slug'), summary=values.get('summary'), surfaces=values.get('surface'), target=values.get('target'))


def _handle_memory_promotion_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _load_memory_promotion_report

    return _load_memory_promotion_report(values, arguments, context)


def _handle_memory_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _load_memory_report

    return _load_memory_report(values, arguments, context)


def _handle_memory_route_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import route_memory

    return route_memory(files=values.get('files'), surfaces=values.get('surface'), target=values.get('target'))


def _handle_memory_route_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _load_memory_route_report

    return _load_memory_route_report(values, arguments, context)


def _handle_memory_search_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import search_memory

    return search_memory(query=values.get('query'), target=values.get('target'))


def _handle_memory_sync_memory_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import sync_memory

    return sync_memory(files=values.get('files'), notes=values.get('notes'), target=values.get('target'))


def _handle_payload_assemble(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _assemble_memory_operation_payload

    return _assemble_memory_operation_payload(values, arguments, context)


def _handle_output_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime_cli import _emit_memory_operation_output

    return _emit_memory_operation_output(values, arguments, context)
