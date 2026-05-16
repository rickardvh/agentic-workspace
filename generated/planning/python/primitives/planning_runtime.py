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

def apply_planning_archive_plan_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_archive_plan_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_delegation_decision_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_delegation_decision_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_new_plan_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_new_plan_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_promote_to_plan_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_promote_to_plan_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_record_recovery_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_record_recovery_operation as source_function

    return source_function(*args, **kwargs)


def emit_planning_operation_output(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import emit_planning_operation_output as source_function

    return source_function(*args, **kwargs)


def load_planning_list_files_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import load_planning_list_files_operation as source_function

    return source_function(*args, **kwargs)


def load_planning_reconcile_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import load_planning_reconcile_operation as source_function

    return source_function(*args, **kwargs)


def load_planning_summary_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import load_planning_summary_operation as source_function

    return source_function(*args, **kwargs)


def render_planning_prompt_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import render_planning_prompt_operation as source_function

    return source_function(*args, **kwargs)


__all__ = [
    'apply_planning_archive_plan_operation',
    'apply_planning_delegation_decision_operation',
    'apply_planning_new_plan_operation',
    'apply_planning_promote_to_plan_operation',
    'apply_planning_record_recovery_operation',
    'emit_planning_operation_output',
    'load_planning_list_files_operation',
    'load_planning_reconcile_operation',
    'load_planning_summary_operation',
    'render_planning_prompt_operation',
]
