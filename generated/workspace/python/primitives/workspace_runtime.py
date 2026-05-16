"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

from typing import Any

# DO NOT EDIT DIRECTLY.
# This generated-local seam makes remaining source-runtime delegates explicit per function.
# Replace individual bindings here with generated/codegen-owned primitives as those operations migrate.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

def _append_workspace_operation_delegation_outcome(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _append_workspace_operation_delegation_outcome as source_function

    return source_function(*args, **kwargs)


def _emit_workspace_operation_output(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _emit_workspace_operation_output as source_function

    return source_function(*args, **kwargs)


def _load_workspace_operation_config(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_config as source_function

    return source_function(*args, **kwargs)


def _load_workspace_operation_defaults(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_defaults as source_function

    return source_function(*args, **kwargs)


def _load_workspace_operation_system_intent_config(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_system_intent_config as source_function

    return source_function(*args, **kwargs)


def _read_or_create_workspace_operation_system_intent_mirror(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _read_or_create_workspace_operation_system_intent_mirror as source_function

    return source_function(*args, **kwargs)


def _refresh_workspace_operation_system_intent_metadata(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _refresh_workspace_operation_system_intent_metadata as source_function

    return source_function(*args, **kwargs)


def _render_workspace_operation_prompt(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _render_workspace_operation_prompt as source_function

    return source_function(*args, **kwargs)


def _resolve_workspace_operation_selection(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _resolve_workspace_operation_selection as source_function

    return source_function(*args, **kwargs)


def _resolve_workspace_operation_target_root(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _resolve_workspace_operation_target_root as source_function

    return source_function(*args, **kwargs)


def _run_external_intent_refresh_github_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_external_intent_refresh_github_adapter as source_function

    return source_function(*args, **kwargs)


def _run_implement_context_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_implement_context_adapter as source_function

    return source_function(*args, **kwargs)


def _run_init_lifecycle_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_init_lifecycle_adapter as source_function

    return source_function(*args, **kwargs)


def _run_lifecycle_mutation_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_mutation_adapter as source_function

    return source_function(*args, **kwargs)


def _run_lifecycle_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_memory_front_door_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_memory_front_door_adapter as source_function

    return source_function(*args, **kwargs)


def _run_modules_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_modules_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_ownership_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_ownership_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_planning_front_door_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_planning_front_door_adapter as source_function

    return source_function(*args, **kwargs)


def _run_preflight_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_preflight_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_proof_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_proof_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_reconcile_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_reconcile_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_report_combined_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_report_combined_adapter as source_function

    return source_function(*args, **kwargs)


def _run_setup_guidance_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_setup_guidance_adapter as source_function

    return source_function(*args, **kwargs)


def _run_skills_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_skills_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_start_context_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_start_context_adapter as source_function

    return source_function(*args, **kwargs)


def _run_summary_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_summary_report_adapter as source_function

    return source_function(*args, **kwargs)


def _select_workspace_operation_defaults(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _select_workspace_operation_defaults as source_function

    return source_function(*args, **kwargs)


def _select_workspace_operation_fields(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _select_workspace_operation_fields as source_function

    return source_function(*args, **kwargs)


__all__ = [
    '_append_workspace_operation_delegation_outcome',
    '_emit_workspace_operation_output',
    '_load_workspace_operation_config',
    '_load_workspace_operation_defaults',
    '_load_workspace_operation_system_intent_config',
    '_read_or_create_workspace_operation_system_intent_mirror',
    '_refresh_workspace_operation_system_intent_metadata',
    '_render_workspace_operation_prompt',
    '_resolve_workspace_operation_selection',
    '_resolve_workspace_operation_target_root',
    '_run_external_intent_refresh_github_adapter',
    '_run_implement_context_adapter',
    '_run_init_lifecycle_adapter',
    '_run_lifecycle_mutation_adapter',
    '_run_lifecycle_report_adapter',
    '_run_memory_front_door_adapter',
    '_run_modules_report_adapter',
    '_run_ownership_report_adapter',
    '_run_planning_front_door_adapter',
    '_run_preflight_report_adapter',
    '_run_proof_report_adapter',
    '_run_reconcile_report_adapter',
    '_run_report_combined_adapter',
    '_run_setup_guidance_adapter',
    '_run_skills_report_adapter',
    '_run_start_context_adapter',
    '_run_summary_report_adapter',
    '_select_workspace_operation_defaults',
    '_select_workspace_operation_fields',
]
