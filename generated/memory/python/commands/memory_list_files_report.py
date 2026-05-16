"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Operation: memory.list-files.report
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..primitives.resources import (
    action_from_entry,
    detect_mode_by_existing_paths,
    emit_action_report,
    find_resource_root,
    project_payload_entries,
    read_first_matching_version,
    resolve_repo_target_root,
)

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

BOOTSTRAP_VERSION = 47
PROJECT_MARKERS = ('pyproject.toml', 'package.json', 'Cargo.toml', '.hg')
PAYLOAD_ROOT_CANDIDATES = (('_payload', 'AGENTS.template.md'), ('packages/memory/bootstrap', 'AGENTS.template.md'))
PAYLOAD_SOURCE_ROOTS = ('AGENTS.md', '.agentic-workspace', 'memory', 'docs')
TARGET_PATH_REWRITES = (
    ('docs', '.agentic-workspace/docs'),
    ('memory/system', '.agentic-workspace/memory'),
    ('memory/bootstrap', '.agentic-workspace/memory/bootstrap'),
    ('memory/skills', '.agentic-workspace/memory/skills'),
    ('memory', '.agentic-workspace/memory/repo'),
)
EXACT_ROLE_RULES = {
    'AGENTS.md': 'local-entrypoint',
    '.agentic-workspace/memory/repo/index.md': 'seed-note',
    '.agentic-workspace/memory/repo/mistakes/recurring-failures.md': 'seed-note',
    '.agentic-workspace/memory/repo/runbooks/recurring-friction-ledger.md': 'seed-note',
}
PREFIX_ROLE_RULES = (
    ('.agentic-workspace/memory/repo/templates/', 'shared-template'),
    ('.agentic-workspace/memory/repo/current/', 'seed-note'),
    ('.agentic-workspace/memory/', 'shared-replaceable'),
)
SUFFIX_ROLE_RULES = (('/README.md', 'seed-note'),)
STRATEGY_BY_ROLE = {
    'local-entrypoint': 'patch-or-review',
    'shared-replaceable': 'replace',
    'shared-template': 'replace',
    'seed-note': 'seed',
    'managed-file': 'create-only',
}
VERSION_PATHS = ('.agentic-workspace/memory/VERSION.md', 'memory/system/VERSION.md')
FULL_MODE_PATHS = (
    '.agentic-workspace/memory',
    '.agentic-workspace/memory/bootstrap',
    '.agentic-workspace/memory/skills',
)


def _assemble_payload(target_root: Path, payload_root: Path) -> dict[str, Any]:
    entries = project_payload_entries(
        payload_root,
        source_roots=PAYLOAD_SOURCE_ROOTS,
        target_path_rewrites=TARGET_PATH_REWRITES,
        exact_roles=EXACT_ROLE_RULES,
        prefix_roles=PREFIX_ROLE_RULES,
        suffix_roles=SUFFIX_ROLE_RULES,
        strategy_by_role=STRATEGY_BY_ROLE,
        default_role='managed-file',
    )
    entries = sorted(entries, key=lambda item: (item['kind'], item['relative_path'], item['source']))
    return {
        'target_root': str(target_root),
        'dry_run': True,
        'mode': detect_mode_by_existing_paths(target_root, FULL_MODE_PATHS, full_mode='full', fallback_mode='augment'),
        'message': 'Packaged bootstrap file preview',
        'detected_version': read_first_matching_version(target_root, VERSION_PATHS, pattern=r'bootstrap version:\s*(\d+)'),
        'bootstrap_version': BOOTSTRAP_VERSION,
        'actions': [action_from_entry(entry) for entry in entries],
        'route_summary': {},
        'missing_note_hint': '',
        'review_summary': {},
        'review_cases': [],
        'sync_summary': {},
        'route_report_summary': {},
        'route_report_feedback_cases': [],
        'route_report_fixture_results': [],
    }


def run(args: argparse.Namespace) -> int:
    target_root = resolve_repo_target_root(getattr(args, 'target', None), PROJECT_MARKERS)
    payload = _assemble_payload(target_root, find_resource_root(__file__, PAYLOAD_ROOT_CANDIDATES))
    emit_action_report(payload, str(getattr(args, 'format', 'text') or 'text'))
    return 0
