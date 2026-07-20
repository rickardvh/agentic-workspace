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


def _field_by_path(payload: Any, path: str, *, copy_value: bool = True) -> tuple[bool, Any]:
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
    return (True, copy.deepcopy(current) if copy_value else None)


_MAX_PROJECTION_SELECTORS = 32
_MAX_PROJECTION_SELECTOR_BYTES = 256
_MAX_PROJECTION_SELECTOR_REQUEST_BYTES = 512
_MAX_SELECTOR_ERROR_TEXT_BYTES = 128
_MAX_SELECTOR_INVENTORY_SAMPLE_PATH_BYTES = 96
_MAX_SELECTOR_INVENTORY_SAMPLE_BYTES = 384
_MAX_SELECTOR_ERROR_ENVELOPE_BYTES = 6000
_SELECTOR_INVENTORY_SAMPLE_LIMIT = 8
_SELECTOR_SUGGESTION_LIMIT = 1


def _utf8_size(value: str) -> int:
    return len(value.encode('utf-8'))


def _utf8_sort_key(value: str) -> bytes:
    return value.encode('utf-8')


def _bounded_selector_error_text(value: str) -> str:
    return value if _utf8_size(value) <= _MAX_SELECTOR_ERROR_TEXT_BYTES else ''


def _selector_error_json_size(payload: dict[str, Any]) -> int:
    return _utf8_size(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))


def _fit_selector_error_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    if _selector_error_json_size(payload) <= _MAX_SELECTOR_ERROR_ENVELOPE_BYTES:
        return payload
    suggestions = payload.get('suggestions')
    if isinstance(suggestions, dict):
        suggestions.clear()
    if _selector_error_json_size(payload) <= _MAX_SELECTOR_ERROR_ENVELOPE_BYTES:
        return payload
    inventory = payload.get('selector_inventory')
    if isinstance(inventory, dict):
        inventory['sample'] = []
        inventory['discovery_command'] = ''
        inventory['inventory_command'] = ''
    if _selector_error_json_size(payload) <= _MAX_SELECTOR_ERROR_ENVELOPE_BYTES:
        return payload
    payload['requested_selectors'] = []
    payload['unknown_selectors'] = []
    return payload


def _selector_tokens(select: str | None) -> dict[str, Any]:
    selectors: list[str] = []
    requested_selector_count = 0
    selector_request_bytes = 0
    token_chars: list[str] = []
    token_bytes = 0
    pending_whitespace = 0
    seen_non_whitespace = False

    def limit_error(*, reason: str, selector_request_bytes_value: int, selector_index: int | None = None, selector_bytes: int | None = None) -> dict[str, Any]:
        error: dict[str, Any] = {'reason': reason, 'requested_selector_count': requested_selector_count, 'selector_request_bytes': selector_request_bytes_value, 'max_selectors': _MAX_PROJECTION_SELECTORS, 'max_selector_bytes': _MAX_PROJECTION_SELECTOR_BYTES, 'max_selector_request_bytes': _MAX_PROJECTION_SELECTOR_REQUEST_BYTES}
        if selector_index is not None:
            error['selector_index'] = selector_index
        if selector_bytes is not None:
            error['selector_bytes'] = selector_bytes
        return error

    def append_selector() -> dict[str, Any] | None:
        nonlocal requested_selector_count, selector_request_bytes, token_chars, token_bytes, pending_whitespace
        token = ''.join(token_chars)
        token_chars = []
        appended_token_bytes = token_bytes
        token_bytes = 0
        pending_whitespace = 0
        if not token:
            return None
        requested_selector_count += 1
        if requested_selector_count > _MAX_PROJECTION_SELECTORS:
            return limit_error(reason='too-many-selectors', selector_request_bytes_value=selector_request_bytes, selector_index=requested_selector_count - 1)
        if selector_request_bytes + appended_token_bytes > _MAX_PROJECTION_SELECTOR_REQUEST_BYTES:
            return limit_error(reason='selector-request-too-large', selector_request_bytes_value=selector_request_bytes + appended_token_bytes, selector_index=requested_selector_count - 1)
        selector_request_bytes += appended_token_bytes
        selectors.append(token)
        return None

    for char in str(select or ''):
        if char == ',':
            error = append_selector()
            if error is not None:
                return {'selectors': selectors, 'error': error}
            seen_non_whitespace = False
            continue
        if char.isspace() and not seen_non_whitespace:
            continue
        if char.isspace():
            pending_whitespace += 1
            continue
        if pending_whitespace:
            token_chars.extend(' ' * pending_whitespace)
            token_bytes += pending_whitespace
            pending_whitespace = 0
        seen_non_whitespace = True
        token_chars.append(char)
        token_bytes += _utf8_size(char)
        if token_bytes > _MAX_PROJECTION_SELECTOR_BYTES:
            requested_selector_count += 1
            error = limit_error(reason='selector-too-long', selector_request_bytes_value=selector_request_bytes + token_bytes, selector_index=requested_selector_count - 1, selector_bytes=token_bytes)
            return {'selectors': selectors, 'error': error}
    error = append_selector()
    return {'selectors': selectors, 'error': error}


