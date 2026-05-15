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
        'planning.archive-plan.lifecycle',
        'planning.close-item.lifecycle',
        'planning.create-review.lifecycle',
        'planning.delegation-decision.lifecycle',
        'planning.doctor.report',
        'planning.handoff.report',
        'planning.init.lifecycle',
        'planning.install.lifecycle',
        'planning.list-files.report',
        'planning.new-plan.lifecycle',
        'planning.promote-to-plan.lifecycle',
        'planning.prompt.render',
        'planning.reconcile.report',
        'planning.record-recovery.lifecycle',
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
                'id': getattr(args, 'id', ''),
                'source': getattr(args, 'source', ''),
                'activate': getattr(args, 'activate', False),
                'queue': getattr(args, 'queue', False),
                'switch_active': getattr(args, 'switch_active', False),
                'prep_only': getattr(args, 'prep_only', False),
                'overwrite': getattr(args, 'overwrite', False),
                'item_id': getattr(args, 'item_id', ''),
                'plan_slug': getattr(args, 'plan_slug', None),
                'plan': getattr(args, 'plan', None),
                'apply_cleanup': getattr(args, 'apply_cleanup', False),
                'prepare_closeout': getattr(args, 'prepare_closeout', False),
                'retain_archive': getattr(args, 'retain_archive', False),
                'parent_lane_closeout': getattr(args, 'parent_lane_closeout', None),
                'closure_decision': getattr(args, 'closure_decision', None),
                'intent_satisfied': getattr(args, 'intent_satisfied', None),
                'unsolved_intent': getattr(args, 'unsolved_intent', None),
                'intent_evidence': getattr(args, 'intent_evidence', None),
                'closure_reason': getattr(args, 'closure_reason', None),
                'closure_evidence': getattr(args, 'closure_evidence', None),
                'reopen_trigger': getattr(args, 'reopen_trigger', None),
                'discard_summary': getattr(args, 'discard_summary', None),
                'continuation_summary': getattr(args, 'continuation_summary', None),
                'route': getattr(args, 'route', ''),
                'skipped_reason': getattr(args, 'skipped_reason', ''),
                'expected_savings': getattr(args, 'expected_savings', ''),
                'actual_friction': getattr(args, 'actual_friction', ''),
                'proof_result': getattr(args, 'proof_result', ''),
                'quality_concern': getattr(args, 'quality_concern', ''),
                'decomposition_adjustment': getattr(args, 'decomposition_adjustment', ''),
                'paths': getattr(args, 'paths', []),
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
                'planning.new-plan.apply': _handle_planning_new_plan_apply,
                'planning.promote-to-plan.apply': _handle_planning_promote_to_plan_apply,
                'planning.archive-plan.apply': _handle_planning_archive_plan_apply,
                'planning.delegation-decision.apply': _handle_planning_delegation_decision_apply,
                'planning.record-recovery.apply': _handle_planning_record_recovery_apply,
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


def _handle_planning_new_plan_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_new_plan_operation

    return apply_planning_new_plan_operation(values, arguments, context)


def _handle_planning_promote_to_plan_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_promote_to_plan_operation

    return apply_planning_promote_to_plan_operation(values, arguments, context)


def _handle_planning_archive_plan_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_archive_plan_operation

    return apply_planning_archive_plan_operation(values, arguments, context)


def _handle_planning_delegation_decision_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_delegation_decision_operation

    return apply_planning_delegation_decision_operation(values, arguments, context)


def _handle_planning_record_recovery_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_record_recovery_operation

    return apply_planning_record_recovery_operation(values, arguments, context)
