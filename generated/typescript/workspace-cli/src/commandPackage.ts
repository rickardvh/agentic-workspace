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
    },
    {
      "adapter_id": "config.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "config"
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
      "interface": {
        "help": "Show the resolved repo-owned workspace config layered onto product defaults.",
        "name": "config",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "config.report",
        "path": "operations/config.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "config loading",
          "payload assembly",
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
    {
      "adapter_id": "modules.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "modules"
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
      "interface": {
        "help": "List workspace modules available to the orchestrator.",
        "name": "modules",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path used to report installed modules.",
            "name": "target"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "modules.report",
        "path": "operations/modules.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "module descriptor inspection",
          "installed-signal detection",
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
          "conformance refs"
        ]
      },
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
    {
      "adapter_id": "start.context.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "start"
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
      "interface": {
        "help": "Return the minimum safe startup context for beginning work in a target repository.",
        "name": "start",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path for startup context (defaults to current workspace).",
            "name": "target"
          },
          {
            "default": [],
            "flags": [
              "--changed"
            ],
            "help": "Optional repo-relative changed paths used to include a proof recommendation.",
            "name": "changed",
            "nargs": "*"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "start.context",
        "path": "operations/start.context.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "startup context assembly",
          "changed-path proof selection",
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
    {
      "adapter_id": "summary.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "summary"
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
      "interface": {
        "help": "Show the active execution summary from the planning module.",
        "name": "summary",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path to read summary from.",
            "name": "target"
          },
          {
            "choices": [
              "compact",
              "full"
            ],
            "default": "compact",
            "flags": [
              "--profile"
            ],
            "name": "profile"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "summary.report",
        "path": "operations/summary.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "planning summary loading",
          "memory consult augmentation",
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
          "conformance refs"
        ]
      },
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
    },
    {
      "adapter_id": "implement.context.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "implement"
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
      "interface": {
        "help": "Return a cheap-implementer context for a bounded changed-path scope.",
        "name": "implement",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path for implementer context (defaults to current workspace).",
            "name": "target"
          },
          {
            "default": [],
            "flags": [
              "--changed"
            ],
            "help": "Repo-relative changed paths used to select inspect scope, boundary warnings, and proof commands.",
            "name": "changed",
            "nargs": "*"
          },
          {
            "flags": [
              "--task"
            ],
            "help": "Optional task text used to route broad external-work requests before implementation.",
            "name": "task"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "implement.context",
        "path": "operations/implement.context.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "implementer context assembly",
          "changed-path proof selection",
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
    {
      "adapter_id": "preflight.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "preflight"
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
      "interface": {
        "help": "Get compact takeover-safe context: startup defaults + resolved config + active planning state in one call.",
        "name": "preflight",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path for preflight context (defaults to current workspace).",
            "name": "target"
          },
          {
            "action": "store_true",
            "flags": [
              "--active-only"
            ],
            "help": "Return only active planning state without startup defaults and config.",
            "name": "active_only"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "preflight.report",
        "path": "operations/preflight.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "preflight token creation",
          "takeover context assembly",
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
    {
      "adapter_id": "proof.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "proof"
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
      "interface": {
        "help": "Show the canonical proof routes and current workspace proof summary.",
        "name": "proof",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path used to inspect installed modules and proof state.",
            "name": "target"
          },
          {
            "flags": [
              "--route"
            ],
            "help": "Return one proof route by id instead of the full proof surface.",
            "name": "route"
          },
          {
            "action": "store_true",
            "flags": [
              "--current"
            ],
            "help": "Return only the current proof summary.",
            "name": "current"
          },
          {
            "default": [],
            "flags": [
              "--changed"
            ],
            "help": "Return required proof commands for the provided repo-relative changed paths.",
            "name": "changed",
            "nargs": "*"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "proof.report",
        "path": "operations/proof.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "proof route resolution",
          "changed-path proof selection",
          "surface-value review",
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
    {
      "adapter_id": "ownership.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "ownership"
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
      "interface": {
        "help": "Show the canonical ownership and authority mapping for the target repository.",
        "name": "ownership",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path used to inspect the ownership ledger.",
            "name": "target"
          },
          {
            "flags": [
              "--concern"
            ],
            "help": "Return one authority-surface answer by concern.",
            "name": "concern"
          },
          {
            "flags": [
              "--path"
            ],
            "help": "Return the ownership answer for one repo-relative path.",
            "name": "path"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "ownership.report",
        "path": "operations/ownership.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "ownership ledger loading",
          "authority answer selection",
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
    {
      "adapter_id": "skills.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "skills"
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
      "interface": {
        "help": "List registered workspace skills from installed package registries and repo-owned skill registries.",
        "name": "skills",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path used to inspect installed and repo-owned skills.",
            "name": "target"
          },
          {
            "flags": [
              "--task"
            ],
            "help": "Optional task description used to recommend likely skills.",
            "name": "task"
          },
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
          }
        ]
      },
      "operation_ref": {
        "id": "skills.report",
        "path": "operations/skills.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "skill registry discovery",
          "task recommendation scoring",
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
