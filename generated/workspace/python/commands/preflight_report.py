"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: preflight.report
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
    from agentic_workspace.workspace_runtime_primitives import _diagnostic_profile, _resolve_target_root, _validate_target_root
    _arg_0_target_root = _resolve_target_root(getattr(args, 'target', None))
    if _arg_0_target_root is None:
        raise ValueError('target root resolution returned None')
    _validate_target_root(command_name='preflight', target_root=_arg_0_target_root)
    _arg_1_active_only = bool(getattr(args, 'active_only', False))
    _arg_2_task_text = getattr(args, 'task', None)
    _arg_3_profile = _diagnostic_profile(args, default='tiny')
    from agentic_workspace.workspace_runtime_primitives import _run_preflight_command
    payload = _run_preflight_command(target_root=_arg_0_target_root, active_only=_arg_1_active_only, task_text=_arg_2_task_text, profile=_arg_3_profile)
    from agentic_workspace.workspace_runtime_primitives import _emit_payload
    _emit_payload(payload=payload, format_name=getattr(args, 'format', 'text'))
    return 0


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('preflight.report' + ' has no generated operation callable')
