"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: proof.report
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse

from typing import Any
from collections.abc import Mapping

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py



def run(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _diagnostic_profile, _module_operations, _resolve_target_root, _validate_descriptor_contract, _validate_target_root
    _arg_0_format_name = getattr(args, 'format', None)
    _arg_1_target_root = _resolve_target_root(getattr(args, 'target', None))
    if _arg_1_target_root is None:
        raise ValueError('target root resolution returned None')
    _validate_target_root(command_name='proof', target_root=_arg_1_target_root)
    _arg_2_descriptors = _module_operations()
    _validate_descriptor_contract(_arg_2_descriptors)
    _arg_3_route = getattr(args, 'route', None)
    _arg_4_current_only = bool(getattr(args, 'current', False))
    _arg_5_changed_paths = list(getattr(args, 'changed', []) or [])
    _arg_6_task_text = getattr(args, 'task', None)
    _arg_7_profile = _diagnostic_profile(args, default='tiny')
    _arg_8_select = getattr(args, 'select', None)
    _arg_9_execute_selected = bool(getattr(args, 'execute_selected', False))
    _arg_10_proof_run_id = getattr(args, 'proof_run_id', '')
    _arg_11_proof_timeout_seconds = getattr(args, 'proof_timeout_seconds', '600')
    _arg_12_proof_cancel_file = getattr(args, 'proof_cancel_file', '')
    _arg_13_record_receipt = bool(getattr(args, 'record_receipt', False))
    _arg_14_receipt_command = getattr(args, 'receipt_command', '')
    _arg_15_receipt_result = getattr(args, 'receipt_result', '')
    _arg_16_receipt_plan = getattr(args, 'receipt_plan', '')
    _arg_17_receipt_log = getattr(args, 'receipt_log', '')
    _arg_18_receipt_route_id = getattr(args, 'receipt_route_id', '')
    _arg_19_receipt_command_id = getattr(args, 'receipt_command_id', '')
    _arg_20_receipt_duration_seconds = getattr(args, 'receipt_duration_seconds', '')
    _arg_21_receipt_timeout = bool(getattr(args, 'receipt_timeout', False))
    _arg_22_receipt_exit_state = getattr(args, 'receipt_exit_state', '')
    _arg_23_receipt_environment = getattr(args, 'receipt_environment', '')
    _arg_24_receipt_claim_sufficiency = getattr(args, 'receipt_claim_sufficiency', '')
    _arg_25_receipt_route_budget_seconds = getattr(args, 'receipt_route_budget_seconds', '')
    _arg_26_receipt_repair_finding_id = getattr(args, 'receipt_repair_finding_id', '')
    _arg_27_receipt_repair_authority_revision = getattr(args, 'receipt_repair_authority_revision', '')
    _arg_28_receipt_repair_disposition = getattr(args, 'receipt_repair_disposition', '')
    _arg_29_receipt_repair_idempotency_key = getattr(args, 'receipt_repair_idempotency_key', '')
    _arg_30_route_repair_mode = getattr(args, 'route_repair_mode', '')
    _arg_31_route_repair_finding_id = getattr(args, 'route_repair_finding_id', '')
    _arg_32_route_repair_authority_path = getattr(args, 'route_repair_authority_path', '')
    _arg_33_route_repair_field_selector = getattr(args, 'route_repair_field_selector', '')
    _arg_34_route_repair_expected_revision = getattr(args, 'route_repair_expected_revision', '')
    _arg_35_route_repair_delta_json = getattr(args, 'route_repair_delta_json', '')
    _arg_36_route_repair_disposition = getattr(args, 'route_repair_disposition', '')
    _arg_37_route_repair_idempotency_key = getattr(args, 'route_repair_idempotency_key', '')
    _arg_38_dry_run = bool(getattr(args, 'dry_run', False))
    from agentic_workspace.workspace_runtime_primitives import _emit_proof
    return int(_emit_proof(format_name=_arg_0_format_name, target_root=_arg_1_target_root, descriptors=_arg_2_descriptors, route=_arg_3_route, current_only=_arg_4_current_only, changed_paths=_arg_5_changed_paths, task_text=_arg_6_task_text, profile=_arg_7_profile, select=_arg_8_select, execute_selected=_arg_9_execute_selected, proof_run_id=_arg_10_proof_run_id, proof_timeout_seconds=_arg_11_proof_timeout_seconds, proof_cancel_file=_arg_12_proof_cancel_file, record_receipt=_arg_13_record_receipt, receipt_command=_arg_14_receipt_command, receipt_result=_arg_15_receipt_result, receipt_plan=_arg_16_receipt_plan, receipt_log=_arg_17_receipt_log, receipt_route_id=_arg_18_receipt_route_id, receipt_command_id=_arg_19_receipt_command_id, receipt_duration_seconds=_arg_20_receipt_duration_seconds, receipt_timeout=_arg_21_receipt_timeout, receipt_exit_state=_arg_22_receipt_exit_state, receipt_environment=_arg_23_receipt_environment, receipt_claim_sufficiency=_arg_24_receipt_claim_sufficiency, receipt_route_budget_seconds=_arg_25_receipt_route_budget_seconds, receipt_repair_finding_id=_arg_26_receipt_repair_finding_id, receipt_repair_authority_revision=_arg_27_receipt_repair_authority_revision, receipt_repair_disposition=_arg_28_receipt_repair_disposition, receipt_repair_idempotency_key=_arg_29_receipt_repair_idempotency_key, route_repair_mode=_arg_30_route_repair_mode, route_repair_finding_id=_arg_31_route_repair_finding_id, route_repair_authority_path=_arg_32_route_repair_authority_path, route_repair_field_selector=_arg_33_route_repair_field_selector, route_repair_expected_revision=_arg_34_route_repair_expected_revision, route_repair_delta_json=_arg_35_route_repair_delta_json, route_repair_disposition=_arg_36_route_repair_disposition, route_repair_idempotency_key=_arg_37_route_repair_idempotency_key, dry_run=_arg_38_dry_run) or 0)


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('proof.report' + ' has no generated operation callable')
