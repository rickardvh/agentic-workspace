# Plan Title

Use this template for an active plan in `docs/execplans/`. Move the file into
`docs/execplans/archive/` once it is completed and no longer affects future execution.
Before archiving, set `## Active Milestone` `Status` to `completed`.
Prefer a feature-scoped file over expanding a shared hot plan, and keep headings stable so concurrent edits merge cleanly.
Prefer replacing resolved status lines instead of appending pass-by-pass history, and do not add retrospective sections such as `Added In This Pass`.

## Goal

-

## Non-Goals

-

## Intent Continuity

- Larger intended outcome:
- This slice completes the larger intended outcome:
- Continuation surface:

Use `none` only when this slice actually completes the larger intended outcome.
If the larger intended outcome is still unfinished, point `Continuation surface` at the checked-in surface that now owns follow-through.

## Required Continuation

- Required follow-on for the larger intended outcome:
- Owner surface:
- Activation trigger:

Use `no` / `none` only when this slice actually finishes the larger intended outcome.
If required follow-on remains, record its checked-in owner and what should cause activation.

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
List only the questions this slice must answer; move optional future ideas to `ROADMAP.md` or canonical docs instead.
Omit the section when no implementation-blocking questions remain.

## Validation Commands

-

## Completion Criteria

-

## Execution Summary

- Outcome delivered:
- Validation confirmed:
- Follow-on routed to:
- Resume from:
- Product improvement signal:

Keep this compact and completion-shaped.
If the slice exposed a repeatable product or workflow improvement, fill `Product improvement signal` with the smallest useful dogfood note instead of leaving that signal only in chat.
Before archiving a completed plan, replace placeholders with the durable summary a later contributor should not have to reconstruct from chat or drift prose.

## Drift Log

- 2026-01-01: Initial plan created.

Keep drift entries short and decision-shaped; archive completed history instead of accumulating logs.
Completed plans should leave the active path quickly instead of becoming long-lived status records.
