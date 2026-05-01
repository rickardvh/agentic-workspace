"""Generated command adapter metadata.

Source: src/agentic_workspace/contracts/command_adapter_generation.json
Program: agentic-workspace
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
  "config": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "config",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "config.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "config.report.cli",
    "operation_id": "config.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "workspace.config.load",
        "workspace.config.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": [
        "workspace_config.schema.json"
      ]
    },
    "status": "generated"
  },
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
  },
  "modules": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "modules",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "modules.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "modules.report.cli",
    "operation_id": "modules.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "workspace.modules.inspect",
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
