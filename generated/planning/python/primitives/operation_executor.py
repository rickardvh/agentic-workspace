"""Generated Python operation IR executor.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
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
                'audit_cursor': getattr(args, 'audit_cursor', ''),
                'audit_page_size': getattr(args, 'audit_page_size', 25),
                'task': getattr(args, 'task', None),
                'changed': getattr(args, 'changed', []),
                'apply_safe_prune': getattr(args, 'apply_safe_prune', False),
                'dry_run': getattr(args, 'dry_run', False),
                'lane': getattr(args, 'lane', ''),
                'apply_lane_reconcile': getattr(args, 'apply_lane_reconcile', False),
                'item': getattr(args, 'item', ''),
                'reason': getattr(args, 'reason', ''),
                'owner': getattr(args, 'owner', ''),
                'owner_ref': getattr(args, 'owner_ref', ''),
                'mode': getattr(args, 'mode', 'local'),
                'current_work_id': getattr(args, 'current_work_id', ''),
                'expect_current_work_revision': getattr(args, 'expect_current_work_revision', ''),
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
                'artifact': getattr(args, 'artifact', ''),
                'activate': getattr(args, 'activate', False),
                'queue': getattr(args, 'queue', False),
                'switch_active': getattr(args, 'switch_active', False),
                'prep_only': getattr(args, 'prep_only', False),
                'overwrite': getattr(args, 'overwrite', False),
                'remove_source': getattr(args, 'remove_source', False),
                'item_id': getattr(args, 'item_id', ''),
                'plan_slug': getattr(args, 'plan_slug', None),
                'lane': getattr(args, 'lane', ''),
                'parent_decomposition': getattr(args, 'parent_decomposition', ''),
                'outcome': getattr(args, 'outcome', ''),
                'promotion_rule': getattr(args, 'promotion_rule', ''),
                'purpose': getattr(args, 'purpose', ''),
                'proof_strategy': getattr(args, 'proof_strategy', ''),
                'current_slice': getattr(args, 'current_slice', ''),
                'proof': getattr(args, 'proof', ''),
                'residual_work': getattr(args, 'residual_work', ''),
                'parent_contribution': getattr(args, 'parent_contribution', ''),
                'parent_close_permission': getattr(args, 'parent_close_permission', 'may-advance-parent'),
                'next_owner': getattr(args, 'next_owner', ''),
                'plan': getattr(args, 'plan', None),
                'apply_cleanup': getattr(args, 'apply_cleanup', False),
                'prepare_closeout': getattr(args, 'prepare_closeout', False),
                'retain_archive': getattr(args, 'retain_archive', False),
                'decision_point_carry_key': getattr(args, 'decision_point_carry_key', ''),
                'prune_decision_point_carry_key': getattr(args, 'prune_decision_point_carry_key', ''),
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
                'claim_level': getattr(args, 'claim_level', 'slice'),
                'intent_status': getattr(args, 'intent_status', 'satisfied'),
                'residue': getattr(args, 'residue', 'none'),
                'proof_from': getattr(args, 'proof_from', 'last'),
                'proof_file': getattr(args, 'proof_file', None),
                'residue_owner': getattr(args, 'residue_owner', None),
                'what_happened': getattr(args, 'what_happened', None),
                'scope_touched': getattr(args, 'scope_touched', None),
                'changed_surfaces': getattr(args, 'changed_surfaces', None),
                'review_summary': getattr(args, 'review_summary', None),
                'outcome_summary': getattr(args, 'outcome_summary', None),
                'discard_archive': getattr(args, 'discard_archive', False),
                'route': getattr(args, 'route', ''),
                'skipped_reason': getattr(args, 'skipped_reason', ''),
                'expected_savings': getattr(args, 'expected_savings', ''),
                'actual_friction': getattr(args, 'actual_friction', ''),
                'proof_result': getattr(args, 'proof_result', ''),
                'quality_concern': getattr(args, 'quality_concern', ''),
                'decomposition_adjustment': getattr(args, 'decomposition_adjustment', ''),
                'expect_planning_revision': getattr(args, 'expect_planning_revision', ''),
                'paths': getattr(args, 'paths', []),
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
                'audit_cursor': values.get('audit_cursor', ''),
                'audit_page_size': values.get('audit_page_size', 25),
                'task': values.get('task', None),
                'changed': values.get('changed', []),
                'apply_safe_prune': values.get('apply_safe_prune', False),
                'dry_run': values.get('dry_run', False),
                'lane': values.get('lane', ''),
                'apply_lane_reconcile': values.get('apply_lane_reconcile', False),
                'item': values.get('item', ''),
                'reason': values.get('reason', ''),
                'owner': values.get('owner', ''),
                'owner_ref': values.get('owner_ref', ''),
                'mode': values.get('mode', 'local'),
                'current_work_id': values.get('current_work_id', ''),
                'expect_current_work_revision': values.get('expect_current_work_revision', ''),
                'issue': values.get('issue', ''),
                'slug': values.get('slug', ''),
                'title': values.get('title', ''),
                'scope': values.get('scope', None),
                'classification': values.get('classification', 'review'),
                'render_markdown': values.get('render_markdown', False),
                'prompt_command': values.get('prompt_command', ''),
                'force': values.get('force', False),
                'local': values.get('local', False),
                'include_optional': values.get('include_optional', False),
                'id': values.get('id', ''),
                'source': values.get('source', ''),
                'artifact': values.get('artifact', ''),
                'activate': values.get('activate', False),
                'queue': values.get('queue', False),
                'switch_active': values.get('switch_active', False),
                'prep_only': values.get('prep_only', False),
                'overwrite': values.get('overwrite', False),
                'remove_source': values.get('remove_source', False),
                'item_id': values.get('item_id', ''),
                'plan_slug': values.get('plan_slug', None),
                'lane': values.get('lane', ''),
                'parent_decomposition': values.get('parent_decomposition', ''),
                'outcome': values.get('outcome', ''),
                'promotion_rule': values.get('promotion_rule', ''),
                'purpose': values.get('purpose', ''),
                'proof_strategy': values.get('proof_strategy', ''),
                'current_slice': values.get('current_slice', ''),
                'proof': values.get('proof', ''),
                'residual_work': values.get('residual_work', ''),
                'parent_contribution': values.get('parent_contribution', ''),
                'parent_close_permission': values.get('parent_close_permission', 'may-advance-parent'),
                'next_owner': values.get('next_owner', ''),
                'plan': values.get('plan', None),
                'apply_cleanup': values.get('apply_cleanup', False),
                'prepare_closeout': values.get('prepare_closeout', False),
                'retain_archive': values.get('retain_archive', False),
                'decision_point_carry_key': values.get('decision_point_carry_key', ''),
                'prune_decision_point_carry_key': values.get('prune_decision_point_carry_key', ''),
                'parent_lane_closeout': values.get('parent_lane_closeout', None),
                'closure_decision': values.get('closure_decision', None),
                'intent_satisfied': values.get('intent_satisfied', None),
                'unsolved_intent': values.get('unsolved_intent', None),
                'intent_evidence': values.get('intent_evidence', None),
                'closure_reason': values.get('closure_reason', None),
                'closure_evidence': values.get('closure_evidence', None),
                'reopen_trigger': values.get('reopen_trigger', None),
                'discard_summary': values.get('discard_summary', None),
                'continuation_summary': values.get('continuation_summary', None),
                'claim_level': values.get('claim_level', 'slice'),
                'intent_status': values.get('intent_status', 'satisfied'),
                'residue': values.get('residue', 'none'),
                'proof_from': values.get('proof_from', 'last'),
                'proof_file': values.get('proof_file', None),
                'residue_owner': values.get('residue_owner', None),
                'what_happened': values.get('what_happened', None),
                'scope_touched': values.get('scope_touched', None),
                'changed_surfaces': values.get('changed_surfaces', None),
                'review_summary': values.get('review_summary', None),
                'outcome_summary': values.get('outcome_summary', None),
                'discard_archive': values.get('discard_archive', False),
                'route': values.get('route', ''),
                'skipped_reason': values.get('skipped_reason', ''),
                'expected_savings': values.get('expected_savings', ''),
                'actual_friction': values.get('actual_friction', ''),
                'proof_result': values.get('proof_result', ''),
                'quality_concern': values.get('quality_concern', ''),
                'decomposition_adjustment': values.get('decomposition_adjustment', ''),
                'expect_planning_revision': values.get('expect_planning_revision', ''),
                'paths': values.get('paths', []),
            },
        ).get('result')
    return result


def run_operation_values(operation: dict[str, Any], *, initial_values: Mapping[str, Any]) -> dict[str, Any]:
    if operation.get("id") not in {
        'planning.adopt.lifecycle',
        'planning.archive-plan.lifecycle',
        'planning.close-item.lifecycle',
        'planning.closeout.lifecycle',
        'planning.create-review.lifecycle',
        'planning.decomposition-create.lifecycle',
        'planning.delegation-decision.lifecycle',
        'planning.doctor.report',
        'planning.handoff.report',
        'planning.init.lifecycle',
        'planning.install.lifecycle',
        'planning.intake-artifact.lifecycle',
        'planning.lane-activate.lifecycle',
        'planning.lane-archive.lifecycle',
        'planning.lane-close.lifecycle',
        'planning.lane-create.lifecycle',
        'planning.lane-promote.lifecycle',
        'planning.list-files.report',
        'planning.new-plan.lifecycle',
        'planning.owner-select.lifecycle',
        'planning.promote-to-plan.lifecycle',
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
        return run_operation_steps(
            operation,
            initial_values=dict(initial_values),
            context=PrimitiveContext(cwd=Path.cwd(), roots={
                'planning.package-payload': _handle_context_root_planning_package_payload(),
                'planning.package-skills': _handle_context_root_planning_package_skills(),
            }),
            handlers={
                'planning.report.load': _handle_planning_report_load,
                'planning.summary.load': _handle_planning_summary_load,
                'planning.reconcile.load': _handle_planning_reconcile_load,
                'planning.prompt.render': _handle_planning_prompt_render,
                'planning.new-plan.apply': _handle_planning_new_plan_apply,
                'planning.intake-artifact.apply': _handle_planning_intake_artifact_apply,
                'planning.promote-to-plan.apply': _handle_planning_promote_to_plan_apply,
                'planning.lane-create.apply': _handle_planning_lane_create_apply,
                'planning.decomposition-create.apply': _handle_planning_decomposition_create_apply,
                'planning.lane-promote.apply': _handle_planning_lane_promote_apply,
                'planning.lane-activate.apply': _handle_planning_lane_activate_apply,
                'planning.lane-close.apply': _handle_planning_lane_close_apply,
                'planning.owner-select.apply': _handle_planning_owner_select_apply,
                'planning.lane-archive.apply': _handle_planning_lane_archive_apply,
                'planning.archive-plan.apply': _handle_planning_archive_plan_apply,
                'planning.closeout.apply': _handle_planning_closeout_apply,
                'planning.delegation-decision.apply': _handle_planning_delegation_decision_apply,
                'planning.adopt.apply': _handle_planning_adopt_apply,
                'planning.close-item.apply': _handle_planning_close_item_apply,
                'planning.create-review.apply': _handle_planning_create_review_apply,
                'planning.bootstrap.doctor.load': _handle_planning_bootstrap_doctor_load,
                'planning.handoff.load': _handle_planning_handoff_load,
                'planning.init.apply': _handle_planning_init_apply,
                'planning.install.apply': _handle_planning_install_apply,
                'planning.bootstrap.status.load': _handle_planning_bootstrap_status_load,
                'planning.uninstall.apply': _handle_planning_uninstall_apply,
                'planning.upgrade.apply': _handle_planning_upgrade_apply,
                'planning.verify-payload.load': _handle_planning_verify_payload_load,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc


def _handle_context_root_planning_package_payload() -> Path:
    from .resources import find_resource_root

    return find_resource_root(__file__, [('_payload', 'AGENTS.template.md')])


def _handle_context_root_planning_package_skills() -> Path:
    from .resources import find_resource_root

    return find_resource_root(__file__, [('_skills', 'REGISTRY.json')])


def _handle_planning_report_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import load_planning_report_operation

    return load_planning_report_operation(values, arguments, context)


def _handle_planning_summary_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import load_planning_summary_operation

    return load_planning_summary_operation(values, arguments, context)


def _handle_planning_reconcile_load(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import load_planning_reconcile_operation

    return load_planning_reconcile_operation(values, arguments, context)


def _handle_planning_prompt_render(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import render_planning_prompt_operation

    return render_planning_prompt_operation(values, arguments, context)


def _handle_planning_new_plan_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_new_plan_operation

    return apply_planning_new_plan_operation(values, arguments, context)


def _handle_planning_intake_artifact_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_intake_artifact_operation

    return apply_planning_intake_artifact_operation(values, arguments, context)


def _handle_planning_promote_to_plan_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_promote_to_plan_operation

    return apply_planning_promote_to_plan_operation(values, arguments, context)


def _handle_planning_lane_create_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_lane_create_operation

    return apply_planning_lane_create_operation(values, arguments, context)


def _handle_planning_decomposition_create_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_decomposition_create_operation

    return apply_planning_decomposition_create_operation(values, arguments, context)


def _handle_planning_lane_promote_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_lane_promote_operation

    return apply_planning_lane_promote_operation(values, arguments, context)


def _handle_planning_lane_activate_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_lane_activate_operation

    return apply_planning_lane_activate_operation(values, arguments, context)


def _handle_planning_lane_close_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_lane_close_operation

    return apply_planning_lane_close_operation(values, arguments, context)


def _handle_planning_owner_select_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_owner_select_operation

    return apply_planning_owner_select_operation(values, arguments, context)


def _handle_planning_lane_archive_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_lane_archive_operation

    return apply_planning_lane_archive_operation(values, arguments, context)


def _handle_planning_archive_plan_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_archive_plan_operation

    return apply_planning_archive_plan_operation(values, arguments, context)


def _handle_planning_closeout_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_closeout_operation

    return apply_planning_closeout_operation(values, arguments, context)


def _handle_planning_delegation_decision_apply(values: dict[str, Any], arguments: dict[str, Any], context: PrimitiveContext) -> Any:
    from .planning_runtime import apply_planning_delegation_decision_operation

    return apply_planning_delegation_decision_operation(values, arguments, context)


def _handle_planning_adopt_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import adopt_bootstrap

    return adopt_bootstrap(dry_run=values.get('dry_run'), include_optional=values.get('include_optional'), target=values.get('target'))


def _handle_planning_close_item_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import close_planning_item

    return close_planning_item(dry_run=values.get('dry_run'), expected_planning_revision=values.get('expect_planning_revision'), issue=values.get('issue'), item=values.get('item'), reason=values.get('reason'), target=values.get('target'))


def _handle_planning_create_review_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import create_review_record

    return create_review_record(classification=values.get('classification'), dry_run=values.get('dry_run'), render_markdown=values.get('render_markdown'), scope=values.get('scope'), slug=values.get('slug'), target=values.get('target'), title=values.get('title'))


def _handle_planning_bootstrap_doctor_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import doctor_bootstrap

    return doctor_bootstrap(target=values.get('target'))


def _handle_planning_handoff_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import planning_handoff

    return planning_handoff(target=values.get('target'))


def _handle_planning_init_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import install_bootstrap

    return install_bootstrap(dry_run=values.get('dry_run'), force=values.get('force'), include_optional=values.get('include_optional'), local_only=values.get('local'), target=values.get('target'))


def _handle_planning_install_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import install_bootstrap

    return install_bootstrap(dry_run=values.get('dry_run'), force=values.get('force'), include_optional=values.get('include_optional'), local_only=values.get('local'), target=values.get('target'))


def _handle_planning_bootstrap_status_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import collect_status

    return collect_status(target=values.get('target'))


def _handle_planning_uninstall_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import uninstall_bootstrap

    return uninstall_bootstrap(dry_run=values.get('dry_run'), target=values.get('target'))


def _handle_planning_upgrade_apply(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import upgrade_bootstrap

    return upgrade_bootstrap(dry_run=values.get('dry_run'), include_optional=values.get('include_optional'), target=values.get('target'))


def _handle_planning_verify_payload_load(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> Any:
    from .planning_installer import verify_payload

    return verify_payload()
