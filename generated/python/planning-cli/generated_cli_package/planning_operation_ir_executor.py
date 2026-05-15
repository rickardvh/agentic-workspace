"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
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
        'planning.adopt.lifecycle',
        'planning.close-item.lifecycle',
        'planning.create-review.lifecycle',
        'planning.doctor.report',
        'planning.handoff.report',
        'planning.init.lifecycle',
        'planning.install.lifecycle',
        'planning.list-files.report',
        'planning.prompt.render',
        'planning.reconcile.report',
        'planning.report.report',
        'planning.status.report',
        'planning.summary.report',
        'planning.uninstall.lifecycle',
        'planning.upgrade.lifecycle',
        'planning.verify-payload.report'
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
                'task': getattr(args, 'task', None),
                'changed': getattr(args, 'changed', []),
                'apply_safe_prune': getattr(args, 'apply_safe_prune', False),
                'dry_run': getattr(args, 'dry_run', False),
                'item': getattr(args, 'item', ''),
                'reason': getattr(args, 'reason', ''),
                'issue': getattr(args, 'issue', ''),
                'slug': getattr(args, 'slug', ''),
                'title': getattr(args, 'title', ''),
                'scope': getattr(args, 'scope', None),
                'classification': getattr(args, 'classification', 'review'),
                'render_markdown': getattr(args, 'render_markdown', False),
                'prompt_command': getattr(args, 'prompt_command', ''),
                'force': getattr(args, 'force', False),
                'local': getattr(args, 'local', False),
                'include_optional': getattr(args, 'include_optional', False),
            },
            context=PrimitiveContext(cwd=Path.cwd(), roots={}),
            handlers={
                'planning.bootstrap.doctor.load': _handle_planning_bootstrap_doctor_load,
                'planning.report.load': _handle_planning_report_load,
                'planning.summary.load': _handle_planning_summary_load,
                'planning.reconcile.load': _handle_planning_reconcile_load,
                'planning.bootstrap.status.load': _handle_planning_bootstrap_status_load,
                'planning.handoff.load': _handle_planning_handoff_load,
                'planning.verify-payload.load': _handle_planning_verify_payload_load,
                'planning.close-item.apply': _handle_planning_close_item_apply,
                'planning.create-review.apply': _handle_planning_create_review_apply,
                'output.emit': _handle_output_emit,
                'planning.list-files.load': _handle_planning_list_files_load,
                'planning.prompt.render': _handle_planning_prompt_render,
                'planning.install.apply': _handle_planning_install_apply,
                'planning.init.apply': _handle_planning_init_apply,
                'planning.adopt.apply': _handle_planning_adopt_apply,
                'planning.upgrade.apply': _handle_planning_upgrade_apply,
                'planning.uninstall.apply': _handle_planning_uninstall_apply,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _handle_planning_bootstrap_doctor_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import doctor_bootstrap

    return doctor_bootstrap(target=values.get('target'))


def _handle_planning_report_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    if values.get('verbose'):
        from repo_planning_bootstrap.installer import planning_report

        return planning_report(target=values.get('target'))
    from repo_planning_bootstrap.installer import planning_report_tiny

    return planning_report_tiny(target=values.get('target'))


def _handle_planning_summary_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import load_planning_summary_operation

    return load_planning_summary_operation(values, arguments, context)


def _handle_planning_reconcile_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import load_planning_reconcile_operation

    return load_planning_reconcile_operation(values, arguments, context)


def _handle_planning_bootstrap_status_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import collect_status

    return collect_status(target=values.get('target'))


def _handle_planning_handoff_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import planning_handoff

    return planning_handoff(target=values.get('target'))


def _handle_planning_verify_payload_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import verify_payload

    return verify_payload()


def _handle_planning_close_item_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import close_planning_item

    return close_planning_item(dry_run=values.get('dry_run'), issue=values.get('issue'), item=values.get('item'), reason=values.get('reason'), target=values.get('target'))


def _handle_planning_create_review_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import create_review_record

    return create_review_record(classification=values.get('classification'), dry_run=values.get('dry_run'), render_markdown=values.get('render_markdown'), scope=values.get('scope'), slug=values.get('slug'), target=values.get('target'), title=values.get('title'))


def _handle_output_emit(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import emit_planning_operation_output

    return emit_planning_operation_output(values, arguments, context)


def _handle_planning_list_files_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import load_planning_list_files_operation

    return load_planning_list_files_operation(values, arguments, context)


def _handle_planning_prompt_render(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import render_planning_prompt_operation

    return render_planning_prompt_operation(values, arguments, context)


def _handle_planning_install_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import install_bootstrap

    return install_bootstrap(dry_run=values.get('dry_run'), force=values.get('force'), include_optional=values.get('include_optional'), local_only=values.get('local'), target=values.get('target'))


def _handle_planning_init_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import install_bootstrap

    return install_bootstrap(dry_run=values.get('dry_run'), force=values.get('force'), include_optional=values.get('include_optional'), local_only=values.get('local'), target=values.get('target'))


def _handle_planning_adopt_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import adopt_bootstrap

    return adopt_bootstrap(dry_run=values.get('dry_run'), include_optional=values.get('include_optional'), target=values.get('target'))


def _handle_planning_upgrade_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import upgrade_bootstrap

    return upgrade_bootstrap(dry_run=values.get('dry_run'), include_optional=values.get('include_optional'), target=values.get('target'))


def _handle_planning_uninstall_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.installer import uninstall_bootstrap

    return uninstall_bootstrap(dry_run=values.get('dry_run'), target=values.get('target'))
