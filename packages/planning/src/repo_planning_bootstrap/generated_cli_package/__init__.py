"""Generated command package metadata.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning-bootstrap
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import json
from typing import Any

# DO NOT EDIT DIRECTLY.
# Command/package interface changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Runtime behavior changes belong in hand-written operation/primitive implementation code.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py
GENERATED_COMMAND_PACKAGE: dict[str, Any] = json.loads(
    r"""
{
  "commands": [
    {
      "adapter_id": "planning.status.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "status"
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
      "operation_ref": {
        "id": "planning.status.report",
        "path": "operations/planning.status.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning bootstrap inspection",
          "module result assembly",
          "output emission"
        ],
        "target_specific": [
          "parser library",
          "package entrypoint wiring",
          "help text layout",
          "test container image"
        ],
        "universal": [
          "command identity",
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
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
  ],
  "id": "planning-bootstrap",
  "package_role": "planning-module-cli",
  "program": "agentic-planning-bootstrap",
  "targets": [
    {
      "entrypoints": [
        "agentic-planning-bootstrap"
      ],
      "generated_root": "packages/planning/src/repo_planning_bootstrap/generated_cli_package",
      "generation_status": "supported-now",
      "kind": "python",
      "package_name": "agentic-planning-bootstrap",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-planning-bootstrap"
      ],
      "generated_root": "generated/typescript/planning-cli",
      "generation_status": "proof-fixture",
      "kind": "typescript",
      "package_name": "@agentic-workspace/planning-cli",
      "test_environment": "docker"
    }
  ]
}
"""
)
