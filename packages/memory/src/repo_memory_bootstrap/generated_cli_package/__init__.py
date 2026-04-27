"""Generated command package metadata.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory-bootstrap
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
      "adapter_id": "memory.status.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "status"
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
      "operation_ref": {
        "id": "memory.status.report",
        "path": "operations/memory.status.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory bootstrap inspection",
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
  ],
  "id": "memory-bootstrap",
  "package_role": "memory-module-cli",
  "program": "agentic-memory-bootstrap",
  "targets": [
    {
      "entrypoints": [
        "agentic-memory-bootstrap"
      ],
      "generated_root": "packages/memory/src/repo_memory_bootstrap/generated_cli_package",
      "generation_status": "supported-now",
      "kind": "python",
      "maturity_level_ref": "metadata-proof-fixture",
      "package_name": "agentic-memory-bootstrap",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-memory-bootstrap"
      ],
      "generated_root": "generated/typescript/memory-cli",
      "generation_status": "proof-fixture",
      "kind": "typescript",
      "maturity_level_ref": "metadata-proof-fixture",
      "package_name": "@agentic-workspace/memory-cli",
      "test_environment": "docker"
    }
  ]
}
"""
)
