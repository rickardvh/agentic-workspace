"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

from typing import Any

# DO NOT EDIT DIRECTLY.
# This generated-local seam makes remaining source-runtime delegates explicit per function.
# Replace individual bindings here with generated/codegen-owned primitives as those operations migrate.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

def planning_report(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import planning_report as source_function

    return source_function(*args, **kwargs)


def planning_report_tiny(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import planning_report_tiny as source_function

    return source_function(*args, **kwargs)


__all__ = [
    'planning_report',
    'planning_report_tiny',
]
