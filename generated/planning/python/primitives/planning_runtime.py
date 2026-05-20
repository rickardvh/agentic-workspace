"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

# DO NOT EDIT DIRECTLY.
# This generated-local seam makes remaining source-runtime delegates explicit per function.
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


def _select_payload_fields(payload: dict[str, Any], *, select: str | None, source_command: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    missing: list[str] = []
    for selector in _selector_tokens(select):
        found, value = _field_by_path(payload, selector)
        if found:
            values[selector] = value
        else:
            missing.append(selector)
    selected: dict[str, Any] = {'kind': 'agentic-workspace/selected-output/v1', 'source_command': source_command, 'values': values}
    if missing:
        selected['missing'] = missing
        selected['selector_rule'] = 'Comma-separated dot paths select exact JSON fields; unknown fields are reported in missing.'
        selected['available_selectors'] = _available_selectors_for_payload(payload)
    return selected


def _selector_refs(*, command: str, answer: Any) -> list[str]:
    refs = ['.agentic-workspace/docs/compact-contract-profile.md', command]
    if isinstance(answer, dict):
        for key in ('canonical_doc', 'command', 'path', 'surface', 'ledger_path'):
            value = answer.get(key)
            if isinstance(value, str) and value not in refs:
                refs.append(value)
    return refs


def _compact_contract_answer(*, surface: str, selector: dict[str, Any], answer: Any, refs: list[str]) -> dict[str, Any]:
    return {'profile': 'compact-contract-answer/v1', 'surface': surface, 'selector': selector, 'matched': True, 'answer': answer, 'refs': refs}


def _select_section(payload: dict[str, Any], *, section: str, source_command: str) -> dict[str, Any]:
    normalized = section.strip()
    if normalized not in payload:
        supported = ', '.join(sorted(str(key) for key in payload))
        raise ValueError(f'{source_command} --section must match one of: {supported}.')
    answer = payload[normalized]
    return _compact_contract_answer(surface=source_command, selector={'section': normalized}, answer=answer, refs=_selector_refs(command=f'agentic-workspace {source_command} --format json', answer=answer))


def _tiny_sectioned_payload(payload: dict[str, Any], *, common_sections: list[str]) -> dict[str, Any]:
    return {
        'kind': 'agentic-workspace/defaults-router/v1',
        'profile': 'tiny',
        'summary': 'Default-route contract sections are available on demand; request one section or full detail instead of loading the whole contract.',
        'available_sections': sorted(str(key) for key in payload),
        'common_sections': list(common_sections),
        'detail_commands': {'section': 'agentic-workspace defaults --section <section> --format json', 'full': 'agentic-workspace defaults --verbose --format json'},
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


def _emit_planning_module_report_text(payload: dict[str, Any]) -> str:
    status = payload.get('status', {})
    next_action = payload.get('next_action', {})
    lines = [
        f"Target: {payload.get('target_root')}",
        f"Command: {payload.get('module', 'planning')}",
        f"Health: {payload.get('health')}",
    ]
    if isinstance(status, dict):
        lines.append(
            'Status: '
            f"{status.get('active_todo_count', 0)} active TODO / "
            f"{status.get('queued_todo_count', 0)} queued TODO / "
            f"{status.get('active_execplan_count', 0)} active execplans / "
            f"{status.get('roadmap_lane_count', 0)} roadmap lanes / "
            f"{status.get('roadmap_candidate_count', 0)} roadmap candidates"
        )
    if isinstance(next_action, dict):
        lines.append(f"Next action: {next_action.get('summary', '')}")
    return '\n'.join(lines) + '\n'


def apply_planning_archive_plan_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_archive_plan_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_closeout_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_closeout_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_delegation_decision_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_delegation_decision_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_intake_artifact_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_intake_artifact_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_new_plan_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_new_plan_operation as source_function

    return source_function(*args, **kwargs)


def apply_planning_promote_to_plan_operation(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.runtime_projection import apply_planning_promote_to_plan_operation as source_function

    return source_function(*args, **kwargs)


def emit_planning_operation_output(values: dict[str, Any], arguments: dict[str, Any], context: Any) -> Any:
    result = values['result']
    if str(values.get('format') or 'text') == 'json' and isinstance(result, dict):
        print(json.dumps(_serialise_value(values['result']), indent=2))
        return None
    if isinstance(result, dict) and (isinstance(result.get('route_report_summary'), dict) or result.get('kind') == 'memory-module-report/v1'):
        from command_generation.primitive_executor import _emit_output

        print(_emit_output(values=values, arguments=arguments), end='')
        return None
    if isinstance(result, dict) and result.get('kind') == 'agentic-workspace/defaults-router/v1':
        print(_emit_tiny_sectioned_text(result), end='')
        return None
    if isinstance(result, dict) and result.get('profile') == 'compact-contract-answer/v1':
        print(_emit_compact_answer_text(result), end='')
        return None
    if isinstance(result, dict) and result.get('kind') == 'agentic-workspace/selected-output/v1':
        print(_emit_selected_output_text(result), end='')
        return None
    if isinstance(result, dict) and result.get('kind') == 'agentic-workspace/delegation-outcomes/v1':
        print(_emit_delegation_outcomes_text(result), end='')
        return None
    if isinstance(result, dict) and result.get('kind') == 'planning-module-report/v1' and result.get('profile') == 'tiny':
        print(_emit_planning_module_report_text(result), end='')
        return None
    from repo_planning_bootstrap.runtime_projection import emit_planning_operation_output as source_function

    return source_function(values, arguments, context)


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
    'apply_planning_closeout_operation',
    'apply_planning_delegation_decision_operation',
    'apply_planning_intake_artifact_operation',
    'apply_planning_new_plan_operation',
    'apply_planning_promote_to_plan_operation',
    'emit_planning_operation_output',
    'load_planning_reconcile_operation',
    'load_planning_summary_operation',
    'render_planning_prompt_operation',
]
