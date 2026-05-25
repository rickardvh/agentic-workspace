"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
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
    if operation.get("id") not in {
        'memory.adopt.lifecycle',
        'memory.bootstrap-cleanup.apply',
        'memory.capture-note.report',
        'memory.create-note.apply',
        'memory.current.report',
        'memory.doctor.report',
        'memory.init.lifecycle',
        'memory.install.lifecycle',
        'memory.migrate-layout.lifecycle',
        'memory.promotion-report.report',
        'memory.prompt.render',
        'memory.report.report',
        'memory.route-report.report',
        'memory.route-review.report',
        'memory.route.report',
        'memory.search.report',
        'memory.status.report',
        'memory.sync-memory.report',
        'memory.uninstall.lifecycle',
        'memory.upgrade.lifecycle',
        'memory.verify-payload.report'
    }:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    try:
        values = run_operation_steps(
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
                'title': getattr(args, 'title', None),
                'folder': getattr(args, 'folder', 'domains'),
                'note_type': getattr(args, 'note_type', 'domain'),
                'applies_to': getattr(args, 'applies_to', []),
                'use_when': getattr(args, 'use_when', []),
                'routes_from': getattr(args, 'routes_from', []),
                'stale_when': getattr(args, 'stale_when', []),
                'evidence': getattr(args, 'evidence', []),
                'memory_role': getattr(args, 'memory_role', ''),
                'promotion_target': getattr(args, 'promotion_target', ''),
                'promotion_trigger': getattr(args, 'promotion_trigger', ''),
                'retention_after_promotion': getattr(args, 'retention_after_promotion', ''),
                'dry_run': getattr(args, 'dry_run', False),
                'policy_profile': getattr(args, 'policy_profile', 'default'),
                'apply_local_entrypoint': getattr(args, 'apply_local_entrypoint', False),
                'force': getattr(args, 'force', False),
                'summary': getattr(args, 'summary', ''),
                'existing_note': getattr(args, 'existing_note', ''),
                'force_new_reason': getattr(args, 'force_new_reason', ''),
                'query': getattr(args, 'query', ''),
                'current_command': getattr(args, 'current_command', 'show'),
                'prompt_command': getattr(args, 'prompt_command', 'install'),
            },
            context=PrimitiveContext(cwd=Path.cwd(), roots={
                'memory.package-payload': _handle_context_root_memory_package_payload(),
                'memory.package-skills': _handle_context_root_memory_package_skills(),
                'memory.contracts': _handle_context_root_memory_contracts(),
            }),
            handlers={
                'path.target_root.resolve': _handle_path_target_root_resolve,
                'memory.bootstrap.doctor.load': _handle_memory_bootstrap_doctor_load,
                'memory.current.load': _handle_memory_current_load,
                'memory.prompt.render': _handle_memory_prompt_render,
                'memory.report.load': _handle_memory_report_load,
                'memory.route_report.load': _handle_memory_route_report_load,
                'output.emit': _handle_output_emit,
            },
        )
        emitted = values.get('emitted')
        if isinstance(emitted, str):
            print(emitted, end='')
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _handle_context_root_memory_package_payload() -> Path:
    from .resources import find_resource_root

    return find_resource_root(__file__, [('_payload', 'AGENTS.template.md')])


def _handle_context_root_memory_package_skills() -> Path:
    from .resources import find_resource_root

    return find_resource_root(__file__, [('_skills', 'REGISTRY.json')])


def _handle_context_root_memory_contracts() -> Path:
    from .resources import find_resource_root

    return find_resource_root(__file__, [('_contracts', 'payload_verification.memory.json')])


def _handle_path_target_root_resolve(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .resources import resolve_repo_target_root

    return resolve_repo_target_root(values.get('target'), ('pyproject.toml', 'package.json', 'Cargo.toml', '.hg'))


def _handle_memory_bootstrap_doctor_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_bootstrap_doctor

    return _load_memory_bootstrap_doctor(values, arguments, context)


def _handle_memory_current_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_current

    return _load_memory_current(values, arguments, context)


def _handle_memory_prompt_render(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_prompt

    return _load_memory_prompt(values, arguments, context)


def _handle_memory_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_report

    return _load_memory_report(values, arguments, context)


def _handle_memory_route_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_route_report

    return _load_memory_route_report(values, arguments, context)


def _handle_output_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _emit_memory_operation_output

    return _emit_memory_operation_output(values, arguments, context)
