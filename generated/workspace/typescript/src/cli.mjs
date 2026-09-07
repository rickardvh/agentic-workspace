#!/usr/bin/env node
// Generated runnable adapter.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-workspace
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { writeSync } from 'node:fs';
import { runGeneratedOperation } from './runtime.mjs';

const supportedCommands = new Set(["agent-guidance", "assignment", "autopilot", "checkpoint", "config", "config-policy", "correction-event", "defaults", "doctor", "evaluation", "external-evidence-query", "external-evidence-submit", "external-intent", "final-response", "implement", "init", "install", "instructions", "memory", "modules", "note-delegation-outcome", "ownership", "planning", "preflight", "prompt", "proof", "reconcile", "report", "session-log", "setup", "skills", "start", "status", "summary", "system-intent", "uninstall", "upgrade", "work-thread"]);
const nativeOperationIds = new Set(["agent-guidance.delete", "agent-guidance.edit", "agent-guidance.merge", "agent-guidance.promote", "agent-guidance.retire", "agent-guidance.revalidate", "agent-guidance.split", "agent-guidance.supersede", "agent-guidance.suppress", "agent-guidance.weaken", "assignment.admit", "assignment.cleanup", "assignment.close", "assignment.dispatch", "assignment.export", "assignment.import", "assignment.integrate", "assignment.override", "assignment.reassign", "assignment.reject", "assignment.repair", "assignment.status", "autopilot.run", "checkpoint.write", "config.policy-apply", "config.report", "correction-event.correct-dispute", "correction-event.identity-init", "correction-event.prune-compact", "correction-event.query", "correction-event.submit", "correction-event.withdraw-supersede", "defaults.report", "delegation-outcome.append", "doctor.report", "evaluation.authority-refresh", "evaluation.delivery-status", "evaluation.external-adapter-receipt", "evaluation.external-delivery", "evaluation.external-host-result-import", "evaluation.external-request", "evaluation.local-delivery", "evaluation.observe", "evaluation.prune", "evaluation.register", "evaluation.report-preview", "evaluation.retry", "evaluation.status", "evaluation.transition", "external-evidence.query", "external-evidence.submit", "external-intent.refresh-github", "final-response.admit", "implement.context", "init.lifecycle", "install.lifecycle", "instructions.check", "instructions.create", "instructions.explain", "instructions.list", "instructions.migrate", "instructions.route-select", "instructions.routes", "memory.front-door", "modules.report", "ownership.report", "planning.front-door", "preflight.report", "prompt.init", "prompt.uninstall", "prompt.upgrade", "proof.report", "reconcile.report", "report.combined", "session-log.manage", "setup.guidance", "skills.report", "start.context", "status.report", "summary.report", "system-intent.sync", "uninstall.lifecycle", "upgrade.lifecycle", "work-thread.carry-inspect", "work-thread.carry-prune", "work-thread.carry-select", "work-thread.prune", "work-thread.select"]);
const commandDefinitions = [
  {
    "interface": {
      "help": "Show module inventory as explicit drill-down; ordinary agents should start from start/report routing.",
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
          "flags": [
            "--section"
          ],
          "help": "Return one module detail section such as package_footprint or participation_model.",
          "name": "section"
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
    "name": "modules",
    "operation_ref": {
      "id": "modules.report",
      "path": "operations/modules.report.json"
    }
  },
  {
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
    "name": "summary",
    "operation_ref": {
      "id": "summary.report",
      "path": "operations/summary.report.json"
    }
  },
  {
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
              "default": "",
              "flags": [
                "--lane"
              ],
              "help": "Explicit active lane that owns this plan; requires --activate.",
              "name": "owner_lane"
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
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "help": "Preview or apply one owner-scoped semantic mutation; ordinary use resolves currentness internally.",
          "name": "targeted-write",
          "options": [
            {
              "flags": [
                "--plan"
              ],
              "help": "Exact live execplan id or repo-relative owner path.",
              "name": "targeted_write_plan",
              "required": true
            },
            {
              "flags": [
                "--patch"
              ],
              "help": "JSON object containing only supported owner-scoped fields.",
              "name": "patch",
              "required": true
            },
            {
              "default": "",
              "flags": [
                "--completion-correction"
              ],
              "help": "Typed JSON completion-truth correction with admitted review evidence and linked proposal guards.",
              "name": "completion_correction"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optional low-level Planning revision guard; ordinary semantic mutation resolves currentness internally.",
              "name": "expect_planning_revision",
              "required": false
            },
            {
              "default": "",
              "flags": [
                "--expect-owner-revision"
              ],
              "help": "Optional low-level owner revision guard; omit all revision guards for ordinary semantic mutation.",
              "name": "expect_owner_revision",
              "required": false
            },
            {
              "default": "",
              "flags": [
                "--expect-lane-revision"
              ],
              "help": "Lane revision guard when the execplan is an active lane slice.",
              "name": "expect_lane_revision"
            },
            {
              "action": "store_true",
              "flags": [
                "--apply"
              ],
              "help": "Apply after rerunning the operation's sealed internal preflight.",
              "name": "apply"
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
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "help": "Create a first-class Planning decomposition record.",
          "name": "decomposition-create",
          "options": [
            {
              "flags": [
                "--id"
              ],
              "help": "Stable decomposition id; used as the .decomposition.json filename.",
              "name": "id",
              "required": true
            },
            {
              "flags": [
                "--title"
              ],
              "help": "Human-readable decomposition title.",
              "name": "title",
              "required": true
            },
            {
              "flags": [
                "--outcome"
              ],
              "help": "Larger intended outcome owned by the decomposition.",
              "name": "outcome",
              "required": true
            },
            {
              "default": "Promote a candidate lane only after its scope, owner surface, and proof are ready.",
              "flags": [
                "--promotion-rule"
              ],
              "help": "Rule for promoting candidate lanes.",
              "name": "promotion_rule"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "help": "Select an existing Planning owner without creating or overwriting it.",
          "name": "owner-select",
          "options": [
            {
              "default": "",
              "flags": [
                "--owner"
              ],
              "help": "Stable existing owner id.",
              "name": "owner"
            },
            {
              "default": "",
              "flags": [
                "--owner-ref"
              ],
              "help": "Explicit repo-relative existing owner reference.",
              "name": "owner_ref"
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
                "local",
                "shared"
              ],
              "default": "local",
              "flags": [
                "--mode"
              ],
              "help": "Selection scope; local is advisory and current-work scoped.",
              "name": "mode"
            },
            {
              "default": "",
              "flags": [
                "--reason"
              ],
              "help": "Required reason for explicit shared checked-in selection.",
              "name": "reason"
            },
            {
              "default": "",
              "flags": [
                "--current-work-id"
              ],
              "help": "Stable current-work context id; defaults to the local context.",
              "name": "current_work_id"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id.",
              "name": "expect_planning_revision"
            },
            {
              "default": "",
              "flags": [
                "--expect-current-work-revision"
              ],
              "help": "Optimistic current-work selection revision.",
              "name": "expect_current_work_revision"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Return the exact proposed delta without writing files.",
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
          "help": "Shape a durable issue-to-lane relation without activating work.",
          "name": "issue-shape",
          "options": [
            {
              "default": "",
              "flags": [
                "--issue"
              ],
              "help": "External issue or tracker id.",
              "name": "issue"
            },
            {
              "default": "",
              "flags": [
                "--external-ref"
              ],
              "help": "Provider-agnostic external work reference.",
              "name": "external_ref"
            },
            {
              "default": "",
              "flags": [
                "--lane"
              ],
              "help": "Strategic Planning lane id; defaults to ungrouped.",
              "name": "issue_lane"
            },
            {
              "default": "",
              "flags": [
                "--priority"
              ],
              "help": "Internal priority within the lane.",
              "name": "priority"
            },
            {
              "default": "",
              "flags": [
                "--depends-on"
              ],
              "help": "Comma-separated external refs this issue depends on.",
              "name": "depends_on"
            },
            {
              "default": "",
              "flags": [
                "--rationale"
              ],
              "help": "Why this issue belongs in the selected lane.",
              "name": "rationale"
            },
            {
              "choices": [
                "observed",
                "shaped",
                "ready-to-promote",
                "blocked",
                "deferred"
              ],
              "default": "",
              "flags": [
                "--maturity"
              ],
              "help": "Strategic shaping maturity.",
              "name": "maturity"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-relation-revision"
              ],
              "help": "Optimistic relation revision required when editing an existing relation.",
              "name": "expect_relation_revision"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Advisory Planning revision captured in the receipt.",
              "name": "expect_planning_revision"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Preview the relation delta without writing files.",
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
          "help": "Create a pending target-branch Planning integration proposal.",
          "name": "integration-propose",
          "options": [
            {
              "default": "",
              "flags": [
                "--proposal-id"
              ],
              "help": "Stable proposal id; defaults from subject and transition.",
              "name": "proposal_id"
            },
            {
              "default": "",
              "flags": [
                "--owner"
              ],
              "help": "Affected Planning owner id.",
              "name": "owner"
            },
            {
              "default": "",
              "flags": [
                "--owner-ref"
              ],
              "help": "Repo-relative affected owner path.",
              "name": "owner_ref"
            },
            {
              "default": "",
              "flags": [
                "--issue"
              ],
              "help": "External issue or tracker id.",
              "name": "issue"
            },
            {
              "default": "",
              "flags": [
                "--external-ref"
              ],
              "help": "Provider-agnostic external work reference.",
              "name": "external_ref"
            },
            {
              "choices": [
                "mark-integrated",
                "close-owner",
                "archive-owner",
                "keep-open"
              ],
              "default": "",
              "flags": [
                "--requested-transition"
              ],
              "help": "Lifecycle transition requested for target-branch apply.",
              "name": "requested_transition"
            },
            {
              "default": "",
              "flags": [
                "--proof"
              ],
              "help": "Comma-separated proof references for the requested transition.",
              "name": "proof"
            },
            {
              "default": "",
              "flags": [
                "--what-happened"
              ],
              "help": "Concrete feature-head outcome; required when the owner cannot derive non-placeholder finish-run evidence.",
              "name": "what_happened"
            },
            {
              "default": "",
              "flags": [
                "--scope-touched"
              ],
              "help": "Concrete feature-head scope touched; required when the owner cannot derive it.",
              "name": "scope_touched"
            },
            {
              "default": "",
              "flags": [
                "--changed-surfaces"
              ],
              "help": "Concrete feature-head changed surfaces; required when the owner cannot derive them.",
              "name": "changed_surfaces"
            },
            {
              "default": "",
              "flags": [
                "--review-summary"
              ],
              "help": "Concrete feature-head scope review, or derive it from admitted owner scope.",
              "name": "review_summary"
            },
            {
              "default": "",
              "flags": [
                "--outcome-summary"
              ],
              "help": "Concrete delivered outcome, or derive it from admitted owner intent.",
              "name": "outcome_summary"
            },
            {
              "default": "",
              "flags": [
                "--parent-boundary"
              ],
              "help": "Boundary that keeps parent/lane truth independent.",
              "name": "parent_boundary"
            },
            {
              "default": "",
              "flags": [
                "--invariant"
              ],
              "help": "Comma-separated invariants preserved by the proposal.",
              "name": "invariant"
            },
            {
              "default": "",
              "flags": [
                "--expect-subject-revision"
              ],
              "help": "Optimistic affected-subject revision.",
              "name": "expect_subject_revision"
            },
            {
              "default": "",
              "flags": [
                "--expect-target-revision"
              ],
              "help": "Alias for --expect-subject-revision.",
              "name": "expect_target_revision"
            },
            {
              "action": "store_true",
              "flags": [
                "--record-feature-completion"
              ],
              "help": "Atomically record accepted feature-head proof and non-terminal closeout posture before creating the guarded integration proposal.",
              "name": "record_feature_completion"
            },
            {
              "action": "store_true",
              "flags": [
                "--refresh-existing"
              ],
              "help": "Refresh revision guards on an existing pending proposal without changing lifecycle semantics.",
              "name": "refresh_existing"
            },
            {
              "default": "",
              "flags": [
                "--expect-proposal-revision"
              ],
              "help": "Optimistic revision of the pending proposal being refreshed.",
              "name": "expect_proposal_revision"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Target-authority guard from planning_revision.target_authority_revision; do not use planning_revision.revision_id.",
              "name": "expect_planning_revision"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Preview the proposal without writing files.",
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
          "help": "Apply a pending Planning integration proposal as target-branch truth.",
          "name": "integration-apply",
          "options": [
            {
              "flags": [
                "--proposal"
              ],
              "help": "Proposal id or repo-relative proposal JSON path.",
              "name": "proposal",
              "required": true
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Advisory Planning revision captured in the receipt.",
              "name": "expect_planning_revision"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Preview the apply transaction without writing files.",
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
          "help": "Create a first-class Planning lane record.",
          "name": "lane-create",
          "options": [
            {
              "flags": [
                "--id"
              ],
              "help": "Stable lane id; used as the .lane.json filename.",
              "name": "id",
              "required": true
            },
            {
              "default": "",
              "flags": [
                "--title"
              ],
              "help": "Human-readable lane title.",
              "name": "title"
            },
            {
              "default": "",
              "flags": [
                "--parent-decomposition"
              ],
              "help": "Optional parent decomposition record path.",
              "name": "parent_decomposition"
            },
            {
              "default": "",
              "flags": [
                "--outcome"
              ],
              "help": "Lane-level outcome.",
              "name": "outcome"
            },
            {
              "default": "",
              "flags": [
                "--purpose"
              ],
              "help": "How this lane advances the parent decomposition.",
              "name": "purpose"
            },
            {
              "default": "",
              "flags": [
                "--proof-strategy"
              ],
              "help": "How slice proofs aggregate into lane proof.",
              "name": "proof_strategy"
            },
            {
              "default": "",
              "flags": [
                "--bind-execplan"
              ],
              "help": "Existing execplan owner to bind atomically as a child of the created or reused lane.",
              "name": "bind_execplan"
            },
            {
              "default": "",
              "flags": [
                "--source-ref"
              ],
              "help": "External parent identity recorded on a newly created lane for deterministic reuse.",
              "name": "source_ref"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "arguments": [
            {
              "help": "Decomposition candidate lane id to promote.",
              "name": "lane"
            }
          ],
          "help": "Promote a decomposition candidate lane into a first-class lane record.",
          "name": "lane-promote",
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--alternate-lane-id"
              ],
              "help": "Use this lane record id when the default owner surface is already owned by incompatible provenance.",
              "name": "alternate_lane_id"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "arguments": [
            {
              "help": "Lane id to activate.",
              "name": "lane"
            }
          ],
          "help": "Mark a lane record active and optionally select its current slice.",
          "name": "lane-activate",
          "options": [
            {
              "default": "",
              "flags": [
                "--current-slice"
              ],
              "help": "Optional lane slice id to mark active.",
              "name": "current_slice"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "arguments": [
            {
              "help": "Lane id to close.",
              "name": "lane"
            }
          ],
          "help": "Record lane proof aggregation, residual work, and parent contribution.",
          "name": "lane-close",
          "options": [
            {
              "default": "",
              "flags": [
                "--proof"
              ],
              "help": "Lane-level proof evidence to aggregate.",
              "name": "proof"
            },
            {
              "default": "",
              "flags": [
                "--residual-work"
              ],
              "help": "Residual lane work or known proof gap.",
              "name": "residual_work"
            },
            {
              "default": "",
              "flags": [
                "--parent-contribution"
              ],
              "help": "How this lane advances the parent epic.",
              "name": "parent_contribution"
            },
            {
              "choices": [
                "do-not-close-parent",
                "may-advance-parent",
                "may-close-parent-after-human-confirmation",
                "may-close-parent"
              ],
              "default": "may-advance-parent",
              "flags": [
                "--parent-close-permission"
              ],
              "help": "Whether this lane permits parent advancement or closure.",
              "name": "parent_close_permission"
            },
            {
              "default": "",
              "flags": [
                "--next-owner"
              ],
              "help": "Owner for residual lane or parent work.",
              "name": "next_owner"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "arguments": [
            {
              "help": "Closed lane id to archive.",
              "name": "lane"
            }
          ],
          "help": "Archive a closed lane record and remove its live state projection.",
          "name": "lane-archive",
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
              "action": "store_true",
              "flags": [
                "--compact-retained"
              ],
              "help": "Replace retained full evidence with a compact receipt after reversible export; use --plan all-archived for incremental batch migration.",
              "name": "compact_retained"
            },
            {
              "flags": [
                "--export-dir"
              ],
              "help": "Export directory outside checked-in Planning state.",
              "name": "export_dir"
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
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
                "--proof-file"
              ],
              "help": "Read closeout proof text from a repo-contained file instead of a shell-sensitive argument.",
              "name": "proof_file"
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
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
              "default": "",
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Optimistic Planning revision id from a read surface; stop if Planning changed before mutation.",
              "name": "expect_planning_revision"
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
          "help": "Create a host architecture decision record scaffold through the configured or discovered decision target.",
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
              "flags": [
                "--scope"
              ],
              "help": "Current handoff scope used by proof-route transition gates.",
              "name": "scope"
            },
            {
              "flags": [
                "--changed-surfaces"
              ],
              "help": "Changed surfaces used to scope proof-route transition gates.",
              "name": "changed_surfaces"
            },
            {
              "flags": [
                "--current-work-id"
              ],
              "help": "Current work identity used to scope proof-route transition gates.",
              "name": "current_work_id"
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
              "flags": [
                "--audit-cursor"
              ],
              "help": "Opaque cursor returned by a previous audit page.",
              "name": "audit_cursor"
            },
            {
              "default": 25,
              "flags": [
                "--audit-page-size"
              ],
              "help": "Maximum closeout records to load for this audit page.",
              "name": "audit_page_size",
              "type": "integer"
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
          "help": "Preview or apply bounded Planning reconciliation transactions.",
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
            },
            {
              "flags": [
                "--lane"
              ],
              "help": "Lane id whose machine-readable child outcomes should be reconciled.",
              "name": "lane"
            },
            {
              "action": "store_true",
              "flags": [
                "--apply-lane-reconcile"
              ],
              "help": "Apply the reported child-outcome delta without closing the parent lane.",
              "name": "apply_lane_reconcile"
            },
            {
              "action": "store_true",
              "flags": [
                "--apply-lane-current-slice-reconcile"
              ],
              "help": "Apply one owner-specific current-slice lane reconciliation transaction.",
              "name": "apply_lane_current_slice_reconcile"
            },
            {
              "flags": [
                "--owner-surface"
              ],
              "help": "Repo-relative owner surface guarded by current-slice reconciliation.",
              "name": "owner_surface"
            },
            {
              "flags": [
                "--relation-identity"
              ],
              "help": "Expected lane current-slice relation identity.",
              "name": "relation_identity"
            },
            {
              "flags": [
                "--subject"
              ],
              "help": "Expected current-slice subject id.",
              "name": "subject"
            },
            {
              "flags": [
                "--expect-lane-revision"
              ],
              "help": "Current lane-record revision required before applying current-slice reconciliation.",
              "name": "expected_lane_revision"
            },
            {
              "choices": [
                "restore",
                "relink",
                "supersede",
                "cancel",
                "human"
              ],
              "flags": [
                "--transition"
              ],
              "help": "Requested current-slice reconciliation transition.",
              "name": "transition"
            },
            {
              "flags": [
                "--expected-execplan"
              ],
              "help": "Repo-relative execplan source: required for relink/supersede, optional for restore, and not used by cancel/human.",
              "name": "expected_execplan"
            },
            {
              "flags": [
                "--issue"
              ],
              "help": "Issue or external reference whose issue-relation record should be reconciled.",
              "name": "issue"
            },
            {
              "flags": [
                "--external-ref"
              ],
              "help": "External reference whose issue-relation record should be reconciled.",
              "name": "external_ref"
            },
            {
              "flags": [
                "--priority"
              ],
              "help": "Resolved issue-relation priority.",
              "name": "priority"
            },
            {
              "flags": [
                "--depends-on"
              ],
              "help": "Comma-separated resolved issue-relation dependencies.",
              "name": "depends_on"
            },
            {
              "flags": [
                "--rationale"
              ],
              "help": "Resolved issue-relation rationale.",
              "name": "rationale"
            },
            {
              "flags": [
                "--maturity"
              ],
              "help": "Resolved issue-relation shaping maturity.",
              "name": "maturity"
            },
            {
              "flags": [
                "--expect-relation-revision"
              ],
              "help": "Current relation revision required by --apply-issue-relation-reconcile.",
              "name": "expect_relation_revision"
            },
            {
              "action": "store_true",
              "flags": [
                "--apply-issue-relation-reconcile"
              ],
              "help": "Apply one revision-guarded semantic issue-relation reconciliation.",
              "name": "apply_issue_relation_reconcile"
            },
            {
              "action": "store_true",
              "flags": [
                "--apply-issue-relation-migration"
              ],
              "help": "Migrate legacy issue authority into issue relations and demote duplicate fields.",
              "name": "apply_issue_relation_migration"
            },
            {
              "action": "store_true",
              "flags": [
                "--apply-pending-integrations"
              ],
              "help": "Apply all eligible pending integration proposals in one target-authority transaction.",
              "name": "apply_pending_integrations"
            },
            {
              "action": "store_true",
              "flags": [
                "--preview"
              ],
              "help": "Compile a reusable reconciliation proposal without mutating Planning state.",
              "name": "preview"
            },
            {
              "action": "store_true",
              "flags": [
                "--apply"
              ],
              "help": "Apply the exact reconciliation proposal guarded by --proposal and --expect-planning-revision.",
              "name": "apply"
            },
            {
              "flags": [
                "--proposal"
              ],
              "help": "Proposal id returned by --preview.",
              "name": "proposal"
            },
            {
              "flags": [
                "--expect-planning-revision"
              ],
              "help": "Planning revision returned by --preview and required by --apply.",
              "name": "expected_planning_revision"
            }
          ],
          "usage_error_hints": [
            {
              "message": "Supported route: agentic-workspace planning reconcile --help",
              "when_message_contains": [
                "unrecognized arguments"
              ]
            }
          ]
        }
      ],
      "subcommands_required": false
    },
    "name": "planning",
    "operation_ref": {
      "id": "planning.front-door",
      "path": "operations/planning.front-door.json"
    }
  },
  {
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
              "default": "",
              "flags": [
                "--task"
              ],
              "help": "Task text for route context. Task prose is not routing authority.",
              "name": "task"
            },
            {
              "choices": [
                "startup",
                "implement",
                "closeout",
                "report"
              ],
              "default": "",
              "flags": [
                "--stage"
              ],
              "help": "Structured workflow stage to use as an explicit routing surface.",
              "name": "stage"
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
          "usage_error_hints": [
            {
              "message": "Memory task tip: 'memory route' routes touched files or explicit surfaces. For task-shaped memory consultation, run 'agentic-workspace start --task \"<task>\" --select memory_consult --format json' or 'agentic-workspace report --section memory_consult --format json'.",
              "when_argv_contains": [
                "memory",
                "route"
              ],
              "when_message_contains": [
                "--task"
              ]
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
                "--task"
              ],
              "help": "Task text for capture context.",
              "name": "task"
            },
            {
              "choices": [
                "startup",
                "implement",
                "closeout",
                "report"
              ],
              "default": "",
              "flags": [
                "--stage"
              ],
              "help": "Structured workflow stage associated with the learning.",
              "name": "stage"
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
          "help": "Create a repo-shared or local-only Memory note.",
          "name": "create-note",
          "options": [
            {
              "default": "",
              "flags": [
                "--slug"
              ],
              "help": "Memory note slug to create.",
              "name": "slug"
            },
            {
              "flags": [
                "--title"
              ],
              "help": "Memory note title. Defaults to a title derived from the slug.",
              "name": "title"
            },
            {
              "default": "domains",
              "flags": [
                "--folder"
              ],
              "help": "Repo Memory folder under .agentic-workspace/memory/repo.",
              "name": "folder"
            },
            {
              "default": "domain",
              "flags": [
                "--note-type"
              ],
              "help": "Repo Memory note type recorded in the manifest.",
              "name": "note_type"
            },
            {
              "default": "",
              "flags": [
                "--summary"
              ],
              "help": "Short note summary.",
              "name": "summary"
            },
            {
              "action": "store_true",
              "flags": [
                "--local"
              ],
              "help": "Create an ignored local-only note under .agentic-workspace/local/memory without updating the repo manifest.",
              "name": "local"
            },
            {
              "default": "",
              "flags": [
                "--local-reason"
              ],
              "help": "Reason this note is machine-local rather than repo-shared.",
              "name": "local_reason"
            },
            {
              "default": [],
              "flags": [
                "--applies-to"
              ],
              "help": "Repo paths or surfaces this note applies to.",
              "name": "applies_to",
              "nargs": "*"
            },
            {
              "default": [],
              "flags": [
                "--use-when"
              ],
              "help": "Routing hints for when to use this note.",
              "name": "use_when",
              "nargs": "*"
            },
            {
              "default": [],
              "flags": [
                "--routes-from"
              ],
              "help": "Surfaces or files that should route to this note.",
              "name": "routes_from",
              "nargs": "*"
            },
            {
              "default": [],
              "flags": [
                "--stale-when"
              ],
              "help": "Conditions that make this note stale.",
              "name": "stale_when",
              "nargs": "*"
            },
            {
              "default": [],
              "flags": [
                "--evidence"
              ],
              "help": "Evidence references supporting this note.",
              "name": "evidence",
              "nargs": "*"
            },
            {
              "default": "",
              "flags": [
                "--memory-role"
              ],
              "help": "Memory role metadata.",
              "name": "memory_role"
            },
            {
              "default": "",
              "flags": [
                "--promotion-target"
              ],
              "help": "Optional durable promotion target.",
              "name": "promotion_target"
            },
            {
              "default": "",
              "flags": [
                "--promotion-trigger"
              ],
              "help": "Optional promotion trigger.",
              "name": "promotion_trigger"
            },
            {
              "default": "",
              "flags": [
                "--retention-after-promotion"
              ],
              "help": "Retention policy after promotion.",
              "name": "retention_after_promotion"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Show planned changes without writing files.",
              "name": "dry_run"
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
    "name": "memory",
    "operation_ref": {
      "id": "memory.front-door",
      "path": "operations/memory.front-door.json"
    }
  },
  {
    "interface": {
      "help": "Create or update ignored local chat continuity checkpoints.",
      "name": "checkpoint",
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
      ],
      "subcommand_dest": "checkpoint_command",
      "subcommands": [
        {
          "help": "Write or refresh .agentic-workspace/local/chat-checkpoint.json.",
          "name": "write",
          "operation_ref": {
            "id": "checkpoint.write",
            "path": "operations/checkpoint.write.json"
          },
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
                "--task"
              ],
              "help": "Short current task summary.",
              "name": "task"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--issue"
              ],
              "help": "Current issue reference, such as #1680. May be repeated.",
              "name": "issue"
            },
            {
              "flags": [
                "--pr"
              ],
              "help": "Current pull request number or URL.",
              "name": "pr"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--durable-source"
              ],
              "help": "Durable source to reread on resume. May be repeated.",
              "name": "durable_source"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--last-proof"
              ],
              "help": "Proof command or receipt summary. May be repeated.",
              "name": "last_proof"
            },
            {
              "flags": [
                "--next-safe-command"
              ],
              "help": "Next safe command to run after resume.",
              "name": "next_safe_command"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--open-blocker"
              ],
              "help": "Short blocker summary. May be repeated.",
              "name": "open_blocker"
            },
            {
              "flags": [
                "--dirty-state-summary"
              ],
              "help": "Short local dirty-state summary.",
              "name": "dirty_state_summary"
            },
            {
              "action": "store_true",
              "flags": [
                "--replace"
              ],
              "help": "Replace mergeable list values instead of preserving existing checkpoint values.",
              "name": "replace"
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
      "subcommands_required": true
    },
    "name": "checkpoint",
    "operation_ref": {
      "id": "checkpoint.write",
      "path": "operations/checkpoint.write.json"
    }
  },
  {
    "interface": {
      "help": "Manage local-first workspace evaluations.",
      "name": "evaluation",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Repository path.",
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
      "subcommand_dest": "evaluation_command",
      "subcommands": [
        {
          "help": "Register or update one evaluation definition.",
          "name": "register",
          "operation_ref": {
            "id": "evaluation.register",
            "path": "operations/evaluation.register.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "flags": [
                "--question"
              ],
              "name": "question",
              "required": true
            },
            {
              "default": "{\"type\":\"workspace-task\"}",
              "flags": [
                "--subject"
              ],
              "name": "subject"
            },
            {
              "flags": [
                "--criteria"
              ],
              "help": "JSON object keyed by criterion id.",
              "name": "criteria",
              "required": true
            },
            {
              "flags": [
                "--decision-owner"
              ],
              "help": "JSON object with id and class.",
              "name": "decision_owner",
              "required": true
            },
            {
              "flags": [
                "--evidence-sources"
              ],
              "help": "Comma-separated evidence source ids.",
              "name": "evidence_sources",
              "required": true
            },
            {
              "flags": [
                "--report-sinks"
              ],
              "help": "Comma-separated report sink ids.",
              "name": "report_sinks",
              "required": true
            },
            {
              "default": "{}",
              "flags": [
                "--selectors"
              ],
              "name": "selectors"
            },
            {
              "default": "{}",
              "flags": [
                "--collection-policy"
              ],
              "name": "collection_policy"
            },
            {
              "default": "{}",
              "flags": [
                "--conclusion-policy"
              ],
              "name": "conclusion_policy"
            },
            {
              "default": "{}",
              "flags": [
                "--action-policy"
              ],
              "name": "action_policy"
            }
          ]
        },
        {
          "help": "Append one local observation.",
          "name": "observe",
          "operation_ref": {
            "id": "evaluation.observe",
            "path": "operations/evaluation.observe.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "flags": [
                "--criterion"
              ],
              "name": "criterion",
              "required": true
            },
            {
              "choices": [
                "supports",
                "contradicts",
                "mixed",
                "not-applicable",
                "unknown"
              ],
              "flags": [
                "--result"
              ],
              "name": "result",
              "required": true
            },
            {
              "default": "",
              "flags": [
                "--evidence-refs"
              ],
              "name": "evidence_refs"
            },
            {
              "choices": [
                "low",
                "medium",
                "high"
              ],
              "default": "medium",
              "flags": [
                "--confidence"
              ],
              "name": "confidence"
            },
            {
              "choices": [
                "low",
                "medium",
                "high"
              ],
              "default": "medium",
              "flags": [
                "--burden"
              ],
              "name": "burden"
            },
            {
              "default": "{}",
              "flags": [
                "--context"
              ],
              "name": "context"
            },
            {
              "default": "",
              "flags": [
                "--finding"
              ],
              "name": "finding"
            },
            {
              "default": "",
              "flags": [
                "--recommended-action"
              ],
              "name": "recommended_action"
            }
          ]
        },
        {
          "help": "Inspect derived evaluation status.",
          "name": "status",
          "operation_ref": {
            "id": "evaluation.status",
            "path": "operations/evaluation.status.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id"
            },
            {
              "flags": [
                "--select"
              ],
              "help": "Expand one or more comma-separated evaluation status detail fields, or full.",
              "name": "select"
            }
          ]
        },
        {
          "help": "Refresh observation authority from a live public assignment or explicit active Planning owner and proof state.",
          "name": "authority-refresh",
          "operation_ref": {
            "id": "evaluation.authority-refresh",
            "path": "operations/evaluation.authority-refresh.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "action": "store_true",
              "flags": [
                "--active-planning-owner"
              ],
              "help": "Use the explicitly selected active Planning owner when no current delegated assignment exists.",
              "name": "active_planning_owner"
            }
          ]
        },
        {
          "help": "Compile the current evaluation report authority without claiming external delivery.",
          "name": "report-preview",
          "operation_ref": {
            "id": "evaluation.report-preview",
            "path": "operations/evaluation.report-preview.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "action": "store_true",
              "default": false,
              "flags": [
                "--explicit"
              ],
              "name": "explicit"
            }
          ]
        },
        {
          "help": "Record a local report compilation receipt without claiming external sink delivery.",
          "name": "local-delivery",
          "operation_ref": {
            "id": "evaluation.local-delivery",
            "path": "operations/evaluation.local-delivery.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "action": "store_true",
              "default": false,
              "flags": [
                "--explicit"
              ],
              "name": "explicit"
            }
          ]
        },
        {
          "help": "Create the current per-sink external delivery request.",
          "name": "external-request",
          "operation_ref": {
            "id": "evaluation.external-request",
            "path": "operations/evaluation.external-request.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "action": "store_true",
              "default": false,
              "flags": [
                "--explicit"
              ],
              "name": "explicit"
            }
          ]
        },
        {
          "help": "Import a provider-owned external adapter host result by opaque reference.",
          "name": "external-host-result-import",
          "operation_ref": {
            "id": "evaluation.external-host-result-import",
            "path": "operations/evaluation.external-host-result-import.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--provider-result-ref"
              ],
              "name": "provider_result_ref",
              "required": true
            },
            {
              "default": "",
              "flags": [
                "--expected-result-digest"
              ],
              "name": "expected_result_digest"
            },
            {
              "default": "",
              "flags": [
                "--capability-revision"
              ],
              "name": "capability_revision"
            }
          ]
        },
        {
          "help": "Record a producer-owned external adapter attempt/result receipt.",
          "name": "external-adapter-receipt",
          "operation_ref": {
            "id": "evaluation.external-adapter-receipt",
            "path": "operations/evaluation.external-adapter-receipt.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--delivery-id"
              ],
              "name": "delivery_id",
              "required": true
            },
            {
              "flags": [
                "--sink-id"
              ],
              "name": "sink_id",
              "required": true
            },
            {
              "flags": [
                "--producer"
              ],
              "name": "producer",
              "required": true
            },
            {
              "flags": [
                "--attempt-revision"
              ],
              "name": "attempt_revision",
              "required": true
            },
            {
              "flags": [
                "--receipt-revision"
              ],
              "name": "receipt_revision",
              "required": true
            },
            {
              "flags": [
                "--capability-revision"
              ],
              "name": "capability_revision",
              "required": true
            },
            {
              "choices": [
                "current",
                "fresh",
                "accepted"
              ],
              "default": "current",
              "flags": [
                "--capability-status"
              ],
              "name": "capability_status"
            },
            {
              "choices": [
                "provider-adapter",
                "external-operation-adapter"
              ],
              "default": "provider-adapter",
              "flags": [
                "--status-owner"
              ],
              "name": "status_owner"
            },
            {
              "choices": [
                "delivered",
                "failed"
              ],
              "flags": [
                "--status"
              ],
              "name": "status",
              "required": true
            },
            {
              "default": "",
              "flags": [
                "--detail"
              ],
              "name": "detail"
            },
            {
              "default": "",
              "flags": [
                "--supersedes"
              ],
              "name": "supersedes"
            },
            {
              "flags": [
                "--host-result-ref"
              ],
              "name": "host_result_ref",
              "required": true
            }
          ]
        },
        {
          "help": "Admit one external delivery result from a current producer-owned adapter receipt.",
          "name": "external-delivery",
          "operation_ref": {
            "id": "evaluation.external-delivery",
            "path": "operations/evaluation.external-delivery.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "flags": [
                "--adapter-receipt-ref"
              ],
              "name": "adapter_receipt_ref",
              "required": true
            },
            {
              "action": "store_true",
              "default": false,
              "flags": [
                "--explicit"
              ],
              "name": "explicit"
            }
          ]
        },
        {
          "help": "Project per-sink report delivery status from admitted receipts.",
          "name": "delivery-status",
          "operation_ref": {
            "id": "evaluation.delivery-status",
            "path": "operations/evaluation.delivery-status.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "action": "store_true",
              "default": false,
              "flags": [
                "--explicit"
              ],
              "name": "explicit"
            }
          ]
        },
        {
          "help": "Return the current retryable external delivery request for pending or failed sinks.",
          "name": "retry",
          "operation_ref": {
            "id": "evaluation.retry",
            "path": "operations/evaluation.retry.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "default": "",
              "flags": [
                "--sink-id"
              ],
              "name": "sink_id"
            }
          ]
        },
        {
          "help": "Move an evaluation through a validated lifecycle transition.",
          "name": "transition",
          "operation_ref": {
            "id": "evaluation.transition",
            "path": "operations/evaluation.transition.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "choices": [
                "collecting",
                "enough-signal",
                "satisfied",
                "contradicted",
                "inconclusive",
                "paused",
                "superseded",
                "archived"
              ],
              "flags": [
                "--lifecycle"
              ],
              "name": "lifecycle",
              "required": true
            },
            {
              "default": "",
              "flags": [
                "--reason"
              ],
              "name": "reason"
            },
            {
              "default": 0,
              "flags": [
                "--expected-revision"
              ],
              "name": "expected_revision",
              "type": "integer"
            }
          ]
        },
        {
          "help": "Prune or compact local evaluation observation history.",
          "name": "prune",
          "operation_ref": {
            "id": "evaluation.prune",
            "path": "operations/evaluation.prune.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Repository path.",
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
                "--evaluation-id"
              ],
              "name": "evaluation_id",
              "required": true
            },
            {
              "action": "store_true",
              "default": false,
              "flags": [
                "--dry-run"
              ],
              "name": "dry_run"
            }
          ]
        }
      ],
      "subcommands_required": true
    },
    "name": "evaluation",
    "operation_ref": {
      "id": "evaluation.register",
      "path": "operations/evaluation.register.json"
    }
  },
  {
    "interface": {
      "help": "Admit model-authored final responses at the host boundary.",
      "name": "final-response",
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
      ],
      "subcommand_dest": "final_response_command",
      "subcommands": [
        {
          "help": "Admit or reject a model-authored final response attempt.",
          "name": "admit",
          "operation_ref": {
            "id": "final-response.admit",
            "path": "operations/final-response.admit.json"
          },
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
                "--task"
              ],
              "help": "Exact direct-work task identity used to reconcile bounded closeout proof.",
              "name": "task"
            },
            {
              "action": "extend",
              "default": [],
              "flags": [
                "--changed"
              ],
              "help": "Repo-relative direct-work paths whose selected proof receipts must reconcile before bounded admission.",
              "name": "changed",
              "nargs": "*"
            },
            {
              "flags": [
                "--residue"
              ],
              "help": "Structured direct-work residue kind: docs, issue, memory, planning, or review.",
              "name": "residue"
            },
            {
              "flags": [
                "--residue-owner"
              ],
              "help": "Structured continuation owner for the still-open larger intent.",
              "name": "residue_owner"
            },
            {
              "default": "",
              "flags": [
                "--attempt"
              ],
              "help": "The model-authored final response text submitted for host admission.",
              "name": "attempt"
            },
            {
              "default": "",
              "flags": [
                "--attempt-file"
              ],
              "help": "Path to a file containing the model-authored final response text submitted for host admission.",
              "name": "attempt_file"
            },
            {
              "default": "",
              "flags": [
                "--executor-command"
              ],
              "help": "Vendor-neutral command that emits the next model-authored final response attempt on stdout; rejected CONTINUE attempts re-enter the command with custody metadata.",
              "name": "executor_command"
            },
            {
              "default": "model-authored-final-response",
              "flags": [
                "--source"
              ],
              "help": "Source label for the final response attempt.",
              "name": "source"
            },
            {
              "choices": [
                "terminal-final",
                "partial-progress",
                "slice-complete"
              ],
              "default": "terminal-final",
              "flags": [
                "--claim-class"
              ],
              "help": "Claim class for admission; bounded classes require matching closeout authorization and never imply parent, lane, or full-intent completion.",
              "name": "claim_class"
            },
            {
              "default": "",
              "flags": [
                "--claim-scope-id"
              ],
              "help": "Closeout-derived bounded claim-scope identity; required for partial-progress or slice-complete admission.",
              "name": "claim_scope_id"
            },
            {
              "action": "store_true",
              "flags": [
                "--after-compaction"
              ],
              "help": "Mark that the attempt happened after a compaction or resume boundary.",
              "name": "after_compaction"
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
      "subcommands_required": true
    },
    "name": "final-response",
    "operation_ref": {
      "id": "final-response.admit",
      "path": "operations/final-response.admit.json"
    }
  },
  {
    "interface": {
      "help": "Run the ordinary AW executor loop through final-response admission.",
      "name": "autopilot",
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
            "--executor-command"
          ],
          "help": "Vendor-neutral command that emits the next model-authored final response attempt on stdout; rejected CONTINUE attempts re-enter the command with custody metadata.",
          "name": "executor_command",
          "required": true
        },
        {
          "default": "autopilot-executor-stdout",
          "flags": [
            "--source"
          ],
          "help": "Source label for the executor final response attempt.",
          "name": "source"
        },
        {
          "action": "store_true",
          "flags": [
            "--after-compaction"
          ],
          "help": "Mark that the first attempt happened after a compaction or resume boundary.",
          "name": "after_compaction"
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
    "name": "autopilot",
    "operation_ref": {
      "id": "autopilot.run",
      "path": "operations/autopilot.run.json"
    }
  },
  {
    "interface": {
      "help": "Manage ignored local work-thread continuation handles.",
      "name": "work-thread",
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
      ],
      "subcommand_dest": "work_thread_command",
      "subcommands": [
        {
          "help": "Select an ignored local work-thread continuation handle.",
          "name": "select",
          "operation_ref": {
            "id": "work-thread.select",
            "path": "operations/work-thread.select.json"
          },
          "options": [
            {
              "flags": [
                "--thread-id"
              ],
              "help": "Local work-thread id to select.",
              "name": "thread_id"
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
          "help": "Inspect decision-point intent carries by exact current-work ownership.",
          "name": "carry-inspect",
          "operation_ref": {
            "id": "work-thread.carry-inspect",
            "path": "operations/work-thread.carry-inspect.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "default": "",
              "flags": [
                "--key"
              ],
              "help": "Optional exact carry key to inspect.",
              "name": "key"
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
          "help": "Select one exact decision-point carry for closeout or stale recovery.",
          "name": "carry-select",
          "operation_ref": {
            "id": "work-thread.carry-select",
            "path": "operations/work-thread.carry-select.json"
          },
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
                "--key"
              ],
              "help": "Exact active carry key to select.",
              "name": "key",
              "required": true
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
          "help": "Mark one exactly selected stale decision-point carry without archiving its owner.",
          "name": "carry-prune",
          "operation_ref": {
            "id": "work-thread.carry-prune",
            "path": "operations/work-thread.carry-prune.json"
          },
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
                "--key"
              ],
              "help": "Exact selected carry key to mark stale.",
              "name": "key",
              "required": true
            },
            {
              "flags": [
                "--expect-context-id"
              ],
              "help": "Optimistic current-work context id returned by carry-select.",
              "name": "expect_context_id",
              "required": true
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Concrete evidence that the selected carry is stale.",
              "name": "reason",
              "required": true
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the exact mutation without changing the carry.",
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
          "help": "Prune ignored local work-thread records already classified as safe candidates.",
          "name": "prune",
          "operation_ref": {
            "id": "work-thread.prune",
            "path": "operations/work-thread.prune.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Optional repository path.",
              "name": "target"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--thread-id"
              ],
              "help": "Local work-thread id to prune. May be repeated.",
              "name": "thread_id"
            },
            {
              "action": "store_true",
              "flags": [
                "--all-candidates"
              ],
              "help": "Prune all current safe local work-thread candidates.",
              "name": "all_candidates"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report candidates without deleting local files.",
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
        }
      ],
      "subcommands_required": true
    },
    "name": "work-thread",
    "operation_ref": {
      "id": "work-thread.prune",
      "path": "operations/work-thread.prune.json"
    }
  },
  {
    "interface": {
      "help": "Inspect or annotate ignored local AW session logs.",
      "name": "session-log",
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
      ],
      "subcommand_dest": "session_log_command",
      "subcommands": [
        {
          "help": "Report local AW session logging status.",
          "name": "status",
          "operation_ref": {
            "id": "session-log.manage",
            "path": "operations/session-log.manage.json"
          },
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
          "help": "Start a new ignored local AW session log.",
          "name": "new-session",
          "operation_ref": {
            "id": "session-log.manage",
            "path": "operations/session-log.manage.json"
          },
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
          "help": "Append an optional note to the current ignored local AW session log.",
          "name": "note",
          "operation_ref": {
            "id": "session-log.manage",
            "path": "operations/session-log.manage.json"
          },
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
                "--text"
              ],
              "help": "Note text to append.",
              "name": "text",
              "required": true
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
          "help": "Capture compact workaround or opportunity evidence for the existing improvement intake.",
          "name": "signal",
          "operation_ref": {
            "id": "session-log.manage",
            "path": "operations/session-log.manage.json"
          },
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
                "workaround",
                "opportunity"
              ],
              "default": "workaround",
              "flags": [
                "--kind"
              ],
              "help": "Observation class.",
              "name": "kind"
            },
            {
              "flags": [
                "--symptom"
              ],
              "help": "Observed workaround, friction, or concrete opportunity.",
              "name": "symptom",
              "required": true
            },
            {
              "flags": [
                "--cost"
              ],
              "help": "Concrete current or future repository cost.",
              "name": "cost",
              "required": true
            },
            {
              "flags": [
                "--expected-benefit"
              ],
              "help": "Expected future-cost or operability benefit; required for opportunities.",
              "name": "expected_benefit"
            },
            {
              "choices": [
                "agent_observed",
                "machine_observed",
                "human_confirmed",
                "review_derived"
              ],
              "default": "agent_observed",
              "flags": [
                "--evidence-class"
              ],
              "help": "Evidence provenance class.",
              "name": "evidence_class"
            },
            {
              "default": "unknown",
              "flags": [
                "--owner-hint"
              ],
              "help": "Suspected repository or AW owner.",
              "name": "owner_hint"
            },
            {
              "choices": [
                "current-scope",
                "adjacent-scope",
                "standalone-repo",
                "aw-internal"
              ],
              "default": "current-scope",
              "flags": [
                "--scope-relation"
              ],
              "help": "Relation to the current task scope.",
              "name": "scope_relation"
            },
            {
              "choices": [
                "first_seen",
                "repeated",
                "human_confirmed"
              ],
              "default": "first_seen",
              "flags": [
                "--recurrence"
              ],
              "help": "Observed recurrence state.",
              "name": "recurrence"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--evidence-ref"
              ],
              "help": "Compact evidence reference; repeat for multiple references.",
              "name": "evidence_ref"
            },
            {
              "default": "unknown",
              "flags": [
                "--likely-remediation"
              ],
              "help": "Likely existing remediation class.",
              "name": "likely_remediation"
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
          "help": "Analyze an ignored local AW session log into counts, repeated commands, failures, artifacts, packet kinds, and friction candidates.",
          "name": "analyze",
          "operation_ref": {
            "id": "session-log.manage",
            "path": "operations/session-log.manage.json"
          },
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
                "--path"
              ],
              "help": "Optional repo-relative session log path; defaults to the current session pointer.",
              "name": "path"
            },
            {
              "flags": [
                "--id"
              ],
              "help": "Optional session id or aw-session-<id> directory name to analyze.",
              "name": "id"
            },
            {
              "flags": [
                "--segment"
              ],
              "help": "Optional segment id to analyze; the response still lists all discovered segments.",
              "name": "segment"
            },
            {
              "choices": [
                "agent",
                "all",
                "test",
                "synthetic",
                "unknown"
              ],
              "default": "agent",
              "flags": [
                "--origin"
              ],
              "help": "Origin scope for operational conclusions; defaults to live agent traffic.",
              "name": "origin"
            },
            {
              "choices": [
                "summary",
                "entries",
                "segments",
                "episodes",
                "contexts",
                "candidates"
              ],
              "default": "summary",
              "flags": [
                "--detail"
              ],
              "help": "Select one pageable detail collection; defaults to the bounded summary.",
              "name": "detail"
            },
            {
              "default": 1,
              "flags": [
                "--page"
              ],
              "help": "One-based detail page number.",
              "name": "page",
              "type": "integer"
            },
            {
              "default": 25,
              "flags": [
                "--page-size"
              ],
              "help": "Detail page size, capped at 100.",
              "name": "page_size",
              "type": "integer"
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
          "help": "Repair or backfill a partial local session-log index from its Markdown entries.",
          "name": "repair",
          "operation_ref": {
            "id": "session-log.manage",
            "path": "operations/session-log.manage.json"
          },
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
                "--path"
              ],
              "help": "Optional repo-relative session log path; defaults to the current session pointer.",
              "name": "path"
            },
            {
              "flags": [
                "--id"
              ],
              "help": "Optional session id or aw-session-<id> directory name to repair.",
              "name": "id"
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
          "help": "Create the explicit share-safe session-log export with known local paths normalized; raw local logs remain distinct.",
          "name": "export",
          "operation_ref": {
            "id": "session-log.manage",
            "path": "operations/session-log.manage.json"
          },
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
                "--path"
              ],
              "help": "Optional repo-relative session log path; defaults to the current session pointer.",
              "name": "path"
            },
            {
              "flags": [
                "--id"
              ],
              "help": "Optional session id or aw-session-<id> directory name to export.",
              "name": "id"
            },
            {
              "action": "store_true",
              "flags": [
                "--no-artifacts"
              ],
              "help": "Exclude raw-output artifacts from the exported bundle.",
              "name": "no_artifacts"
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
    "name": "session-log",
    "operation_ref": {
      "id": "session-log.manage",
      "path": "operations/session-log.manage.json"
    }
  },
  {
    "interface": {
      "help": "Return the minimum safe startup context for beginning work in a target repository.",
      "name": "start",
      "options": [
        {
          "flags": [
            "--request"
          ],
          "help": "Complete returned public request JSON. Discover semantic route requests with --select semantic_route_result; edit only the declared arguments.",
          "name": "request"
        },
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
    "name": "start",
    "operation_ref": {
      "id": "start.context",
      "path": "operations/start.context.json"
    }
  },
  {
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
            "--startup-route-fingerprint"
          ],
          "help": "Optional fingerprint emitted by start; stale identities are rebound before implement commits carry.",
          "name": "startup_route_fingerprint"
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
    "name": "implement",
    "operation_ref": {
      "id": "implement.context",
      "path": "operations/implement.context.json"
    }
  },
  {
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
    "name": "defaults",
    "operation_ref": {
      "id": "defaults.report",
      "path": "operations/defaults.report.json"
    }
  },
  {
    "interface": {
      "help": "Submit an external proof candidate by opaque signed host-result reference.",
      "name": "external-evidence-submit",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Repository path.",
          "name": "target"
        },
        {
          "flags": [
            "--candidate-json"
          ],
          "help": "Provider-neutral external evidence candidate JSON.",
          "name": "candidate_json",
          "required": true
        },
        {
          "flags": [
            "--host-result-ref"
          ],
          "help": "Opaque package-trusted host result reference.",
          "name": "host_result_ref",
          "required": true
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
    "name": "external-evidence-submit",
    "operation_ref": {
      "id": "external-evidence.submit",
      "path": "operations/external-evidence.submit.json"
    }
  },
  {
    "interface": {
      "help": "Query and revalidate one admitted external proof result.",
      "name": "external-evidence-query",
      "options": [
        {
          "flags": [
            "--target"
          ],
          "help": "Repository path.",
          "name": "target"
        },
        {
          "flags": [
            "--candidate-json"
          ],
          "help": "Provider-neutral external evidence candidate JSON.",
          "name": "candidate_json",
          "required": true
        },
        {
          "flags": [
            "--host-result-ref"
          ],
          "help": "Opaque package-trusted host result reference.",
          "name": "host_result_ref",
          "required": true
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
    "name": "external-evidence-query",
    "operation_ref": {
      "id": "external-evidence.query",
      "path": "operations/external-evidence.query.json"
    }
  },
  {
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
            "--task"
          ],
          "help": "Optional task description used to keep changed-path proof selection aligned with the active task context.",
          "name": "task"
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
          "action": "store_true",
          "flags": [
            "--execute-selected"
          ],
          "help": "Execute and reconcile the currently selected changed-path proof set as one resumable operation.",
          "name": "execute_selected"
        },
        {
          "default": "",
          "flags": [
            "--proof-run-id"
          ],
          "help": "Optional existing proof run identity to resume; stale subject identities fail closed.",
          "name": "proof_run_id"
        },
        {
          "default": "600",
          "flags": [
            "--proof-timeout-seconds"
          ],
          "help": "Per-command timeout budget for selected proof execution.",
          "name": "proof_timeout_seconds"
        },
        {
          "default": "",
          "flags": [
            "--proof-cancel-file"
          ],
          "help": "Optional cancellation sentinel checked before each selected proof command.",
          "name": "proof_cancel_file"
        },
        {
          "action": "store_true",
          "flags": [
            "--record-receipt"
          ],
          "help": "Record a compact proof receipt from an actually run validation command.",
          "name": "record_receipt"
        },
        {
          "default": "",
          "flags": [
            "--receipt-command"
          ],
          "help": "Validation command or evidence to store in the proof receipt.",
          "name": "receipt_command"
        },
        {
          "default": "",
          "flags": [
            "--receipt-result"
          ],
          "help": "Validation result to store in the proof receipt, such as passed or failed.",
          "name": "receipt_result"
        },
        {
          "default": "",
          "flags": [
            "--receipt-plan"
          ],
          "help": "Optional planning id that the proof receipt applies to.",
          "name": "receipt_plan"
        },
        {
          "default": "",
          "flags": [
            "--receipt-log"
          ],
          "help": "Optional repo-local log path or short excerpt used to attach a compact failed-proof summary.",
          "name": "receipt_log"
        },
        {
          "default": "",
          "flags": [
            "--receipt-route-id"
          ],
          "help": "Structured proof route identity for the executed receipt.",
          "name": "receipt_route_id"
        },
        {
          "default": "",
          "flags": [
            "--receipt-command-id"
          ],
          "help": "Structured command identity for the executed receipt.",
          "name": "receipt_command_id"
        },
        {
          "default": "",
          "flags": [
            "--receipt-duration-seconds"
          ],
          "help": "Seconds-normalized execution duration for the receipt.",
          "name": "receipt_duration_seconds"
        },
        {
          "action": "store_true",
          "flags": [
            "--receipt-timeout"
          ],
          "help": "Record that the validation execution timed out.",
          "name": "receipt_timeout"
        },
        {
          "default": "",
          "flags": [
            "--receipt-exit-state"
          ],
          "help": "Structured exit state for the validation execution.",
          "name": "receipt_exit_state"
        },
        {
          "default": "",
          "flags": [
            "--receipt-environment"
          ],
          "help": "JSON object describing the execution environment or resource posture.",
          "name": "receipt_environment"
        },
        {
          "default": "",
          "flags": [
            "--receipt-claim-sufficiency"
          ],
          "help": "Independent claim sufficiency review: sufficient, insufficient, or not-reviewed.",
          "name": "receipt_claim_sufficiency"
        },
        {
          "default": "",
          "flags": [
            "--receipt-route-budget-seconds"
          ],
          "help": "Route-specific duration budget in seconds, when declared by route authority.",
          "name": "receipt_route_budget_seconds"
        },
        {
          "default": "",
          "flags": [
            "--receipt-repair-finding-id"
          ],
          "help": "Stable proof-route finding id retired by this validation receipt.",
          "name": "receipt_repair_finding_id"
        },
        {
          "default": "",
          "flags": [
            "--receipt-repair-authority-revision"
          ],
          "help": "Verified proof-route authority revision after applying the repair.",
          "name": "receipt_repair_authority_revision"
        },
        {
          "default": "",
          "flags": [
            "--receipt-repair-disposition"
          ],
          "help": "Disposition for the repaired proof-route finding.",
          "name": "receipt_repair_disposition"
        },
        {
          "default": "",
          "flags": [
            "--receipt-repair-idempotency-key"
          ],
          "help": "Idempotency key from the proof-route repair operation.",
          "name": "receipt_repair_idempotency_key"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-mode"
          ],
          "help": "Preview or apply a guarded proof-route authority repair.",
          "name": "route_repair_mode"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-finding-id"
          ],
          "help": "Stable proof-route finding id being repaired.",
          "name": "route_repair_finding_id"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-authority-path"
          ],
          "help": "Single repo-relative authority path to update.",
          "name": "route_repair_authority_path"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-field-selector"
          ],
          "help": "Single authority field selector scoped by the repair.",
          "name": "route_repair_field_selector"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-expected-revision"
          ],
          "help": "Expected proof-route authority revision before apply.",
          "name": "route_repair_expected_revision"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-delta-json"
          ],
          "help": "Machine-readable field-scoped repair delta JSON.",
          "name": "route_repair_delta_json"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-disposition"
          ],
          "help": "Disposition to associate with the repaired finding.",
          "name": "route_repair_disposition"
        },
        {
          "default": "",
          "flags": [
            "--route-repair-idempotency-key"
          ],
          "help": "Idempotency key for the guarded proof-route repair apply.",
          "name": "route_repair_idempotency_key"
        },
        {
          "action": "store_true",
          "flags": [
            "--dry-run"
          ],
          "help": "Show the receipt payload without writing it.",
          "name": "dry_run"
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
    "name": "proof",
    "operation_ref": {
      "id": "proof.report",
      "path": "operations/proof.report.json"
    }
  },
  {
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
    "name": "setup",
    "operation_ref": {
      "id": "setup.guidance",
      "path": "operations/setup.guidance.json"
    }
  },
  {
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
    "name": "ownership",
    "operation_ref": {
      "id": "ownership.report",
      "path": "operations/ownership.report.json"
    }
  },
  {
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
          "flags": [
            "--scope"
          ],
          "help": "Current handoff scope used by proof-route transition gates.",
          "name": "scope"
        },
        {
          "flags": [
            "--changed-surfaces"
          ],
          "help": "Changed surfaces used to scope proof-route transition gates.",
          "name": "changed_surfaces"
        },
        {
          "flags": [
            "--current-work-id"
          ],
          "help": "Current work identity used to scope proof-route transition gates.",
          "name": "current_work_id"
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
    "name": "config",
    "operation_ref": {
      "id": "config.report",
      "path": "operations/config.report.json"
    }
  },
  {
    "interface": {
      "help": "Apply one structured shared or local workspace policy decision without replacing unrelated configuration.",
      "name": "config-policy",
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
          "help": "Optional repository path containing the owned config surface.",
          "name": "target"
        },
        {
          "flags": [
            "--decision-json"
          ],
          "help": "Authorised agentic-workspace/config-policy-decision/v1 JSON object.",
          "name": "decision_json",
          "required": true
        },
        {
          "flags": [
            "--expect-config-revision"
          ],
          "help": "Exact sha256 revision reported for the selected shared or local config surface.",
          "name": "expect_config_revision",
          "required": true
        },
        {
          "flags": [
            "--expect-setup-identity"
          ],
          "help": "Exact setup readiness identity against which the decision was made.",
          "name": "expect_setup_identity",
          "required": true
        },
        {
          "action": "store_true",
          "flags": [
            "--dry-run"
          ],
          "help": "Validate and preview the bounded policy effects without writing.",
          "name": "dry_run"
        }
      ]
    },
    "name": "config-policy",
    "operation_ref": {
      "id": "config.policy-apply",
      "path": "operations/config.policy-apply.json"
    }
  },
  {
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
    "name": "system-intent",
    "operation_ref": {
      "id": "system-intent.sync",
      "path": "operations/system-intent.sync.json"
    }
  },
  {
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
          "flags": [
            "--scope-class"
          ],
          "help": "Independent bounded scope class for this delegated run.",
          "name": "scope_class",
          "required": true
        },
        {
          "choices": [
            "submit",
            "correct-or-dispute",
            "supersede",
            "prune-or-compact"
          ],
          "default": "submit",
          "flags": [
            "--operation"
          ],
          "help": "Evidence lifecycle operation.",
          "name": "operation"
        },
        {
          "flags": [
            "--predecessor-id"
          ],
          "help": "Existing record id required for lifecycle transition operations.",
          "name": "predecessor_id"
        },
        {
          "default": "local-outcome-ledger",
          "flags": [
            "--authority"
          ],
          "help": "Authority class for the admitted evidence.",
          "name": "authority"
        },
        {
          "choices": [
            "low",
            "medium",
            "high"
          ],
          "default": "medium",
          "flags": [
            "--confidence"
          ],
          "help": "Confidence classification for the admitted evidence.",
          "name": "confidence"
        },
        {
          "flags": [
            "--source-type"
          ],
          "help": "Provenance source type for the evidence.",
          "name": "source_type"
        },
        {
          "flags": [
            "--source-ref"
          ],
          "help": "Exact source reference for duplicate/idempotency and audit.",
          "name": "source_ref"
        },
        {
          "flags": [
            "--producer-class"
          ],
          "help": "Producer class resolved by the operation boundary.",
          "name": "producer_class"
        },
        {
          "flags": [
            "--route-outcome"
          ],
          "help": "Structured route outcome observation.",
          "name": "route_outcome"
        },
        {
          "flags": [
            "--assignment-route"
          ],
          "help": "Assignment route observed for this outcome.",
          "name": "assignment_route"
        },
        {
          "flags": [
            "--proof-observation"
          ],
          "help": "Proof observation associated with the outcome.",
          "name": "proof_observation"
        },
        {
          "flags": [
            "--review-observation"
          ],
          "help": "Review observation associated with the outcome.",
          "name": "review_observation"
        },
        {
          "flags": [
            "--handoff-burden"
          ],
          "help": "Handoff burden observation.",
          "name": "handoff_burden"
        },
        {
          "flags": [
            "--repair-burden"
          ],
          "help": "Repair burden observation.",
          "name": "repair_burden"
        },
        {
          "flags": [
            "--retry-burden"
          ],
          "help": "Retry burden observation.",
          "name": "retry_burden"
        },
        {
          "flags": [
            "--restart-burden"
          ],
          "help": "Restart burden observation.",
          "name": "restart_burden"
        },
        {
          "flags": [
            "--expected-burden"
          ],
          "help": "Expected burden before execution.",
          "name": "expected_burden"
        },
        {
          "flags": [
            "--observed-burden"
          ],
          "help": "Observed burden after execution.",
          "name": "observed_burden"
        },
        {
          "flags": [
            "--context-cost-json"
          ],
          "help": "Provider-neutral assignment context-cost observation encoded as JSON.",
          "name": "context_cost_json"
        },
        {
          "flags": [
            "--scope-drift"
          ],
          "help": "Scope drift state.",
          "name": "scope_drift"
        },
        {
          "flags": [
            "--contradiction-state"
          ],
          "help": "Contradiction or dispute state.",
          "name": "contradiction_state"
        },
        {
          "flags": [
            "--uncertainty-state"
          ],
          "help": "Uncertainty state preserved for non-routing evidence.",
          "name": "uncertainty_state"
        },
        {
          "flags": [
            "--idempotency-key"
          ],
          "help": "Stable idempotency key supplied by the producer.",
          "name": "idempotency_key"
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
    "name": "note-delegation-outcome",
    "operation_ref": {
      "id": "delegation-outcome.append",
      "path": "operations/delegation-outcome.append.json"
    }
  },
  {
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
    "name": "skills",
    "operation_ref": {
      "id": "skills.report",
      "path": "operations/skills.report.json"
    }
  },
  {
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
        },
        {
          "action": "extend",
          "default": [],
          "flags": [
            "--changed"
          ],
          "help": "Optional repo-relative changed paths used by task-scoped report sections such as closeout_trust.",
          "name": "changed",
          "nargs": "*"
        },
        {
          "flags": [
            "--task"
          ],
          "help": "Optional task description used by task-scoped report sections such as closeout_trust.",
          "name": "task"
        },
        {
          "flags": [
            "--select"
          ],
          "help": "Comma-separated JSON fields to return from the selected report payload, such as answer.closeout_protocol.",
          "name": "select"
        },
        {
          "choices": [
            "strict-current"
          ],
          "flags": [
            "--fail-on"
          ],
          "help": "Assert the named versioned health policy and exit non-zero when current state violates it.",
          "name": "fail_on"
        }
      ]
    },
    "name": "report",
    "operation_ref": {
      "id": "report.combined",
      "path": "operations/report.combined.json"
    }
  },
  {
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
    "name": "reconcile",
    "operation_ref": {
      "id": "reconcile.report",
      "path": "operations/reconcile.report.json"
    }
  },
  {
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
              "action": "append",
              "default": [],
              "flags": [
                "--issue"
              ],
              "help": "Specific GitHub issue number or reference to import via gh issue view. May be repeated.",
              "name": "issue"
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
            },
            {
              "action": "store_true",
              "flags": [
                "--verbose"
              ],
              "help": "Include candidate, grouping, cache, and reconciliation detail for an issue-scoped refresh.",
              "name": "verbose"
            }
          ]
        }
      ]
    },
    "name": "external-intent",
    "operation_ref": {
      "id": "external-intent.refresh-github",
      "path": "operations/external-intent.refresh-github.json"
    }
  },
  {
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
    "name": "preflight",
    "operation_ref": {
      "id": "preflight.report",
      "path": "operations/preflight.report.json"
    }
  },
  {
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
          "action": "append",
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
            "--mirror-payload"
          ],
          "help": "Opt in to checking in the full generic package payload mirror instead of the ordinary necessary-surface footprint.",
          "name": "mirror_payload"
        },
        {
          "action": "store_true",
          "flags": [
            "--verbose"
          ],
          "help": "Show the full lifecycle, module, configuration, and provenance payload instead of the ordinary decision envelope.",
          "name": "verbose"
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
    "name": "install",
    "operation_ref": {
      "id": "install.lifecycle",
      "path": "operations/install.lifecycle.json"
    }
  },
  {
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
          "action": "append",
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
            "--mirror-payload"
          ],
          "help": "Opt in to checking in the full generic package payload mirror instead of the ordinary necessary-surface footprint.",
          "name": "mirror_payload"
        },
        {
          "action": "store_true",
          "flags": [
            "--verbose"
          ],
          "help": "Show the full lifecycle, module, configuration, and provenance payload instead of the ordinary decision envelope.",
          "name": "verbose"
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
    "name": "init",
    "operation_ref": {
      "id": "init.lifecycle",
      "path": "operations/init.lifecycle.json"
    }
  },
  {
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
    "name": "prompt",
    "operation_ref": {
      "id": "prompt.init",
      "path": "operations/prompt.init.json"
    }
  },
  {
    "interface": {
      "help": "Show installed-module health for lifecycle checks; ordinary agents should use start/report routing first.",
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
    "name": "status",
    "operation_ref": {
      "id": "status.report",
      "path": "operations/status.report.json"
    }
  },
  {
    "interface": {
      "help": "Show drift diagnostics for recovery or remediation; ordinary agents should use start/report routing first.",
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
    "name": "doctor",
    "operation_ref": {
      "id": "doctor.report",
      "path": "operations/doctor.report.json"
    }
  },
  {
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
          "action": "append",
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
            "--verbose"
          ],
          "help": "Emit full lifecycle and per-file detail. The default upgrade output is compact and decision-first.",
          "name": "verbose"
        },
        {
          "flags": [
            "--select"
          ],
          "help": "Return selected fields from the full upgrade payload.",
          "name": "select"
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
            "--legacy-scratch-cleanup"
          ],
          "help": "Run the explicit legacy AW local scratch cleanup route. Defaults to dry-run unless --apply-legacy-scratch-cleanup is also set.",
          "name": "legacy_scratch_cleanup"
        },
        {
          "action": "store_true",
          "flags": [
            "--apply-legacy-scratch-cleanup"
          ],
          "help": "Apply the explicit legacy AW local scratch cleanup after reviewing the dry-run output.",
          "name": "apply_legacy_scratch_cleanup"
        },
        {
          "action": "store_true",
          "flags": [
            "--repair-managed-local-instructions"
          ],
          "help": "Refresh only the workspace-managed .agentic-workspace local agent instructions file.",
          "name": "repair_managed_local_instructions"
        },
        {
          "action": "store_true",
          "flags": [
            "--repair-root-startup-pointer"
          ],
          "help": "Patch only the managed workflow pointer fence in the configured root startup file.",
          "name": "repair_root_startup_pointer"
        },
        {
          "action": "store_true",
          "flags": [
            "--adopt-local-only"
          ],
          "help": "Transition a local-only Agentic Workspace install to checked-in mode while preserving durable AW state.",
          "name": "adopt_local_only"
        },
        {
          "action": "store_true",
          "flags": [
            "--to-payload-target"
          ],
          "help": "Read [payload] from repo config and sync managed payload/provenance to the declared target.",
          "name": "to_payload_target"
        },
        {
          "action": "store_true",
          "flags": [
            "--to-necessary-surfaces"
          ],
          "help": "Migrate legacy checked-in AW package payload to necessary repo surfaces while preserving durable Planning, Memory, and Verification state.",
          "name": "to_necessary_surfaces"
        }
      ]
    },
    "name": "upgrade",
    "operation_ref": {
      "id": "upgrade.lifecycle",
      "path": "operations/upgrade.lifecycle.json"
    }
  },
  {
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
          "action": "append",
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
    "name": "uninstall",
    "operation_ref": {
      "id": "uninstall.lifecycle",
      "path": "operations/uninstall.lifecycle.json"
    }
  },
  {
    "interface": {
      "help": "Create, validate, and explain scoped Markdown instructions through generated operations.",
      "name": "instructions",
      "options": [],
      "subcommand_dest": "instructions_command",
      "subcommands": [
        {
          "help": "List scoped instructions without loading irrelevant bodies.",
          "name": "list",
          "operation_ref": {
            "id": "instructions.list",
            "path": "operations/instructions.list.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to current directory.",
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
          "help": "Scaffold one global or path-scoped Markdown instruction.",
          "name": "new",
          "operation_ref": {
            "id": "instructions.create",
            "path": "operations/instructions.create.json"
          },
          "options": [
            {
              "flags": [
                "--name"
              ],
              "help": "Lowercase instruction identity used as the filename stem.",
              "name": "name",
              "required": true
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--paths"
              ],
              "help": "Repository-relative applicability pattern. Repeat for multiple patterns.",
              "name": "paths"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to current directory.",
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
          "help": "Validate instruction syntax and references without executing checks.",
          "name": "check",
          "operation_ref": {
            "id": "instructions.check",
            "path": "operations/instructions.check.json"
          },
          "options": [
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to current directory.",
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
          "help": "Explain task-specific applicability in repository vocabulary.",
          "name": "explain",
          "operation_ref": {
            "id": "instructions.explain",
            "path": "operations/instructions.explain.json"
          },
          "options": [
            {
              "default": "",
              "flags": [
                "--task"
              ],
              "help": "Optional task text used during applicability explanation.",
              "name": "task"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--changed"
              ],
              "help": "Changed or target path. Repeat for multiple paths.",
              "name": "changed"
            },
            {
              "action": "store_true",
              "flags": [
                "--verbose"
              ],
              "help": "Include the compiled instruction program.",
              "name": "verbose"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to current directory.",
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
          "help": "Discover repo-owned semantic task routes one branch or leaf at a time.",
          "name": "routes",
          "operation_ref": {
            "id": "instructions.routes",
            "path": "operations/instructions.routes.json"
          },
          "options": [
            {
              "default": "",
              "flags": [
                "--parent"
              ],
              "help": "Optional route branch to expand one level.",
              "name": "parent"
            },
            {
              "default": "",
              "flags": [
                "--exact"
              ],
              "help": "Optional known route leaf to inspect directly.",
              "name": "exact"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to current directory.",
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
          "help": "Select existing semantic route facts for the resolved current work.",
          "name": "select-route",
          "operation_ref": {
            "id": "instructions.route-select",
            "path": "operations/instructions.route-select.json"
          },
          "options": [
            {
              "choices": [
                "selected",
                "none",
                "unresolved"
              ],
              "flags": [
                "--posture"
              ],
              "help": "Explicit semantic applicability posture.",
              "name": "posture",
              "required": true
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--route"
              ],
              "help": "Existing route leaf. Repeat for multiple facets.",
              "name": "route"
            },
            {
              "default": "",
              "flags": [
                "--current-work-id"
              ],
              "help": "Optional exact current-work guard.",
              "name": "current_work_id"
            },
            {
              "flags": [
                "--expect-source-revision"
              ],
              "help": "Exact source revision returned by route discovery.",
              "name": "expected_source_revision",
              "required": true
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Validate the selection without writing local state.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to current directory.",
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
          "help": "Give non-destructive incremental migration guidance.",
          "name": "migrate",
          "operation_ref": {
            "id": "instructions.migrate",
            "path": "operations/instructions.migrate.json"
          },
          "options": [
            {
              "flags": [
                "--from"
              ],
              "help": "Repository-relative instruction source to inspect.",
              "name": "source",
              "required": true
            },
            {
              "flags": [
                "--target"
              ],
              "help": "Target repository path. Defaults to current directory.",
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
        }
      ],
      "subcommands_required": true
    },
    "name": "instructions",
    "operation_ref": {
      "id": "instructions.explain",
      "path": "operations/instructions.explain.json"
    }
  },
  {
    "interface": {
      "help": "Promote and mutate local target guidance through generated operations.",
      "name": "agent-guidance",
      "options": [],
      "subcommand_dest": "agent_guidance_command",
      "subcommands": [
        {
          "help": "Promote one authorised guidance candidate into its lifecycle store.",
          "name": "promote",
          "operation_ref": {
            "id": "agent-guidance.promote",
            "path": "operations/agent-guidance.promote.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Edit one guidance record while preserving provenance and revision history.",
          "name": "edit",
          "operation_ref": {
            "id": "agent-guidance.edit",
            "path": "operations/agent-guidance.edit.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Merge guidance records and preserve source lineage.",
          "name": "merge",
          "operation_ref": {
            "id": "agent-guidance.merge",
            "path": "operations/agent-guidance.merge.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Split one guidance record into replacement records.",
          "name": "split",
          "operation_ref": {
            "id": "agent-guidance.split",
            "path": "operations/agent-guidance.split.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Suppress guidance without deleting provenance.",
          "name": "suppress",
          "operation_ref": {
            "id": "agent-guidance.suppress",
            "path": "operations/agent-guidance.suppress.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Revalidate guidance against the current target identity.",
          "name": "revalidate",
          "operation_ref": {
            "id": "agent-guidance.revalidate",
            "path": "operations/agent-guidance.revalidate.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Weaken guidance to advisory-only routing.",
          "name": "weaken",
          "operation_ref": {
            "id": "agent-guidance.weaken",
            "path": "operations/agent-guidance.weaken.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Supersede guidance with a replacement record.",
          "name": "supersede",
          "operation_ref": {
            "id": "agent-guidance.supersede",
            "path": "operations/agent-guidance.supersede.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Retire guidance from future routing.",
          "name": "retire",
          "operation_ref": {
            "id": "agent-guidance.retire",
            "path": "operations/agent-guidance.retire.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Delete guidance routing while retaining mutation receipt provenance.",
          "name": "delete",
          "operation_ref": {
            "id": "agent-guidance.delete",
            "path": "operations/agent-guidance.delete.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--guidance-id"
              ],
              "help": "Guidance lifecycle record id.",
              "name": "guidance_id"
            },
            {
              "flags": [
                "--expected-revision"
              ],
              "help": "Expected current record revision for transition operations.",
              "name": "expected_revision"
            },
            {
              "flags": [
                "--expected-record-revisions-json"
              ],
              "help": "JSON object of related guidance ids to expected revisions.",
              "name": "expected_record_revisions_json"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable lifecycle transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--instruction"
              ],
              "help": "Replacement instruction for edit operations.",
              "name": "instruction"
            },
            {
              "flags": [
                "--replacement-guidance-id"
              ],
              "help": "Replacement guidance id for supersede operations.",
              "name": "replacement_guidance_id"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--merge-guidance-id"
              ],
              "help": "Guidance id to merge into the selected record. Repeat for multiple ids.",
              "name": "merge_guidance_ids"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--split-instruction"
              ],
              "help": "Replacement instruction for split operations. Repeat at least twice.",
              "name": "split_instructions"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Promotion task class filter.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Promotion scope class filter.",
              "name": "scope_class"
            },
            {
              "action": "store_true",
              "flags": [
                "--explicit-remember"
              ],
              "help": "Request immediate remember promotion; ignored without a trusted remember receipt.",
              "name": "explicit_remember"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        }
      ]
    },
    "name": "agent-guidance",
    "operation_ref": {
      "id": "agent-guidance.promote",
      "path": "operations/agent-guidance.promote.json"
    }
  },
  {
    "interface": {
      "help": "Execute public assignment/run lifecycle operations.",
      "name": "assignment",
      "options": [],
      "subcommand_dest": "assignment_command",
      "subcommands": [
        {
          "help": "Execute one configured automatic assignment transport and capture its return for admission.",
          "name": "dispatch",
          "operation_ref": {
            "id": "assignment.dispatch",
            "path": "operations/assignment.dispatch.json"
          },
          "options": [
            {
              "flags": [
                "--configuration-revision"
              ],
              "help": "Current execution configuration offer revision; pair with configuration-id before materializing an assignment.",
              "name": "configuration_revision"
            },
            {
              "flags": [
                "--configuration-id"
              ],
              "help": "Acting orchestrator choice of one eligible execution configuration; cannot replace an existing assignment.",
              "name": "configuration_id"
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
                "--target"
              ],
              "help": "Target repository path. Defaults to the current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id"
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "flags": [
                "--task"
              ],
              "help": "Full human intent used when dispatch must materialize the live assignment first.",
              "name": "task"
            },
            {
              "action": "append",
              "flags": [
                "--changed"
              ],
              "help": "Changed or allowed path used to bind a newly materialized assignment.",
              "name": "changed"
            },
            {
              "choices": [
                "internal",
                "cli",
                "api"
              ],
              "flags": [
                "--transport"
              ],
              "help": "Configured automatic transport route.",
              "name": "transport",
              "required": true
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts or executing transport.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Prepare a durable assignment handoff packet and pasteable prompt from one assignment authority.",
          "name": "export",
          "operation_ref": {
            "id": "assignment.export",
            "path": "operations/assignment.export.json"
          },
          "options": [
            {
              "flags": [
                "--configuration-revision"
              ],
              "help": "Current execution configuration offer revision; pair with configuration-id before materializing an assignment.",
              "name": "configuration_revision"
            },
            {
              "flags": [
                "--configuration-id"
              ],
              "help": "Acting orchestrator choice of one eligible execution configuration; cannot replace an existing assignment.",
              "name": "configuration_id"
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
                "--target"
              ],
              "help": "Target repository path. Defaults to the current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id"
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "flags": [
                "--task"
              ],
              "help": "Full human intent used when export must materialize the live assignment first.",
              "name": "task"
            },
            {
              "action": "append",
              "flags": [
                "--changed"
              ],
              "help": "Changed or allowed path used to bind a newly materialized assignment.",
              "name": "changed"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Import returned delegated work into received/awaiting-admission without proof or integration.",
          "name": "import",
          "operation_ref": {
            "id": "assignment.import",
            "path": "operations/assignment.import.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-file"
              ],
              "help": "Repo-contained UTF-8 file holding returned worker-result JSON; mutually exclusive with --return-json.",
              "name": "return_file"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Record an AW-owned admission decision after current authority revalidation.",
          "name": "admit",
          "operation_ref": {
            "id": "assignment.admit",
            "path": "operations/assignment.admit.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref",
              "required": false
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline",
              "required": false
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            },
            {
              "flags": [
                "--review-result-json"
              ],
              "help": "Serialized producer-owned independent-review result envelope.",
              "name": "review_result_json"
            },
            {
              "flags": [
                "--review-result-ref"
              ],
              "help": "Repo-relative independent-review result envelope to admit.",
              "name": "review_result_ref"
            },
            {
              "flags": [
                "--host-result-ref"
              ],
              "help": "Opaque host/adapter independent-review result ref to import and admit; a protected host/adapter resolver must supply the admission verdict.",
              "name": "host_result_ref"
            },
            {
              "choices": [
                "fresh-context",
                "separate-actor",
                "distinct-provider",
                "human"
              ],
              "flags": [
                "--required-mode"
              ],
              "help": "Required independent-review separation mode.",
              "name": "required_mode"
            },
            {
              "action": "extend",
              "default": [],
              "flags": [
                "--changed"
              ],
              "help": "Changed paths whose review scope must match the admitted result.",
              "name": "changed",
              "nargs": "*"
            }
          ]
        },
        {
          "help": "Reject a returned assignment result with stable recovery evidence.",
          "name": "reject",
          "operation_ref": {
            "id": "assignment.reject",
            "path": "operations/assignment.reject.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason",
              "required": true
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Request repair for a returned assignment result without admitting mutation.",
          "name": "repair",
          "operation_ref": {
            "id": "assignment.repair",
            "path": "operations/assignment.repair.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason",
              "required": true
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Supersede one assignment run and bind follow-up ownership to a new target.",
          "name": "reassign",
          "operation_ref": {
            "id": "assignment.reassign",
            "path": "operations/assignment.reassign.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name",
              "required": true
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason",
              "required": true
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Move an admitted return through the protected integration boundary.",
          "name": "integrate",
          "operation_ref": {
            "id": "assignment.integrate",
            "path": "operations/assignment.integrate.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref",
              "required": false
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline",
              "required": false
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Inspect one exact assignment run and its current continuation without mutation.",
          "name": "status",
          "operation_ref": {
            "id": "assignment.status",
            "path": "operations/assignment.status.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id"
            }
          ]
        },
        {
          "help": "Close an integrated or intentionally rejected assignment run with a local receipt.",
          "name": "close",
          "operation_ref": {
            "id": "assignment.close",
            "path": "operations/assignment.close.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--task-proof-receipt-ref"
              ],
              "help": "Repo-relative admitted AW proof receipt sealed for the exact assignment obligation.",
              "name": "task_proof_receipt_ref",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Archive disposable local assignment run artifacts after closeout.",
          "name": "cleanup",
          "operation_ref": {
            "id": "assignment.cleanup",
            "path": "operations/assignment.cleanup.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id"
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id",
              "required": true
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason"
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope"
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        },
        {
          "help": "Record a scoped authorised human override with expiry and proof/claim consequences.",
          "name": "override",
          "operation_ref": {
            "id": "assignment.override",
            "path": "operations/assignment.override.json"
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
                "--assignment-id"
              ],
              "help": "Stable Planning assignment id.",
              "name": "assignment_id",
              "required": true
            },
            {
              "flags": [
                "--assignment-revision"
              ],
              "help": "Current assignment identity revision.",
              "name": "assignment_revision"
            },
            {
              "flags": [
                "--run-id"
              ],
              "help": "Stable assignment run id.",
              "name": "run_id"
            },
            {
              "flags": [
                "--target-name"
              ],
              "help": "Selected target name.",
              "name": "target_name"
            },
            {
              "choices": [
                "manual",
                "internal",
                "cli",
                "api"
              ],
              "default": "manual",
              "flags": [
                "--transport"
              ],
              "help": "Selected transport route.",
              "name": "transport"
            },
            {
              "flags": [
                "--packet-json"
              ],
              "help": "Structured assignment packet JSON.",
              "name": "packet_json"
            },
            {
              "flags": [
                "--return-json"
              ],
              "help": "Returned worker-result JSON.",
              "name": "return_json"
            },
            {
              "flags": [
                "--return-id"
              ],
              "help": "Stable imported return id.",
              "name": "return_id"
            },
            {
              "flags": [
                "--artifact-ref"
              ],
              "help": "Local artifact reference for the transition.",
              "name": "artifact_ref"
            },
            {
              "flags": [
                "--current-authority-ref"
              ],
              "help": "Current Planning/proof/run authority reference resolved immediately before admission or integration.",
              "name": "current_authority_ref"
            },
            {
              "flags": [
                "--live-mutation-baseline"
              ],
              "help": "Live worktree mutation baseline resolved immediately before admission or integration.",
              "name": "live_mutation_baseline"
            },
            {
              "choices": [
                "admitted",
                "rejected",
                "repair-requested"
              ],
              "flags": [
                "--admission-status"
              ],
              "help": "Admission result to record.",
              "name": "admission_status"
            },
            {
              "flags": [
                "--reason"
              ],
              "help": "Human-readable transition reason.",
              "name": "reason",
              "required": true
            },
            {
              "flags": [
                "--scope"
              ],
              "help": "Bounded override or assignment scope.",
              "name": "scope",
              "required": true
            },
            {
              "flags": [
                "--expires-at"
              ],
              "help": "Override expiry or revalidation timestamp.",
              "name": "expires_at",
              "required": true
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report the transition without writing local artifacts.",
              "name": "dry_run"
            },
            {
              "flags": [
                "--assignment-gate-json"
              ],
              "help": "Serialized current assignment gate authority.",
              "name": "assignment_gate_json"
            },
            {
              "flags": [
                "--assignment-policy-json"
              ],
              "help": "Serialized current assignment policy authority.",
              "name": "assignment_policy_json"
            },
            {
              "flags": [
                "--delegation-decision-json"
              ],
              "help": "Serialized current delegation decision authority.",
              "name": "delegation_decision_json"
            },
            {
              "flags": [
                "--aw-proof-receipt-json"
              ],
              "help": "Serialized AW proof receipt authority.",
              "name": "aw_proof_receipt_json"
            },
            {
              "flags": [
                "--run-state-json"
              ],
              "help": "Serialized current assignment run state authority.",
              "name": "run_state_json"
            }
          ]
        }
      ]
    },
    "name": "assignment",
    "operation_ref": {
      "id": "assignment.export",
      "path": "operations/assignment.export.json"
    }
  },
  {
    "interface": {
      "help": "Submit, query, and compact local correction events through generated operations.",
      "name": "correction-event",
      "options": [],
      "subcommand_dest": "correction_event_command",
      "subcommands": [
        {
          "help": "Initialize a collision-checked stable identity for one configured target profile in local config.",
          "name": "identity-init",
          "operation_ref": {
            "id": "correction-event.identity-init",
            "path": "operations/correction-event.identity-init.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--target-profile"
              ],
              "help": "Configured target profile name. Defaults to delegation.current_target.",
              "name": "target_profile"
            },
            {
              "flags": [
                "--target-id"
              ],
              "help": "Optional explicit stable id; omission uses the collision-checked generated proposal.",
              "name": "target_id"
            },
            {
              "flags": [
                "--expected-config-digest"
              ],
              "help": "Optional config digest from a dry run for compare-and-swap admission.",
              "name": "expected_config_digest"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Return the exact identity/config mutation without writing local config.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Submit a correction event through the public local operation boundary.",
          "name": "submit",
          "operation_ref": {
            "id": "correction-event.submit",
            "path": "operations/correction-event.submit.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--event-json"
              ],
              "help": "Serialized correction event JSON.",
              "name": "event_json"
            },
            {
              "flags": [
                "--trusted-host-event-json"
              ],
              "help": "Signed producer-owned host observation envelope; caller labels do not confer authority.",
              "name": "trusted_host_event_json"
            },
            {
              "flags": [
                "--host-event-ref"
              ],
              "help": "Opaque trusted-host observation reference for later normalization or disposition.",
              "name": "host_event_ref"
            },
            {
              "flags": [
                "--trusted-authority-receipt-ref"
              ],
              "help": "Repo-relative AW/human authority receipt reference resolved by the host boundary.",
              "name": "trusted_authority_receipt_ref"
            },
            {
              "flags": [
                "--idempotency-key"
              ],
              "help": "Stable delivery idempotency key.",
              "name": "idempotency_key"
            },
            {
              "flags": [
                "--delivery-id"
              ],
              "help": "Stable delivery id.",
              "name": "delivery_id"
            },
            {
              "flags": [
                "--event-id"
              ],
              "help": "Existing normalized correction event id for a route/disposition update.",
              "name": "event_id"
            },
            {
              "flags": [
                "--target-identity-ref"
              ],
              "help": "Target id/name/alias to resolve.",
              "name": "target_identity_ref"
            },
            {
              "flags": [
                "--target-revision"
              ],
              "help": "Submitted target revision.",
              "name": "target_revision"
            },
            {
              "flags": [
                "--source-ref"
              ],
              "help": "Stable source reference.",
              "name": "source_ref"
            },
            {
              "flags": [
                "--source"
              ],
              "help": "Submitted source label.",
              "name": "source"
            },
            {
              "flags": [
                "--producer-class"
              ],
              "help": "Submitted producer class; cannot upgrade authority without a trusted receipt.",
              "name": "producer_class"
            },
            {
              "flags": [
                "--producer-id"
              ],
              "help": "Producer id.",
              "name": "producer_id"
            },
            {
              "flags": [
                "--authority"
              ],
              "help": "Claimed authority; ignored for upgrade without trusted receipt.",
              "name": "authority"
            },
            {
              "flags": [
                "--desired-behavior"
              ],
              "help": "Desired behavior.",
              "name": "desired_behavior"
            },
            {
              "flags": [
                "--replaced-behavior"
              ],
              "help": "Replaced behavior.",
              "name": "replaced_behavior"
            },
            {
              "flags": [
                "--invariant-id"
              ],
              "help": "Structured invariant id.",
              "name": "invariant_id"
            },
            {
              "flags": [
                "--behavior-class"
              ],
              "help": "Structured behavior class.",
              "name": "behavior_class"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Task class applicability.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Scope class applicability.",
              "name": "scope_class"
            },
            {
              "flags": [
                "--phase"
              ],
              "help": "Workflow phase applicability.",
              "name": "phase"
            },
            {
              "flags": [
                "--subsystem"
              ],
              "help": "Subsystem applicability.",
              "name": "subsystem"
            },
            {
              "flags": [
                "--surface"
              ],
              "help": "Operation or artifact surface applicability.",
              "name": "surface"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--route-decision"
              ],
              "help": "Route decision. Repeat for multiple routes.",
              "name": "route_decisions"
            },
            {
              "flags": [
                "--canonical-owner-ref"
              ],
              "help": "Existing canonical owner for an evidence-backed no-duplicate disposition.",
              "name": "canonical_owner_ref"
            },
            {
              "flags": [
                "--canonical-owner-evidence-ref"
              ],
              "help": "Evidence that the named canonical owner already owns the corrected invariant.",
              "name": "canonical_owner_evidence_ref"
            },
            {
              "flags": [
                "--evidence-hash"
              ],
              "help": "Evidence hash.",
              "name": "evidence_hash"
            },
            {
              "flags": [
                "--evidence-ref"
              ],
              "help": "Evidence reference.",
              "name": "evidence_ref"
            },
            {
              "flags": [
                "--predecessor-event-id"
              ],
              "help": "Predecessor event id for lifecycle transitions.",
              "name": "predecessor_event_id"
            },
            {
              "choices": [
                "withdraw",
                "supersede"
              ],
              "flags": [
                "--lifecycle-action"
              ],
              "help": "Withdraw/supersede action.",
              "name": "lifecycle_action"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Query admitted and low-authority correction events from bounded local storage.",
          "name": "query",
          "operation_ref": {
            "id": "correction-event.query",
            "path": "operations/correction-event.query.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--event-json"
              ],
              "help": "Serialized correction event JSON.",
              "name": "event_json"
            },
            {
              "flags": [
                "--trusted-authority-receipt-ref"
              ],
              "help": "Repo-relative AW/human authority receipt reference resolved by the host boundary.",
              "name": "trusted_authority_receipt_ref"
            },
            {
              "flags": [
                "--idempotency-key"
              ],
              "help": "Stable delivery idempotency key.",
              "name": "idempotency_key"
            },
            {
              "flags": [
                "--delivery-id"
              ],
              "help": "Stable delivery id.",
              "name": "delivery_id"
            },
            {
              "flags": [
                "--target-identity-ref"
              ],
              "help": "Target id/name/alias to resolve.",
              "name": "target_identity_ref"
            },
            {
              "flags": [
                "--target-revision"
              ],
              "help": "Submitted target revision.",
              "name": "target_revision"
            },
            {
              "flags": [
                "--source-ref"
              ],
              "help": "Stable source reference.",
              "name": "source_ref"
            },
            {
              "flags": [
                "--source"
              ],
              "help": "Submitted source label.",
              "name": "source"
            },
            {
              "flags": [
                "--producer-class"
              ],
              "help": "Submitted producer class; cannot upgrade authority without a trusted receipt.",
              "name": "producer_class"
            },
            {
              "flags": [
                "--producer-id"
              ],
              "help": "Producer id.",
              "name": "producer_id"
            },
            {
              "flags": [
                "--authority"
              ],
              "help": "Claimed authority; ignored for upgrade without trusted receipt.",
              "name": "authority"
            },
            {
              "flags": [
                "--desired-behavior"
              ],
              "help": "Desired behavior.",
              "name": "desired_behavior"
            },
            {
              "flags": [
                "--replaced-behavior"
              ],
              "help": "Replaced behavior.",
              "name": "replaced_behavior"
            },
            {
              "flags": [
                "--invariant-id"
              ],
              "help": "Structured invariant id.",
              "name": "invariant_id"
            },
            {
              "flags": [
                "--behavior-class"
              ],
              "help": "Structured behavior class.",
              "name": "behavior_class"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Task class applicability.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Scope class applicability.",
              "name": "scope_class"
            },
            {
              "flags": [
                "--phase"
              ],
              "help": "Workflow phase applicability.",
              "name": "phase"
            },
            {
              "flags": [
                "--subsystem"
              ],
              "help": "Subsystem applicability.",
              "name": "subsystem"
            },
            {
              "flags": [
                "--surface"
              ],
              "help": "Operation or artifact surface applicability.",
              "name": "surface"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--route-decision"
              ],
              "help": "Route decision. Repeat for multiple routes.",
              "name": "route_decisions"
            },
            {
              "flags": [
                "--evidence-hash"
              ],
              "help": "Evidence hash.",
              "name": "evidence_hash"
            },
            {
              "flags": [
                "--evidence-ref"
              ],
              "help": "Evidence reference.",
              "name": "evidence_ref"
            },
            {
              "flags": [
                "--predecessor-event-id"
              ],
              "help": "Predecessor event id for lifecycle transitions.",
              "name": "predecessor_event_id"
            },
            {
              "choices": [
                "withdraw",
                "supersede"
              ],
              "flags": [
                "--lifecycle-action"
              ],
              "help": "Withdraw/supersede action.",
              "name": "lifecycle_action"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Record a dispute/correction transition for a prior correction event.",
          "name": "correct-dispute",
          "operation_ref": {
            "id": "correction-event.correct-dispute",
            "path": "operations/correction-event.correct-dispute.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--event-json"
              ],
              "help": "Serialized correction event JSON.",
              "name": "event_json"
            },
            {
              "flags": [
                "--trusted-authority-receipt-ref"
              ],
              "help": "Repo-relative AW/human authority receipt reference resolved by the host boundary.",
              "name": "trusted_authority_receipt_ref"
            },
            {
              "flags": [
                "--idempotency-key"
              ],
              "help": "Stable delivery idempotency key.",
              "name": "idempotency_key"
            },
            {
              "flags": [
                "--delivery-id"
              ],
              "help": "Stable delivery id.",
              "name": "delivery_id"
            },
            {
              "flags": [
                "--target-identity-ref"
              ],
              "help": "Target id/name/alias to resolve.",
              "name": "target_identity_ref"
            },
            {
              "flags": [
                "--target-revision"
              ],
              "help": "Submitted target revision.",
              "name": "target_revision"
            },
            {
              "flags": [
                "--source-ref"
              ],
              "help": "Stable source reference.",
              "name": "source_ref"
            },
            {
              "flags": [
                "--source"
              ],
              "help": "Submitted source label.",
              "name": "source"
            },
            {
              "flags": [
                "--producer-class"
              ],
              "help": "Submitted producer class; cannot upgrade authority without a trusted receipt.",
              "name": "producer_class"
            },
            {
              "flags": [
                "--producer-id"
              ],
              "help": "Producer id.",
              "name": "producer_id"
            },
            {
              "flags": [
                "--authority"
              ],
              "help": "Claimed authority; ignored for upgrade without trusted receipt.",
              "name": "authority"
            },
            {
              "flags": [
                "--desired-behavior"
              ],
              "help": "Desired behavior.",
              "name": "desired_behavior"
            },
            {
              "flags": [
                "--replaced-behavior"
              ],
              "help": "Replaced behavior.",
              "name": "replaced_behavior"
            },
            {
              "flags": [
                "--invariant-id"
              ],
              "help": "Structured invariant id.",
              "name": "invariant_id"
            },
            {
              "flags": [
                "--behavior-class"
              ],
              "help": "Structured behavior class.",
              "name": "behavior_class"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Task class applicability.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Scope class applicability.",
              "name": "scope_class"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--route-decision"
              ],
              "help": "Route decision. Repeat for multiple routes.",
              "name": "route_decisions"
            },
            {
              "flags": [
                "--evidence-hash"
              ],
              "help": "Evidence hash.",
              "name": "evidence_hash"
            },
            {
              "flags": [
                "--evidence-ref"
              ],
              "help": "Evidence reference.",
              "name": "evidence_ref"
            },
            {
              "flags": [
                "--predecessor-event-id"
              ],
              "help": "Predecessor event id for lifecycle transitions.",
              "name": "predecessor_event_id"
            },
            {
              "choices": [
                "withdraw",
                "supersede"
              ],
              "flags": [
                "--lifecycle-action"
              ],
              "help": "Withdraw/supersede action.",
              "name": "lifecycle_action"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Withdraw or supersede a prior correction event.",
          "name": "withdraw-supersede",
          "operation_ref": {
            "id": "correction-event.withdraw-supersede",
            "path": "operations/correction-event.withdraw-supersede.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--event-json"
              ],
              "help": "Serialized correction event JSON.",
              "name": "event_json"
            },
            {
              "flags": [
                "--trusted-authority-receipt-ref"
              ],
              "help": "Repo-relative AW/human authority receipt reference resolved by the host boundary.",
              "name": "trusted_authority_receipt_ref"
            },
            {
              "flags": [
                "--idempotency-key"
              ],
              "help": "Stable delivery idempotency key.",
              "name": "idempotency_key"
            },
            {
              "flags": [
                "--delivery-id"
              ],
              "help": "Stable delivery id.",
              "name": "delivery_id"
            },
            {
              "flags": [
                "--target-identity-ref"
              ],
              "help": "Target id/name/alias to resolve.",
              "name": "target_identity_ref"
            },
            {
              "flags": [
                "--target-revision"
              ],
              "help": "Submitted target revision.",
              "name": "target_revision"
            },
            {
              "flags": [
                "--source-ref"
              ],
              "help": "Stable source reference.",
              "name": "source_ref"
            },
            {
              "flags": [
                "--source"
              ],
              "help": "Submitted source label.",
              "name": "source"
            },
            {
              "flags": [
                "--producer-class"
              ],
              "help": "Submitted producer class; cannot upgrade authority without a trusted receipt.",
              "name": "producer_class"
            },
            {
              "flags": [
                "--producer-id"
              ],
              "help": "Producer id.",
              "name": "producer_id"
            },
            {
              "flags": [
                "--authority"
              ],
              "help": "Claimed authority; ignored for upgrade without trusted receipt.",
              "name": "authority"
            },
            {
              "flags": [
                "--desired-behavior"
              ],
              "help": "Desired behavior.",
              "name": "desired_behavior"
            },
            {
              "flags": [
                "--replaced-behavior"
              ],
              "help": "Replaced behavior.",
              "name": "replaced_behavior"
            },
            {
              "flags": [
                "--invariant-id"
              ],
              "help": "Structured invariant id.",
              "name": "invariant_id"
            },
            {
              "flags": [
                "--behavior-class"
              ],
              "help": "Structured behavior class.",
              "name": "behavior_class"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Task class applicability.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Scope class applicability.",
              "name": "scope_class"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--route-decision"
              ],
              "help": "Route decision. Repeat for multiple routes.",
              "name": "route_decisions"
            },
            {
              "flags": [
                "--evidence-hash"
              ],
              "help": "Evidence hash.",
              "name": "evidence_hash"
            },
            {
              "flags": [
                "--evidence-ref"
              ],
              "help": "Evidence reference.",
              "name": "evidence_ref"
            },
            {
              "flags": [
                "--predecessor-event-id"
              ],
              "help": "Predecessor event id for lifecycle transitions.",
              "name": "predecessor_event_id"
            },
            {
              "choices": [
                "withdraw",
                "supersede"
              ],
              "flags": [
                "--lifecycle-action"
              ],
              "help": "Withdraw/supersede action.",
              "name": "lifecycle_action"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        },
        {
          "help": "Compact bounded local correction-event storage while preserving lineage.",
          "name": "prune-compact",
          "operation_ref": {
            "id": "correction-event.prune-compact",
            "path": "operations/correction-event.prune-compact.json"
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
              "help": "Target repository path. Defaults to current directory.",
              "name": "target"
            },
            {
              "flags": [
                "--event-json"
              ],
              "help": "Serialized correction event JSON.",
              "name": "event_json"
            },
            {
              "flags": [
                "--trusted-authority-receipt-ref"
              ],
              "help": "Repo-relative AW/human authority receipt reference resolved by the host boundary.",
              "name": "trusted_authority_receipt_ref"
            },
            {
              "flags": [
                "--idempotency-key"
              ],
              "help": "Stable delivery idempotency key.",
              "name": "idempotency_key"
            },
            {
              "flags": [
                "--delivery-id"
              ],
              "help": "Stable delivery id.",
              "name": "delivery_id"
            },
            {
              "flags": [
                "--target-identity-ref"
              ],
              "help": "Target id/name/alias to resolve.",
              "name": "target_identity_ref"
            },
            {
              "flags": [
                "--target-revision"
              ],
              "help": "Submitted target revision.",
              "name": "target_revision"
            },
            {
              "flags": [
                "--source-ref"
              ],
              "help": "Stable source reference.",
              "name": "source_ref"
            },
            {
              "flags": [
                "--source"
              ],
              "help": "Submitted source label.",
              "name": "source"
            },
            {
              "flags": [
                "--producer-class"
              ],
              "help": "Submitted producer class; cannot upgrade authority without a trusted receipt.",
              "name": "producer_class"
            },
            {
              "flags": [
                "--producer-id"
              ],
              "help": "Producer id.",
              "name": "producer_id"
            },
            {
              "flags": [
                "--authority"
              ],
              "help": "Claimed authority; ignored for upgrade without trusted receipt.",
              "name": "authority"
            },
            {
              "flags": [
                "--desired-behavior"
              ],
              "help": "Desired behavior.",
              "name": "desired_behavior"
            },
            {
              "flags": [
                "--replaced-behavior"
              ],
              "help": "Replaced behavior.",
              "name": "replaced_behavior"
            },
            {
              "flags": [
                "--invariant-id"
              ],
              "help": "Structured invariant id.",
              "name": "invariant_id"
            },
            {
              "flags": [
                "--behavior-class"
              ],
              "help": "Structured behavior class.",
              "name": "behavior_class"
            },
            {
              "flags": [
                "--task-class"
              ],
              "help": "Task class applicability.",
              "name": "task_class"
            },
            {
              "flags": [
                "--scope-class"
              ],
              "help": "Scope class applicability.",
              "name": "scope_class"
            },
            {
              "action": "append",
              "default": [],
              "flags": [
                "--route-decision"
              ],
              "help": "Route decision. Repeat for multiple routes.",
              "name": "route_decisions"
            },
            {
              "flags": [
                "--evidence-hash"
              ],
              "help": "Evidence hash.",
              "name": "evidence_hash"
            },
            {
              "flags": [
                "--evidence-ref"
              ],
              "help": "Evidence reference.",
              "name": "evidence_ref"
            },
            {
              "flags": [
                "--predecessor-event-id"
              ],
              "help": "Predecessor event id for lifecycle transitions.",
              "name": "predecessor_event_id"
            },
            {
              "choices": [
                "withdraw",
                "supersede"
              ],
              "flags": [
                "--lifecycle-action"
              ],
              "help": "Withdraw/supersede action.",
              "name": "lifecycle_action"
            },
            {
              "action": "store_true",
              "flags": [
                "--dry-run"
              ],
              "help": "Report without mutation.",
              "name": "dry_run"
            }
          ]
        }
      ]
    },
    "name": "correction-event",
    "operation_ref": {
      "id": "correction-event.submit",
      "path": "operations/correction-event.submit.json"
    }
  }
];
const commandByName = new Map(commandDefinitions.map((definition) => [definition.name, definition.interface]));
const commandDefinitionByName = new Map(commandDefinitions.map((definition) => [definition.name, definition]));
const argv = process.argv.slice(2);
const command = argv[0];

function optionFlags(option) {
  return Array.isArray(option.flags) ? option.flags : [];
}

function interfaceOptions(iface) {
  return Array.isArray(iface.options) ? iface.options : [];
}

function interfaceArguments(iface) {
  return Array.isArray(iface.arguments) ? iface.arguments : [];
}

function interfaceSubcommands(iface) {
  return Array.isArray(iface.subcommands) ? iface.subcommands : [];
}

function isHelpToken(token) {
  return token === '--help' || token === '-h';
}

function printRootHelp() {
  console.log(`Usage: agentic-workspace <command> [options]`);
  console.log(`Supported generated commands: ${Array.from(supportedCommands).join(', ')}`);
  console.log('Weak-agent routing: allowed-mutation-with-review');
  console.log('TypeScript CLI boundary: generated parser, validation, and command execution are Node/TypeScript only.');
  console.log('Recovery: use a supported generated command or inspect the generated command contract.');
}

function printInterfaceHelp(path, iface) {
  const argumentNames = interfaceArguments(iface).map((argument) => argument.nargs === '?' ? `[${argument.name}]` : `<${argument.name}>`);
  const hasSubcommands = interfaceSubcommands(iface).length > 0;
  const subcommandSuffix = hasSubcommands ? ' <subcommand>' : '';
  const argumentSuffix = argumentNames.length ? ` ${argumentNames.join(' ')}` : '';
  console.log(`Usage: ${path.join(' ')}${subcommandSuffix} [options]${argumentSuffix}`);
  if (iface.help) console.log(String(iface.help));
  const options = interfaceOptions(iface);
  if (options.length) {
    console.log('Options:');
    for (const option of options) {
      const choices = Array.isArray(option.choices) ? ` choices=${option.choices.join('|')}` : '';
      const required = option.required === true ? ' required' : '';
      console.log(`  ${optionFlags(option).join(', ')}${required}${choices}  ${option.help ?? ''}`);
    }
  }
  const subcommands = interfaceSubcommands(iface);
  if (subcommands.length) {
    console.log('Subcommands:');
    for (const subcommand of subcommands) {
      console.log(`  ${subcommand.name}  ${subcommand.help ?? ''}`);
    }
  }
}

const generatedProgram = "agentic-workspace";

function authoritativeInterface(path) {
  let current = commandDefinitionByName.get(path[0])?.interface;
  for (const token of path.slice(1)) {
    current = interfaceSubcommands(current).find((candidate) => candidate.name === token);
  }
  return current;
}

function canonicalRecovery(path, unknown, replacement) {
  const candidatePath = [...path, replacement];
  if (interfaceRequiresHelp(authoritativeInterface(candidatePath))) return [generatedProgram, ...candidatePath, '--help'].map(shellQuote).join(' ');
  let remaining = argv.slice(path.length);
  while (path.length && path.every((token, index) => remaining[index] === token)) remaining = remaining.slice(path.length);
  remaining = remaining.map((token) => token === unknown ? replacement : token);
  return [generatedProgram, ...path, ...remaining].map(shellQuote).join(' ');
}

function shellQuote(token) {
  const value = String(token);
  return /^[A-Za-z0-9_@%+=:,./-]+$/.test(value) ? value : `'${value.replace(/'/g, `'"'"'`)}'`;
}

function normalizedCommandTokens(tokens, path) {
  let remaining = [...tokens];
  while (path.length && path.every((token, index) => remaining[index] === token)) remaining = remaining.slice(path.length);
  return remaining;
}

function interfaceRequiresHelp(iface) {
  if (!iface) return false;
  if (interfaceSubcommands(iface).length && iface.subcommands_required !== false) return true;
  if (interfaceArguments(iface).some((argument) => argument.nargs !== '?' && !Object.prototype.hasOwnProperty.call(argument, 'default'))) return true;
  return interfaceOptions(iface).some((option) => option.required === true);
}

function closestAuthoritativeChoice(token, choices) {
  if (!token || !choices.length) return '';
  const distance = (left, right) => {
    const rows = Array.from({ length: left.length + 1 }, (_, index) => [index]);
    for (let column = 0; column <= right.length; column += 1) rows[0][column] = column;
    for (let row = 1; row <= left.length; row += 1) {
      for (let column = 1; column <= right.length; column += 1) {
        rows[row][column] = left[row - 1] === right[column - 1]
          ? rows[row - 1][column - 1]
          : 1 + Math.min(rows[row - 1][column], rows[row][column - 1], rows[row - 1][column - 1]);
      }
    }
    return rows[left.length][right.length];
  };
  const subsequence = (left, right) => {
    const rows = Array.from({ length: left.length + 1 }, () => Array(right.length + 1).fill(0));
    for (let row = 1; row <= left.length; row += 1) {
      for (let column = 1; column <= right.length; column += 1) {
        rows[row][column] = left[row - 1] === right[column - 1]
          ? rows[row - 1][column - 1] + 1
          : Math.max(rows[row - 1][column], rows[row][column - 1]);
      }
    }
    return rows[left.length][right.length];
  };
  const best = choices.reduce((current, candidate) => {
    const candidateDistance = distance(token, candidate);
    const currentDistance = distance(token, current);
    return candidateDistance < currentDistance || (candidateDistance === currentDistance && subsequence(token, candidate) > subsequence(token, current)) ? candidate : current;
  }, choices[0]);
  const similarity = 1 - distance(token, best) / Math.max(token.length, best.length, 1);
  return similarity >= 0.55 ? best : '';
}

function failValidation(message, path = []) {
  const unknown = /^unknown command ([^ ]+)/.exec(message)?.[1] ?? '';
  const choices = path.length
    ? interfaceSubcommands(authoritativeInterface(path)).map((candidate) => candidate.name)
    : commandDefinitions.map((definition) => definition.name);
  const suggestion = unknown ? closestAuthoritativeChoice(unknown, choices) : '';
  const suggestedCommand = suggestion ? canonicalRecovery(path, unknown, suggestion) : '';
  const payload = {
    kind: `${generatedProgram}/retryable-cli-error/v1`,
    exit_status: 2,
    failure_class: unknown ? 'invalid-command' : 'usage-error',
    safe_to_retry: Boolean(suggestedCommand) || !unknown,
    message,
    suggested_command: suggestedCommand,
    alternatives: [],
  };
  if (argv.includes('--format') && argv[argv.indexOf('--format') + 1] === 'json') {
    console.log(JSON.stringify(payload, null, 2));
  } else {
    console.error(`TypeScript CLI validation failed: ${message}`);
    if (suggestedCommand) console.error(`Did you mean: ${suggestedCommand}`);
    console.error(`Recovery: run ${generatedProgram} --help and choose a supported generated command or valid option.`);
  }
  process.exit(2);
}

function validateChoice(spec, value, label) {
  if (Array.isArray(spec.choices) && !spec.choices.includes(value)) {
    failValidation(`${label} must be one of: ${spec.choices.join(', ')}`);
  }
  if (spec.type === 'integer' && !/^-?\d+$/.test(value)) {
    failValidation(`${label} must be an integer`);
  }
}

function optionByFlag(iface, flag) {
  return interfaceOptions(iface).find((option) => optionFlags(option).includes(flag));
}

function consumeOption(iface, option, tokens, index, seenOptions) {
  const optionName = option.name ?? optionFlags(option)[0];
  if (optionName) seenOptions.add(optionName);
  if (option.action === 'store_true') return index + 1;
  if (option.action === 'append') {
    if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) {
      failValidation(`${optionFlags(option)[0]} requires a value`);
    }
    const value = String(tokens[index + 1]);
    validateChoice(option, value, optionFlags(option)[0]);
    return index + 2;
  }
  if (option.nargs === '*') {
    let cursor = index + 1;
    while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {
      validateChoice(option, String(tokens[cursor]), optionFlags(option)[0]);
      cursor += 1;
    }
    return cursor;
  }
  if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) {
    failValidation(`${optionFlags(option)[0]} requires a value`);
  }
  const value = String(tokens[index + 1]);
  validateChoice(option, value, optionFlags(option)[0]);
  return index + 2;
}

function validateInterface(iface, tokens, path) {
  const seenOptions = new Set();
  const positional = [];
  let index = 0;
  while (index < tokens.length) {
    const token = String(tokens[index]);
    if (isHelpToken(token)) {
      printInterfaceHelp(path, iface);
      process.exit(0);
    }
    if (token.startsWith('-')) {
      const option = optionByFlag(iface, token);
      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);
      index = consumeOption(iface, option, tokens, index, seenOptions);
      continue;
    }
    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);
    if (subcommand) {
      validateInterface(subcommand, tokens.slice(index + 1), [...path, token]);
      return;
    }
    if (interfaceSubcommands(iface).length) failValidation(`unknown command ${token} for ${path.join(' ')}`, path);
    positional.push(token);
    index += 1;
  }
  for (const option of interfaceOptions(iface)) {
    const optionName = option.name ?? optionFlags(option)[0];
    if (option.required === true && optionName && !seenOptions.has(optionName)) {
      failValidation(`missing required option ${optionFlags(option)[0]} for ${path.join(' ')}`);
    }
  }
  const positionalSpecs = interfaceArguments(iface);
  const requiredPositionals = positionalSpecs.filter((argument) => argument.nargs !== '?' && argument.default === undefined);
  if (positional.length < requiredPositionals.length) {
    failValidation(`missing required argument for ${path.join(' ')}`);
  }
  if (positional.length > positionalSpecs.length) {
    failValidation(`unexpected argument ${positional[positionalSpecs.length]} for ${path.join(' ')}`);
  }
  positional.forEach((value, position) => validateChoice(positionalSpecs[position] ?? {}, value, positionalSpecs[position]?.name ?? 'argument'));
  if (interfaceSubcommands(iface).length && iface.subcommands_required !== false && positional.length === 0) {
    failValidation(`missing subcommand for ${path.join(' ')}`);
  }
}

function optionDefault(option) {
  if (Object.prototype.hasOwnProperty.call(option, 'default')) return option.default;
  if (option.action === 'store_true') return false;
  if (option.action === 'append') return [];
  if (option.nargs === '*') return [];
  return undefined;
}

function initialValues(iface) {
  const values = {};
  for (const option of interfaceOptions(iface)) {
    const optionName = option.name ?? optionFlags(option)[0];
    if (!optionName) continue;
    const defaultValue = optionDefault(option);
    if (defaultValue !== undefined) values[optionName] = Array.isArray(defaultValue) ? [...defaultValue] : defaultValue;
  }
  return values;
}

function optionValue(option, token) {
  const value = String(token);
  return option.type === 'integer' ? Number(value) : value;
}

function argumentValue(argument, token) {
  const value = String(token);
  return argument.type === 'integer' ? Number(value) : value;
}

function parseInvocation(definition, tokens, path) {
  const iface = definition.interface;
  const values = initialValues(iface);
  const positional = [];
  let index = 0;
  while (index < tokens.length) {
    const token = String(tokens[index]);
    if (isHelpToken(token)) {
      printInterfaceHelp(path, iface);
      process.exit(0);
    }
    if (token.startsWith('-')) {
      const option = optionByFlag(iface, token);
      if (!option) failValidation(`unknown option ${token} for ${path.join(' ')}`);
      const optionName = option.name ?? optionFlags(option)[0];
      if (option.action === 'store_true') {
        values[optionName] = true;
        index += 1;
        continue;
      }
      if (option.action === 'append') {
        if (index + 1 >= tokens.length || isHelpToken(tokens[index + 1])) failValidation(`${optionFlags(option)[0]} requires a value`);
        if (!Array.isArray(values[optionName])) values[optionName] = [];
        values[optionName].push(optionValue(option, tokens[index + 1]));
        index += 2;
        continue;
      }
      if (option.nargs === '*') {
        const collected = [];
        let cursor = index + 1;
        while (cursor < tokens.length && !String(tokens[cursor]).startsWith('-')) {
          collected.push(optionValue(option, tokens[cursor]));
          cursor += 1;
        }
        values[optionName] = collected;
        index = cursor;
        continue;
      }
      values[optionName] = optionValue(option, tokens[index + 1]);
      index += 2;
      continue;
    }
    const subcommand = interfaceSubcommands(iface).find((candidate) => candidate.name === token);
    if (subcommand) {
      const nested = parseInvocation({ interface: subcommand, operation_ref: subcommand.operation_ref ?? definition.operation_ref }, tokens.slice(index + 1), [...path, token]);
      const parentDefaults = initialValues(iface);
      for (const [name, value] of Object.entries(values)) {
        if (JSON.stringify(value) !== JSON.stringify(parentDefaults[name])) nested.values[name] = value;
      }
      if (iface.subcommand_dest) nested.values[iface.subcommand_dest] = token;
      return nested;
    }
    if (interfaceSubcommands(iface).length) failValidation(`unknown command ${token} for ${path.join(' ')}`, path);
    positional.push(token);
    index += 1;
  }
  interfaceArguments(iface).forEach((argument, position) => {
    if (position < positional.length) values[argument.name] = argumentValue(argument, positional[position]);
    else if (Object.prototype.hasOwnProperty.call(argument, 'default')) values[argument.name] = argument.default;
  });
  values._command_path = path;
  return { values, operationRef: definition.operation_ref ?? iface.operation_ref ?? null };
}

function runNativeOperation(operationId, operationPath, values) {
  if (!nativeOperationIds.has(operationId)) {
    console.error(`Unsupported native TypeScript operation: ${operationId}`);
    return 2;
  }
  return runGeneratedOperation({ operationId, operationPath, values });
}

function maybeRunNativeOperation() {
  const invocation = parseInvocation(commandDefinitionByName.get(command), normalizedCommandTokens(argv.slice(1), [command]), [command]);
  const operationId = invocation.operationRef?.id;
  const operationPath = invocation.operationRef?.path;
  if (invocation.values.strict_preflight && !invocation.values.preflight_token) {
    console.error("Strict preflight gate is enabled. Provide --preflight-token from 'agentic-workspace preflight --format json'.");
    process.exit(2);
  }
  try {
    const nativeStatus = runNativeOperation(operationId, operationPath, invocation.values);
    process.exit(nativeStatus);
  } catch (error) {
    console.error(`TypeScript native runtime failed: ${error.message}`);
    console.error('Recovery: run agentic-workspace --help and inspect the generated command contract.');
    process.exit(1);
  }
}

if (!command || command === '--help' || command === '-h') {
  printRootHelp();
  process.exit(0);
}

if (!supportedCommands.has(command)) {
  failValidation(`unknown command ${command}`, []);
}

validateInterface(commandByName.get(command), normalizedCommandTokens(argv.slice(1), [command]), [command]);

maybeRunNativeOperation();
