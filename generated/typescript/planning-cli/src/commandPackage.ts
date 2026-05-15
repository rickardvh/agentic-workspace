// Generated command package metadata.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-planning
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
      "interface": {
        "help": "Report whether planning bootstrap files are present.",
        "name": "status",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
            "action": "store_true",
            "flags": [
              "--apply-safe-prune"
            ],
            "help": "Apply only reconcile cleanup targets that are already marked safe_to_prune.",
            "name": "apply_safe_prune"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Preview --apply-safe-prune without writing files.",
            "name": "dry_run"
          }
        ]
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
    },
    {
      "adapter_id": "planning.doctor.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "doctor"
      },
      "conformance_refs": [
        "planning.doctor.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Read-only doctor report.",
        "name": "doctor",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
        "id": "planning.doctor.report",
        "path": "operations/planning.doctor.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "package-local primitive implementation",
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
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
      "runtime_binding": {
        "kind": "operation-primitive-sequence",
        "primitive_refs": [
          "planning.bootstrap.doctor.load",
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
      "adapter_id": "planning.summary.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "summary"
      },
      "conformance_refs": [
        "planning.summary.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Read-only summary report.",
        "name": "summary",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
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
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
        "id": "planning.summary.report",
        "path": "operations/planning.summary.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "package-local primitive implementation",
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
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
      "runtime_binding": {
        "kind": "operation-primitive-sequence",
        "primitive_refs": [
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
      "adapter_id": "planning.report.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "report"
      },
      "conformance_refs": [
        "planning.report.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Read-only report report.",
        "name": "report",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic output for debugging or audit detail.",
            "name": "verbose"
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
        "id": "planning.report.report",
        "path": "operations/planning.report.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "package-local primitive implementation",
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
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
      "runtime_binding": {
        "kind": "operation-primitive-sequence",
        "primitive_refs": [
          "planning.report.load",
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
      "adapter_id": "planning.reconcile.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "reconcile"
      },
      "conformance_refs": [
        "planning.reconcile.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Read-only reconcile report.",
        "name": "reconcile",
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
        "id": "planning.reconcile.report",
        "path": "operations/planning.reconcile.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "package-local primitive implementation",
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
          "operation reference",
          "runtime primitive reference",
          "effect hints",
          "conformance refs"
        ]
      },
      "runtime_binding": {
        "kind": "operation-primitive-sequence",
        "primitive_refs": [
          "planning.reconcile.load",
          "planning.reconcile.load",
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
  "operation_contract_root": "packages/planning/src/repo_planning_bootstrap/contracts",
  "package_role": "planning-module-cli",
  "program": "agentic-planning",
  "python_runtime_binding": {
    "entrypoint": "agentic-planning",
    "operation_executor": {
      "handlers": [
        {
          "function": "doctor_bootstrap",
          "handler": "function_call",
          "import_module": "repo_planning_bootstrap.installer",
          "kwargs": {
            "target": {
              "value": "target"
            }
          },
          "primitive": "planning.bootstrap.doctor.load"
        },
        {
          "condition_value": "verbose",
          "handler": "conditional_function_call",
          "if_false": {
            "function": "planning_report_tiny",
            "import_module": "repo_planning_bootstrap.installer",
            "kwargs": {
              "target": {
                "value": "target"
              }
            }
          },
          "if_true": {
            "function": "planning_report",
            "import_module": "repo_planning_bootstrap.installer",
            "kwargs": {
              "target": {
                "value": "target"
              }
            }
          },
          "primitive": "planning.report.load"
        },
        {
          "function": "_load_planning_summary_operation",
          "handler": "runtime_handler",
          "primitive": "planning.summary.load"
        },
        {
          "function": "_load_planning_reconcile_operation",
          "handler": "runtime_handler",
          "primitive": "planning.reconcile.load"
        },
        {
          "function": "collect_status",
          "handler": "function_call",
          "import_module": "repo_planning_bootstrap.installer",
          "kwargs": {
            "target": {
              "value": "target"
            }
          },
          "primitive": "planning.bootstrap.status.load"
        },
        {
          "function": "_emit_planning_operation_output",
          "handler": "runtime_handler",
          "primitive": "output.emit"
        }
      ],
      "initial_values": [
        {
          "arg": "target",
          "default": null,
          "name": "target"
        },
        {
          "arg": "format",
          "default": "text",
          "name": "format"
        },
        {
          "arg": "verbose",
          "default": false,
          "name": "verbose"
        },
        {
          "arg": "task",
          "default": null,
          "name": "task"
        },
        {
          "arg": "changed",
          "default": [],
          "name": "changed"
        },
        {
          "arg": "apply_safe_prune",
          "default": false,
          "name": "apply_safe_prune"
        },
        {
          "arg": "dry_run",
          "default": false,
          "name": "dry_run"
        }
      ],
      "module_file": "planning_operation_ir_executor",
      "supported_operation_ids": [
        "planning.doctor.report",
        "planning.reconcile.report",
        "planning.report.report",
        "planning.status.report",
        "planning.summary.report"
      ]
    },
    "runtime_module_file": "planning_runtime_cli"
  },
  "targets": [
    {
      "entrypoints": [
        "agentic-planning"
      ],
      "generated_root": "generated/python/planning-cli",
      "generation_status": "weak-agent-safe-adapter",
      "kind": "python",
      "maturity_level_ref": "weak-agent-safe-adapter",
      "package_name": "agentic-planning",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-planning"
      ],
      "generated_root": "generated/typescript/planning-cli",
      "generation_status": "weak-agent-safe-adapter",
      "kind": "typescript",
      "maturity_level_ref": "weak-agent-safe-adapter",
      "package_name": "@agentic-workspace/planning-cli",
      "test_environment": "docker"
    }
  ]
} as const;

export type GeneratedCommandPackage = typeof generatedCommandPackage;
