#!/usr/bin/env node
// Generated runnable adapter.
// Source: src/agentic_workspace/contracts/command_package_ir.json
// Program: agentic-planning
// Regenerate with: uv run python scripts/generate/generate_command_packages.py
// DO NOT EDIT DIRECTLY.

import { writeSync } from 'node:fs';
import { runGeneratedOperation } from './runtime.mjs';

const supportedCommands = new Set(["adopt", "archive-plan", "close-item", "closeout", "create-review", "delegation-decision", "doctor", "handoff", "init", "install", "intake-artifact", "lane-activate", "lane-archive", "lane-close", "lane-create", "lane-promote", "list-files", "new-plan", "promote-to-plan", "prompt", "reconcile", "report", "status", "summary", "uninstall", "upgrade", "verify-payload"]);
const nativeOperationIds = new Set(["planning.adopt.lifecycle", "planning.archive-plan.lifecycle", "planning.close-item.lifecycle", "planning.closeout.lifecycle", "planning.create-review.lifecycle", "planning.delegation-decision.lifecycle", "planning.doctor.report", "planning.handoff.report", "planning.init.lifecycle", "planning.install.lifecycle", "planning.intake-artifact.lifecycle", "planning.lane-activate.lifecycle", "planning.lane-archive.lifecycle", "planning.lane-close.lifecycle", "planning.lane-create.lifecycle", "planning.lane-promote.lifecycle", "planning.list-files.report", "planning.new-plan.lifecycle", "planning.promote-to-plan.lifecycle", "planning.prompt.render", "planning.reconcile.report", "planning.report.report", "planning.status.report", "planning.summary.report", "planning.uninstall.lifecycle", "planning.upgrade.lifecycle", "planning.verify-payload.report"]);
const commandDefinitions = [
  {
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
    "name": "adopt",
    "operation_ref": {
      "id": "planning.adopt.lifecycle",
      "path": "operations/planning.adopt.lifecycle.json"
    }
  },
  {
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
    "name": "archive-plan",
    "operation_ref": {
      "id": "planning.archive-plan.lifecycle",
      "path": "operations/planning.archive-plan.lifecycle.json"
    }
  },
  {
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
    "name": "closeout",
    "operation_ref": {
      "id": "planning.closeout.lifecycle",
      "path": "operations/planning.closeout.lifecycle.json"
    }
  },
  {
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
    "name": "close-item",
    "operation_ref": {
      "id": "planning.close-item.lifecycle",
      "path": "operations/planning.close-item.lifecycle.json"
    }
  },
  {
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
    "name": "create-review",
    "operation_ref": {
      "id": "planning.create-review.lifecycle",
      "path": "operations/planning.create-review.lifecycle.json"
    }
  },
  {
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
    "name": "delegation-decision",
    "operation_ref": {
      "id": "planning.delegation-decision.lifecycle",
      "path": "operations/planning.delegation-decision.lifecycle.json"
    }
  },
  {
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
    "name": "doctor",
    "operation_ref": {
      "id": "planning.doctor.report",
      "path": "operations/planning.doctor.report.json"
    }
  },
  {
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
    "name": "handoff",
    "operation_ref": {
      "id": "planning.handoff.report",
      "path": "operations/planning.handoff.report.json"
    }
  },
  {
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
    "name": "init",
    "operation_ref": {
      "id": "planning.init.lifecycle",
      "path": "operations/planning.init.lifecycle.json"
    }
  },
  {
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
    "name": "install",
    "operation_ref": {
      "id": "planning.install.lifecycle",
      "path": "operations/planning.install.lifecycle.json"
    }
  },
  {
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
    "name": "list-files",
    "operation_ref": {
      "id": "planning.list-files.report",
      "path": "operations/planning.list-files.report.json"
    }
  },
  {
    "interface": {
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
          "flags": [
            "--target"
          ],
          "help": "Target repository path. Defaults to the current directory.",
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
    "name": "lane-create",
    "operation_ref": {
      "id": "planning.lane-create.lifecycle",
      "path": "operations/planning.lane-create.lifecycle.json"
    }
  },
  {
    "interface": {
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
          "help": "Target repository path. Defaults to the current directory.",
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
    "name": "lane-promote",
    "operation_ref": {
      "id": "planning.lane-promote.lifecycle",
      "path": "operations/planning.lane-promote.lifecycle.json"
    }
  },
  {
    "interface": {
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
          "help": "Target repository path. Defaults to the current directory.",
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
    "name": "lane-activate",
    "operation_ref": {
      "id": "planning.lane-activate.lifecycle",
      "path": "operations/planning.lane-activate.lifecycle.json"
    }
  },
  {
    "interface": {
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
          "help": "Target repository path. Defaults to the current directory.",
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
    "name": "lane-close",
    "operation_ref": {
      "id": "planning.lane-close.lifecycle",
      "path": "operations/planning.lane-close.lifecycle.json"
    }
  },
  {
    "interface": {
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
          "help": "Target repository path. Defaults to the current directory.",
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
    "name": "lane-archive",
    "operation_ref": {
      "id": "planning.lane-archive.lifecycle",
      "path": "operations/planning.lane-archive.lifecycle.json"
    }
  },
  {
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
    "name": "new-plan",
    "operation_ref": {
      "id": "planning.new-plan.lifecycle",
      "path": "operations/planning.new-plan.lifecycle.json"
    }
  },
  {
    "interface": {
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
          "help": "Target repository path. Defaults to the current directory.",
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
    "name": "intake-artifact",
    "operation_ref": {
      "id": "planning.intake-artifact.lifecycle",
      "path": "operations/planning.intake-artifact.lifecycle.json"
    }
  },
  {
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
    "name": "promote-to-plan",
    "operation_ref": {
      "id": "planning.promote-to-plan.lifecycle",
      "path": "operations/planning.promote-to-plan.lifecycle.json"
    }
  },
  {
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
    "name": "prompt",
    "operation_ref": {
      "id": "planning.prompt.render",
      "path": "operations/planning.prompt.render.json"
    }
  },
  {
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
    "name": "reconcile",
    "operation_ref": {
      "id": "planning.reconcile.report",
      "path": "operations/planning.reconcile.report.json"
    }
  },
  {
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
    "name": "report",
    "operation_ref": {
      "id": "planning.report.report",
      "path": "operations/planning.report.report.json"
    }
  },
  {
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
    "name": "status",
    "operation_ref": {
      "id": "planning.status.report",
      "path": "operations/planning.status.report.json"
    }
  },
  {
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
    "name": "summary",
    "operation_ref": {
      "id": "planning.summary.report",
      "path": "operations/planning.summary.report.json"
    }
  },
  {
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
    "name": "uninstall",
    "operation_ref": {
      "id": "planning.uninstall.lifecycle",
      "path": "operations/planning.uninstall.lifecycle.json"
    }
  },
  {
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
    "name": "upgrade",
    "operation_ref": {
      "id": "planning.upgrade.lifecycle",
      "path": "operations/planning.upgrade.lifecycle.json"
    }
  },
  {
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
    "name": "verify-payload",
    "operation_ref": {
      "id": "planning.verify-payload.report",
      "path": "operations/planning.verify-payload.report.json"
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
  console.log(`Usage: agentic-planning <command> [options]`);
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

function failValidation(message) {
  console.error(`TypeScript CLI validation failed: ${message}`);
  console.error('Recovery: run agentic-planning --help and choose a supported generated command or valid option.');
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
      if (iface.subcommand_dest) nested.values[iface.subcommand_dest] = token;
      return nested;
    }
    positional.push(token);
    index += 1;
  }
  interfaceArguments(iface).forEach((argument, position) => {
    if (position < positional.length) values[argument.name] = positional[position];
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
  const invocation = parseInvocation(commandDefinitionByName.get(command), argv.slice(1), [command]);
  const operationId = invocation.operationRef?.id;
  const operationPath = invocation.operationRef?.path;
  try {
    const nativeStatus = runNativeOperation(operationId, operationPath, invocation.values);
    process.exit(nativeStatus);
  } catch (error) {
    console.error(`TypeScript native runtime failed: ${error.message}`);
    console.error('Recovery: run agentic-planning --help and inspect the generated command contract.');
    process.exit(1);
  }
}

if (!command || command === '--help' || command === '-h') {
  printRootHelp();
  process.exit(0);
}

if (!supportedCommands.has(command)) {
  console.error(`Unsupported generated command: ${command}`);
  console.error('Recovery: run agentic-planning --help and choose one of the supported generated commands.');
  process.exit(2);
}

validateInterface(commandByName.get(command), argv.slice(1), [command]);

maybeRunNativeOperation();
