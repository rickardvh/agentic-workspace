"""Generic command package generation boundary."""

from __future__ import annotations

from command_generation.artifacts import CanonicalCommandArtifact, canonical_command_artifacts
from command_generation.generator import GeneratedOutput, generate_command_packages, render_outputs
from command_generation.ir import load_command_package_ir
from command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, execute_primitive, run_operation_steps

__all__ = [
    "CanonicalCommandArtifact",
    "GeneratedOutput",
    "PrimitiveContext",
    "PrimitiveExecutionError",
    "canonical_command_artifacts",
    "execute_primitive",
    "generate_command_packages",
    "load_command_package_ir",
    "render_outputs",
    "run_operation_steps",
]
