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
        'memory.adopt.lifecycle',
        'memory.bootstrap-cleanup.apply',
        'memory.capture-note.report',
        'memory.create-note.apply',
        'memory.current.report',
        'memory.doctor.report',
        'memory.init.lifecycle',
        'memory.install.lifecycle',
        'memory.list-files.report',
        'memory.list-skills.report',
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
            }),
            handlers={
                'path.target_root.resolve': _handle_path_target_root_resolve,
                'memory.bootstrap.doctor.load': _handle_memory_bootstrap_doctor_load,
                'memory.bootstrap.status.load': _handle_memory_bootstrap_status_load,
                'memory.install.apply': _handle_memory_install_apply,
                'memory.init.apply': _handle_memory_init_apply,
                'memory.adopt.apply': _handle_memory_adopt_apply,
                'memory.upgrade.apply': _handle_memory_upgrade_apply,
                'memory.migrate_layout.apply': _handle_memory_migrate_layout_apply,
                'memory.uninstall.apply': _handle_memory_uninstall_apply,
                'memory.bootstrap.cleanup': _handle_memory_bootstrap_cleanup,
                'memory.current.load': _handle_memory_current_load,
                'memory.promotion_report.load': _handle_memory_promotion_report_load,
                'memory.prompt.render': _handle_memory_prompt_render,
                'memory.report.load': _handle_memory_report_load,
                'memory.route_report.load': _handle_memory_route_report_load,
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
    from repo_memory_bootstrap.runtime_primitives import _resolve_memory_target_root

    return _resolve_memory_target_root(values, arguments, context)


def _handle_memory_bootstrap_doctor_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_bootstrap_doctor

    return _load_memory_bootstrap_doctor(values, arguments, context)


def _handle_memory_bootstrap_status_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_bootstrap_status

    return _load_memory_bootstrap_status(values, arguments, context)


def _handle_memory_install_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import install_bootstrap

    return install_bootstrap(dry_run=values.get('dry_run'), force=values.get('force'), key_repo_docs=values.get('key_repo_docs'), key_subsystems=values.get('key_subsystems'), other_key_commands=values.get('other_key_commands'), policy_profile=values.get('policy_profile'), primary_build_command=values.get('primary_build_command'), primary_test_command=values.get('primary_test_command'), project_name=values.get('project_name'), project_purpose=values.get('project_purpose'), target=values.get('target'))


def _handle_memory_init_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import install_bootstrap

    return install_bootstrap(dry_run=values.get('dry_run'), force=values.get('force'), key_repo_docs=values.get('key_repo_docs'), key_subsystems=values.get('key_subsystems'), other_key_commands=values.get('other_key_commands'), policy_profile=values.get('policy_profile'), primary_build_command=values.get('primary_build_command'), primary_test_command=values.get('primary_test_command'), project_name=values.get('project_name'), project_purpose=values.get('project_purpose'), target=values.get('target'))


def _handle_memory_adopt_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import adopt_bootstrap

    return adopt_bootstrap(apply_local_entrypoint=values.get('apply_local_entrypoint'), dry_run=values.get('dry_run'), key_repo_docs=values.get('key_repo_docs'), key_subsystems=values.get('key_subsystems'), other_key_commands=values.get('other_key_commands'), policy_profile=values.get('policy_profile'), primary_build_command=values.get('primary_build_command'), primary_test_command=values.get('primary_test_command'), project_name=values.get('project_name'), project_purpose=values.get('project_purpose'), target=values.get('target'))


def _handle_memory_upgrade_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import upgrade_bootstrap

    return upgrade_bootstrap(apply_local_entrypoint=values.get('apply_local_entrypoint'), dry_run=values.get('dry_run'), force=values.get('force'), key_repo_docs=values.get('key_repo_docs'), key_subsystems=values.get('key_subsystems'), other_key_commands=values.get('other_key_commands'), policy_profile=values.get('policy_profile'), primary_build_command=values.get('primary_build_command'), primary_test_command=values.get('primary_test_command'), project_name=values.get('project_name'), project_purpose=values.get('project_purpose'), target=values.get('target'))


def _handle_memory_migrate_layout_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import migrate_layout

    return migrate_layout(dry_run=values.get('dry_run'), target=values.get('target'))


def _handle_memory_uninstall_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import uninstall_bootstrap

    return uninstall_bootstrap(dry_run=values.get('dry_run'), key_repo_docs=values.get('key_repo_docs'), key_subsystems=values.get('key_subsystems'), other_key_commands=values.get('other_key_commands'), primary_build_command=values.get('primary_build_command'), primary_test_command=values.get('primary_test_command'), project_name=values.get('project_name'), project_purpose=values.get('project_purpose'), target=values.get('target'))


def _handle_memory_bootstrap_cleanup(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import cleanup_bootstrap_workspace

    return cleanup_bootstrap_workspace(target=values.get('target'))


def _handle_memory_current_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_current

    return _load_memory_current(values, arguments, context)


def _handle_memory_promotion_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_promotion_report

    return _load_memory_promotion_report(values, arguments, context)


def _handle_memory_prompt_render(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_prompt

    return _load_memory_prompt(values, arguments, context)


def _handle_memory_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_report

    return _load_memory_report(values, arguments, context)


def _handle_memory_route_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_route_report

    return _load_memory_route_report(values, arguments, context)


def _handle_payload_assemble(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _assemble_memory_operation_payload

    return _assemble_memory_operation_payload(values, arguments, context)


def _handle_output_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _emit_memory_operation_output

    return _emit_memory_operation_output(values, arguments, context)
