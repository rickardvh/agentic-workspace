"""Generated Python runtime operation handler module.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any

# DO NOT EDIT DIRECTLY.
# Runtime handler changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py
from . import build_generated_parser as build_generated_cli_package_parser
from . import generated_command_names as generated_cli_package_command_names
from . import generated_operation_contract as generated_cli_package_operation_contract
from . import run_generated_command as run_generated_cli_package_command
from . import supports_generated_command as supports_generated_cli_package_command
from .workspace_operation_ir_executor import run_operation_ir


from agentic_workspace.workspace_runtime_primitives import __version__ as __version__


from agentic_workspace.workspace_runtime_primitives import _authority_marker_for_path as _authority_marker_for_path


from agentic_workspace.workspace_runtime_primitives import _command_with_cli_invoke as _command_with_cli_invoke


from agentic_workspace.workspace_runtime_primitives import _command_suggestions as _command_suggestions


from agentic_workspace.workspace_runtime_primitives import _compact_contract_answer as _compact_contract_answer


from agentic_workspace.workspace_runtime_primitives import _defaults_payload as _defaults_payload


from agentic_workspace.workspace_runtime_primitives import _friction_response_order_payload as _friction_response_order_payload


from agentic_workspace.workspace_runtime_primitives import _implement_payload as _implement_payload


from agentic_workspace.workspace_runtime_primitives import _invoke_module_command as _invoke_module_command


from agentic_workspace.workspace_runtime_primitives import _improvement_boundary_test_payload as _improvement_boundary_test_payload


from agentic_workspace.workspace_runtime_primitives import _improvement_latitude_payload as _improvement_latitude_payload


from agentic_workspace.workspace_runtime_primitives import _load_workspace_config as _load_workspace_config


from agentic_workspace.workspace_runtime_primitives import _module_operations as _module_operations


from agentic_workspace.workspace_runtime_primitives import _module_registry as _module_registry


from agentic_workspace.workspace_runtime_primitives import _MODULE_REGISTRY_ENTRIES as _MODULE_REGISTRY_ENTRIES


from agentic_workspace.workspace_runtime_primitives import _optimization_bias_payload as _optimization_bias_payload


from agentic_workspace.workspace_runtime_primitives import _ordered_module_names as _ordered_module_names


from agentic_workspace.workspace_runtime_primitives import _planning_module_argv as _planning_module_argv


from agentic_workspace.workspace_runtime_primitives import _ownership_payload as _ownership_payload


from agentic_workspace.workspace_runtime_primitives import _PREFLIGHT_STRICT_GATE_POLICY as _PREFLIGHT_STRICT_GATE_POLICY


from agentic_workspace.workspace_runtime_primitives import _product_managed_enclave_payload as _product_managed_enclave_payload


from agentic_workspace.workspace_runtime_primitives import _repo_directed_improvement_evidence_threshold_payload as _repo_directed_improvement_evidence_threshold_payload


from agentic_workspace.workspace_runtime_primitives import _reporting_schema_payload as _reporting_schema_payload


from agentic_workspace.workspace_runtime_primitives import _resolve_option_choices as _resolve_option_choices


from agentic_workspace.workspace_runtime_primitives import _resolve_option_default as _resolve_option_default


from agentic_workspace.workspace_runtime_primitives import _resolve_option_type as _resolve_option_type


from agentic_workspace.workspace_runtime_primitives import _resolved_option_help as _resolved_option_help


from agentic_workspace.workspace_runtime_primitives import _runtime_resolution_payload as _runtime_resolution_payload


from agentic_workspace.workspace_runtime_primitives import _run_report_command as _run_report_command


from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_command as _run_lifecycle_command


from agentic_workspace.workspace_runtime_primitives import _selected_modules as _selected_modules


from agentic_workspace.workspace_runtime_primitives import _setup_finding_class_payload as _setup_finding_class_payload


from agentic_workspace.workspace_runtime_primitives import _start_payload as _start_payload


from agentic_workspace.workspace_runtime_primitives import _validation_friction_payload as _validation_friction_payload


from agentic_workspace.workspace_runtime_primitives import _validate_selected_module_contract as _validate_selected_module_contract


from agentic_workspace.workspace_runtime_primitives import _workflow_artifact_profile_payload as _workflow_artifact_profile_payload


from agentic_workspace.workspace_runtime_primitives import _workspace_agents_template as _workspace_agents_template


from agentic_workspace.workspace_runtime_primitives import _workspace_self_adaptation_guardrail_payload as _workspace_self_adaptation_guardrail_payload


from agentic_workspace.workspace_runtime_primitives import _workspace_self_adaptation_payload as _workspace_self_adaptation_payload


from agentic_workspace.workspace_runtime_primitives import DEFAULT_IMPROVEMENT_LATITUDE as DEFAULT_IMPROVEMENT_LATITUDE


from agentic_workspace.workspace_runtime_primitives import DEFAULT_OPTIMIZATION_BIAS as DEFAULT_OPTIMIZATION_BIAS


from agentic_workspace.workspace_runtime_primitives import DEFAULT_PREFLIGHT_MAX_AGE_SECONDS as DEFAULT_PREFLIGHT_MAX_AGE_SECONDS


from agentic_workspace.workspace_runtime_primitives import DEFAULT_WORKFLOW_ARTIFACT_PROFILE as DEFAULT_WORKFLOW_ARTIFACT_PROFILE


from agentic_workspace.workspace_runtime_primitives import HIGH_RISK_COMMANDS as HIGH_RISK_COMMANDS


from agentic_workspace.workspace_runtime_primitives import MEMORY_POINTER_BLOCK as MEMORY_POINTER_BLOCK


from agentic_workspace.workspace_runtime_primitives import MEMORY_WORKFLOW_MARKER_END as MEMORY_WORKFLOW_MARKER_END


from agentic_workspace.workspace_runtime_primitives import MEMORY_WORKFLOW_MARKER_START as MEMORY_WORKFLOW_MARKER_START


from agentic_workspace.workspace_runtime_primitives import MIXED_AGENT_LOCAL_OVERRIDE_FIELDS as MIXED_AGENT_LOCAL_OVERRIDE_FIELDS


from agentic_workspace.workspace_runtime_primitives import MODULE_COMMAND_ARGS as MODULE_COMMAND_ARGS


from agentic_workspace.workspace_runtime_primitives import MODULE_UPGRADE_SOURCE_PATHS as MODULE_UPGRADE_SOURCE_PATHS


from agentic_workspace.workspace_runtime_primitives import ModuleDescriptor as ModuleDescriptor


from agentic_workspace.workspace_runtime_primitives import ModuleSelectionError as ModuleSelectionError


from agentic_workspace.workspace_runtime_primitives import ModuleResultContract as ModuleResultContract


from agentic_workspace.workspace_runtime_primitives import PREFLIGHT_TOKEN_PREFIX as PREFLIGHT_TOKEN_PREFIX


from agentic_workspace.workspace_runtime_primitives import RootAgentsCleanupBlock as RootAgentsCleanupBlock


from agentic_workspace.workspace_runtime_primitives import SETUP_FINDING_PROMOTION_THRESHOLD as SETUP_FINDING_PROMOTION_THRESHOLD


from agentic_workspace.workspace_runtime_primitives import SETUP_FINDINGS_KIND as SETUP_FINDINGS_KIND


from agentic_workspace.workspace_runtime_primitives import SETUP_FINDINGS_PATH as SETUP_FINDINGS_PATH


from agentic_workspace.workspace_runtime_primitives import SUBSYSTEM_INTENT_KIND as SUBSYSTEM_INTENT_KIND


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_DELEGATION_OUTCOMES as SUPPORTED_DELEGATION_OUTCOMES


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS as SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_DELEGATION_TARGET_STRENGTHS as SUPPORTED_DELEGATION_TARGET_STRENGTHS


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_HANDOFF_SUFFICIENCY as SUPPORTED_HANDOFF_SUFFICIENCY


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_IMPROVEMENT_LATITUDES as SUPPORTED_IMPROVEMENT_LATITUDES


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_OPTIMIZATION_BIASES as SUPPORTED_OPTIMIZATION_BIASES


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_REVIEW_BURDENS as SUPPORTED_REVIEW_BURDENS


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_SETUP_FINDING_CLASSES as SUPPORTED_SETUP_FINDING_CLASSES


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_WORKFLOW_ARTIFACT_PROFILES as SUPPORTED_WORKFLOW_ARTIFACT_PROFILES


from agentic_workspace.workspace_runtime_primitives import SUPPORTED_WORKFLOW_OBLIGATION_STAGES as SUPPORTED_WORKFLOW_OBLIGATION_STAGES


from agentic_workspace.workspace_runtime_primitives import SYSTEM_INTENT_MIRROR_KIND as SYSTEM_INTENT_MIRROR_KIND


from agentic_workspace.workspace_runtime_primitives import WORKSPACE_AGENTS_PATH as WORKSPACE_AGENTS_PATH


from agentic_workspace.workspace_runtime_primitives import WORKSPACE_HANDOFF_SURFACES as WORKSPACE_HANDOFF_SURFACES


from agentic_workspace.workspace_runtime_primitives import WORKSPACE_PAYLOAD_FILES as WORKSPACE_PAYLOAD_FILES


from agentic_workspace.workspace_runtime_primitives import WORKSPACE_POINTER_BLOCK as WORKSPACE_POINTER_BLOCK


from agentic_workspace.workspace_runtime_primitives import datetime as datetime


from agentic_workspace.workspace_runtime_primitives import subprocess as subprocess


from agentic_workspace.workspace_runtime_primitives import timedelta as timedelta


from agentic_workspace.workspace_runtime_primitives import timezone as timezone


_RUNTIME_EXPORT_SOURCES = (
    ('agentic_workspace.workspace_runtime_primitives', '__version__', '__version__'),
    ('agentic_workspace.workspace_runtime_primitives', '_authority_marker_for_path', '_authority_marker_for_path'),
    ('agentic_workspace.workspace_runtime_primitives', '_command_with_cli_invoke', '_command_with_cli_invoke'),
    ('agentic_workspace.workspace_runtime_primitives', '_command_suggestions', '_command_suggestions'),
    ('agentic_workspace.workspace_runtime_primitives', '_compact_contract_answer', '_compact_contract_answer'),
    ('agentic_workspace.workspace_runtime_primitives', '_defaults_payload', '_defaults_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_friction_response_order_payload', '_friction_response_order_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_implement_payload', '_implement_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_invoke_module_command', '_invoke_module_command'),
    ('agentic_workspace.workspace_runtime_primitives', '_improvement_boundary_test_payload', '_improvement_boundary_test_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_improvement_latitude_payload', '_improvement_latitude_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_load_workspace_config', '_load_workspace_config'),
    ('agentic_workspace.workspace_runtime_primitives', '_module_operations', '_module_operations'),
    ('agentic_workspace.workspace_runtime_primitives', '_module_registry', '_module_registry'),
    ('agentic_workspace.workspace_runtime_primitives', '_MODULE_REGISTRY_ENTRIES', '_MODULE_REGISTRY_ENTRIES'),
    ('agentic_workspace.workspace_runtime_primitives', '_optimization_bias_payload', '_optimization_bias_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_ordered_module_names', '_ordered_module_names'),
    ('agentic_workspace.workspace_runtime_primitives', '_planning_module_argv', '_planning_module_argv'),
    ('agentic_workspace.workspace_runtime_primitives', '_ownership_payload', '_ownership_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_PREFLIGHT_STRICT_GATE_POLICY', '_PREFLIGHT_STRICT_GATE_POLICY'),
    ('agentic_workspace.workspace_runtime_primitives', '_product_managed_enclave_payload', '_product_managed_enclave_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_repo_directed_improvement_evidence_threshold_payload', '_repo_directed_improvement_evidence_threshold_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_reporting_schema_payload', '_reporting_schema_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolve_option_choices', '_resolve_option_choices'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolve_option_default', '_resolve_option_default'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolve_option_type', '_resolve_option_type'),
    ('agentic_workspace.workspace_runtime_primitives', '_resolved_option_help', '_resolved_option_help'),
    ('agentic_workspace.workspace_runtime_primitives', '_runtime_resolution_payload', '_runtime_resolution_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_run_report_command', '_run_report_command'),
    ('agentic_workspace.workspace_runtime_primitives', '_run_lifecycle_command', '_run_lifecycle_command'),
    ('agentic_workspace.workspace_runtime_primitives', '_selected_modules', '_selected_modules'),
    ('agentic_workspace.workspace_runtime_primitives', '_setup_finding_class_payload', '_setup_finding_class_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_start_payload', '_start_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_validation_friction_payload', '_validation_friction_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_validate_selected_module_contract', '_validate_selected_module_contract'),
    ('agentic_workspace.workspace_runtime_primitives', '_workflow_artifact_profile_payload', '_workflow_artifact_profile_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_workspace_agents_template', '_workspace_agents_template'),
    ('agentic_workspace.workspace_runtime_primitives', '_workspace_self_adaptation_guardrail_payload', '_workspace_self_adaptation_guardrail_payload'),
    ('agentic_workspace.workspace_runtime_primitives', '_workspace_self_adaptation_payload', '_workspace_self_adaptation_payload'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_IMPROVEMENT_LATITUDE', 'DEFAULT_IMPROVEMENT_LATITUDE'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_OPTIMIZATION_BIAS', 'DEFAULT_OPTIMIZATION_BIAS'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_PREFLIGHT_MAX_AGE_SECONDS', 'DEFAULT_PREFLIGHT_MAX_AGE_SECONDS'),
    ('agentic_workspace.workspace_runtime_primitives', 'DEFAULT_WORKFLOW_ARTIFACT_PROFILE', 'DEFAULT_WORKFLOW_ARTIFACT_PROFILE'),
    ('agentic_workspace.workspace_runtime_primitives', 'HIGH_RISK_COMMANDS', 'HIGH_RISK_COMMANDS'),
    ('agentic_workspace.workspace_runtime_primitives', 'MEMORY_POINTER_BLOCK', 'MEMORY_POINTER_BLOCK'),
    ('agentic_workspace.workspace_runtime_primitives', 'MEMORY_WORKFLOW_MARKER_END', 'MEMORY_WORKFLOW_MARKER_END'),
    ('agentic_workspace.workspace_runtime_primitives', 'MEMORY_WORKFLOW_MARKER_START', 'MEMORY_WORKFLOW_MARKER_START'),
    ('agentic_workspace.workspace_runtime_primitives', 'MIXED_AGENT_LOCAL_OVERRIDE_FIELDS', 'MIXED_AGENT_LOCAL_OVERRIDE_FIELDS'),
    ('agentic_workspace.workspace_runtime_primitives', 'MODULE_COMMAND_ARGS', 'MODULE_COMMAND_ARGS'),
    ('agentic_workspace.workspace_runtime_primitives', 'MODULE_UPGRADE_SOURCE_PATHS', 'MODULE_UPGRADE_SOURCE_PATHS'),
    ('agentic_workspace.workspace_runtime_primitives', 'ModuleDescriptor', 'ModuleDescriptor'),
    ('agentic_workspace.workspace_runtime_primitives', 'ModuleSelectionError', 'ModuleSelectionError'),
    ('agentic_workspace.workspace_runtime_primitives', 'ModuleResultContract', 'ModuleResultContract'),
    ('agentic_workspace.workspace_runtime_primitives', 'PREFLIGHT_TOKEN_PREFIX', 'PREFLIGHT_TOKEN_PREFIX'),
    ('agentic_workspace.workspace_runtime_primitives', 'RootAgentsCleanupBlock', 'RootAgentsCleanupBlock'),
    ('agentic_workspace.workspace_runtime_primitives', 'SETUP_FINDING_PROMOTION_THRESHOLD', 'SETUP_FINDING_PROMOTION_THRESHOLD'),
    ('agentic_workspace.workspace_runtime_primitives', 'SETUP_FINDINGS_KIND', 'SETUP_FINDINGS_KIND'),
    ('agentic_workspace.workspace_runtime_primitives', 'SETUP_FINDINGS_PATH', 'SETUP_FINDINGS_PATH'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUBSYSTEM_INTENT_KIND', 'SUBSYSTEM_INTENT_KIND'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_DELEGATION_OUTCOMES', 'SUPPORTED_DELEGATION_OUTCOMES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS', 'SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_DELEGATION_TARGET_STRENGTHS', 'SUPPORTED_DELEGATION_TARGET_STRENGTHS'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_HANDOFF_SUFFICIENCY', 'SUPPORTED_HANDOFF_SUFFICIENCY'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_IMPROVEMENT_LATITUDES', 'SUPPORTED_IMPROVEMENT_LATITUDES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_OPTIMIZATION_BIASES', 'SUPPORTED_OPTIMIZATION_BIASES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_REVIEW_BURDENS', 'SUPPORTED_REVIEW_BURDENS'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_SETUP_FINDING_CLASSES', 'SUPPORTED_SETUP_FINDING_CLASSES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_WORKFLOW_ARTIFACT_PROFILES', 'SUPPORTED_WORKFLOW_ARTIFACT_PROFILES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SUPPORTED_WORKFLOW_OBLIGATION_STAGES', 'SUPPORTED_WORKFLOW_OBLIGATION_STAGES'),
    ('agentic_workspace.workspace_runtime_primitives', 'SYSTEM_INTENT_MIRROR_KIND', 'SYSTEM_INTENT_MIRROR_KIND'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_AGENTS_PATH', 'WORKSPACE_AGENTS_PATH'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_HANDOFF_SURFACES', 'WORKSPACE_HANDOFF_SURFACES'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_PAYLOAD_FILES', 'WORKSPACE_PAYLOAD_FILES'),
    ('agentic_workspace.workspace_runtime_primitives', 'WORKSPACE_POINTER_BLOCK', 'WORKSPACE_POINTER_BLOCK'),
    ('agentic_workspace.workspace_runtime_primitives', 'datetime', 'datetime'),
    ('agentic_workspace.workspace_runtime_primitives', 'subprocess', 'subprocess'),
    ('agentic_workspace.workspace_runtime_primitives', 'timedelta', 'timedelta'),
    ('agentic_workspace.workspace_runtime_primitives', 'timezone', 'timezone'),
)


def _sync_runtime_export_patches() -> None:
    for module_name, source_name, exported_name in _RUNTIME_EXPORT_SOURCES:
        value = globals().get(exported_name)
        module = importlib.import_module(module_name)
        if getattr(module, source_name, None) is not value:
            setattr(module, source_name, value)


def _program_name() -> str:
    invoked = sys.argv[0].replace("\\", "/").rsplit("/", 1)[-1]
    if invoked == 'agentic-workspace':
        return invoked
    return 'agentic-workspace'


def build_parser() -> argparse.ArgumentParser:
    return build_generated_cli_package_parser()


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    try:
        return run_generated_cli_package_command(argv_list, _run_generated_cli_operation)
    except Exception as exc:
        if exc.__class__.__name__.endswith('UsageError') or exc.__class__.__name__ == 'RepoDetectionError':
            build_generated_cli_package_parser().error(str(exc))
        raise


def _run_generated_cli_operation(operation_id: str, args: argparse.Namespace) -> int:
    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is None:
        build_generated_cli_package_parser().error(
            f"Generated adapter for {getattr(args, 'command', operation_id)} references unsupported operation {operation_id}."
        )
        raise SystemExit(2)
    _sync_runtime_export_patches()
    return handler(args)


def _run_config_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('config.report'), args)


def _run_defaults_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('defaults.report'), args)


def _run_delegation_outcome_append_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('delegation-outcome.append'), args)


def _run_doctor_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_report_adapter

    return _run_lifecycle_report_adapter(args)


def _run_external_intent_refresh_github_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_external_intent_refresh_github_adapter

    return _run_external_intent_refresh_github_adapter(args)


def _run_implement_context_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_implement_context_adapter

    return _run_implement_context_adapter(args)


def _run_init_lifecycle_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_init_lifecycle_adapter

    return _run_init_lifecycle_adapter(args)


def _run_install_lifecycle_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_init_lifecycle_adapter

    return _run_init_lifecycle_adapter(args)


def _run_memory_front_door_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_memory_front_door_adapter

    return _run_memory_front_door_adapter(args)


def _run_modules_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_modules_report_adapter

    return _run_modules_report_adapter(args)


def _run_ownership_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_ownership_report_adapter

    return _run_ownership_report_adapter(args)


def _run_planning_front_door_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_planning_front_door_adapter

    return _run_planning_front_door_adapter(args)


def _run_preflight_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_preflight_report_adapter

    return _run_preflight_report_adapter(args)


def _run_prompt_init_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('prompt.init'), args)


def _run_prompt_uninstall_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('prompt.uninstall'), args)


def _run_prompt_upgrade_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('prompt.upgrade'), args)


def _run_proof_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_proof_report_adapter

    return _run_proof_report_adapter(args)


def _run_reconcile_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_reconcile_report_adapter

    return _run_reconcile_report_adapter(args)


def _run_report_combined_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_report_combined_adapter

    return _run_report_combined_adapter(args)


def _run_setup_guidance_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_setup_guidance_adapter

    return _run_setup_guidance_adapter(args)


def _run_skills_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_skills_report_adapter

    return _run_skills_report_adapter(args)


def _run_start_context_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_start_context_adapter

    return _run_start_context_adapter(args)


def _run_status_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_report_adapter

    return _run_lifecycle_report_adapter(args)


def _run_summary_report_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_summary_report_adapter

    return _run_summary_report_adapter(args)


def _run_system_intent_sync_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('system-intent.sync'), args)


def _run_uninstall_lifecycle_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_mutation_adapter

    return _run_lifecycle_mutation_adapter(args)


def _run_upgrade_lifecycle_adapter(args: argparse.Namespace) -> int:
    from agentic_workspace.workspace_runtime_primitives import _run_lifecycle_mutation_adapter

    return _run_lifecycle_mutation_adapter(args)



_GENERATED_RUNTIME_HANDLERS = {
    'config.report': _run_config_report_adapter,
    'defaults.report': _run_defaults_report_adapter,
    'delegation-outcome.append': _run_delegation_outcome_append_adapter,
    'doctor.report': _run_doctor_report_adapter,
    'external-intent.refresh-github': _run_external_intent_refresh_github_adapter,
    'implement.context': _run_implement_context_adapter,
    'init.lifecycle': _run_init_lifecycle_adapter,
    'install.lifecycle': _run_install_lifecycle_adapter,
    'memory.front-door': _run_memory_front_door_adapter,
    'modules.report': _run_modules_report_adapter,
    'ownership.report': _run_ownership_report_adapter,
    'planning.front-door': _run_planning_front_door_adapter,
    'preflight.report': _run_preflight_report_adapter,
    'prompt.init': _run_prompt_init_adapter,
    'prompt.uninstall': _run_prompt_uninstall_adapter,
    'prompt.upgrade': _run_prompt_upgrade_adapter,
    'proof.report': _run_proof_report_adapter,
    'reconcile.report': _run_reconcile_report_adapter,
    'report.combined': _run_report_combined_adapter,
    'setup.guidance': _run_setup_guidance_adapter,
    'skills.report': _run_skills_report_adapter,
    'start.context': _run_start_context_adapter,
    'status.report': _run_status_report_adapter,
    'summary.report': _run_summary_report_adapter,
    'system-intent.sync': _run_system_intent_sync_adapter,
    'uninstall.lifecycle': _run_uninstall_lifecycle_adapter,
    'upgrade.lifecycle': _run_upgrade_lifecycle_adapter,
}
