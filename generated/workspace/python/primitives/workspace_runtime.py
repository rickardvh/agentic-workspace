"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-workspace
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

# DO NOT EDIT DIRECTLY.
# This generated-local seam makes remaining source-runtime delegates explicit per function.
# Export semantics: generated wrappers perform live source-module lookup at call time.
# Monkeypatching this facade is local to the facade; it is not forwarded back into source modules.
# Replace individual bindings here with generated/codegen-owned primitives as those operations migrate.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

def _serialise_value(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {key: _serialise_value(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_serialise_value(item) for item in value]
    return value


def _field_by_path(payload: Any, path: str) -> tuple[bool, Any]:
    current = payload
    for part in path.split('.'):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list):
            try:
                current = current[int(part)]
                continue
            except (ValueError, IndexError):
                return (False, None)
        return (False, None)
    return (True, copy.deepcopy(current))


def _selector_tokens(select: str | None) -> list[str]:
    return [token.strip() for token in str(select or '').split(',') if token.strip()]


def _available_selectors_for_payload(payload: Any, prefix: str = '') -> list[str]:
    selectors: list[str] = []
    if isinstance(payload, dict):
        for key in sorted(str(item) for item in payload):
            path = f'{prefix}.{key}' if prefix else key
            selectors.append(path)
            selectors.extend(_available_selectors_for_payload(payload.get(key), path))
    elif isinstance(payload, list):
        for index, item in enumerate(payload[:10]):
            path = f'{prefix}.{index}' if prefix else str(index)
            selectors.append(path)
            selectors.extend(_available_selectors_for_payload(item, path))
    return selectors


def _select_payload_fields(payload: dict[str, Any], *, select: str | None, source_command: str, selected_output_kind: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    missing: list[str] = []
    for selector in _selector_tokens(select):
        found, value = _field_by_path(payload, selector)
        if found:
            values[selector] = value
        else:
            missing.append(selector)
    selected: dict[str, Any] = {'kind': selected_output_kind, 'source_command': source_command, 'values': values}
    if missing:
        selected['missing'] = missing
        selected['selector_rule'] = 'Comma-separated dot paths select exact JSON fields; unknown fields are reported in missing.'
        selected['available_selectors'] = _available_selectors_for_payload(payload)
    return selected


def _selector_refs(*, command: str, answer: Any, compact_profile_ref: str = '') -> list[str]:
    refs = [ref for ref in (compact_profile_ref, command) if ref]
    if isinstance(answer, dict):
        for key in ('canonical_doc', 'command', 'path', 'surface', 'ledger_path'):
            value = answer.get(key)
            if isinstance(value, str) and value not in refs:
                refs.append(value)
    return refs


def _compact_contract_answer(*, surface: str, selector: dict[str, Any], answer: Any, refs: list[str]) -> dict[str, Any]:
    return {'profile': 'compact-contract-answer/v1', 'surface': surface, 'selector': selector, 'matched': True, 'answer': answer, 'refs': refs}


def _select_section(payload: dict[str, Any], *, section: str, source_command: str, command_ref: str, compact_profile_ref: str) -> dict[str, Any]:
    normalized = section.strip()
    if normalized not in payload:
        supported = ', '.join(sorted(str(key) for key in payload))
        raise ValueError(f'{source_command} --section must match one of: {supported}.')
    answer = payload[normalized]
    return _compact_contract_answer(surface=source_command, selector={'section': normalized}, answer=answer, refs=_selector_refs(command=command_ref, answer=answer, compact_profile_ref=compact_profile_ref))


def _tiny_sectioned_payload(payload: dict[str, Any], *, common_sections: list[str], sectioned_payload_kind: str, section_detail_command: str, full_detail_command: str) -> dict[str, Any]:
    return {
        'kind': sectioned_payload_kind,
        'profile': 'tiny',
        'summary': 'Default-route contract sections are available on demand; request one section or full detail instead of loading the whole contract.',
        'available_sections': sorted(str(key) for key in payload),
        'common_sections': list(common_sections),
        'detail_commands': {'section': section_detail_command, 'full': full_detail_command},
    }


def _emit_tiny_sectioned_text(payload: dict[str, Any]) -> str:
    lines = [str(payload.get('summary', ''))]
    common_sections = payload.get('common_sections', [])
    if common_sections:
        lines.append('Common sections:')
        lines.extend(f'- {section}' for section in common_sections)
    detail_commands = payload.get('detail_commands', {})
    if isinstance(detail_commands, dict) and detail_commands:
        lines.append('Detail commands:')
        lines.extend(f'- {key}: {value}' for key, value in detail_commands.items())
    return '\n'.join(lines) + '\n'


def _emit_compact_answer_text(payload: dict[str, Any]) -> str:
    lines = [
        f"Profile: {payload.get('profile')}",
        f"Surface: {payload.get('surface')}",
        f"Selector: {json.dumps(payload.get('selector', {}), sort_keys=True)}",
        f"Matched: {payload.get('matched')}",
        'Answer:',
        json.dumps(_serialise_value(payload.get('answer')), indent=2),
    ]
    refs = payload.get('refs', [])
    if refs:
        lines.append('Refs:')
        lines.extend(f'- {ref}' for ref in refs)
    return '\n'.join(lines) + '\n'


def _emit_selected_output_text(payload: dict[str, Any]) -> str:
    lines = [
        f"Kind: {payload.get('kind')}",
        f"Source command: {payload.get('source_command')}",
        'Values:',
        json.dumps(_serialise_value(payload.get('values', {})), indent=2),
    ]
    missing = payload.get('missing', [])
    if missing:
        lines.append('Missing:')
        lines.extend(f'- {item}' for item in missing)
    return '\n'.join(lines) + '\n'


def _emit_delegation_outcomes_text(payload: dict[str, Any]) -> str:
    recorded = payload.get('recorded', {})
    lines = [
        f"Kind: {payload.get('kind')}",
        f"Path: {payload.get('path')}",
        f"Record count: {payload.get('record_count')}",
        f"Rule: {payload.get('rule')}",
    ]
    if isinstance(recorded, dict):
        lines.append('Recorded:')
        for key in ('recorded_at', 'delegation_target', 'task_class', 'outcome', 'handoff_sufficiency', 'review_burden', 'escalation_required'):
            if key in recorded:
                lines.append(f'- {key}: {recorded[key]}')
    return '\n'.join(lines) + '\n'




def _emit_config_tiny_text(payload: dict[str, Any]) -> str:
    workspace = payload['workspace']
    local_runtime = payload['local_runtime']
    next_detail = payload['next_detail']
    lines = [
        f"Target: {payload['target']}",
        f"Config path: {payload['config_path']}",
        f"AW enabled: {workspace['enabled']} ({workspace['enabled_source']})",
        f"Enabled modules: {', '.join(workspace['enabled_modules']) or '(none)'}",
        f"Improvement latitude: {workspace['improvement_latitude']}",
        f"Optimization bias: {workspace['optimization_bias']}",
        f"Delegation mode: {local_runtime['delegation_mode']['value']}",
        f"Safe to auto-run commands: {local_runtime['safe_to_auto_run_commands']['value']}",
        f"Select fields: {next_detail['select']}",
        f"Verbose diagnostics: {next_detail['verbose']}",
    ]
    return '\n'.join(lines) + '\n'


def _emit_config_compact_text(payload: dict[str, Any]) -> str:
    workspace = payload['workspace']
    local_runtime = payload['local_runtime']
    lines = [
        f"Target: {payload['target']}",
        f"Config path: {payload['config_path']}",
        f"Exists: {payload['exists']}",
        f"AW enabled: {workspace['enabled']} ({workspace['enabled_source']})",
        f"Enabled modules: {', '.join(workspace['enabled_modules']) or '(none)'}",
        f"Improvement latitude: {workspace['improvement_latitude']}",
        f"Optimization bias: {workspace['optimization_bias']}",
        f"Workflow obligations: {len(workspace['workflow_obligations'])} configured",
        f"Delegation mode: {local_runtime['delegation_mode']['value']}",
        f"Safe to auto-run commands: {local_runtime['safe_to_auto_run_commands']['value']}",
        f"Full profile: {payload['full_profile_command']}",
    ]
    return '\n'.join(lines) + '\n'


def _emit_config_full_text(payload: dict[str, Any]) -> str:
    workspace = payload['workspace']
    edit_reference = payload['edit_reference']
    mixed_agent = payload['mixed_agent']
    lines = [
        f"Target: {payload['target']}",
        f"Config path: {payload['config_path']}",
        f"Exists: {payload['exists']}",
        f"AW enabled: {workspace['enabled']} ({workspace['enabled_source']})",
        f"Reference: {edit_reference['reference_doc']}",
        f"Schema: {edit_reference['source_schema']}",
        f"Check command: {edit_reference['check_command']}",
    ]
    warnings = payload['warnings']
    if warnings:
        lines.append('Warnings:')
        lines.extend(f'- {warning}' for warning in warnings)
    lines.extend([
        f"Enabled modules: {', '.join(workspace['enabled_modules']) or '(none)'}",
        f"Agent instructions file: {workspace['agent_instructions_file']} ({workspace['agent_instructions_file_source']})",
        f"Workflow artifact profile: {workspace['workflow_artifact_profile']} ({workspace['workflow_artifact_profile_source']})",
        f"Agent configuration substrate: {workspace['agent_configuration_substrate']['canonical_doc']} ({workspace['agent_configuration_substrate']['owner_surface']})",
        f"System-intent sources: {', '.join(workspace['system_intent']['sources']) or 'none'} ({workspace['system_intent']['sources_source']})",
        f"Workflow obligations: {len(workspace['workflow_obligations'])} configured",
        f"Improvement latitude: {workspace['improvement_latitude']} ({workspace['improvement_latitude_source']})",
        f"Optimization bias: {workspace['optimization_bias']} ({workspace['optimization_bias_source']})",
        f"Advanced features: {', '.join(workspace['advanced_features']) or 'none'} ({workspace['advanced_features_source']})",
        f"CLI invoke: {workspace['cli_invoke']} ({workspace['cli_invoke_source']})",
        f"Wrapper rule: {payload['update']['wrapper_rule']}",
        'Update modules:',
    ])
    for module in payload['update']['modules']:
        lines.append(f"- {module['module']}: {module['source_type']} {module['source_ref']}")
        lines.append(f"  label: {module['source_label']}")
        lines.append(f"  metadata: {module['metadata_path']} ({module['sync_status']})")
    lines.extend([
        'Mixed-agent:',
        f"- rule: {mixed_agent['rule']}",
        f"- repo policy: {mixed_agent['repo_policy']['path']} ({mixed_agent['repo_policy']['source']})",
        f"- local override: {mixed_agent['local_override']['path']} ({mixed_agent['local_override']['status']})",
        f"- local integration area: {mixed_agent['local_integration_area']['root']} ({mixed_agent['local_integration_area']['status']})",
        f"- effective posture: internal delegation={mixed_agent['effective_posture']['supports_internal_delegation']['value']}, strong planner={mixed_agent['effective_posture']['strong_planner_available']['value']}, cheap bounded executor={mixed_agent['effective_posture']['cheap_bounded_executor_available']['value']}",
        f"- delegation targets: {len(mixed_agent['delegation_targets']['profiles'])} configured",
        f"- delegation outcome evidence: {mixed_agent['delegation_targets']['outcome_artifact']['path']} ({mixed_agent['delegation_targets']['outcome_artifact']['status']})",
    ])
    return '\n'.join(lines) + '\n'




def _append_workspace_operation_delegation_outcome(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _append_workspace_operation_delegation_outcome as source_function

    return source_function(*args, **kwargs)


def _emit_workspace_config_output(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Any:
    result = values['result']
    output_format = str(values.get('format') or 'text')
    if not isinstance(result, dict):
        raise ValueError('workspace config output requires an object result payload')
    if output_format == 'json':
        print(json.dumps(_serialise_value(result), indent=2))
        return None
    if result.get('kind') == 'agentic-workspace/selected-output/v1':
        print(_emit_selected_output_text(result), end='')
        return None
    if result.get('kind') == 'agentic-workspace/config-tiny/v1':
        print(_emit_config_tiny_text(result), end='')
        return None
    if result.get('profile') == 'compact':
        print(_emit_config_compact_text(result), end='')
        return None
    print(_emit_config_full_text(result), end='')
    return None


def _emit_workspace_operation_output(values: dict[str, Any], arguments: dict[str, Any], context: Any) -> Any:
    result = values['result']
    selected_output_kind = 'agentic-workspace/selected-output/v1'
    sectioned_payload_kind = 'agentic-workspace/defaults-router/v1'
    delegation_outcomes_kind = 'agentic-workspace/delegation-outcomes/v1'
    if str(values.get('format') or 'text') == 'json' and isinstance(result, dict):
        print(json.dumps(_serialise_value(values['result']), indent=2))
        return None
    if isinstance(result, dict) and (isinstance(result.get('route_report_summary'), dict) or result.get('kind') == 'memory-module-report/v1' or (result.get('kind') == 'planning-module-report/v1' and result.get('profile') == 'tiny')):
        from .primitive_executor import _emit_output

        print(_emit_output(values=values, arguments=arguments), end='')
        return None
    if isinstance(result, dict) and result.get('kind') == sectioned_payload_kind:
        print(_emit_tiny_sectioned_text(result), end='')
        return None
    if isinstance(result, dict) and result.get('profile') == 'compact-contract-answer/v1':
        print(_emit_compact_answer_text(result), end='')
        return None
    if isinstance(result, dict) and result.get('kind') == selected_output_kind:
        print(_emit_selected_output_text(result), end='')
        return None
    if delegation_outcomes_kind and isinstance(result, dict) and result.get('kind') == delegation_outcomes_kind:
        print(_emit_delegation_outcomes_text(result), end='')
        return None
    from agentic_workspace.workspace_runtime_primitives import _emit_workspace_operation_output as source_function

    return source_function(values, arguments, context)


def _load_workspace_operation_config(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _load_workspace_operation_config as source_function

    return source_function(*args, **kwargs)


def _load_workspace_operation_defaults(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> dict[str, Any]:
    from .resources import find_resource_root, read_json_object

    resource_root = find_resource_root(__file__, [('_contracts', 'payload.json')])
    return read_json_object(resource_root, 'payload.json')


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


def _resolve_workspace_operation_target_root(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Path:
    target_value = values.get('target')
    target_root = Path(str(target_value)).resolve() if target_value else Path.cwd().resolve()
    if not target_root.exists():
        raise ValueError(f'Target path does not exist: {target_root}')
    if not target_root.is_dir():
        raise ValueError(f'Target path is not a directory: {target_root}')
    return target_root


def _run_checkpoint_write_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_checkpoint_write_adapter as source_function

    return source_function(*args, **kwargs)


def _run_external_intent_refresh_github_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_external_intent_refresh_github_adapter as source_function

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


def _run_reconcile_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_reconcile_report_adapter as source_function

    return source_function(*args, **kwargs)


def _run_report_combined_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_report_combined_adapter as source_function

    return source_function(*args, **kwargs)


def _run_setup_guidance_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_setup_guidance_adapter as source_function

    return source_function(*args, **kwargs)


def _run_summary_report_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_summary_report_adapter as source_function

    return source_function(*args, **kwargs)


def _select_workspace_operation_defaults(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> dict[str, Any]:
    payload = values['defaults_payload']
    section = values.get('section')
    if section is not None:
        payload = _select_section(payload, section=str(section), source_command='defaults', command_ref='agentic-workspace defaults --format json', compact_profile_ref='.agentic-workspace/docs/compact-contract-profile.md')
    elif ('full' if values.get('verbose') else str(values.get('profile') or 'tiny')) == 'tiny':
        payload = _tiny_sectioned_payload(payload, common_sections=['startup', 'proof_surfaces', 'memory_routing', 'capability_routing', 'closeout_trust', 'compact_contract_profile', 'workflow_sufficiency', 'authority_hierarchy', 'compliance_economics'], sectioned_payload_kind='agentic-workspace/defaults-router/v1', section_detail_command='agentic-workspace defaults --section <section> --format json', full_detail_command='agentic-workspace defaults --verbose --format json')
    select = values.get('select')
    if select is not None:
        payload = _select_payload_fields(payload, select=str(select), source_command='defaults', selected_output_kind='agentic-workspace/selected-output/v1')
    return _serialise_value(payload)


__all__ = [
    '_append_workspace_operation_delegation_outcome',
    '_emit_workspace_config_output',
    '_emit_workspace_operation_output',
    '_load_workspace_operation_config',
    '_load_workspace_operation_defaults',
    '_load_workspace_operation_system_intent_config',
    '_read_or_create_workspace_operation_system_intent_mirror',
    '_refresh_workspace_operation_system_intent_metadata',
    '_render_workspace_operation_prompt',
    '_resolve_workspace_operation_selection',
    '_resolve_workspace_operation_target_root',
    '_run_checkpoint_write_adapter',
    '_run_external_intent_refresh_github_adapter',
    '_run_init_lifecycle_adapter',
    '_run_lifecycle_mutation_adapter',
    '_run_lifecycle_report_adapter',
    '_run_reconcile_report_adapter',
    '_run_report_combined_adapter',
    '_run_setup_guidance_adapter',
    '_run_summary_report_adapter',
    '_select_workspace_operation_defaults',
]
