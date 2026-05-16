"""Generated target-local resource and output primitives.

Source: src/agentic_workspace/contracts/command_package_ir.json
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import json
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
