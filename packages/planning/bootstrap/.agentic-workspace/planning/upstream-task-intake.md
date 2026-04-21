# Upstream Task Intake

Canonical planning contract for turning externally tracked work into checked-in planning.

Use this when work begins in GitHub Issues, Linear, Jira, Notion, internal task docs, or another upstream tracker, but execution should happen from checked-in planning surfaces.

## Purpose

- keep external trackers as intake sources rather than execution authorities
- preserve enough upstream metadata for restart and auditability
- route accepted work into `.agentic-workspace/planning/state.toml` and `.agentic-workspace/planning/execplans/` cleanly
- stay neutral across trackers instead of baking GitHub-specific behavior into the planning contract

## Non-Goals

- Do not make any external tracker mandatory.
- Do not mirror full issue threads into checked-in docs.
- Do not turn planning into a bidirectional sync layer.
- Do not execute directly from an upstream issue once the work is accepted.

## Intake Flow

1. Read the upstream task.
2. Normalize the signal into a compact planning summary.
3. Decide the next state:
   - dismiss
   - bounded review artifact in `.agentic-workspace/planning/reviews/`
   - inactive candidate in `.agentic-workspace/planning/state.toml` (`roadmap`)
   - direct active task in `.agentic-workspace/planning/state.toml` (`todo.active_items`) when truly tiny
   - active work in `todo.active_items` plus `.agentic-workspace/planning/execplans/`
4. Preserve the upstream source reference in the promoted planning surface.
5. Execute from checked-in planning, not from the upstream tracker thread.

## Surface Ownership

- `.agentic-workspace/planning/upstream-task-intake.md` owns the intake rules.
- `.agentic-workspace/planning/reviews/` owns bounded review capture when the upstream signal needs analysis before planning.
- `roadmap` in `.agentic-workspace/planning/state.toml` owns inactive accepted candidates.
- `todo.active_items` in `.agentic-workspace/planning/state.toml` owns the active queue plus the smallest near-term same-thread follow-on that should not be lost.
- `.agentic-workspace/planning/execplans/` own active execution contracts and the detailed upstream intake record for active promoted work.

Do not use `todo.active_items` as the place to store upstream issue transcripts or detailed intake metadata.

## Minimum Metadata To Preserve

Preserve the smallest stable set that makes the work restartable:

- upstream system
- stable upstream identifier or URL
- upstream title or short label
- one-paragraph normalized problem summary
- triage decision
- product-first reasoning when the signal may imply package or contract work

Optional when it materially changes execution:

- capture date
- upstream status at capture time
- linked review artifact
- explicit reason for promoting directly to active work

## Canonical Placement

### Inactive accepted work

Use `roadmap` in `.agentic-workspace/planning/state.toml` for future candidates.

Keep the roadmap entry compact. Preserve the upstream source as one short clause instead of copying the whole issue body.

Example shape:

- Tracker-agnostic upstream task ingestion: define the intake contract for external tasks while keeping checked-in planning authoritative. Source: GitHub issue `#2`.

### Active work

When an upstream task becomes active planned work, keep the queue small in `todo.active_items` and preserve the source metadata in the execplan.
Use a near-term queued active item only when the next chunk is concrete enough to follow the active work soon; otherwise leave it inactive in `roadmap`.

Use an `## Intake Source` section in the execplan with compact fields such as:

- system
- id or URL
- title
- captured reason

The execplan may also include a short normalized summary when the upstream wording is too tracker-specific or too long.

### Tiny direct tasks

Only keep upstream-sourced work as a direct `todo.active_items` task when one coherent pass can finish it and the source reference fits cleanly inside the active-item row.

If the upstream context needs more than a short source cue, promote to an execplan and store the intake details there instead.

## Promotion Rules

- Dismiss when the upstream item is duplicate, weak, or out of scope.
- Use a review artifact when the signal is real but still needs bounded analysis before planning.
- Use `roadmap` in `.agentic-workspace/planning/state.toml` when the work is accepted but inactive.
- Use `todo.active_items` plus an execplan when the work is accepted and active.
- Prefer direct TODO execution only for truly small local work.

Promotion into active work should happen only through explicit maintainer choice, clear urgency, or a strong enough planning signal that the task is ready to execute from checked-in surfaces.
Promotion into planning at all should normally require measured friction, repeated failure, repeated dogfooding pain, or an explicit maintainer override rather than concept opportunity alone.

## Authority Rule

After promotion, the external tracker is no longer the execution authority.

The checked-in planning surfaces decide:

- what is active now
- what the bounded scope is
- what counts as done
- what validation is required

The upstream tracker remains a source reference and coordination surface only.

## Product-First Question

When an upstream task reports friction discovered in this repository, ask:

Could or should this have been found, prevented, or remediated by the product itself?

If yes, preserve that reasoning in the planning artifact so later work can prefer package or contract improvements over repo-local workaround guidance.

## Intake Guardrail

When an upstream task still reads mainly like an idea, potential enhancement, or nice-to-have concept rather than a response to measured friction or repeated failure, prefer dismissal or bounded review over adding it to planning.
