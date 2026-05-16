"""Generated executable command projection.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
Operation: planning.list-files.report
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ..primitives.resources import emit_json_or_lines, find_resource_root, list_resource_files

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


PAYLOAD_ROOT_CANDIDATES = (('_payload', 'AGENTS.template.md'), ('packages/planning/bootstrap', 'AGENTS.template.md'))
SKILLS_ROOT_CANDIDATES = (('_skills', 'REGISTRY.json'), ('packages/planning/skills', 'REGISTRY.json'))


def _assemble_payload(payload_root: Path, skills_root: Path) -> dict[str, Any]:
    return {
        'files': list_resource_files(payload_root),
        'default_files': list(DEFAULT_PAYLOAD_FILES),
        'optional_files': list(OPTIONAL_PAYLOAD_FILES),
        'bundled_skill_files': list_resource_files(skills_root),
        'optional_enable_commands': list(OPTIONAL_ENABLE_COMMANDS),
    }


def run(args: argparse.Namespace) -> int:
    payload_root = find_resource_root(__file__, PAYLOAD_ROOT_CANDIDATES)
    skills_root = find_resource_root(__file__, SKILLS_ROOT_CANDIDATES)
    payload = _assemble_payload(payload_root, skills_root)
    emit_json_or_lines(payload, str(getattr(args, 'format', 'text') or 'text'), line_field='files')
    return 0
