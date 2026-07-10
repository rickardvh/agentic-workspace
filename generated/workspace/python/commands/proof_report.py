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
    _arg_9_record_receipt = bool(getattr(args, 'record_receipt', False))
    _arg_10_receipt_command = getattr(args, 'receipt_command', '')
    _arg_11_receipt_result = getattr(args, 'receipt_result', '')
    _arg_12_receipt_plan = getattr(args, 'receipt_plan', '')
    _arg_13_receipt_log = getattr(args, 'receipt_log', '')
    _arg_14_dry_run = bool(getattr(args, 'dry_run', False))
    from agentic_workspace.workspace_runtime_primitives import _emit_proof
    _emit_proof(format_name=_arg_0_format_name, target_root=_arg_1_target_root, descriptors=_arg_2_descriptors, route=_arg_3_route, current_only=_arg_4_current_only, changed_paths=_arg_5_changed_paths, task_text=_arg_6_task_text, profile=_arg_7_profile, select=_arg_8_select, record_receipt=_arg_9_record_receipt, receipt_command=_arg_10_receipt_command, receipt_result=_arg_11_receipt_result, receipt_plan=_arg_12_receipt_plan, receipt_log=_arg_13_receipt_log, dry_run=_arg_14_dry_run)
    return 0


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('proof.report' + ' has no generated operation callable')
