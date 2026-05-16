"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import copy
import json
import tomllib
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


class RepoDetectionError(ValueError):
    pass


def _has_git_boundary(path: Path) -> bool:
    git_dir = path / '.git'
    return git_dir.is_dir() or git_dir.is_file()


def _resolve_repo_target_root(target: Any) -> Path:
    explicit_target = target is not None
    start = Path(str(target)).resolve() if explicit_target else Path.cwd().resolve()
    if not start.exists():
        raise RepoDetectionError(f'Target does not exist: {start}')
    if not start.is_dir():
        raise RepoDetectionError(f'Target must be a directory: {start}')
    if explicit_target:
        return start
    markers = ('pyproject.toml', 'package.json', 'Cargo.toml', '.hg')
    candidates = [
        candidate
        for candidate in [start, *start.parents]
        if _has_git_boundary(candidate) or any((candidate / marker).exists() for marker in markers)
    ]
    if not candidates:
        raise RepoDetectionError('Could not find a repository root from the current directory. Pass --target explicitly.')
    if len(candidates) > 1:
        roots = ', '.join(str(path) for path in candidates)
        raise RepoDetectionError(f'Ambiguous repository root detected ({roots}). Pass --target explicitly. Retry with --target .')
    return candidates[0]


def _toml_table_record_counts(
    target_root: Path,
    *,
    relative_path: str,
    table_name: str,
    relevance_field: str,
    required_value: str,
    optional_value: str,
    routing_only_field: str,
) -> dict[str, object]:
    manifest_path = target_root / relative_path
    if not manifest_path.exists():
        return {'status': 'missing', 'note_count': 0, 'required_count': 0, 'optional_count': 0, 'routing_only_count': 0, 'path': relative_path}
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, tomllib.TOMLDecodeError):
        return {'status': 'invalid', 'note_count': 0, 'required_count': 0, 'optional_count': 0, 'routing_only_count': 0, 'path': relative_path}
    records = payload.get(table_name, {}) if isinstance(payload, dict) else {}
    record_values = list(records.values()) if isinstance(records, dict) else []
    required_count = 0
    optional_count = 0
    routing_only_count = 0
    for record in record_values:
        if not isinstance(record, dict):
            continue
        relevance = str(record.get(relevance_field, '')).strip().lower()
        if relevance == required_value:
            required_count += 1
        elif relevance == optional_value:
            optional_count += 1
        if bool(record.get(routing_only_field, False)):
            routing_only_count += 1
    return {
        'status': 'present',
        'note_count': len(record_values),
        'required_count': required_count,
        'optional_count': optional_count,
        'routing_only_count': routing_only_count,
        'path': relative_path,
    }


def _tiny_lifecycle_payload_from_toml_table_counts(
    *,
    target: Any,
    relative_path: str,
    table_name: str,
    relevance_field: str,
    required_value: str,
    optional_value: str,
    routing_only_field: str,
    message: str,
    dry_run: bool,
    detail_command: str,
    unhealthy_detail: str,
) -> dict[str, object]:
    target_root = _resolve_repo_target_root(target)
    counts = _toml_table_record_counts(
        target_root,
        relative_path=relative_path,
        table_name=table_name,
        relevance_field=relevance_field,
        required_value=required_value,
        optional_value=optional_value,
        routing_only_field=routing_only_field,
    )
    health = 'healthy' if counts['status'] == 'present' else 'attention-needed'
    return {
        'target_root': str(target_root),
        'dry_run': dry_run,
        'mode': '',
        'message': message,
        'health': health,
        'detected_version': None,
        'bootstrap_version': None,
        'action_count': 0 if health == 'healthy' else 1,
        'actions': [] if health == 'healthy' else [{'kind': counts['status'], 'path': counts['path'], 'detail': unhealthy_detail}],
        'active': counts,
        'detail_command': detail_command,
    }


