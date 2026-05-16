"""Generated target-local resource and output primitives.

Source: src/agentic_workspace/contracts/command_package_ir.json
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

# DO NOT EDIT DIRECTLY.
# Primitive behavior changes belong to command_generation's Python target renderer.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py


ResourceCandidate = tuple[str, str]


def find_resource_root(anchor_file: str, candidates: Iterable[ResourceCandidate]) -> Path:
    for parent in Path(anchor_file).resolve().parents:
        for relative_root, marker in candidates:
            candidate = parent.joinpath(*Path(relative_root).parts)
            if (candidate / marker).is_file():
                return candidate
    rendered = ', '.join(f'{root} with marker {marker}' for root, marker in candidates)
    raise FileNotFoundError(f'Resource root is not available for any candidate: {rendered}')


def list_resource_files(root: Path) -> list[str]:
    return [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob('*'))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'
    ]


def read_json_object(root: Path, relative_path: str) -> dict[str, Any]:
    payload = json.loads((root / relative_path).read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise RuntimeError(f'{relative_path} must parse to an object')
    return payload


def emit_json_or_lines(payload: dict[str, Any], output_format: str, *, line_field: str) -> None:
    if output_format == 'json':
        print(json.dumps(payload, indent=2))
        return
    lines = payload.get(line_field, [])
    if not isinstance(lines, list):
        raise RuntimeError(f'{line_field} must be a list for text emission')
    for line in lines:
        print(str(line))


def find_repo_candidates(start: Path, project_markers: Iterable[str]) -> list[Path]:
    candidates = []
    for path in (start, *start.parents):
        marker_found = any((path / marker).exists() for marker in project_markers)
        if marker_found or (path / '.git').exists():
            candidates.append(path)
    return candidates


def resolve_repo_target_root(target: str | None, project_markers: Iterable[str]) -> Path:
    explicit = target is not None
    start = Path(target or Path.cwd()).resolve()
    if not start.exists():
        raise RuntimeError(f'Target does not exist: {start}')
    if start.is_file():
        raise RuntimeError(f'Target must be a directory: {start}')
    if explicit:
        return start
    candidates = find_repo_candidates(start, project_markers)
    if not candidates:
        message = 'Could not find a repository root from the current directory. Pass --target explicitly.'
        raise RuntimeError(message)
    if len(candidates) > 1:
        roots = ', '.join(str(path) for path in candidates)
        raise RuntimeError(f'Ambiguous repository root detected ({roots}). Pass --target explicitly. Retry with --target .')
    return candidates[0]


def rewrite_relative_path(relative_path: Path, rules: Iterable[tuple[str, str]]) -> Path:
    path_str = relative_path.as_posix()
    for source_prefix, target_prefix in rules:
        normalized = source_prefix.rstrip('/')
        if path_str != normalized and not path_str.startswith(f'{normalized}/'):
            continue
        suffix = relative_path.relative_to(Path(normalized))
        return Path(target_prefix) / suffix
    return relative_path


def classify_relative_path(
    relative_path: Path,
    *,
    exact_roles: dict[str, str],
    prefix_roles: Iterable[tuple[str, str]],
    suffix_roles: Iterable[tuple[str, str]],
    default_role: str,
) -> str:
    path_str = relative_path.as_posix()
    if path_str in exact_roles:
        return exact_roles[path_str]
    for prefix, role in prefix_roles:
        if path_str.startswith(prefix):
            return role
    for suffix, role in suffix_roles:
        if path_str.endswith(suffix):
            return role
    return default_role


def project_payload_entries(
    source_root: Path,
    *,
    source_roots: Iterable[str],
    target_path_rewrites: Iterable[tuple[str, str]],
    exact_roles: dict[str, str],
    prefix_roles: Iterable[tuple[str, str]],
    suffix_roles: Iterable[tuple[str, str]],
    strategy_by_role: dict[str, str],
    default_role: str,
) -> list[dict[str, str]]:
    entries = []
    seen = set()
    for source_root_name in source_roots:
        relative_root = Path(source_root_name)
        source_path = source_root / relative_root
        if not source_path.exists() and relative_root.name.endswith('.md'):
            template_name = relative_root.name.replace('.md', '.template.md')
            template_path = source_root / relative_root.with_name(template_name)
            if template_path.exists():
                source_path = template_path
        if not source_path.exists():
            continue
        if source_path.is_file():
            children = [source_path]
        else:
            children = sorted(path for path in source_path.rglob('*') if path.is_file())
        for child in children:
            source_relative = child.relative_to(source_root)
            target_relative = source_relative
            if target_relative.name.endswith('.template.md'):
                target_name = target_relative.name.replace('.template.md', '.md')
                target_relative = target_relative.with_name(target_name)
            target_relative = rewrite_relative_path(target_relative, target_path_rewrites)
            if target_relative in seen:
                continue
            seen.add(target_relative)
            role = classify_relative_path(
                target_relative,
                exact_roles=exact_roles,
                prefix_roles=prefix_roles,
                suffix_roles=suffix_roles,
                default_role=default_role,
            )
            entries.append({
                'relative_path': target_relative.as_posix(),
                'role': role,
                'strategy': strategy_by_role[role],
                'kind': 'managed file',
                'source': target_relative.as_posix(),
                'source_relative': source_relative.as_posix(),
            })
    return entries


def read_first_matching_version(
    target_root: Path,
    relative_paths: Iterable[str],
    *,
    pattern: str,
    flags: int = re.IGNORECASE,
) -> int | None:
    version_pattern = re.compile(pattern, flags)
    for relative in relative_paths:
        path = target_root / relative
        if path.exists():
            match = version_pattern.search(path.read_text(encoding='utf-8'))
            return int(match.group(1)) if match else None
    return None


def detect_mode_by_existing_paths(
    target_root: Path,
    full_mode_paths: Iterable[str],
    *,
    full_mode: str,
    fallback_mode: str,
) -> str:
    if any((target_root / path).exists() for path in full_mode_paths):
        return full_mode
    return fallback_mode


def action_from_entry(entry: dict[str, str]) -> dict[str, str]:
    return {
        'kind': entry['kind'],
        'path': entry['relative_path'],
        'detail': entry['strategy'],
        'role': entry['role'],
        'safety': 'safe',
        'source': entry['source'],
        'category': 'safe-update',
        'remediation_kind': '',
        'remediation_target': '',
        'remediation_reason': '',
        'remediation_confidence': '',
        'memory_action': '',
        'match_source': '',
    }


def emit_action_report(payload: dict[str, Any], output_format: str) -> None:
    if output_format == 'json':
        print(json.dumps(payload, indent=2))
        return
    print(f"Target: {payload['target_root']}")
    print(str(payload['message']))
    detected = payload['detected_version']
    if detected is None:
        print(f"Detected version: none (payload version {payload['bootstrap_version']})")
    else:
        print(f"Detected version: {detected} (payload version {payload['bootstrap_version']})")
    for action in payload['actions']:
        print(
            f"- {action['kind']}: {action['path']} "
            f"({action['detail']}; role={action['role']}; safety={action['safety']}; category={action['category']})"
        )
