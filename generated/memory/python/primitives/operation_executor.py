"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
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
                'task': getattr(args, 'task', ''),
                'stage': getattr(args, 'stage', ''),
                'mode': getattr(args, 'mode', None),
                'slug': getattr(args, 'slug', ''),
                'title': getattr(args, 'title', None),
                'folder': getattr(args, 'folder', 'domains'),
                'note_type': getattr(args, 'note_type', 'domain'),
                'local': getattr(args, 'local', False),
                'local_reason': getattr(args, 'local_reason', ''),
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
                'format': values.get('format', 'text'),
                'verbose': values.get('verbose', False),
                'strict_doc_ownership': values.get('strict_doc_ownership', False),
                'project_name': values.get('project_name', None),
                'project_purpose': values.get('project_purpose', None),
                'key_repo_docs': values.get('key_repo_docs', None),
                'key_subsystems': values.get('key_subsystems', None),
                'primary_build_command': values.get('primary_build_command', None),
                'primary_test_command': values.get('primary_test_command', None),
                'other_key_commands': values.get('other_key_commands', None),
                'notes': values.get('notes', None),
                'files': values.get('files', []),
                'surface': values.get('surface', []),
                'task': values.get('task', ''),
                'stage': values.get('stage', ''),
                'mode': values.get('mode', None),
                'slug': values.get('slug', ''),
                'title': values.get('title', None),
                'folder': values.get('folder', 'domains'),
                'note_type': values.get('note_type', 'domain'),
                'local': values.get('local', False),
                'local_reason': values.get('local_reason', ''),
                'applies_to': values.get('applies_to', []),
                'use_when': values.get('use_when', []),
                'routes_from': values.get('routes_from', []),
                'stale_when': values.get('stale_when', []),
                'evidence': values.get('evidence', []),
                'memory_role': values.get('memory_role', ''),
                'promotion_target': values.get('promotion_target', ''),
                'promotion_trigger': values.get('promotion_trigger', ''),
                'retention_after_promotion': values.get('retention_after_promotion', ''),
                'dry_run': values.get('dry_run', False),
                'policy_profile': values.get('policy_profile', 'default'),
                'apply_local_entrypoint': values.get('apply_local_entrypoint', False),
                'force': values.get('force', False),
                'summary': values.get('summary', ''),
                'existing_note': values.get('existing_note', ''),
                'force_new_reason': values.get('force_new_reason', ''),
                'query': values.get('query', ''),
                'current_command': values.get('current_command', 'show'),
                'prompt_command': values.get('prompt_command', 'install'),
            },
        ).get('result')
    return result


def run_operation_values(operation: dict[str, Any], *, initial_values: Mapping[str, Any]) -> dict[str, Any]:
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
        return run_operation_steps(
            operation,
            initial_values=dict(initial_values),
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
                'memory.promotion_report.load': _handle_memory_promotion_report_load,
                'memory.report.load': _handle_memory_report_load,
                'memory.route_report.load': _handle_memory_route_report_load,
                'memory.install.apply': _handle_memory_install_apply,
                'memory.init.apply': _handle_memory_init_apply,
                'memory.adopt.apply': _handle_memory_adopt_apply,
                'memory.upgrade.apply': _handle_memory_upgrade_apply,
                'memory.migrate_layout.apply': _handle_memory_migrate_layout_apply,
                'memory.uninstall.apply': _handle_memory_uninstall_apply,
                'memory.bootstrap.cleanup': _handle_memory_bootstrap_cleanup,
                'memory.capture_note.load': _handle_memory_capture_note_load,
                'memory.note.create': _handle_memory_note_create,
                'memory.route.load': _handle_memory_route_load,
                'memory.sync_memory.load': _handle_memory_sync_memory_load,
                'memory.route_review.load': _handle_memory_route_review_load,
                'memory.search.load': _handle_memory_search_load,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc


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


def _handle_memory_promotion_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_promotion_report

    return _load_memory_promotion_report(values, arguments, context)


def _handle_memory_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_report

    return _load_memory_report(values, arguments, context)


def _handle_memory_route_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .memory_runtime import _load_memory_route_report

    return _load_memory_route_report(values, arguments, context)


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


def _handle_memory_capture_note_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import suggest_memory_note_capture

    return suggest_memory_note_capture(existing_note=values.get('existing_note'), files=values.get('files'), force_new_reason=values.get('force_new_reason'), slug=values.get('slug'), stage=values.get('stage'), summary=values.get('summary'), surfaces=values.get('surface'), target=values.get('target'), task=values.get('task'))


def _handle_memory_note_create(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import create_memory_note

    return create_memory_note(applies_to=values.get('applies_to'), dry_run=values.get('dry_run'), evidence=values.get('evidence'), folder=values.get('folder'), local=values.get('local'), local_reason=values.get('local_reason'), memory_role=values.get('memory_role'), note_type=values.get('note_type'), promotion_target=values.get('promotion_target'), promotion_trigger=values.get('promotion_trigger'), retention_after_promotion=values.get('retention_after_promotion'), routes_from=values.get('routes_from'), slug=values.get('slug'), stale_when=values.get('stale_when'), summary=values.get('summary'), target=values.get('target'), title=values.get('title'), use_when=values.get('use_when'))


def _handle_memory_route_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import route_memory

    return route_memory(files=values.get('files'), stage=values.get('stage'), surfaces=values.get('surface'), target=values.get('target'), task=values.get('task'))


def _handle_memory_sync_memory_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import sync_memory

    return sync_memory(files=values.get('files'), notes=values.get('notes'), target=values.get('target'))


def _handle_memory_route_review_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.installer import review_routes

    return review_routes(target=values.get('target'))


def _handle_memory_search_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_memory_bootstrap.runtime_search import search_memory

    return search_memory(query=values.get('query'), target=values.get('target'))
