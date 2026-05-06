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
          },
          {
            "choices": [
              "tiny",
              "compact",
              "full"
            ],
            "default": "full",
            "flags": [
              "--profile"
            ],
            "help": "Select compact agent-facing config or full resolved config detail.",
            "name": "profile"
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
            "flags": [
              "--task"
            ],
            "help": "Optional task description used to include task-specific skill recommendations in startup context.",
            "name": "task"
          },
          {
            "choices": [
              "full",
              "tiny"
            ],
            "default": "full",
            "flags": [
              "--profile"
            ],
            "help": "Startup output profile. Use tiny for the cheapest first-contact routing answer.",
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
            "flags": [
              "--task"
            ],
            "help": "Optional task text used to return a task-scoped compact summary.",
            "name": "task"
          },
          {
            "default": [],
            "flags": [
              "--changed"
            ],
            "help": "Optional changed paths used to scope compact summary output.",
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
            "flags": [
              "--task-file"
            ],
            "help": "Optional repo-local file containing task text; use this instead of repeating long task prompts.",
            "name": "task_file"
          },
          {
            "choices": [
              "full",
              "tiny"
            ],
            "default": "full",
            "flags": [
              "--profile"
            ],
            "help": "Implementer output profile. Use tiny for the next decision and proof commands only.",
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
          "output.profile.select",
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
            "flags": [
              "--task"
            ],
            "help": "Optional task description used to include task-specific skill recommendations in preflight context.",
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
              "full",
              "tiny"
            ],
            "default": "full",
            "flags": [
              "--profile"
            ],
            "help": "Proof output profile. Use tiny for the next validation action and command list only.",
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
          "output.profile.select",
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
    },
    {
      "adapter_id": "report.combined.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "report"
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
      "interface": {
        "help": "Show a compact combined workspace report for installed modules, mixed-agent posture, and next-action guidance.",
        "name": "report",
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
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "flags": [
              "--preset"
            ],
            "help": "Named module bundle.",
            "name": "preset"
          },
          {
            "flags": [
              "--modules"
            ],
            "help": "Comma-separated module selection.",
            "name": "modules"
          },
          {
            "action": "store_true",
            "flags": [
              "--non-interactive"
            ],
            "help": "Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents.",
            "name": "non_interactive"
          },
          {
            "action": "store_true",
            "flags": [
              "--startup"
            ],
            "help": "Return the high-signal orientation block for fresh agents.",
            "name": "startup"
          },
          {
            "choices": [
              "router",
              "full"
            ],
            "default": "router",
            "flags": [
              "--profile"
            ],
            "help": "Select the compact router profile or the full combined report.",
            "name": "profile"
          },
          {
            "flags": [
              "--section"
            ],
            "help": "Return one top-level full-report section in the compact contract profile.",
            "name": "section"
          }
        ]
      },
      "operation_ref": {
        "id": "report.combined",
        "path": "operations/report.combined.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "config loading",
          "module selection",
          "combined report assembly",
          "profile or section selection",
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
    {
      "adapter_id": "reconcile.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "reconcile"
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
      "interface": {
        "help": "Show stale planning state against provider-agnostic external work evidence.",
        "name": "reconcile",
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
              "--target"
            ],
            "help": "Optional repository path used to reconcile planning state.",
            "name": "target"
          }
        ]
      },
      "operation_ref": {
        "id": "reconcile.report",
        "path": "operations/reconcile.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "external intent cache refresh when available",
          "planning reconciliation loading",
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
    {
      "adapter_id": "setup.guidance.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "setup"
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
      "interface": {
        "help": "Show the bounded post-bootstrap setup guidance for a mature repository.",
        "name": "setup",
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
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "flags": [
              "--preset"
            ],
            "help": "Named module bundle.",
            "name": "preset"
          },
          {
            "flags": [
              "--modules"
            ],
            "help": "Comma-separated module selection.",
            "name": "modules"
          },
          {
            "action": "store_true",
            "flags": [
              "--non-interactive"
            ],
            "help": "Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents.",
            "name": "non_interactive"
          }
        ]
      },
      "operation_ref": {
        "id": "setup.guidance",
        "path": "operations/setup.guidance.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "module selection",
          "setup guidance assembly",
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
    {
      "adapter_id": "status.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "status"
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
      "interface": {
        "help": "Report installed modules and workspace health summary.",
        "name": "status",
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
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "flags": [
              "--preset"
            ],
            "help": "Named module bundle.",
            "name": "preset"
          },
          {
            "flags": [
              "--modules"
            ],
            "help": "Comma-separated module selection.",
            "name": "modules"
          },
          {
            "action": "store_true",
            "flags": [
              "--non-interactive"
            ],
            "help": "Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents.",
            "name": "non_interactive"
          }
        ]
      },
      "operation_ref": {
        "id": "status.report",
        "path": "operations/status.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "module selection",
          "status report assembly",
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
    {
      "adapter_id": "doctor.report.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "doctor"
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
      "interface": {
        "help": "Report drift, missing surfaces, and recommended remediation.",
        "name": "doctor",
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
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "flags": [
              "--preset"
            ],
            "help": "Named module bundle.",
            "name": "preset"
          },
          {
            "flags": [
              "--modules"
            ],
            "help": "Comma-separated module selection.",
            "name": "modules"
          },
          {
            "action": "store_true",
            "flags": [
              "--non-interactive"
            ],
            "help": "Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents.",
            "name": "non_interactive"
          }
        ]
      },
      "operation_ref": {
        "id": "doctor.report",
        "path": "operations/doctor.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "module selection",
          "doctor report assembly",
          "repair guidance assembly",
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
