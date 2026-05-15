"""Generated target-local primitive executor facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

# DO NOT EDIT DIRECTLY.
# Primitive implementations belong to command_generation. This module makes the target-local boundary explicit.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps

__all__ = [
    "PrimitiveContext",
    "PrimitiveExecutionError",
    "execute_primitive",
    "run_operation_steps",
]
