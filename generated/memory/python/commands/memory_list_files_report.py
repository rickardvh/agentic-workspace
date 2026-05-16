"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Operation: memory.list-files.report
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

BOOTSTRAP_VERSION = 47
PROJECT_MARKERS = ('pyproject.toml', 'package.json', 'Cargo.toml', '.hg')
AGENTS_PATH = Path('AGENTS.md')
MANAGED_ROOT = Path('.agentic-workspace/memory')
VERSION_PATH = MANAGED_ROOT / 'VERSION.md'
LEGACY_VERSION_PATH = Path('memory/system/VERSION.md')
BOOTSTRAP_WORKSPACE_ROOT = MANAGED_ROOT / 'bootstrap'
SHIPPED_SKILLS_ROOT = MANAGED_ROOT / 'skills'
LEGACY_SYSTEM_ROOT = Path('memory/system')
LEGACY_BOOTSTRAP_WORKSPACE_ROOT = Path('memory/bootstrap')
LEGACY_SHIPPED_SKILLS_ROOT = Path('memory/skills')
VERSION_RE = re.compile(r'bootstrap version:\s*(\d+)', re.IGNORECASE)


class RepoDetectionError(RuntimeError):
    pass


def _payload_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / '_payload', parent / 'packages' / 'memory' / 'bootstrap'):
            if (candidate / 'AGENTS.template.md').is_file():
                return candidate
    raise FileNotFoundError('Bootstrap payload directory is not available.')


def _find_repo_candidates(start: Path) -> list[Path]:
    candidates = []
    for path in (start, *start.parents):
        if any((path / marker).exists() for marker in PROJECT_MARKERS) or (path / '.git').exists():
            candidates.append(path)
    return candidates


def _resolve_target_root(target: str | None) -> Path:
    explicit = target is not None
    start = Path(target or Path.cwd()).resolve()
    if not start.exists():
        raise RepoDetectionError(f'Target does not exist: {start}')
    if start.is_file():
        raise RepoDetectionError(f'Target must be a directory: {start}')
    if explicit:
        return start
    candidates = _find_repo_candidates(start)
    if not candidates:
        raise RepoDetectionError('Could not find a repository root from the current directory. Pass --target explicitly.')
    if len(candidates) > 1:
        roots = ', '.join(str(path) for path in candidates)
        raise RepoDetectionError(f'Ambiguous repository root detected ({roots}). Pass --target explicitly. Retry with --target .')
    return candidates[0]


def _target_relative_path(relative_path: Path) -> Path:
    path_str = relative_path.as_posix()
    if path_str.startswith('docs/'):
        return Path('.agentic-workspace/docs') / relative_path.relative_to('docs')
    if path_str.startswith('memory/system/'):
        return Path('.agentic-workspace/memory') / relative_path.relative_to('memory/system')
    if path_str.startswith('memory/bootstrap/'):
        return Path('.agentic-workspace/memory/bootstrap') / relative_path.relative_to('memory/bootstrap')
    if path_str.startswith('memory/skills/'):
        return Path('.agentic-workspace/memory/skills') / relative_path.relative_to('memory/skills')
    if path_str.startswith('memory/'):
        return Path('.agentic-workspace/memory/repo') / relative_path.relative_to('memory')
    return relative_path


def _classify_role(relative_path: Path) -> str:
    path_str = relative_path.as_posix()
    if relative_path == AGENTS_PATH:
        return 'local-entrypoint'
    if path_str.startswith('.agentic-workspace/memory/repo/templates/'):
        return 'shared-template'
    if path_str in {
        '.agentic-workspace/memory/repo/index.md',
        '.agentic-workspace/memory/repo/mistakes/recurring-failures.md',
        '.agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md',
    }:
        return 'seed-note'
    if path_str.startswith('.agentic-workspace/memory/repo/current/'):
        return 'seed-note'
    if path_str.startswith('.agentic-workspace/memory/'):
        return 'shared-replaceable'
    if path_str.startswith(BOOTSTRAP_WORKSPACE_ROOT.as_posix()):
        return 'shared-replaceable'
    if path_str.startswith(SHIPPED_SKILLS_ROOT.as_posix()):
        return 'shared-replaceable'
    if path_str.endswith('/README.md'):
        return 'seed-note'
    return 'managed-file'


def _strategy_for_role(role: str) -> str:
    return {
        'local-entrypoint': 'patch-or-review',
        'shared-replaceable': 'replace',
        'shared-template': 'replace',
        'seed-note': 'seed',
        'managed-file': 'create-only',
    }[role]


def _payload_entries(source_root: Path) -> list[dict[str, str]]:
    entries = []
    seen = set()
    for relative_root in (AGENTS_PATH, Path('.agentic-workspace'), Path('memory'), Path('docs')):
        source_path = source_root / relative_root
        if not source_path.exists() and relative_root.name.endswith('.md'):
            template_path = source_root / relative_root.with_name(relative_root.name.replace('.md', '.template.md'))
            if template_path.exists():
                source_path = template_path
        if not source_path.exists():
            continue
        children = [source_path] if source_path.is_file() else sorted(path for path in source_path.rglob('*') if path.is_file())
        for child in children:
            source_relative = child.relative_to(source_root)
            target_relative = source_relative
            if target_relative.name.endswith('.template.md'):
                target_relative = target_relative.with_name(target_relative.name.replace('.template.md', '.md'))
            target_relative = _target_relative_path(target_relative)
            if target_relative in seen:
                continue
            seen.add(target_relative)
            role = _classify_role(target_relative)
            entries.append({
                'relative_path': target_relative.as_posix(),
                'role': role,
                'strategy': _strategy_for_role(role),
                'kind': 'managed file',
                'source': target_relative.as_posix(),
                'source_relative': source_relative.as_posix(),
            })
    return entries


def _read_installed_version(target_root: Path) -> int | None:
    for relative in (VERSION_PATH, LEGACY_VERSION_PATH):
        path = target_root / relative
        if path.exists():
            match = VERSION_RE.search(path.read_text(encoding='utf-8'))
            return int(match.group(1)) if match else None
    return None


def _detect_mode(target_root: Path) -> str:
    if any((target_root / path).exists() for path in (MANAGED_ROOT, BOOTSTRAP_WORKSPACE_ROOT, SHIPPED_SKILLS_ROOT)):
        return 'full'
    return 'augment'


def _action(entry: dict[str, str], target_root: Path) -> dict[str, str]:
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


def _assemble_payload(target_root: Path, payload_root: Path) -> dict[str, Any]:
    entries = sorted(_payload_entries(payload_root), key=lambda item: (item['kind'], item['relative_path'], item['source']))
    return {
        'target_root': str(target_root),
        'dry_run': True,
        'mode': _detect_mode(target_root),
        'message': 'Packaged bootstrap file preview',
        'detected_version': _read_installed_version(target_root),
        'bootstrap_version': BOOTSTRAP_VERSION,
        'actions': [_action(entry, target_root) for entry in entries],
        'route_summary': {},
        'missing_note_hint': '',
        'review_summary': {},
        'review_cases': [],
        'sync_summary': {},
        'route_report_summary': {},
        'route_report_feedback_cases': [],
        'route_report_fixture_results': [],
    }


def _emit_output(payload: dict[str, Any], output_format: str) -> None:
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


def run(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(getattr(args, 'target', None))
    payload = _assemble_payload(target_root, _payload_root())
    _emit_output(payload, str(getattr(args, 'format', 'text') or 'text'))
    return 0
