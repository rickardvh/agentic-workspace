// Generated command package metadata.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-planning
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

export const generatedCommandPackage = {
  "commands": [
    {
      "adapter_id": "planning.adopt.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "adopt"
      },
      "conformance_refs": [
        "planning.adopt.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Conservatively add planning bootstrap files to an existing repository.",
        "name": "adopt",
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
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--include-optional"
            ],
            "help": "Copy optional planning docs for richer review, intake, and recovery workflows.",
            "name": "include_optional"
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
        "id": "planning.adopt.lifecycle",
        "path": "operations/planning.adopt.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning lifecycle policy",
          "managed planning payload mutation",
          "module result assembly"
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
          "python.function.call",
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
      "adapter_id": "planning.archive-plan.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "archive-plan"
      },
      "conformance_refs": [
        "planning.archive-plan.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "arguments": [
          {
            "help": "Execplan path, slug, or id to archive.",
            "name": "plan",
            "nargs": "?"
          }
        ],
        "help": "Close a completed execplan or parent lane after distillation.",
        "name": "archive-plan",
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
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--apply-cleanup"
            ],
            "help": "Apply narrow cleanup tied to the archived plan.",
            "name": "apply_cleanup"
          },
          {
            "action": "store_true",
            "flags": [
              "--prepare-closeout"
            ],
            "help": "Write package-normalized closeout fields before archive validation runs.",
            "name": "prepare_closeout"
          },
          {
            "action": "store_true",
            "flags": [
              "--retain-archive"
            ],
            "help": "Keep a completed execplan record under execplans/archive.",
            "name": "retain_archive"
          },
          {
            "flags": [
              "--parent-lane-closeout"
            ],
            "help": "Close a parent lane from structured planning state.",
            "name": "parent_lane_closeout"
          },
          {
            "choices": [
              "archive-and-close",
              "archive-but-keep-lane-open"
            ],
            "flags": [
              "--closure-decision"
            ],
            "help": "Closeout decision to write.",
            "name": "closure_decision"
          },
          {
            "choices": [
              "yes",
              "no",
              "true",
              "false"
            ],
            "flags": [
              "--intent-satisfied"
            ],
            "help": "Whether the larger original intent is fully satisfied.",
            "name": "intent_satisfied"
          },
          {
            "flags": [
              "--unsolved-intent"
            ],
            "help": "Continuation owner for unsolved larger intent.",
            "name": "unsolved_intent"
          },
          {
            "flags": [
              "--intent-evidence"
            ],
            "help": "Evidence of intent satisfaction.",
            "name": "intent_evidence"
          },
          {
            "flags": [
              "--closure-reason"
            ],
            "help": "Why the prepared closure decision is honest.",
            "name": "closure_reason"
          },
          {
            "flags": [
              "--closure-evidence"
            ],
            "help": "Evidence carried forward by the prepared closure.",
            "name": "closure_evidence"
          },
          {
            "flags": [
              "--reopen-trigger"
            ],
            "help": "Reopen trigger for prepared closure.",
            "name": "reopen_trigger"
          },
          {
            "flags": [
              "--discard-summary"
            ],
            "help": "Closeout distillation discard bucket summary.",
            "name": "discard_summary"
          },
          {
            "flags": [
              "--continuation-summary"
            ],
            "help": "Closeout distillation continuation bucket summary.",
            "name": "continuation_summary"
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
        "id": "planning.archive-plan.lifecycle",
        "path": "operations/planning.archive-plan.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning state mutation policy",
          "planning provenance updates",
          "module result assembly"
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
          "planning.archive-plan.apply",
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
      "adapter_id": "planning.closeout.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "closeout"
      },
      "conformance_refs": [
        "planning.closeout.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "arguments": [
          {
            "help": "Execplan path, slug, or id to close out.",
            "name": "plan",
            "nargs": "?"
          }
        ],
        "help": "Close out a completed execplan through one command-owned writer.",
        "name": "closeout",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path.",
            "name": "target"
          },
          {
            "choices": [
              "slice",
              "lane",
              "epic"
            ],
            "default": "slice",
            "flags": [
              "--claim-level"
            ],
            "help": "Scope claimed by this closeout.",
            "name": "claim_level"
          },
          {
            "choices": [
              "satisfied",
              "partial",
              "unsatisfied",
              "deferred-with-owner"
            ],
            "default": "satisfied",
            "flags": [
              "--intent-status"
            ],
            "help": "Intent result for the closeout claim.",
            "name": "intent_status"
          },
          {
            "choices": [
              "none",
              "memory",
              "planning",
              "docs",
              "tests",
              "contracts",
              "issue",
              "dismissed"
            ],
            "default": "none",
            "flags": [
              "--residue"
            ],
            "help": "Durable residue route for follow-up or learning.",
            "name": "residue"
          },
          {
            "default": "last",
            "flags": [
              "--proof-from"
            ],
            "help": "Use existing proof with 'last' or record the supplied proof command/text.",
            "name": "proof_from"
          },
          {
            "flags": [
              "--residue-owner"
            ],
            "help": "Canonical owner for non-empty residue or deferred intent.",
            "name": "residue_owner"
          },
          {
            "flags": [
              "--what-happened"
            ],
            "help": "Finished-run summary to write when the execplan still has placeholder execution evidence.",
            "name": "what_happened"
          },
          {
            "flags": [
              "--scope-touched"
            ],
            "help": "Concrete scope touched by the finished run.",
            "name": "scope_touched"
          },
          {
            "flags": [
              "--changed-surfaces"
            ],
            "help": "Concrete files or surfaces changed by the finished run.",
            "name": "changed_surfaces"
          },
          {
            "flags": [
              "--review-summary"
            ],
            "help": "Closeout review summary for scope and intent reconciliation.",
            "name": "review_summary"
          },
          {
            "flags": [
              "--outcome-summary"
            ],
            "help": "Outcome delivered summary for the finished run.",
            "name": "outcome_summary"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Show closeout actions without mutating files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--discard-archive"
            ],
            "help": "Do not retain the archived execplan record after cleanup.",
            "name": "discard_archive"
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
        "id": "planning.closeout.lifecycle",
        "path": "operations/planning.closeout.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning closeout policy",
          "managed planning payload mutation",
          "module result assembly"
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
          "planning.closeout.apply",
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
      "adapter_id": "planning.close-item.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "close-item"
      },
      "conformance_refs": [
        "planning.close-item.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "arguments": [
          {
            "help": "Planning item id, issue id, or execplan slug to close.",
            "name": "item"
          }
        ],
        "help": "Close completed planning residue by id.",
        "name": "close-item",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "default": "",
            "flags": [
              "--reason"
            ],
            "help": "Optional closure reason recorded with the mutation.",
            "name": "reason"
          },
          {
            "default": "",
            "flags": [
              "--issue"
            ],
            "help": "Optional issue reference associated with the closure.",
            "name": "issue"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Preview closure without writing files.",
            "name": "dry_run"
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
        "id": "planning.close-item.lifecycle",
        "path": "operations/planning.close-item.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning lifecycle mutation primitive",
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
          "python.function.call",
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
      "adapter_id": "planning.create-review.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "create-review"
      },
      "conformance_refs": [
        "planning.create-review.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "arguments": [
          {
            "help": "Review slug or title used to derive the review filename.",
            "name": "slug"
          }
        ],
        "help": "Create a schema-valid planning review record skeleton.",
        "name": "create-review",
        "options": [
          {
            "flags": [
              "--title"
            ],
            "help": "Human-readable review title.",
            "name": "title",
            "required": true
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
              "--scope"
            ],
            "help": "Optional review scope.",
            "name": "scope"
          },
          {
            "default": "review",
            "flags": [
              "--classification"
            ],
            "help": "Review classification.",
            "name": "classification"
          },
          {
            "action": "store_true",
            "flags": [
              "--render-markdown"
            ],
            "help": "Also render the derived markdown review projection.",
            "name": "render_markdown"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Preview review creation without writing files.",
            "name": "dry_run"
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
        "id": "planning.create-review.lifecycle",
        "path": "operations/planning.create-review.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning lifecycle mutation primitive",
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
          "python.function.call",
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
      "adapter_id": "planning.delegation-decision.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "delegation-decision"
      },
      "conformance_refs": [
        "planning.delegation-decision.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Record the delegation route chosen for the active execplan.",
        "name": "delegation-decision",
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
              "--plan"
            ],
            "help": "Plan path, slug, or id; defaults to the active execplan.",
            "name": "plan"
          },
          {
            "choices": [
              "keep-local",
              "delegate-exploration",
              "delegate-implementation",
              "delegate-validation",
              "escalate-review",
              "no-safe-route"
            ],
            "flags": [
              "--route"
            ],
            "help": "Delegation route selected for the plan.",
            "name": "route",
            "required": true
          },
          {
            "default": "",
            "flags": [
              "--skipped-reason"
            ],
            "help": "Reason delegation was skipped.",
            "name": "skipped_reason"
          },
          {
            "default": "",
            "flags": [
              "--expected-savings"
            ],
            "help": "Expected savings from delegation.",
            "name": "expected_savings"
          },
          {
            "default": "",
            "flags": [
              "--actual-friction"
            ],
            "help": "Actual delegation friction observed.",
            "name": "actual_friction"
          },
          {
            "default": "",
            "flags": [
              "--proof-result"
            ],
            "help": "Proof result from the delegated or local route.",
            "name": "proof_result"
          },
          {
            "default": "",
            "flags": [
              "--quality-concern"
            ],
            "help": "Quality concern discovered during delegation.",
            "name": "quality_concern"
          },
          {
            "default": "",
            "flags": [
              "--decomposition-adjustment"
            ],
            "help": "Planning decomposition adjustment to record.",
            "name": "decomposition_adjustment"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
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
        "id": "planning.delegation-decision.lifecycle",
        "path": "operations/planning.delegation-decision.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning state mutation policy",
          "planning provenance updates",
          "module result assembly"
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
          "planning.delegation-decision.apply",
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
          "python.function.call",
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
      "adapter_id": "planning.handoff.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "handoff"
      },
      "conformance_refs": [
        "planning.handoff.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Emit the compact delegated-worker handoff derived from active planning state.",
        "name": "handoff",
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
        "id": "planning.handoff.report",
        "path": "operations/planning.handoff.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning handoff assembly",
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
          "python.function.call",
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
      "adapter_id": "planning.init.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "init"
      },
      "conformance_refs": [
        "planning.init.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Install bootstrap files into a repository.",
        "name": "init",
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
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--force"
            ],
            "help": "Overwrite managed files when needed.",
            "name": "force"
          },
          {
            "action": "store_true",
            "flags": [
              "--local"
            ],
            "help": "Set up the workspace in a local, non-tracked directory.",
            "name": "local"
          },
          {
            "action": "store_true",
            "flags": [
              "--include-optional"
            ],
            "help": "Copy optional planning docs for richer review, intake, and recovery workflows.",
            "name": "include_optional"
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
        "id": "planning.init.lifecycle",
        "path": "operations/planning.init.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning lifecycle policy",
          "managed planning payload mutation",
          "module result assembly"
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
          "python.function.call",
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
      "adapter_id": "planning.install.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "install"
      },
      "conformance_refs": [
        "planning.install.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Install bootstrap files into a repository.",
        "name": "install",
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
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--force"
            ],
            "help": "Overwrite managed files when needed.",
            "name": "force"
          },
          {
            "action": "store_true",
            "flags": [
              "--local"
            ],
            "help": "Set up the workspace in a local, non-tracked directory.",
            "name": "local"
          },
          {
            "action": "store_true",
            "flags": [
              "--include-optional"
            ],
            "help": "Copy optional planning docs for richer review, intake, and recovery workflows.",
            "name": "include_optional"
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
        "id": "planning.install.lifecycle",
        "path": "operations/planning.install.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning lifecycle policy",
          "managed planning payload mutation",
          "module result assembly"
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
          "python.function.call",
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
      "adapter_id": "planning.list-files.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "list-files"
      },
      "conformance_refs": [
        "planning.list-files.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "List bundled planning payload files.",
        "name": "list-files",
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
        "id": "planning.list-files.report",
        "path": "operations/planning.list-files.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning payload inventory",
          "module result assembly"
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
          "filesystem.glob",
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
      "adapter_id": "planning.new-plan.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "new-plan"
      },
      "conformance_refs": [
        "planning.new-plan.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Create a schema-valid execplan scaffold and optionally register it.",
        "name": "new-plan",
        "options": [
          {
            "flags": [
              "--id"
            ],
            "help": "Stable slug/id for the plan; used as the .plan.json filename.",
            "name": "id",
            "required": true
          },
          {
            "flags": [
              "--title"
            ],
            "help": "Human-readable plan title.",
            "name": "title",
            "required": true
          },
          {
            "default": "",
            "flags": [
              "--source"
            ],
            "help": "Optional source reference such as an issue URL or chat-intake summary.",
            "name": "source"
          },
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
              "--activate"
            ],
            "help": "Register the new plan in todo.active_items.",
            "name": "activate"
          },
          {
            "action": "store_true",
            "flags": [
              "--queue"
            ],
            "help": "Register the new plan in todo.queued_items.",
            "name": "queue"
          },
          {
            "action": "store_true",
            "flags": [
              "--switch-active"
            ],
            "help": "When used with --activate, demote existing active items into the queue before registering the new active plan.",
            "name": "switch_active"
          },
          {
            "action": "store_true",
            "flags": [
              "--prep-only"
            ],
            "help": "Mark this scaffold as a planning-only handoff slice.",
            "name": "prep_only"
          },
          {
            "action": "store_true",
            "flags": [
              "--overwrite"
            ],
            "help": "Replace an existing scaffold with the same id.",
            "name": "overwrite"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
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
        "id": "planning.new-plan.lifecycle",
        "path": "operations/planning.new-plan.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning state mutation policy",
          "planning provenance updates",
          "module result assembly"
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
          "planning.new-plan.apply",
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
      "adapter_id": "planning.promote-to-plan.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "promote-to-plan"
      },
      "conformance_refs": [
        "planning.promote-to-plan.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "arguments": [
          {
            "help": "TODO item id or decomposition lane id to promote.",
            "name": "item_id"
          }
        ],
        "help": "Promote a direct TODO item into an execplan scaffold.",
        "name": "promote-to-plan",
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
              "--plan-slug"
            ],
            "help": "Optional plan slug for the created execplan.",
            "name": "plan_slug"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
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
        "id": "planning.promote-to-plan.lifecycle",
        "path": "operations/planning.promote-to-plan.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning state mutation policy",
          "planning provenance updates",
          "module result assembly"
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
          "planning.promote-to-plan.apply",
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
      "adapter_id": "planning.prompt.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "prompt"
      },
      "conformance_refs": [
        "planning.prompt.process"
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
            "choices": [
              "install",
              "adopt"
            ],
            "help": "Prompt guidance to render.",
            "name": "prompt_command"
          }
        ],
        "help": "Render planning bootstrap prompt guidance.",
        "name": "prompt",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to ./repo in prompt text.",
            "name": "target"
          }
        ]
      },
      "operation_ref": {
        "id": "planning.prompt.render",
        "path": "operations/planning.prompt.render.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning upgrade-source guidance",
          "prompt text compatibility formatting"
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
          "planning.prompt.render",
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
    },
    {
      "adapter_id": "planning.record-recovery.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "record-recovery"
      },
      "conformance_refs": [
        "planning.record-recovery.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Bless an emergency manual repair to managed planning surfaces with explicit provenance.",
        "name": "record-recovery",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Target repository path. Defaults to the current directory.",
            "name": "target"
          },
          {
            "action": "append",
            "flags": [
              "--path"
            ],
            "help": "Managed planning path repaired manually.",
            "name": "paths",
            "required": true
          },
          {
            "flags": [
              "--reason"
            ],
            "help": "Reason the recovery was needed.",
            "name": "reason",
            "required": true
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
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
        "id": "planning.record-recovery.lifecycle",
        "path": "operations/planning.record-recovery.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning state mutation policy",
          "planning provenance updates",
          "module result assembly"
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
          "planning.record-recovery.apply",
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
          "python.function.call",
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
      "adapter_id": "planning.uninstall.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "uninstall"
      },
      "conformance_refs": [
        "planning.uninstall.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": true,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Remove managed bootstrap files when they still match package content.",
        "name": "uninstall",
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
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
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
        "id": "planning.uninstall.lifecycle",
        "path": "operations/planning.uninstall.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning lifecycle policy",
          "managed planning payload mutation",
          "module result assembly"
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
          "python.function.call",
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
      "adapter_id": "planning.upgrade.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "upgrade"
      },
      "conformance_refs": [
        "planning.upgrade.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Refresh package-managed helper surfaces without overwriting repo-owned root planning files.",
        "name": "upgrade",
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
              "--dry-run"
            ],
            "help": "Preview changes without writing files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--include-optional"
            ],
            "help": "Copy optional planning docs for richer review, intake, and recovery workflows.",
            "name": "include_optional"
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
        "id": "planning.upgrade.lifecycle",
        "path": "operations/planning.upgrade.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning lifecycle policy",
          "managed planning payload mutation",
          "module result assembly"
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
          "python.function.call",
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
      "adapter_id": "planning.verify-payload.cli",
      "command": {
        "manifest_ref": "package:planning:cli",
        "name": "verify-payload"
      },
      "conformance_refs": [
        "planning.verify-payload.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Verify bundled planning payload and generated operation resources.",
        "name": "verify-payload",
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
        "id": "planning.verify-payload.report",
        "path": "operations/planning.verify-payload.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning payload verification",
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
          "python.function.call",
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
    "local_runtime_bindings": [
      {
        "module_file": "primitives.planning_installer",
        "source_import_module": "repo_planning_bootstrap.installer"
      },
      {
        "generated_function_overrides": [
          {
            "function": "emit_planning_operation_output",
            "implementation": "json_output_with_source_fallback"
          }
        ],
        "module_file": "primitives.planning_runtime",
        "source_import_module": "repo_planning_bootstrap.runtime_projection"
      }
    ],
    "operation_executor": {
      "handlers": [
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
          "function": "load_planning_summary_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.summary.load"
        },
        {
          "function": "load_planning_reconcile_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.reconcile.load"
        },
        {
          "function": "emit_planning_operation_output",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "output.emit"
        },
        {
          "function": "render_planning_prompt_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.prompt.render"
        },
        {
          "function": "apply_planning_new_plan_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.new-plan.apply"
        },
        {
          "function": "apply_planning_promote_to_plan_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.promote-to-plan.apply"
        },
        {
          "function": "apply_planning_archive_plan_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.archive-plan.apply"
        },
        {
          "function": "apply_planning_closeout_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.closeout.apply"
        },
        {
          "function": "apply_planning_delegation_decision_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.delegation-decision.apply"
        },
        {
          "function": "apply_planning_record_recovery_operation",
          "handler": "runtime_handler",
          "import_module": "repo_planning_bootstrap.runtime_projection",
          "primitive": "planning.record-recovery.apply"
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
        },
        {
          "arg": "item",
          "default": "",
          "name": "item"
        },
        {
          "arg": "reason",
          "default": "",
          "name": "reason"
        },
        {
          "arg": "issue",
          "default": "",
          "name": "issue"
        },
        {
          "arg": "slug",
          "default": "",
          "name": "slug"
        },
        {
          "arg": "title",
          "default": "",
          "name": "title"
        },
        {
          "arg": "scope",
          "default": null,
          "name": "scope"
        },
        {
          "arg": "classification",
          "default": "review",
          "name": "classification"
        },
        {
          "arg": "render_markdown",
          "default": false,
          "name": "render_markdown"
        },
        {
          "arg": "prompt_command",
          "default": "",
          "name": "prompt_command"
        },
        {
          "arg": "force",
          "default": false,
          "name": "force"
        },
        {
          "arg": "local",
          "default": false,
          "name": "local"
        },
        {
          "arg": "include_optional",
          "default": false,
          "name": "include_optional"
        },
        {
          "arg": "id",
          "default": "",
          "name": "id"
        },
        {
          "arg": "source",
          "default": "",
          "name": "source"
        },
        {
          "arg": "activate",
          "default": false,
          "name": "activate"
        },
        {
          "arg": "queue",
          "default": false,
          "name": "queue"
        },
        {
          "arg": "switch_active",
          "default": false,
          "name": "switch_active"
        },
        {
          "arg": "prep_only",
          "default": false,
          "name": "prep_only"
        },
        {
          "arg": "overwrite",
          "default": false,
          "name": "overwrite"
        },
        {
          "arg": "item_id",
          "default": "",
          "name": "item_id"
        },
        {
          "arg": "plan_slug",
          "default": null,
          "name": "plan_slug"
        },
        {
          "arg": "plan",
          "default": null,
          "name": "plan"
        },
        {
          "arg": "apply_cleanup",
          "default": false,
          "name": "apply_cleanup"
        },
        {
          "arg": "prepare_closeout",
          "default": false,
          "name": "prepare_closeout"
        },
        {
          "arg": "retain_archive",
          "default": false,
          "name": "retain_archive"
        },
        {
          "arg": "parent_lane_closeout",
          "default": null,
          "name": "parent_lane_closeout"
        },
        {
          "arg": "closure_decision",
          "default": null,
          "name": "closure_decision"
        },
        {
          "arg": "intent_satisfied",
          "default": null,
          "name": "intent_satisfied"
        },
        {
          "arg": "unsolved_intent",
          "default": null,
          "name": "unsolved_intent"
        },
        {
          "arg": "intent_evidence",
          "default": null,
          "name": "intent_evidence"
        },
        {
          "arg": "closure_reason",
          "default": null,
          "name": "closure_reason"
        },
        {
          "arg": "closure_evidence",
          "default": null,
          "name": "closure_evidence"
        },
        {
          "arg": "reopen_trigger",
          "default": null,
          "name": "reopen_trigger"
        },
        {
          "arg": "discard_summary",
          "default": null,
          "name": "discard_summary"
        },
        {
          "arg": "continuation_summary",
          "default": null,
          "name": "continuation_summary"
        },
        {
          "arg": "claim_level",
          "default": "slice",
          "name": "claim_level"
        },
        {
          "arg": "intent_status",
          "default": "satisfied",
          "name": "intent_status"
        },
        {
          "arg": "residue",
          "default": "none",
          "name": "residue"
        },
        {
          "arg": "proof_from",
          "default": "last",
          "name": "proof_from"
        },
        {
          "arg": "residue_owner",
          "default": null,
          "name": "residue_owner"
        },
        {
          "arg": "what_happened",
          "default": null,
          "name": "what_happened"
        },
        {
          "arg": "scope_touched",
          "default": null,
          "name": "scope_touched"
        },
        {
          "arg": "changed_surfaces",
          "default": null,
          "name": "changed_surfaces"
        },
        {
          "arg": "review_summary",
          "default": null,
          "name": "review_summary"
        },
        {
          "arg": "outcome_summary",
          "default": null,
          "name": "outcome_summary"
        },
        {
          "arg": "discard_archive",
          "default": false,
          "name": "discard_archive"
        },
        {
          "arg": "route",
          "default": "",
          "name": "route"
        },
        {
          "arg": "skipped_reason",
          "default": "",
          "name": "skipped_reason"
        },
        {
          "arg": "expected_savings",
          "default": "",
          "name": "expected_savings"
        },
        {
          "arg": "actual_friction",
          "default": "",
          "name": "actual_friction"
        },
        {
          "arg": "proof_result",
          "default": "",
          "name": "proof_result"
        },
        {
          "arg": "quality_concern",
          "default": "",
          "name": "quality_concern"
        },
        {
          "arg": "decomposition_adjustment",
          "default": "",
          "name": "decomposition_adjustment"
        },
        {
          "arg": "paths",
          "default": [],
          "name": "paths"
        }
      ],
      "module_file": "primitives.operation_executor",
      "supported_operation_ids": [
        "planning.adopt.lifecycle",
        "planning.archive-plan.lifecycle",
        "planning.closeout.lifecycle",
        "planning.close-item.lifecycle",
        "planning.create-review.lifecycle",
        "planning.delegation-decision.lifecycle",
        "planning.doctor.report",
        "planning.handoff.report",
        "planning.init.lifecycle",
        "planning.install.lifecycle",
        "planning.new-plan.lifecycle",
        "planning.promote-to-plan.lifecycle",
        "planning.prompt.render",
        "planning.reconcile.report",
        "planning.record-recovery.lifecycle",
        "planning.report.report",
        "planning.status.report",
        "planning.summary.report",
        "planning.uninstall.lifecycle",
        "planning.upgrade.lifecycle",
        "planning.verify-payload.report"
      ]
    },
    "render_runtime_module": true,
    "runtime_module_file": "cli"
  },
  "targets": [
    {
      "entrypoints": [
        "agentic-planning"
      ],
      "generated_root": "generated/planning/python",
      "generation_status": "mutation-capable-adapter",
      "kind": "python",
      "maturity_level_ref": "mutation-capable-adapter",
      "package_name": "agentic-planning",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-planning"
      ],
      "generated_root": "generated/typescript/planning-cli",
      "generation_status": "mutation-capable-adapter",
      "kind": "typescript",
      "maturity_level_ref": "mutation-capable-adapter",
      "package_name": "@agentic-workspace/planning-cli",
      "test_environment": "docker"
    }
  ]
} as const;

export type GeneratedCommandPackage = typeof generatedCommandPackage;
