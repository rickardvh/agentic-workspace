// Generated command package metadata.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-workspace
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

export const generatedCommandPackage = {
  "commands": [
    {
      "adapter_id": "defaults.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "defaults"
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
      "interface": {
        "help": "Show the machine-readable default-route contract for startup, lifecycle, skills, validation, and combined installs.",
        "name": "defaults",
        "options": [
          {
            "choices": [
              "text",
              "json"
            ],
            "default": "text",
            "flags": [
              "--format"
            ],
            "help": "Output format.",
            "name": "format"
          },
          {
            "flags": [
              "--section"
            ],
            "help": "Return only one top-level defaults section in the compact contract profile.",
            "name": "section"
          }
        ]
      },
      "operation_ref": {
        "id": "defaults.report",
        "path": "operations/defaults.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "defaults payload assembly",
          "section selection",
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
          "option semantics",
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "schema refs",
          "conformance refs"
        ]
      },
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
  ],
  "id": "root-workspace",
  "package_role": "root-workspace-cli",
  "program": "agentic-workspace",
  "targets": [
    {
      "entrypoints": [
        "agentic-workspace"
      ],
      "generated_root": "src/agentic_workspace/generated_cli_package",
      "generation_status": "runtime-backed-read-only-adapter",
      "kind": "python",
      "maturity_level_ref": "runtime-backed-read-only-adapter",
      "package_name": "agentic-workspace",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-workspace"
      ],
      "generated_root": "generated/typescript/workspace-cli",
      "generation_status": "runnable-read-only-adapter",
      "kind": "typescript",
      "maturity_level_ref": "runnable-read-only-adapter",
      "package_name": "@agentic-workspace/workspace-cli",
      "test_environment": "docker"
    },
    {
      "entrypoints": [
        "agentic-workspace"
      ],
      "generated_root": "generated/shell/bash",
      "generation_status": "deferred",
      "kind": "bash",
      "maturity_level_ref": "deferred",
      "package_name": "agentic-workspace-shell",
      "test_environment": "docker"
    },
    {
      "entrypoints": [
        "agentic-workspace"
      ],
      "generated_root": "generated/shell/powershell",
      "generation_status": "deferred",
      "kind": "powershell",
      "maturity_level_ref": "deferred",
      "package_name": "AgenticWorkspace.PowerShell",
      "test_environment": "docker"
    }
  ]
} as const;

export type GeneratedCommandPackage = typeof generatedCommandPackage;
