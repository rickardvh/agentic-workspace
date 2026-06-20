"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: ownership.report
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
    from agentic_workspace.workspace_runtime_primitives import _module_operations, _resolve_target_root, _validate_descriptor_contract, _validate_target_root
    _arg_0_format_name = getattr(args, 'format', None)
    _arg_1_target_root = _resolve_target_root(getattr(args, 'target', None))
    if _arg_1_target_root is None:
        raise ValueError('target root resolution returned None')
    _validate_target_root(command_name='ownership', target_root=_arg_1_target_root)
    _arg_2_descriptors = _module_operations()
    _validate_descriptor_contract(_arg_2_descriptors)
    _arg_3_concern = getattr(args, 'concern', None)
    _arg_4_repo_path = getattr(args, 'path', None)
    from agentic_workspace.workspace_runtime_primitives import _emit_ownership
    _emit_ownership(format_name=_arg_0_format_name, target_root=_arg_1_target_root, descriptors=_arg_2_descriptors, concern=_arg_3_concern, repo_path=_arg_4_repo_path)
    return 0


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('ownership.report' + ' has no generated operation callable')
