from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def load_command_package_ir(ir_path: Path, schema_path: Path) -> dict[str, Any]:
    """Load and validate command-package IR from explicit paths."""
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(ir), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(error.message for error in errors)
        raise ValueError(f"{ir_path} does not match {schema_path}: {details}")
    if not isinstance(ir, dict):
        raise ValueError(f"{ir_path} must contain a JSON object")
    return ir
