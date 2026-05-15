"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Operation: memory.list-skills.report
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# DO NOT EDIT DIRECTLY.
# Command behavior changes belong in src/agentic_workspace/contracts/command_package_ir.json and the referenced operation contract.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py


def _skills_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / '_skills', parent / 'packages' / 'memory' / 'skills'):
            if (candidate / 'REGISTRY.json').is_file():
                return candidate
    raise FileNotFoundError('Bundled memory skill registry is not available.')


def _read_json_resource(root: Path, relative_path: str) -> dict[str, Any]:
    payload = json.loads((root / relative_path).read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise RuntimeError(f'{relative_path} must parse to an object')
    return payload


def _action_for_skill(skill: dict[str, Any], skills_root: Path) -> dict[str, str]:
    skill_id = str(skill.get('id', '')).strip()
    relative = Path(str(skill.get('path', '')).strip())
    return {
        'kind': 'bundled skill',
        'path': (skills_root / relative.parent).relative_to(skills_root).as_posix(),
        'detail': 'registered packaged product skill',
        'role': 'skill',
        'safety': 'safe',
        'source': skill_id,
        'category': 'safe-update',
        'remediation_kind': '',
        'remediation_target': '',
        'remediation_reason': '',
        'remediation_confidence': '',
        'memory_action': '',
        'match_source': '',
    }


def _assemble_payload(registry: dict[str, Any], skills_root: Path) -> dict[str, Any]:
    actions = []
    for skill in registry.get('skills', []):
        if not isinstance(skill, dict):
            continue
        if not str(skill.get('id', '')).strip() or not str(skill.get('path', '')).strip():
            continue
        actions.append(_action_for_skill(skill, skills_root))
    return {
        'target_root': str(skills_root),
        'dry_run': True,
        'mode': 'skills',
        'message': 'Bundled skills',
        'detected_version': None,
        'bootstrap_version': registry.get('bootstrap_version'),
        'actions': actions,
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
    print(f"Detected version: none (payload version {payload['bootstrap_version']})")
    for action in payload['actions']:
        print(
            f"- {action['kind']}: {action['path']} "
            f"({action['detail']}; role={action['role']}; safety={action['safety']}; category={action['category']})"
        )


def run(args: argparse.Namespace) -> int:
    skills_root = _skills_root()
    registry = _read_json_resource(skills_root, 'REGISTRY.json')
    payload = _assemble_payload(registry, skills_root)
    _emit_output(payload, str(getattr(args, 'format', 'text') or 'text'))
    return 0
