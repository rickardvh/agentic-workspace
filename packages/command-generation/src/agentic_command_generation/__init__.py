"""Generic command package generation boundary."""

from __future__ import annotations

from agentic_command_generation.generator import GeneratedOutput, generate_command_packages, render_outputs
from agentic_command_generation.ir import load_command_package_ir

__all__ = ["GeneratedOutput", "generate_command_packages", "load_command_package_ir", "render_outputs"]
