"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: modules.report
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
    _arg_0_format_name = getattr(args, 'format', None)
    _arg_1_target_root = _resolve_target_root(getattr(args, 'target', None)) if getattr(args, 'target', None) else None
    if _arg_1_target_root is not None:
        _validate_target_root(command_name='modules', target_root=_arg_1_target_root)
    _arg_2_profile = _diagnostic_profile(args, default='tiny')
    _arg_3_section = getattr(args, 'section', None)
    from agentic_workspace.workspace_runtime_primitives import _emit_modules
    _emit_modules(format_name=_arg_0_format_name, target_root=_arg_1_target_root, profile=_arg_2_profile, section=_arg_3_section)
    return 0


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('modules.report' + ' has no generated operation callable')
