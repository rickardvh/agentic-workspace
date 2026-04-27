// Generated command package metadata.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-planning-bootstrap
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

export const generatedCommandPackage = {
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
      "maturity_level_ref": "metadata-proof-fixture",
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
      "maturity_level_ref": "metadata-proof-fixture",
      "package_name": "@agentic-workspace/planning-cli",
      "test_environment": "docker"
    }
  ]
} as const;

export type GeneratedCommandPackage = typeof generatedCommandPackage;
