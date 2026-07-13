"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: work-thread.select
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
    from agentic_workspace.workspace_runtime_core import _run_work_thread_prune_adapter

    return _run_work_thread_prune_adapter(args)


def invoke(_values: Mapping[str, Any]) -> object:
    raise RuntimeError('work-thread.select' + ' has no generated operation callable')
