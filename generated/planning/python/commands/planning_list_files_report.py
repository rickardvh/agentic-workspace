"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
Operation: planning.list-files.report
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

DEFAULT_PAYLOAD_FILES = ['AGENTS.template.md', '.agentic-workspace/docs/execution-flow-contract.md', '.agentic-workspace/docs/system-intent-contract.md', '.agentic-workspace/docs/routing-contract.md', '.agentic-workspace/docs/minimum-operating-model.md', '.agentic-workspace/docs/lifecycle-and-config-contract.md', '.agentic-workspace/docs/workspace-config-contract.md', '.agentic-workspace/planning/execplans/README.md', '.agentic-workspace/planning/execplans/TEMPLATE.plan.json', '.agentic-workspace/planning/execplans/archive/README.md', '.agentic-workspace/planning/decompositions/README.md', '.agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json', '.agentic-workspace/planning/schemas/planning-execplan.schema.json', '.agentic-workspace/planning/schemas/planning-decomposition.schema.json', '.agentic-workspace/planning/schemas/planning-review.schema.json', '.agentic-workspace/planning/schemas/planning-external-intent-evidence.schema.json', '.agentic-workspace/planning/schemas/planning-finished-work-evidence.schema.json', '.agentic-workspace/planning/UPGRADE-SOURCE.toml', '.agentic-workspace/planning/agent-manifest.json']
OPTIONAL_PAYLOAD_FILES = ['.agentic-workspace/docs/capability-contract.json', '.agentic-workspace/planning/reviews/README.md', '.agentic-workspace/planning/reviews/TEMPLATE.review.json', '.agentic-workspace/planning/upstream-task-intake.md', '.agentic-workspace/planning/pre-ingestion-refinement.md']
OPTIONAL_ENABLE_COMMANDS = (
    'agentic-planning install --include-optional',
    'agentic-planning adopt --include-optional',
    'agentic-planning upgrade --include-optional',
)


def _payload_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / '_payload', parent / 'packages' / 'planning' / 'bootstrap'):
            if (candidate / 'AGENTS.template.md').is_file():
                return candidate
    raise FileNotFoundError('Planning payload directory is not available.')


def _skills_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / '_skills', parent / 'packages' / 'planning' / 'skills'):
            if (candidate / 'REGISTRY.json').is_file():
                return candidate
    raise FileNotFoundError('Planning skills directory is not available.')


def _resource_files(root: Path) -> list[str]:
    return [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob('*'))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'
    ]


def _assemble_payload(payload_root: Path, skills_root: Path) -> dict[str, Any]:
    return {
        'files': _resource_files(payload_root),
        'default_files': list(DEFAULT_PAYLOAD_FILES),
        'optional_files': list(OPTIONAL_PAYLOAD_FILES),
        'bundled_skill_files': _resource_files(skills_root),
        'optional_enable_commands': list(OPTIONAL_ENABLE_COMMANDS),
    }


def _emit_output(payload: dict[str, Any], output_format: str) -> None:
    if output_format == 'json':
        print(json.dumps(payload, indent=2))
        return
    for path in payload['files']:
        print(path)


def run(args: argparse.Namespace) -> int:
    payload = _assemble_payload(_payload_root(), _skills_root())
    _emit_output(payload, str(getattr(args, 'format', 'text') or 'text'))
    return 0