def _tiny_memory_report_payload_from_toml_table_counts(
    *,
    target: Any,
    relative_path: str,
    table_name: str,
    relevance_field: str,
    required_value: str,
    optional_value: str,
    routing_only_field: str,
    detail_command: str,
    unhealthy_detail: str,
) -> dict[str, object]:
    target_root = _resolve_repo_target_root(target)
    counts = _toml_table_record_counts(
        target_root,
        relative_path=relative_path,
        table_name=table_name,
        relevance_field=relevance_field,
        required_value=required_value,
        optional_value=optional_value,
        routing_only_field=routing_only_field,
    )
    health = 'healthy' if counts['status'] == 'present' else 'attention-needed'
    findings = [] if health == 'healthy' else [{'severity': 'warning', 'path': counts['path'], 'message': unhealthy_detail}]
    return {
        'kind': 'memory-module-report/v1',
        'profile': 'tiny',
        'module': 'memory',
        'target_root': str(target_root),
        'health': health,
        'status': {
            'detected_version': None,
            'bootstrap_version': None,
            'note_count': counts['note_count'],
            'manifest_status': counts['status'],
        },
        'active': {
            'note_count': counts['note_count'],
            'manifest_note_count': counts['note_count'],
            'required_count': counts['required_count'],
            'optional_count': counts['optional_count'],
            'routing_only_count': counts['routing_only_count'],
        },
        'habitual_pull': {
            'status': 'available' if counts['status'] == 'present' else 'unavailable',
            'read_first': ['.agentic-workspace/memory/repo/index.md'],
            'do_not_bulk_read': True,
        },
        'promotion_pressure': {'status': 'not-evaluated', 'detail_command': detail_command},
        'trust': {'status': 'not-evaluated', 'detail_command': detail_command},
        'finding_count': len(findings),
        'findings': findings,
        'next_action': {
            'summary': 'No immediate memory action.' if health == 'healthy' else 'Run full memory report for remediation detail.',
            'commands': [] if health == 'healthy' else [detail_command],
        },
        'detail_commands': {
            'full': detail_command,
            'route': 'agentic-memory route --target . --files <paths> --format json',
        },
    }


def _emit_memory_operation_output(values: dict[str, Any], arguments: dict[str, Any], context: Any) -> Any:
    result = values['result']
    if str(values.get('format') or 'text') == 'json' and isinstance(result, dict):
        print(json.dumps(_serialise_value(values['result']), indent=2))
        return None
    from repo_memory_bootstrap.runtime_primitives import _emit_memory_operation_output as source_function

    return source_function(values, arguments, context)


def _load_memory_bootstrap_doctor(values: dict[str, Any], arguments: dict[str, Any], context: Any) -> Any:
    if str(values.get('format') or 'text') == 'json' and not values.get('verbose'):
        return _tiny_lifecycle_payload_from_toml_table_counts(
            target=values.get('target'),
            relative_path='.agentic-workspace/memory/repo/manifest.toml',
            table_name='notes',
            relevance_field='task_relevance',
            required_value='required',
            optional_value='optional',
            routing_only_field='routing_only',
            message='Doctor report',
            dry_run=True,
            detail_command='agentic-memory doctor --target . --verbose --format json',
            unhealthy_detail='memory manifest is not readable; run full doctor for remediation detail',
        )
    from repo_memory_bootstrap.runtime_primitives import _load_memory_bootstrap_doctor as source_function

    return source_function(values, arguments, context)


def _load_memory_bootstrap_status(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_bootstrap_status as source_function

    return source_function(*args, **kwargs)


def _load_memory_current(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_current as source_function

    return source_function(*args, **kwargs)


def _load_memory_prompt(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_prompt as source_function

    return source_function(*args, **kwargs)


def _load_memory_report(values: dict[str, Any], arguments: dict[str, Any], context: Any) -> Any:
    if str(values.get('format') or 'text') == 'json' and not values.get('verbose'):
        return _tiny_memory_report_payload_from_toml_table_counts(
            target=values.get('target'),
            relative_path='.agentic-workspace/memory/repo/manifest.toml',
            table_name='notes',
            relevance_field='task_relevance',
            required_value='required',
            optional_value='optional',
            routing_only_field='routing_only',
            detail_command='agentic-memory report --target . --verbose --format json',
            unhealthy_detail='Memory manifest is not readable; run full report for remediation detail.',
        )
    from repo_memory_bootstrap.runtime_primitives import _load_memory_report as source_function

    return source_function(values, arguments, context)


def _load_memory_route_report(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_route_report as source_function

    return source_function(*args, **kwargs)


__all__ = [
    '_emit_memory_operation_output',
    '_load_memory_bootstrap_doctor',
    '_load_memory_bootstrap_status',
    '_load_memory_current',
    '_load_memory_prompt',
    '_load_memory_report',
    '_load_memory_route_report',
]