def _selector_inventory_summary(payload: Any, sample_limit: int = 8) -> tuple[int, list[str]]:
    count = 0
    sample_candidates: list[str] = []
    def record_sample(path: str) -> None:
        if sample_limit <= 0:
            return
        path_bytes = _utf8_size(path)
        if path_bytes > _MAX_SELECTOR_INVENTORY_SAMPLE_PATH_BYTES:
            return
        sample_candidates.append(path)
        sample_candidates.sort(key=_utf8_sort_key)
        if len(sample_candidates) > sample_limit:
            sample_candidates.pop()

    def budgeted_sample() -> list[str]:
        sample: list[str] = []
        sample_bytes = 0
        for path in sample_candidates:
            path_bytes = _utf8_size(path)
            if sample_bytes + path_bytes > _MAX_SELECTOR_INVENTORY_SAMPLE_BYTES:
                break
            sample.append(path)
            sample_bytes += path_bytes
        return sample

    def visit(current: Any, prefix: str) -> None:
        nonlocal count
        if isinstance(current, dict):
            entries = current.items()
        elif isinstance(current, list):
            entries = enumerate(current)
        else:
            return
        for key, value in entries:
            path = f'{prefix}.{key}' if prefix else str(key)
            count += 1
            record_sample(path)
            visit(value, path)
    visit(payload, '')
    return count, budgeted_sample()


def _selector_validation_kind(selected_output_kind: str) -> str:
    if '/selected-output/' in selected_output_kind:
        kind = selected_output_kind.replace('/selected-output/', '/selector-validation-error/', 1)
    elif selected_output_kind.endswith('/selected-output'):
        kind = f"{selected_output_kind.removesuffix('/selected-output')}/selector-validation-error"
    else:
        kind = 'command-generation/selector-validation-error/v1'
    if _utf8_size(kind) <= _MAX_SELECTOR_ERROR_TEXT_BYTES:
        return kind
    return 'command-generation/selector-validation-error/v1'


def _selector_suggestions(unknown: str, available: list[str], *, limit: int = 3) -> list[str]:
    terms = [part for part in unknown.replace('_', '.').split('.') if part]
    matches: list[str] = []
    for selector in available:
        selector_terms = selector.split('.')
        if unknown in selector or any(term in selector_terms or term in selector for term in terms):
            matches.append(selector)
        if len(matches) >= limit:
            return matches
    return available[:limit]


def _selector_validation_error(*, payload: Any, selectors: list[str], missing: list[str], source_command: str, selected_output_kind: str, discovery_command: str, detail_command: str) -> dict[str, Any]:
    sample_limit = _SELECTOR_INVENTORY_SAMPLE_LIMIT
    available_count, available = _selector_inventory_summary(payload, sample_limit=sample_limit)
    error = {
        'kind': _selector_validation_kind(selected_output_kind),
        'status': 'invalid-selector',
        'source_command': _bounded_selector_error_text(source_command),
        'requested_selectors': selectors,
        'unknown_selectors': missing,
        'selector_inventory': {
            'status': 'omitted-from-validation-error',
            'available_count': available_count,
            'sample': available,
            'sample_limit': sample_limit,
            'discovery_command': _bounded_selector_error_text(discovery_command),
            'inventory_command': _bounded_selector_error_text(detail_command),
            'rule': 'Full selector inventories are omitted from validation errors; use the inventory command for complete details.',
        },
        'suggestions': {selector: _selector_suggestions(selector, available, limit=_SELECTOR_SUGGESTION_LIMIT) for selector in missing},
        'validation_rule': 'Selector requests are atomic: any unknown selector prevents partial projection output.',
    }


    return _fit_selector_error_envelope(error)


