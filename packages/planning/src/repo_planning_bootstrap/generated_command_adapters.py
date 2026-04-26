"""Generated command adapter metadata.

Source: src/agentic_workspace/contracts/command_adapter_generation.json
Program: agentic-planning-bootstrap
Regenerate with: uv run python scripts/generate/generate_command_adapters.py
"""

from __future__ import annotations

import json
from typing import Any

# DO NOT EDIT DIRECTLY.
# Command/interface changes belong in src/agentic_workspace/contracts/command_adapter_generation.json.
# Runtime behavior changes belong in hand-written operation/primitive implementation code.
# Regenerate with: uv run python scripts/generate/generate_command_adapters.py
GENERATED_COMMAND_ADAPTERS_BY_COMMAND: dict[str, dict[str, Any]] = json.loads(
    r"""
{
  "status": {
    "command": {
      "command_manifest": "package:planning:cli",
      "name": "status",
      "option_group_manifest": "package:planning:cli",
      "program": "agentic-planning-bootstrap"
    },
    "conformance_refs": [
      "planning.status.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "planning.status.cli",
    "operation_id": "planning.status.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "planning.bootstrap.status.load",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  }
}
"""
)
