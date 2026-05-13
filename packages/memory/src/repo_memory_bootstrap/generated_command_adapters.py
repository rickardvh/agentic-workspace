"""Generated command adapter metadata.

Source: src/agentic_workspace/contracts/command_adapter_generation.json
Program: agentic-memory
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
  "doctor": {
    "command": {
      "command_manifest": "package:memory:cli",
      "name": "doctor",
      "option_group_manifest": "package:memory:cli",
      "program": "agentic-memory"
    },
    "conformance_refs": [
      "memory.doctor.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "memory.doctor.cli",
    "operation_id": "memory.doctor.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "memory.bootstrap.doctor.load",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "list-files": {
    "command": {
      "command_manifest": "package:memory:cli",
      "name": "list-files",
      "option_group_manifest": "package:memory:cli",
      "program": "agentic-memory"
    },
    "conformance_refs": [
      "memory.list-files.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "memory.list-files.cli",
    "operation_id": "memory.list-files.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "path.target_root.resolve",
        "filesystem.glob",
        "payload.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "list-skills": {
    "command": {
      "command_manifest": "package:memory:cli",
      "name": "list-skills",
      "option_group_manifest": "package:memory:cli",
      "program": "agentic-memory"
    },
    "conformance_refs": [
      "memory.list-skills.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "memory.list-skills.cli",
    "operation_id": "memory.list-skills.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "filesystem.read",
        "json.parse",
        "payload.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "promotion-report": {
    "command": {
      "command_manifest": "package:memory:cli",
      "name": "promotion-report",
      "option_group_manifest": "package:memory:cli",
      "program": "agentic-memory"
    },
    "conformance_refs": [
      "memory.promotion-report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "memory.promotion-report.cli",
    "operation_id": "memory.promotion-report.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "memory.promotion_report.load",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "report": {
    "command": {
      "command_manifest": "package:memory:cli",
      "name": "report",
      "option_group_manifest": "package:memory:cli",
      "program": "agentic-memory"
    },
    "conformance_refs": [
      "memory.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "memory.report.cli",
    "operation_id": "memory.report.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "memory.report.load",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "route-report": {
    "command": {
      "command_manifest": "package:memory:cli",
      "name": "route-report",
      "option_group_manifest": "package:memory:cli",
      "program": "agentic-memory"
    },
    "conformance_refs": [
      "memory.route-report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "memory.route-report.cli",
    "operation_id": "memory.route-report.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "memory.route_report.load",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "status": {
    "command": {
      "command_manifest": "package:memory:cli",
      "name": "status",
      "option_group_manifest": "package:memory:cli",
      "program": "agentic-memory"
    },
    "conformance_refs": [
      "memory.status.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "memory.status.cli",
    "operation_id": "memory.status.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "memory.bootstrap.status.load",
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