def _selector_request_validation_error(*, selectors: list[str], request_error: dict[str, Any], source_command: str, selected_output_kind: str) -> dict[str, Any]:
    error = {
        'kind': _selector_validation_kind(selected_output_kind),
        'status': 'invalid-selector-request',
        'source_command': _bounded_selector_error_text(source_command),
        'requested_selectors': selectors,
        'selector_request': {'status': 'rejected', **request_error},
        'validation_rule': 'Selector requests are bounded and atomic: too many selectors or overlong selectors are rejected before projection.',
    }


    return _fit_selector_error_envelope(error)


def _select_payload_fields(payload: dict[str, Any], *, select: str | None, source_command: str, selected_output_kind: str, discovery_command: str, detail_command: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    missing: list[str] = []
    selector_request = _selector_tokens(select)
    selectors = selector_request['selectors']
    request_error = selector_request['error']
    if request_error is not None:
        return _selector_request_validation_error(selectors=selectors, request_error=request_error, source_command=source_command, selected_output_kind=selected_output_kind)
    missing = [selector for selector in selectors if not _field_by_path(payload, selector, copy_value=False)[0]]
    if missing:
        return _selector_validation_error(payload=payload, selectors=selectors, missing=missing, source_command=source_command, selected_output_kind=selected_output_kind, discovery_command=discovery_command, detail_command=detail_command)
    for selector in selectors:
        found, value = _field_by_path(payload, selector)
        if found:
            values[selector] = value
        else:
            missing.append(selector)
    selected: dict[str, Any] = {'kind': selected_output_kind, 'source_command': source_command, 'values': values}
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




def _append_workspace_operation_delegation_outcome(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _append_workspace_operation_delegation_outcome as source_function

    return source_function(*args, **kwargs)


def _emit_workspace_operation_output(values: dict[str, Any], arguments: dict[str, Any], context: Any) -> Any:
    result = values['result']
    selected_output_kind = 'agentic-workspace/selected-output/v1'
    sectioned_payload_kind = 'agentic-workspace/defaults-router/v1'
    delegation_outcomes_kind = 'agentic-workspace/delegation-outcomes/v1'
    if str(values.get('format') or 'text') == 'json' and isinstance(result, dict):
        print(json.dumps(_serialise_value(values['result']), indent=2))
        return None
    if isinstance(result, dict) and arguments.get('text_views'):
        from .primitive_executor import _emit_output

        print(_emit_output(values=values, arguments=arguments), end='')
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


def _resolve_workspace_operation_target_root(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Path:
    target_value = values.get('target')
    target_root = Path(str(target_value)).resolve() if target_value else Path.cwd().resolve()
    if not target_root.exists():
        raise ValueError(f'Target path does not exist: {target_root}')
    if not target_root.is_dir():
        raise ValueError(f'Target path is not a directory: {target_root}')
    return target_root


def _run_autopilot_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_autopilot_adapter as source_function

    return source_function(*args, **kwargs)


def _run_checkpoint_write_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_checkpoint_write_adapter as source_function

    return source_function(*args, **kwargs)


def _run_external_intent_refresh_github_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_external_intent_refresh_github_adapter as source_function

    return source_function(*args, **kwargs)


def _run_final_response_admit_adapter(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _run_final_response_admit_adapter as source_function

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


def _select_workspace_operation_defaults(*args: Any, **kwargs: Any) -> Any:
    from agentic_workspace.workspace_runtime_primitives import _select_workspace_operation_defaults as source_function

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
    '_run_autopilot_adapter',
    '_run_checkpoint_write_adapter',
    '_run_external_intent_refresh_github_adapter',
    '_run_final_response_admit_adapter',
    '_run_init_lifecycle_adapter',
    '_run_lifecycle_mutation_adapter',
    '_run_lifecycle_report_adapter',
    '_run_reconcile_report_adapter',
    '_run_report_combined_adapter',
    '_run_setup_guidance_adapter',
    '_run_summary_report_adapter',
    '_select_workspace_operation_defaults',
]
