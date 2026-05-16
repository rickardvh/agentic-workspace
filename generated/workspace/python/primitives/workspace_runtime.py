"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

from agentic_workspace.workspace_runtime_primitives import (
    _append_workspace_operation_delegation_outcome,
    _emit_workspace_operation_output,
    _load_workspace_operation_config,
    _load_workspace_operation_defaults,
    _load_workspace_operation_system_intent_config,
    _read_or_create_workspace_operation_system_intent_mirror,
    _refresh_workspace_operation_system_intent_metadata,
    _render_workspace_operation_prompt,
    _resolve_workspace_operation_selection,
    _resolve_workspace_operation_target_root,
    _run_external_intent_refresh_github_adapter,
    _run_implement_context_adapter,
    _run_init_lifecycle_adapter,
    _run_lifecycle_mutation_adapter,
    _run_lifecycle_report_adapter,
    _run_memory_front_door_adapter,
    _run_modules_report_adapter,
    _run_ownership_report_adapter,
    _run_planning_front_door_adapter,
    _run_preflight_report_adapter,
    _run_proof_report_adapter,
    _run_reconcile_report_adapter,
    _run_report_combined_adapter,
    _run_setup_guidance_adapter,
    _run_skills_report_adapter,
    _run_start_context_adapter,
    _run_summary_report_adapter,
    _select_workspace_operation_defaults,
    _select_workspace_operation_fields,
)

# DO NOT EDIT DIRECTLY.
# This generated-local seam lets generated workspace outputs avoid direct source-runtime imports.
# Replace individual bindings here with generated/codegen-owned primitives as those operations migrate.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

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
