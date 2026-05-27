"""Generated target-local primitive executor facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

# DO NOT EDIT DIRECTLY.
# Primitive implementations are generated into this target-local package.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from .primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps

__all__ = [
    "PrimitiveContext",
    "PrimitiveExecutionError",
    "execute_primitive",
    "run_operation_steps",
]
