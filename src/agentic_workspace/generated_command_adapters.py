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
  "doctor": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "doctor",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "doctor.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "doctor.report.cli",
    "operation_id": "doctor.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "workspace.selection.resolve",
        "workspace.report.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "implement": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "implement",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "implement.context.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "implement.context.cli",
    "operation_id": "implement.context",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "implementer.context.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
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
  },
  "ownership": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "ownership",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "ownership.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "ownership.report.cli",
    "operation_id": "ownership.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "ownership.answer.resolve",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "preflight": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "preflight",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "preflight.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": false,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "preflight.report.cli",
    "operation_id": "preflight.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "workspace.defaults.load",
        "workspace.config.load",
        "planning.summary.load",
        "preflight.token.create",
        "preflight.context.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "proof": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "proof",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "proof.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "proof.report.cli",
    "operation_id": "proof.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "proof.routes.resolve",
        "proof.routes.resolve",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "reconcile": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "reconcile",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "reconcile.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "reconcile.report.cli",
    "operation_id": "reconcile.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "planning.reconcile.load",
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
      "command_manifest": "cli_commands.json",
      "name": "report",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "report.combined.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "report.combined.cli",
    "operation_id": "report.combined",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "workspace.config.load",
        "workspace.selection.resolve",
        "workspace.report.assemble",
        "workspace.report.select",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "setup": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "setup",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "setup.guidance.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "setup.guidance.cli",
    "operation_id": "setup.guidance",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "workspace.selection.resolve",
        "workspace.report.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "skills": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "skills",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "skills.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "skills.report.cli",
    "operation_id": "skills.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "skills.registry.inspect",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "start": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "start",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "start.context.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "start.context.cli",
    "operation_id": "start.context",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "preflight.context.assemble",
        "startup.context.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": [
        "startup_context.schema.json"
      ]
    },
    "status": "generated"
  },
  "status": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "status",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "status.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "status.report.cli",
    "operation_id": "status.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "workspace.selection.resolve",
        "workspace.report.assemble",
        "output.emit"
      ]
    },
    "schemas": {
      "input": [],
      "output": []
    },
    "status": "generated"
  },
  "summary": {
    "command": {
      "command_manifest": "cli_commands.json",
      "name": "summary",
      "option_group_manifest": "cli_option_groups.json",
      "program": "agentic-workspace"
    },
    "conformance_refs": [
      "summary.report.process"
    ],
    "effect_hints": {
      "destructive": false,
      "idempotent": true,
      "read_only": true,
      "requires_preflight_gate": false,
      "writes_repo_state": false
    },
    "id": "summary.report.cli",
    "operation_id": "summary.report",
    "runtime_binding": {
      "kind": "operation-primitive-sequence",
      "primitive_refs": [
        "workspace.root.resolve",
        "planning.summary.load",
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
