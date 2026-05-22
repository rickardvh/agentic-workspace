// Generated command package metadata.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-workspace
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

export const generatedCommandPackage = {
  "commands": [
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
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit full module registry and component detail. Prefer the default output for ordinary routing.",
            "name": "verbose"
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
            "flags": [
              "--select"
            ],
            "help": "Return only comma-separated top-level or dotted JSON fields from the full command payload. Prefer this over --verbose when one or a few fields are needed.",
            "name": "select"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit full planning summary detail. Prefer selectors/default routing for ordinary startup.",
            "name": "verbose"
          },
          {
            "flags": [
              "--task"
            ],
            "help": "Optional task text used to return a task-scoped compact summary.",
            "name": "task"
          },
          {
            "action": "extend",
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
          "output.fields.select",
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
      "adapter_id": "planning.front-door.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "planning"
      },
      "conformance_refs": [
        "planning.front-door.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Show planning workflow help or run Planning operations through the workspace front door.",
        "name": "planning",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path used in example commands.",
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
        ],
        "subcommand_dest": "planning_command",
        "subcommands": [
          {
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
                "help": "Optional repository path.",
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
                "help": "Show planned changes without mutating files.",
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
          {
            "help": "Promote a planning item into an execplan scaffold.",
            "name": "promote-to-plan",
            "options": [
              {
                "flags": [
                  "--item-id"
                ],
                "help": "Planning item id to promote.",
                "name": "item_id",
                "required": true
              },
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "flags": [
                  "--plan-slug"
                ],
                "help": "Optional generated plan slug override.",
                "name": "plan_slug"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show planned changes without mutating files.",
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
          {
            "help": "Route a freehand planning artifact into a canonical Planning surface.",
            "name": "intake-artifact",
            "options": [
              {
                "flags": [
                  "--artifact"
                ],
                "help": "Freehand planning artifact path inside the target repository.",
                "name": "artifact",
                "required": true
              },
              {
                "choices": [
                  "auto",
                  "execplan",
                  "decomposition"
                ],
                "default": "auto",
                "flags": [
                  "--route"
                ],
                "help": "Canonical Planning surface to route the artifact into.",
                "name": "route"
              },
              {
                "default": "",
                "flags": [
                  "--id"
                ],
                "help": "Optional target id or slug for the canonical Planning surface.",
                "name": "id"
              },
              {
                "default": "",
                "flags": [
                  "--title"
                ],
                "help": "Optional title when routing to an execplan scaffold.",
                "name": "title"
              },
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "action": "store_true",
                "flags": [
                  "--activate"
                ],
                "help": "Register an execplan route in todo.active_items.",
                "name": "activate"
              },
              {
                "action": "store_true",
                "flags": [
                  "--queue"
                ],
                "help": "Register an execplan route in todo.queued_items.",
                "name": "queue"
              },
              {
                "action": "store_true",
                "flags": [
                  "--switch-active"
                ],
                "help": "When used with --activate, demote existing active items before registering the new active plan.",
                "name": "switch_active"
              },
              {
                "action": "store_true",
                "flags": [
                  "--remove-source"
                ],
                "help": "Remove the original artifact after successful canonical intake.",
                "name": "remove_source"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show planned changes without mutating files.",
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
          {
            "help": "Close a completed execplan or parent lane after distillation.",
            "name": "archive-plan",
            "options": [
              {
                "flags": [
                  "--plan"
                ],
                "help": "Plan path, slug, or id to archive.",
                "name": "plan"
              },
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show planned changes without mutating files.",
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
                "help": "Closeout decision to write when --prepare-closeout is used.",
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
                "help": "Evidence of intent satisfaction for prepared closeout.",
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
                "help": "Reopen trigger for the prepared closure.",
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
          {
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
          {
            "help": "Close completed planning residue by id without hand-editing checked-in state.",
            "name": "close-item",
            "options": [
              {
                "flags": [
                  "--item"
                ],
                "help": "Planning item id to close.",
                "name": "item",
                "required": true
              },
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "flags": [
                  "--reason"
                ],
                "help": "Optional closure reason to record in the action detail.",
                "name": "reason"
              },
              {
                "flags": [
                  "--issue"
                ],
                "help": "Optional upstream issue reference tied to the closeout.",
                "name": "issue"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show planned changes without mutating files.",
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
          {
            "help": "Create a schema-valid planning review record skeleton.",
            "name": "create-review",
            "options": [
              {
                "flags": [
                  "--slug"
                ],
                "help": "Stable review record slug.",
                "name": "slug",
                "required": true
              },
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
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "flags": [
                  "--scope"
                ],
                "help": "Review scope summary.",
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
                "help": "Also render the derived markdown companion.",
                "name": "render_markdown"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show planned changes without mutating files.",
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
          {
            "help": "Record the delegation route chosen for the active execplan before mechanical lane work proceeds.",
            "name": "delegation-decision",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
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
                "help": "Delegation route chosen for this slice.",
                "name": "route",
                "required": true
              },
              {
                "default": "",
                "flags": [
                  "--skipped-reason"
                ],
                "help": "Required explanation when route is keep-local.",
                "name": "skipped_reason"
              },
              {
                "default": "",
                "flags": [
                  "--expected-savings"
                ],
                "help": "Expected time or token savings.",
                "name": "expected_savings"
              },
              {
                "default": "",
                "flags": [
                  "--actual-friction"
                ],
                "help": "Observed delegation friction.",
                "name": "actual_friction"
              },
              {
                "default": "",
                "flags": [
                  "--proof-result"
                ],
                "help": "Proof or validation result for the delegation decision.",
                "name": "proof_result"
              },
              {
                "default": "",
                "flags": [
                  "--quality-concern"
                ],
                "help": "Any quality concern from delegation or skipping it.",
                "name": "quality_concern"
              },
              {
                "default": "",
                "flags": [
                  "--decomposition-adjustment"
                ],
                "help": "Any follow-up adjustment needed in the decomposition.",
                "name": "decomposition_adjustment"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show planned changes without mutating files.",
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
          {
            "help": "Create a host architecture decision record scaffold through the configured decision target.",
            "name": "decision-scaffold",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "flags": [
                  "--title"
                ],
                "help": "Decision title.",
                "name": "title",
                "required": true
              },
              {
                "default": "",
                "flags": [
                  "--summary"
                ],
                "help": "Short decision statement.",
                "name": "summary"
              },
              {
                "flags": [
                  "--decision-id"
                ],
                "help": "Optional stable decision id; defaults to a slug of --title.",
                "name": "decision_id"
              },
              {
                "default": "proposed",
                "flags": [
                  "--status"
                ],
                "help": "Decision status to write into the scaffold.",
                "name": "status"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show the planned decision record without writing it.",
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
          {
            "help": "Promote a planning architecture-decision candidate into the configured decision target.",
            "name": "decision-promote",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "flags": [
                  "--from-plan"
                ],
                "help": "Repo-relative planning execplan JSON path.",
                "name": "from_plan",
                "required": true
              },
              {
                "default": "",
                "flags": [
                  "--title"
                ],
                "help": "Override promoted decision title.",
                "name": "title"
              },
              {
                "default": "",
                "flags": [
                  "--summary"
                ],
                "help": "Override promoted decision statement.",
                "name": "summary"
              },
              {
                "flags": [
                  "--decision-id"
                ],
                "help": "Optional stable decision id; defaults to a slug of the promoted title.",
                "name": "decision_id"
              },
              {
                "default": "proposed",
                "flags": [
                  "--status"
                ],
                "help": "Decision status to write into the promoted scaffold.",
                "name": "status"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Show the planned decision record without writing it.",
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
          {
            "help": "Emit the compact delegated-worker handoff derived from active planning state.",
            "name": "handoff",
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
          {
            "help": "Report compact planning module state.",
            "name": "report",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "action": "store_true",
                "flags": [
                  "--verbose"
                ],
                "help": "Emit broad diagnostic report detail.",
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
          }
        ],
        "subcommands_required": false
      },
      "operation_ref": {
        "id": "planning.front-door",
        "path": "operations/planning.front-door.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "planning module policy",
          "module runtime execution",
          "output emission"
        ],
        "target_specific": [
          "parser library",
          "package entrypoint wiring",
          "help text layout",
          "test container image"
        ],
        "universal": [
          "root command identity",
          "nested subcommand option semantics",
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
          "planning.front_door.dispatch",
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
      "adapter_id": "memory.front-door.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "memory"
      },
      "conformance_refs": [
        "memory.front-door.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Show memory workflow help or run Memory operations through the workspace front door.",
        "name": "memory",
        "options": [
          {
            "flags": [
              "--target"
            ],
            "help": "Optional repository path used in example commands.",
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
        ],
        "subcommand_dest": "memory_command",
        "subcommands": [
          {
            "help": "Suggest the smallest relevant durable note set for touched files or surfaces.",
            "name": "route",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
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
                "name": "surfaces",
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
          {
            "help": "Suggest memory updates for changed work.",
            "name": "sync-memory",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
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
          {
            "help": "Suggest memory notes that should be promoted or eliminated.",
            "name": "promotion-report",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
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
                "help": "Report all candidates or only remediation candidates.",
                "name": "mode"
              },
              {
                "action": "store_true",
                "flags": [
                  "--verbose"
                ],
                "help": "Emit broad diagnostic report detail.",
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
          {
            "help": "Recommend whether durable learning should update or create a Memory note.",
            "name": "capture-note",
            "options": [
              {
                "default": "",
                "flags": [
                  "--slug"
                ],
                "help": "Suggested note slug.",
                "name": "slug"
              },
              {
                "default": "",
                "flags": [
                  "--summary"
                ],
                "help": "Memory learning summary.",
                "name": "summary"
              },
              {
                "default": [],
                "flags": [
                  "--files"
                ],
                "help": "Changed files associated with the learning.",
                "name": "files",
                "nargs": "*"
              },
              {
                "default": [],
                "flags": [
                  "--surface"
                ],
                "help": "Explicit routing surfaces.",
                "name": "surfaces",
                "nargs": "*"
              },
              {
                "default": "",
                "flags": [
                  "--existing-note"
                ],
                "help": "Existing note path to update.",
                "name": "existing_note"
              },
              {
                "default": "",
                "flags": [
                  "--force-new-reason"
                ],
                "help": "Reason a new note is required.",
                "name": "force_new_reason"
              },
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
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
          {
            "help": "Report compact memory module state.",
            "name": "report",
            "options": [
              {
                "flags": [
                  "--target"
                ],
                "help": "Optional repository path.",
                "name": "target"
              },
              {
                "action": "store_true",
                "flags": [
                  "--verbose"
                ],
                "help": "Emit broad diagnostic report detail.",
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
          }
        ],
        "subcommands_required": false
      },
      "operation_ref": {
        "id": "memory.front-door",
        "path": "operations/memory.front-door.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "memory module policy",
          "module runtime execution",
          "output emission"
        ],
        "target_specific": [
          "parser library",
          "package entrypoint wiring",
          "help text layout",
          "test container image"
        ],
        "universal": [
          "root command identity",
          "nested subcommand option semantics",
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
          "memory.front_door.dispatch",
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
            "action": "extend",
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
            "flags": [
              "--select"
            ],
            "help": "Comma-separated startup fields to return, such as cli_invocation,durable_intent,skill_routing.",
            "name": "select"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit broad diagnostic startup output. Prefer --select for ordinary detail.",
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
            "action": "extend",
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
            "flags": [
              "--select"
            ],
            "help": "Return only comma-separated top-level or dotted JSON fields from the implementer context. Prefer this when one or a few fields are needed.",
            "name": "select"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit full implementer context. Prefer the default output for ordinary bounded implementation.",
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
          "output.fields.select",
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
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit the complete default-route contract. Prefer --section or default output for ordinary lookup.",
            "name": "verbose"
          },
          {
            "flags": [
              "--section"
            ],
            "help": "Return only one top-level defaults section in the compact contract profile.",
            "name": "section"
          },
          {
            "flags": [
              "--select"
            ],
            "help": "Return only comma-separated top-level or dotted JSON fields from the defaults payload. Prefer this over --verbose when one or a few fields are needed.",
            "name": "select"
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
            "action": "extend",
            "default": [],
            "flags": [
              "--changed"
            ],
            "help": "Return required proof commands for the provided repo-relative changed paths.",
            "name": "changed",
            "nargs": "*"
          },
          {
            "flags": [
              "--select"
            ],
            "help": "Return exact comma-separated field paths from the proof answer.",
            "name": "select"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit all proof routing detail. Prefer the default changed-path proof answer for ordinary validation.",
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
          "output.fields.select",
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
            "flags": [
              "--select"
            ],
            "help": "Return only comma-separated top-level or dotted JSON fields from the full command payload. Prefer this over --verbose when one or a few fields are needed.",
            "name": "select"
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit full resolved config detail. Prefer default output or targeted fields for ordinary posture checks.",
            "name": "verbose"
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
          "output.fields.select",
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
      "adapter_id": "system-intent.sync.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "system-intent"
      },
      "conformance_refs": [
        "system-intent.sync.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Show or refresh the workspace-owned compiled system-intent declaration.",
        "name": "system-intent",
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
            "help": "Optional repository path used to inspect system intent.",
            "name": "target"
          },
          {
            "action": "store_true",
            "flags": [
              "--sync"
            ],
            "help": "Refresh source discovery metadata and create the compiled system-intent declaration if it is missing.",
            "name": "sync"
          }
        ]
      },
      "operation_ref": {
        "id": "system-intent.sync",
        "path": "operations/system-intent.sync.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "system-intent source metadata refresh",
          "compiled intent mirror loading",
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
          "system_intent.config.resolve",
          "system_intent.source_metadata.refresh",
          "system_intent.mirror.read_or_create",
          "system_intent.result.emit"
        ]
      },
      "schemas": {
        "input": [],
        "output": []
      },
      "status": "generated"
    },
    {
      "adapter_id": "delegation-outcome.append.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "note-delegation-outcome"
      },
      "conformance_refs": [
        "delegation-outcome.append.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": false,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Append one local-only delegation outcome record for target-profile tuning.",
        "name": "note-delegation-outcome",
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
            "help": "Optional repository path used to record the local outcome.",
            "name": "target"
          },
          {
            "flags": [
              "--delegation-target"
            ],
            "help": "Local delegation target alias.",
            "name": "delegation_target",
            "required": true
          },
          {
            "flags": [
              "--task-class"
            ],
            "help": "Bounded task class label for this delegated run.",
            "name": "task_class",
            "required": true
          },
          {
            "choices": [
              "success",
              "mixed",
              "failed"
            ],
            "flags": [
              "--outcome"
            ],
            "help": "High-level delegated execution outcome.",
            "name": "outcome",
            "required": true
          },
          {
            "choices": [
              "sufficient",
              "borderline",
              "insufficient"
            ],
            "default": "sufficient",
            "flags": [
              "--handoff-sufficiency"
            ],
            "help": "Whether the checked-in handoff was enough for the delegated worker.",
            "name": "handoff_sufficiency"
          },
          {
            "choices": [
              "light",
              "normal",
              "high"
            ],
            "default": "normal",
            "flags": [
              "--review-burden"
            ],
            "help": "How much review/rework burden remained after delegation.",
            "name": "review_burden"
          },
          {
            "action": "store_true",
            "flags": [
              "--escalation-required"
            ],
            "help": "Record that the delegated run had to stop and escalate.",
            "name": "escalation_required"
          }
        ]
      },
      "operation_ref": {
        "id": "delegation-outcome.append",
        "path": "operations/delegation-outcome.append.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "local delegation outcome append",
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
          "delegation.outcome.append",
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
            "flags": [
              "--select"
            ],
            "help": "Comma-separated JSON fields to return, such as recommendations,warnings or top_recommendations,warnings.",
            "name": "select"
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
          "output.fields.select",
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
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit the full combined workspace report. Prefer default router output or --section for ordinary inspection.",
            "name": "verbose"
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
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
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
        "id": "reconcile.report",
        "path": "operations/reconcile.report.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "external intent cache refresh when available",
          "planning reconciliation loading",
          "safe-prune state mutation",
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
      "adapter_id": "external-intent.refresh-github.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "external-intent"
      },
      "conformance_refs": [
        "external-intent.refresh-github.help.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Refresh optional provider-agnostic external intent evidence through adapter subcommands.",
        "name": "external-intent",
        "options": [],
        "subcommand_dest": "external_intent_command",
        "subcommands": [
          {
            "help": "Refresh external intent evidence from GitHub issues through the optional gh CLI adapter.",
            "name": "refresh-github",
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
                "help": "Optional repository path whose external intent evidence should be refreshed.",
                "name": "target"
              },
              {
                "flags": [
                  "--repo"
                ],
                "help": "GitHub repository in owner/name form. Defaults to the gh repository for the target.",
                "name": "repo"
              },
              {
                "choices": [
                  "open",
                  "closed",
                  "all"
                ],
                "flags": [
                  "--state"
                ],
                "help": "GitHub issue state to import. Defaults to open; closed or all are explicit audit scopes.",
                "name": "state"
              },
              {
                "flags": [
                  "--limit"
                ],
                "help": "Maximum number of GitHub issues to import. Defaults to 1000.",
                "name": "limit",
                "type": "integer"
              },
              {
                "choices": [
                  "cache",
                  "planning"
                ],
                "default": "cache",
                "flags": [
                  "--storage"
                ],
                "help": "Where to write refreshed evidence. Defaults to ignored local cache; planning writes the legacy planning evidence path explicitly.",
                "name": "storage"
              },
              {
                "action": "store_true",
                "flags": [
                  "--apply-planning-candidates"
                ],
                "help": "Append schema-valid open prioritized issue candidates to Planning roadmap state after refresh.",
                "name": "apply_planning_candidates"
              },
              {
                "action": "store_true",
                "flags": [
                  "--dry-run"
                ],
                "help": "Preview refresh counts without writing external intent evidence.",
                "name": "dry_run"
              }
            ]
          }
        ]
      },
      "operation_ref": {
        "id": "external-intent.refresh-github",
        "path": "operations/external-intent.refresh-github.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "target root resolution",
          "optional gh adapter invocation",
          "provider-agnostic evidence normalization",
          "evidence write policy",
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
          "external_intent.github.repo.resolve",
          "external_intent.github.issues.list",
          "external_intent.evidence.normalize",
          "external_intent.evidence.write",
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
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit complete takeover/recovery context. Prefer default output for ordinary recovery routing.",
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
      "adapter_id": "install.lifecycle.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "install"
      },
      "conformance_refs": [
        "install.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Bootstrap selected modules into a target repository.",
        "name": "install",
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
              "--modules",
              "--module"
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
              "--strict-preflight"
            ],
            "help": "Require a fresh --preflight-token before running high-risk mutating commands.",
            "name": "strict_preflight"
          },
          {
            "flags": [
              "--preflight-token"
            ],
            "help": "Token emitted by 'agentic-workspace preflight --format json'.",
            "name": "preflight_token"
          },
          {
            "default": 900,
            "flags": [
              "--preflight-max-age-seconds"
            ],
            "help": "Maximum token age when --strict-preflight is enabled (default: 900).",
            "name": "preflight_max_age_seconds",
            "type": "integer"
          },
          {
            "action": "store_true",
            "flags": [
              "--local-only"
            ],
            "help": "Install in the normal repository layout while recording `.agentic-workspace/` in git-local exclude metadata.",
            "name": "local_only"
          },
          {
            "flags": [
              "--agent-instructions-file"
            ],
            "help": "Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md).",
            "name": "agent_instructions_file"
          },
          {
            "action": "store_true",
            "flags": [
              "--adopt"
            ],
            "help": "Force conservative adopt behavior.",
            "name": "adopt"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Show planned changes without mutating files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--print-prompt"
            ],
            "help": "Print the generated handoff prompt.",
            "name": "print_prompt"
          },
          {
            "flags": [
              "--write-prompt"
            ],
            "help": "Write the generated handoff prompt to a file.",
            "name": "write_prompt"
          }
        ]
      },
      "operation_ref": {
        "id": "install.lifecycle",
        "path": "operations/install.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "lifecycle selection",
          "preflight/destructive safety gates",
          "module mutation policy",
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
          "workspace.lifecycle.plan",
          "workspace.lifecycle.apply",
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
      "adapter_id": "init.lifecycle.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "init"
      },
      "conformance_refs": [
        "init.lifecycle.dry-run.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": false,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Bootstrap selected modules into a target repository.",
        "name": "init",
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
              "--modules",
              "--module"
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
              "--strict-preflight"
            ],
            "help": "Require a fresh --preflight-token before running high-risk mutating commands.",
            "name": "strict_preflight"
          },
          {
            "flags": [
              "--preflight-token"
            ],
            "help": "Token emitted by 'agentic-workspace preflight --format json'.",
            "name": "preflight_token"
          },
          {
            "default": 900,
            "flags": [
              "--preflight-max-age-seconds"
            ],
            "help": "Maximum token age when --strict-preflight is enabled (default: 900).",
            "name": "preflight_max_age_seconds",
            "type": "integer"
          },
          {
            "action": "store_true",
            "flags": [
              "--local-only"
            ],
            "help": "Install in the normal repository layout while recording `.agentic-workspace/` in git-local exclude metadata.",
            "name": "local_only"
          },
          {
            "flags": [
              "--agent-instructions-file"
            ],
            "help": "Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md).",
            "name": "agent_instructions_file"
          },
          {
            "action": "store_true",
            "flags": [
              "--adopt"
            ],
            "help": "Force conservative adopt behavior.",
            "name": "adopt"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Show planned changes without mutating files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--print-prompt"
            ],
            "help": "Print the generated handoff prompt.",
            "name": "print_prompt"
          },
          {
            "flags": [
              "--write-prompt"
            ],
            "help": "Write the generated handoff prompt to a file.",
            "name": "write_prompt"
          }
        ]
      },
      "operation_ref": {
        "id": "init.lifecycle",
        "path": "operations/init.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "lifecycle selection",
          "preflight/destructive safety gates",
          "module mutation policy",
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
          "workspace.lifecycle.plan",
          "workspace.lifecycle.apply",
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
      "adapter_id": "prompt.lifecycle.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "prompt"
      },
      "conformance_refs": [
        "prompt.init.process",
        "prompt.upgrade.process",
        "prompt.uninstall.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": true,
        "requires_preflight_gate": false,
        "writes_repo_state": false
      },
      "interface": {
        "help": "Print a ready-to-paste workspace lifecycle handoff prompt.",
        "name": "prompt",
        "options": [],
        "subcommand_dest": "prompt_command",
        "subcommands": [
          {
            "help": "Print the workspace bootstrap handoff prompt.",
            "name": "init",
            "operation_ref": {
              "id": "prompt.init",
              "path": "operations/prompt.init.json"
            },
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
                "flags": [
                  "--agent-instructions-file"
                ],
                "help": "Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md).",
                "name": "agent_instructions_file"
              },
              {
                "action": "store_true",
                "flags": [
                  "--adopt"
                ],
                "help": "Force conservative adopt behavior.",
                "name": "adopt"
              }
            ]
          },
          {
            "help": "Print the workspace upgrade handoff prompt.",
            "name": "upgrade",
            "operation_ref": {
              "id": "prompt.upgrade",
              "path": "operations/prompt.upgrade.json"
            },
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
          {
            "help": "Print the workspace uninstall handoff prompt.",
            "name": "uninstall",
            "operation_ref": {
              "id": "prompt.uninstall",
              "path": "operations/prompt.uninstall.json"
            },
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
          }
        ]
      },
      "operation_ref": {
        "id": "prompt.init",
        "path": "operations/prompt.init.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "module selection",
          "lifecycle handoff prompt rendering",
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
          "workspace.selection.resolve",
          "prompt.render",
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
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit all module lifecycle status detail. Prefer default output for ordinary health routing.",
            "name": "verbose"
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
          },
          {
            "action": "store_true",
            "flags": [
              "--verbose"
            ],
            "help": "Emit all diagnostic detail. Prefer default output for ordinary remediation routing.",
            "name": "verbose"
          },
          {
            "flags": [
              "--select"
            ],
            "help": "Return only comma-separated top-level or dotted JSON fields from the full command payload. Prefer this over --verbose when one or a few fields are needed.",
            "name": "select"
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
          "output.fields.select",
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
      "adapter_id": "upgrade.lifecycle.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "upgrade"
      },
      "conformance_refs": [
        "upgrade.lifecycle.dry-run.process",
        "upgrade.lifecycle.strict-preflight-refusal.process"
      ],
      "effect_hints": {
        "destructive": false,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": true,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Refresh managed surfaces for selected installed modules.",
        "name": "upgrade",
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
              "--modules",
              "--module"
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
              "--strict-preflight"
            ],
            "help": "Require a fresh --preflight-token before running high-risk mutating commands.",
            "name": "strict_preflight"
          },
          {
            "flags": [
              "--preflight-token"
            ],
            "help": "Token emitted by 'agentic-workspace preflight --format json'.",
            "name": "preflight_token"
          },
          {
            "default": 900,
            "flags": [
              "--preflight-max-age-seconds"
            ],
            "help": "Maximum token age when --strict-preflight is enabled (default: 900).",
            "name": "preflight_max_age_seconds",
            "type": "integer"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Show planned changes without mutating files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--repair-managed-local-instructions"
            ],
            "help": "Refresh only the workspace-managed .agentic-workspace local agent instructions file.",
            "name": "repair_managed_local_instructions"
          }
        ]
      },
      "operation_ref": {
        "id": "upgrade.lifecycle",
        "path": "operations/upgrade.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "lifecycle selection",
          "preflight/destructive safety gates",
          "module mutation policy",
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
          "workspace.lifecycle.plan",
          "workspace.lifecycle.apply",
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
      "adapter_id": "uninstall.lifecycle.cli",
      "command": {
        "manifest_ref": "cli_commands.json",
        "name": "uninstall"
      },
      "conformance_refs": [
        "uninstall.lifecycle.destructive-refusal.process",
        "uninstall.lifecycle.strict-preflight-refusal.process"
      ],
      "effect_hints": {
        "destructive": true,
        "idempotent": true,
        "read_only": false,
        "requires_preflight_gate": true,
        "writes_repo_state": true
      },
      "interface": {
        "help": "Remove managed surfaces conservatively for selected installed modules.",
        "name": "uninstall",
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
              "--modules",
              "--module"
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
              "--strict-preflight"
            ],
            "help": "Require a fresh --preflight-token before running high-risk mutating commands.",
            "name": "strict_preflight"
          },
          {
            "flags": [
              "--preflight-token"
            ],
            "help": "Token emitted by 'agentic-workspace preflight --format json'.",
            "name": "preflight_token"
          },
          {
            "default": 900,
            "flags": [
              "--preflight-max-age-seconds"
            ],
            "help": "Maximum token age when --strict-preflight is enabled (default: 900).",
            "name": "preflight_max_age_seconds",
            "type": "integer"
          },
          {
            "action": "store_true",
            "flags": [
              "--dry-run"
            ],
            "help": "Show planned changes without mutating files.",
            "name": "dry_run"
          },
          {
            "action": "store_true",
            "flags": [
              "--local-only"
            ],
            "help": "Remove the local-only workspace state from the normal repository layout.",
            "name": "local_only"
          }
        ]
      },
      "operation_ref": {
        "id": "uninstall.lifecycle",
        "path": "operations/uninstall.lifecycle.json"
      },
      "projection_boundary": {
        "runtime_owned": [
          "lifecycle selection",
          "preflight/destructive safety gates",
          "module mutation policy",
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
          "workspace.lifecycle.plan",
          "workspace.lifecycle.apply",
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
  "operation_contract_root": "src/agentic_workspace/contracts",
  "package_role": "root-workspace-cli",
  "program": "agentic-workspace",
  "python_runtime_binding": {
    "entrypoint": "agentic-workspace",
    "local_runtime_bindings": [
      {
        "generated_function_overrides": [
          {
            "function": "_resolve_workspace_operation_target_root",
            "implementation": "target_root_resolve"
          },
          {
            "function": "_load_workspace_operation_defaults",
            "generated_root": "_contracts",
            "implementation": "json_resource_load",
            "relative_path": "payload.json",
            "required_marker": "payload.json"
          },
          {
            "common_sections": [
              "startup",
              "proof_surfaces",
              "memory_routing",
              "capability_routing",
              "closeout_trust",
              "compact_contract_profile",
              "workflow_sufficiency",
              "authority_hierarchy",
              "compliance_economics"
            ],
            "function": "_select_workspace_operation_defaults",
            "implementation": "sectioned_payload_select",
            "payload_value": "defaults_payload",
            "source_command": "defaults"
          },
          {
            "function": "_emit_workspace_operation_output",
            "implementation": "json_output_with_source_fallback"
          }
        ],
        "module_file": "primitives.workspace_runtime",
        "source_import_module": "agentic_workspace.workspace_runtime_primitives"
      }
    ],
    "operation_executor": {
      "handlers": [
        {
          "function": "_resolve_workspace_operation_target_root",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "workspace.root.resolve"
        },
        {
          "function": "_load_workspace_operation_config",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "workspace.config.load"
        },
        {
          "function": "_load_workspace_operation_defaults",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "workspace.defaults.load"
        },
        {
          "function": "_select_workspace_operation_defaults",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "workspace.defaults.select"
        },
        {
          "function": "_resolve_workspace_operation_selection",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "workspace.selection.resolve"
        },
        {
          "function": "_render_workspace_operation_prompt",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "prompt.render"
        },
        {
          "function": "_append_workspace_operation_delegation_outcome",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "delegation.outcome.append"
        },
        {
          "function": "_load_workspace_operation_system_intent_config",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "system_intent.config.resolve"
        },
        {
          "function": "_refresh_workspace_operation_system_intent_metadata",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "system_intent.source_metadata.refresh"
        },
        {
          "function": "_read_or_create_workspace_operation_system_intent_mirror",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "system_intent.mirror.read_or_create"
        },
        {
          "function": "_emit_workspace_operation_output",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "system_intent.result.emit"
        },
        {
          "function": "_select_workspace_operation_fields",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "output.fields.select"
        },
        {
          "function": "_emit_workspace_operation_output",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "output.emit"
        },
        {
          "function": "_emit_workspace_operation_output",
          "handler": "runtime_handler",
          "import_module": "agentic_workspace.workspace_runtime_primitives",
          "primitive": "workspace.config.emit"
        }
      ],
      "initial_values": [
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
          "arg": "adopt",
          "default": false,
          "name": "adopt"
        },
        {
          "arg": "agent_instructions_file",
          "default": null,
          "name": "agent_instructions_file"
        },
        {
          "arg": "delegation_target",
          "default": null,
          "name": "delegation_target"
        },
        {
          "arg": "escalation_required",
          "default": false,
          "name": "escalation_required"
        },
        {
          "arg": "handoff_sufficiency",
          "default": null,
          "name": "handoff_sufficiency"
        },
        {
          "arg": "module",
          "default": null,
          "name": "module"
        },
        {
          "arg": "non_interactive",
          "default": false,
          "name": "non_interactive"
        },
        {
          "arg": "outcome",
          "default": null,
          "name": "outcome"
        },
        {
          "arg": "prompt_command",
          "default": null,
          "name": "prompt_command"
        },
        {
          "arg": "preset",
          "default": null,
          "name": "preset"
        },
        {
          "arg": "review_burden",
          "default": null,
          "name": "review_burden"
        },
        {
          "arg": "section",
          "default": null,
          "name": "section"
        },
        {
          "arg": "select",
          "default": null,
          "name": "select"
        },
        {
          "arg": "sync",
          "default": false,
          "name": "sync"
        },
        {
          "arg": "target",
          "default": null,
          "name": "target"
        },
        {
          "arg": "task_class",
          "default": null,
          "name": "task_class"
        }
      ],
      "module_file": "primitives.operation_executor",
      "supported_operation_ids": [
        "config.report",
        "defaults.report",
        "delegation-outcome.append",
        "prompt.init",
        "prompt.uninstall",
        "prompt.upgrade",
        "system-intent.sync"
      ]
    },
    "render_runtime_module": true,
    "resource_copies": [
      {
        "generated_root": "_contracts",
        "required_marker": "payload.json",
        "source_root": "src/agentic_workspace/contracts/workspace_defaults"
      }
    ],
    "runtime_module_file": "cli",
    "runtime_module_handlers": [
      {
        "function": "_run_lifecycle_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "doctor.report"
      },
      {
        "function": "_run_external_intent_refresh_github_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "external-intent.refresh-github"
      },
      {
        "function": "_run_implement_context_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "implement.context"
      },
      {
        "function": "_run_init_lifecycle_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "init.lifecycle"
      },
      {
        "function": "_run_init_lifecycle_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "install.lifecycle"
      },
      {
        "function": "_run_memory_front_door_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "memory.front-door"
      },
      {
        "function": "_run_modules_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "modules.report"
      },
      {
        "function": "_run_ownership_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "ownership.report"
      },
      {
        "function": "_run_planning_front_door_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "planning.front-door"
      },
      {
        "function": "_run_preflight_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "preflight.report"
      },
      {
        "function": "_run_proof_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "proof.report"
      },
      {
        "function": "_run_reconcile_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "reconcile.report"
      },
      {
        "function": "_run_report_combined_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "report.combined"
      },
      {
        "function": "_run_setup_guidance_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "setup.guidance"
      },
      {
        "function": "_run_skills_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "skills.report"
      },
      {
        "function": "_run_start_context_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "start.context"
      },
      {
        "function": "_run_lifecycle_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "status.report"
      },
      {
        "function": "_run_summary_report_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "summary.report"
      },
      {
        "function": "_run_lifecycle_mutation_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "uninstall.lifecycle"
      },
      {
        "function": "_run_lifecycle_mutation_adapter",
        "import_module": "agentic_workspace.workspace_runtime_primitives",
        "operation_id": "upgrade.lifecycle"
      }
    ]
  },
  "targets": [
    {
      "entrypoints": [
        "agentic-workspace"
      ],
      "generated_root": "generated/workspace/python",
      "generation_status": "mutation-capable-adapter",
      "kind": "python",
      "maturity_level_ref": "mutation-capable-adapter",
      "package_name": "agentic-workspace",
      "test_environment": "python-dev"
    },
    {
      "entrypoints": [
        "agentic-workspace"
      ],
      "generated_root": "generated/typescript/workspace-cli",
      "generation_status": "mutation-capable-adapter",
      "kind": "typescript",
      "maturity_level_ref": "mutation-capable-adapter",
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
