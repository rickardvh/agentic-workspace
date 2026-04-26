"""Generated command adapter metadata.

Source: src/agentic_workspace/contracts/command_adapter_generation.json
Regenerate with: uv run python scripts/generate/generate_command_adapters.py
"""

from __future__ import annotations

import json
from typing import Any

# Generated file; edit command_adapter_generation.json instead.
GENERATED_COMMAND_ADAPTERS_BY_COMMAND: dict[str, dict[str, Any]] = json.loads(
    r"""
{
  "defaults": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "defaults",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "defaults.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "defaults.report.cli",
    "operation_id": "defaults.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.defaults.load",
        "workspace.defaults.select",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": [
        "compact_contract_answer.schema.json"
      ]
    },
    "status": "generated"
  }
}
"""
)
