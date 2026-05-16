"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Operation: summary.report
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py



def run(args: argparse.Namespace) -> int:
    from ..primitives.workspace_runtime import _run_summary_report_adapter

    return _run_summary_report_adapter(args)
