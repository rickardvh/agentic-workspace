"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Operation: memory.search.report
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from ..cli import generated_operation_contract
from ..operation_executor import run_operation_ir


def run(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_operation_contract('memory.search.report'), args)
