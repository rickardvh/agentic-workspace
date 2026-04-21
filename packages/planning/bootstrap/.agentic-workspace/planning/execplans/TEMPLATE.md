# Plan Title

Use this template for an active plan in `.agentic-workspace/planning/execplans/`. Move the file into
`.agentic-workspace/planning/execplans/archive/` once it is completed and no longer affects future execution.
Before archiving, set `## Active Milestone` `Status` to `completed` and fill the `## Proof Report`, `## Intent Satisfaction`, and `## Closure Check` sections with the closure evidence.
Prefer a feature-scoped file over expanding a shared hot plan, and keep headings stable so concurrent edits merge cleanly.
Prefer replacing resolved status lines instead of appending pass-by-pass history, and do not add retrospective sections such as `Added In This Pass`.
This file is a thin human view over the canonical `planning_record` surfaced by `agentic-workspace summary --format json`; use the summary first when you need the compact active state.

## Goal

-

## Non-Goals

-

## Machine-Readable Contract

```yaml
# This section is for high-efficiency agentic parsing. 
# Keep it in sync with the prose sections below.
intent:
  outcome: ""
  constraints: ""
  latitude: ""
  escalation: ""
execution:
  milestone: ""
  status: ""
  next_step: ""
  proof: ""
scope:
  touched: []
  invariants: []
```

## Intent Continuity

- Larger intended outcome:
- This slice completes the larger intended outcome:
- Continuation surface:
- Parent lane:

Use `none` only when this slice actually completes the larger intended outcome.
If the larger intended outcome is still unfinished, point `Continuation surface` at the checked-in surface that now owns follow-through.
Use `Parent lane` when the current chunk belongs to a roadmap lane and later agents should be able to recover that larger queue context from summary/report output without rereading roadmap prose.

## Required Continuation

- Required follow-on for the larger intended outcome:
- Owner surface:
- Activation trigger:

Use `no` / `none` only when this slice actually finishes the larger intended outcome.
If required follow-on remains, record its checked-in owner and what should cause activation.

## Iterative Follow-Through

- What this slice enabled:
- Intentionally deferred:
- Discovered implications:
- Proof achieved now:
- Validation still needed:
- Next likely slice:

Use this section when the slice is expected to stop before the broader goal is complete or when the work is likely to surface new implications that the next iteration should not have to rediscover.
Keep it compact and carry-forward shaped.
Record what this slice changed about the broader line of work, not a backlog dump or a second drift log.

## Context Budget

- Live working set:
- Recoverable later:
- Externalize before shift:
- Tiny resumability note:
- Context-shift triggers:

Keep this section tiny.
It exists to distinguish what must stay mentally live now from what can be reloaded later and from the residue that must be externalized before a context shift.
Do not turn it into a broad notebook or second memory surface.

## Delegated Judgment

- Requested outcome:
- Hard constraints:
- Agent may decide locally:
- Escalate when:

Use `none` only when the slice is so local that delegated-judgment framing would add no value.
Otherwise keep this section compact and specific so later contributors do not have to reconstruct the intended end state, allowed local latitude, or escalation triggers from chat residue.

## Active Milestone

- Status:
- Scope:
- Ready:
- Blocked:
- optional_deps:

Keep one active milestone by default.
Keep branch-local progress, blockers, and next-step state here rather than in durable docs or broad summaries.

## Immediate Next Action

-

Keep exactly one immediate action by default; avoid multi-step mini-plans here.
Replace stale immediate-action text when the next step changes instead of preserving old actions as history.

## Blockers

- None.

## Touched Paths

-

Keep this as a scope guard, not a broad file inventory.
Avoid large hand-maintained tables in active plans; compact bullets are easier to merge.

## Invariants

-

Keep invariants contract-shaped and brief.

## Contract Decisions To Freeze

-

Use this section when the slice is primarily deciding product shape, schema, or policy rather than implementing it.
Record only the decisions that the next implementation tranche must be able to trust without reopening debate.
Omit the section for straightforward implementation-only slices.

## Open Questions To Close

-

Use this section when unresolved contract questions still block safe implementation.
List only the questions this slice must answer; move optional future ideas to `roadmap` in `.agentic-workspace/planning/state.toml` or canonical docs instead.
Omit the section when no implementation-blocking questions remain.

## Validation Commands

-

If the slice renames, moves, retires, or refactors a named surface, include a cheap stale-reference sweep here as part of closure proof.
Prefer a narrow search such as `rg old-surface-name` or the relevant planning checker over broad rereads.

## Required Tools

- None.

Use this section when the plan depends on a capability that a weaker or differently provisioned agent might not have.
List only the concrete tools or capability surfaces that the task must have before execution starts.
Keep the first slice advisory: if a required tool is unavailable, stop or escalate instead of attempting an impossible substitute.

## Completion Criteria

-

## Proof Report

- Validation proof (logs, command output, or screenshots):
- Proof achieved now:
- Evidence for "Proof achieved" state:

## Intent Satisfaction

- Original intent:
- Was original intent fully satisfied?:
- Evidence of intent satisfaction:
- Unsolved intent passed to:

## Closure Check

- Slice status:
- Larger-intent status:
- Closure decision:
- Why this decision is honest:
- Evidence carried forward:
- Reopen trigger:

Use `archive-and-close` only when the larger intended outcome is actually satisfied.
Use `archive-but-keep-lane-open` when the slice is complete but required continuation remains in another checked-in owner.
Make the closure decision explicit enough that later contributors do not have to infer it from chat or issue prose.

## Execution Summary

- Outcome delivered:
- Validation confirmed:
- Follow-on routed to:
- Knowledge promoted (Memory/Docs/Config):
- Resume from:

Keep this compact and completion-shaped.
Before archiving a completed plan, replace placeholders with the durable summary a later contributor should not have to reconstruct from chat or drift prose.
Use `Iterative Follow-Through` to preserve deferred work and discovered implications; use `Execution Summary` to record the bounded slice outcome once this plan stops.

## Drift Log

- 2026-01-01: Initial plan created.

Keep drift entries short and decision-shaped; archive completed history instead of accumulating logs.
Completed plans should leave the active path quickly instead of becoming long-lived status records.
