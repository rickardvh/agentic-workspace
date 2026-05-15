// Generated command package metadata.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-memory
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

export const generatedCommandPackage = {
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
      "interface": {
        "help": "Report whether memory bootstrap files are present.",
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
          }
        ]
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
    },
    {
      "adapter_id": "memory.doctor.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "doctor"
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
              "--strict-doc-ownership"
            ],
            "help": "Enforce doc-ownership audits even when the repo manifest has not enabled them.",
            "name": "strict_doc_ownership"
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
        "id": "memory.doctor.report",
        "path": "operations/memory.doctor.report.json"
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
    {
      "adapter_id": "memory.capture-note.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "capture-note"
      },
      "conformance_refs": [
        "memory.capture-note.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "arguments": [
          {
            "default": "",
            "help": "Optional note slug to create when a new note is recommended.",
            "name": "slug",
            "nargs": "?"
          }
        ],
        "help": "Recommend whether durable learning should update an existing Memory note or create a new one.",
        "name": "capture-note",
        "options": [
          {
            "default": "",
            "flags": [
              "--summary"
            ],
            "help": "Short summary of the learning to preserve.",
            "name": "summary"
          },
          {
            "default": [],
            "flags": [
              "--files"
            ],
            "help": "Changed files that should influence routing.",
            "name": "files",
            "nargs": "*"
          },
          {
            "default": [],
            "flags": [
              "--surface"
            ],
            "help": "Explicit routing surfaces.",
            "name": "surface",
            "nargs": "*"
          },
          {
            "default": "",
            "flags": [
              "--existing-note"
            ],
            "help": "Existing note path to force-review first.",
            "name": "existing_note"
          },
          {
            "default": "",
            "flags": [
              "--force-new-reason"
            ],
            "help": "Reason a new note is preferred even when related notes exist.",
            "name": "force_new_reason"
          },
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
        "id": "memory.capture-note.report",
        "path": "operations/memory.capture-note.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory capture recommendation policy",
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
          "memory.capture_note.load",
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
      "adapter_id": "memory.report.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "report"
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
        "id": "memory.report.report",
        "path": "operations/memory.report.report.json"
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
    {
      "adapter_id": "memory.route-report.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "route-report"
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
      "interface": {
        "help": "Show a compact aggregate routing snapshot derived from checked-in feedback cases and fixtures.",
        "name": "route-report",
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
        "id": "memory.route-report.report",
        "path": "operations/memory.route-report.report.json"
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
    {
      "adapter_id": "memory.route.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "route"
      },
      "conformance_refs": [
        "memory.route.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Suggest the smallest relevant durable note set for touched files or surfaces so the agent can read less, not more.",
        "name": "route",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "default": [],
            "flags": [
              "--files"
            ],
            "help": "Touched file paths to route from.",
            "name": "files",
            "nargs": "*"
          },
          {
            "default": [],
            "flags": [
              "--surface"
            ],
            "help": "Explicit routing surfaces.",
            "name": "surface",
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
        "id": "memory.route.report",
        "path": "operations/memory.route.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory routing policy",
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
          "memory.route.load",
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
      "adapter_id": "memory.sync-memory.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "sync-memory"
      },
      "conformance_refs": [
        "memory.sync-memory.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Suggest memory updates for changed work and surface compact upstream improvement candidates.",
        "name": "sync-memory",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "default": [],
            "flags": [
              "--files"
            ],
            "help": "Changed file paths to inspect.",
            "name": "files",
            "nargs": "*"
          },
          {
            "default": [],
            "flags": [
              "--notes"
            ],
            "help": "Explicit memory notes to review.",
            "name": "notes",
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
        "id": "memory.sync-memory.report",
        "path": "operations/memory.sync-memory.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory sync suggestion policy",
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
          "memory.sync_memory.load",
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
      "adapter_id": "memory.route-review.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "route-review"
      },
      "conformance_refs": [
        "memory.route-review.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Review checked-in routing feedback cases against the current routing result.",
        "name": "route-review",
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
        "id": "memory.route-review.report",
        "path": "operations/memory.route-review.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory routing review policy",
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
          "memory.route_review.load",
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
      "adapter_id": "memory.search.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "search"
      },
      "conformance_refs": [
        "memory.search.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "arguments": [
          {
            "help": "Keyword or pattern to search for.",
            "name": "query"
          }
        ],
        "help": "Search for keywords across all memory notes.",
        "name": "search",
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
        "id": "memory.search.report",
        "path": "operations/memory.search.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory search policy",
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
          "memory.search.load",
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
      "adapter_id": "memory.verify-payload.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "verify-payload"
      },
      "conformance_refs": [
        "memory.verify-payload.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Verify the packaged bootstrap payload contract.",
        "name": "verify-payload",
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
        "id": "memory.verify-payload.report",
        "path": "operations/memory.verify-payload.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory payload verification policy",
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
          "memory.verify-payload.load",
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
      "adapter_id": "memory.promotion-report.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "promotion-report"
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
      "interface": {
        "help": "Suggest memory notes that should be promoted into canonical docs or considered for elimination through skills, scripts, tests, or refactors.",
        "name": "promotion-report",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "default": [],
            "flags": [
              "--notes"
            ],
            "help": "Explicit memory notes to inspect.",
            "name": "notes",
            "nargs": "*"
          },
          {
            "choices": [
              "all",
              "remediation"
            ],
            "default": "all",
            "flags": [
              "--mode"
            ],
            "help": "Report all candidates or only medium/high-confidence remediation candidates.",
            "name": "mode"
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
        "id": "memory.promotion-report.report",
        "path": "operations/memory.promotion-report.report.json"
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
    {
      "adapter_id": "memory.list-files.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "list-files"
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
      "interface": {
        "help": "Preview packaged bootstrap files.",
        "name": "list-files",
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
        "id": "memory.list-files.report",
        "path": "operations/memory.list-files.report.json"
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
    {
      "adapter_id": "memory.list-skills.cli",
      "command": {
        "manifest_ref": "package:memory:cli",
        "name": "list-skills"
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
      "interface": {
        "help": "List bundled bootstrap-lifecycle skills.",
        "name": "list-skills",
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
          }
        ]
      },
      "operation_ref": {
        "id": "memory.list-skills.report",
        "path": "operations/memory.list-skills.report.json"
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
    }
  ],
  "id": "memory-bootstrap",
  "operation_contract_root": "packages/memory/src/repo_memory_bootstrap/contracts",
  "package_role": "memory-module-cli",
  "program": "agentic-memory",
  "python_runtime_binding": {
    "entrypoint": "agentic-memory",
    "operation_executor": {
      "context_roots": [
        {
          "function": "payload_root",
          "import_module": "repo_memory_bootstrap._installer_paths",
          "name": "memory.package-payload"
        },
        {
          "function": "skills_root",
          "import_module": "repo_memory_bootstrap._installer_paths",
          "name": "memory.package-skills"
        }
      ],
      "handlers": [
        {
          "function": "_resolve_memory_target_root",
          "handler": "runtime_handler",
          "primitive": "path.target_root.resolve"
        },
        {
          "function": "_load_memory_bootstrap_doctor",
          "handler": "runtime_handler",
          "primitive": "memory.bootstrap.doctor.load"
        },
        {
          "function": "_load_memory_bootstrap_status",
          "handler": "runtime_handler",
          "primitive": "memory.bootstrap.status.load"
        },
        {
          "function": "suggest_memory_note_capture",
          "handler": "function_call",
          "import_module": "repo_memory_bootstrap.installer",
          "kwargs": {
            "existing_note": {
              "value": "existing_note"
            },
            "files": {
              "value": "files"
            },
            "force_new_reason": {
              "value": "force_new_reason"
            },
            "slug": {
              "value": "slug"
            },
            "summary": {
              "value": "summary"
            },
            "surfaces": {
              "value": "surface"
            },
            "target": {
              "value": "target"
            }
          },
          "primitive": "memory.capture_note.load"
        },
        {
          "function": "_load_memory_promotion_report",
          "handler": "runtime_handler",
          "primitive": "memory.promotion_report.load"
        },
        {
          "function": "_load_memory_report",
          "handler": "runtime_handler",
          "primitive": "memory.report.load"
        },
        {
          "function": "route_memory",
          "handler": "function_call",
          "import_module": "repo_memory_bootstrap.installer",
          "kwargs": {
            "files": {
              "value": "files"
            },
            "surfaces": {
              "value": "surface"
            },
            "target": {
              "value": "target"
            }
          },
          "primitive": "memory.route.load"
        },
        {
          "function": "_load_memory_route_report",
          "handler": "runtime_handler",
          "primitive": "memory.route_report.load"
        },
        {
          "function": "review_routes",
          "handler": "function_call",
          "import_module": "repo_memory_bootstrap.installer",
          "kwargs": {
            "target": {
              "value": "target"
            }
          },
          "primitive": "memory.route_review.load"
        },
        {
          "function": "search_memory",
          "handler": "function_call",
          "import_module": "repo_memory_bootstrap.installer",
          "kwargs": {
            "query": {
              "value": "query"
            },
            "target": {
              "value": "target"
            }
          },
          "primitive": "memory.search.load"
        },
        {
          "function": "verify_payload",
          "handler": "function_call",
          "import_module": "repo_memory_bootstrap.installer",
          "kwargs": {
            "target": {
              "value": "target"
            }
          },
          "primitive": "memory.verify-payload.load"
        },
        {
          "function": "sync_memory",
          "handler": "function_call",
          "import_module": "repo_memory_bootstrap.installer",
          "kwargs": {
            "files": {
              "value": "files"
            },
            "notes": {
              "value": "notes"
            },
            "target": {
              "value": "target"
            }
          },
          "primitive": "memory.sync_memory.load"
        },
        {
          "function": "_assemble_memory_operation_payload",
          "handler": "runtime_handler",
          "primitive": "payload.assemble"
        },
        {
          "function": "_emit_memory_operation_output",
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
          "arg": "strict_doc_ownership",
          "default": false,
          "name": "strict_doc_ownership"
        },
        {
          "arg": "project_name",
          "default": null,
          "name": "project_name"
        },
        {
          "arg": "project_purpose",
          "default": null,
          "name": "project_purpose"
        },
        {
          "arg": "key_repo_docs",
          "default": null,
          "name": "key_repo_docs"
        },
        {
          "arg": "key_subsystems",
          "default": null,
          "name": "key_subsystems"
        },
        {
          "arg": "primary_build_command",
          "default": null,
          "name": "primary_build_command"
        },
        {
          "arg": "primary_test_command",
          "default": null,
          "name": "primary_test_command"
        },
        {
          "arg": "other_key_commands",
          "default": null,
          "name": "other_key_commands"
        },
        {
          "arg": "notes",
          "default": null,
          "name": "notes"
        },
        {
          "arg": "files",
          "default": [],
          "name": "files"
        },
        {
          "arg": "surface",
          "default": [],
          "name": "surface"
        },
        {
          "arg": "mode",
          "default": null,
          "name": "mode"
        },
        {
          "arg": "slug",
          "default": "",
          "name": "slug"
        },
        {
          "arg": "summary",
          "default": "",
          "name": "summary"
        },
        {
          "arg": "existing_note",
          "default": "",
          "name": "existing_note"
        },
        {
          "arg": "force_new_reason",
          "default": "",
          "name": "force_new_reason"
        },
        {
          "arg": "query",
          "default": "",
          "name": "query"
        }
      ],
      "module_file": "memory_operation_ir_executor",
      "supported_operation_ids": [
        "memory.doctor.report",
        "memory.capture-note.report",
        "memory.list-files.report",
        "memory.list-skills.report",
        "memory.promotion-report.report",
        "memory.report.report",
        "memory.route.report",
        "memory.route-report.report",
        "memory.route-review.report",
        "memory.search.report",
        "memory.verify-payload.report",
        "memory.status.report",
        "memory.sync-memory.report"
      ]
    },
    "runtime_module_file": "memory_runtime_cli"
  },
  "targets": [
    {
      "entrypoints": [
        "agentic-memory"
      ],
      "generated_root": "generated/python/memory-cli",
      "generation_status": "weak-agent-safe-adapter",
      "kind": "python",
      "maturity_level_ref": "weak-agent-safe-adapter",
      "package_name": "agentic-memory",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-memory"
      ],
      "generated_root": "generated/typescript/memory-cli",
      "generation_status": "weak-agent-safe-adapter",
      "kind": "typescript",
      "maturity_level_ref": "weak-agent-safe-adapter",
      "package_name": "@agentic-workspace/memory-cli",
      "test_environment": "docker"
    }
  ]
} as const;

export type GeneratedCommandPackage = typeof generatedCommandPackage;
