---
name: planning-intake-upstream-task
description: Turn an externally tracked task into checked-in planning without making the upstream tracker the execution authority.
---

# Planning Intake Upstream Task

Planning Intake Upstream Task converts an upstream issue, ticket, or task into the repo's checked-in planning surfaces.

It exists to keep external trackers as intake sources while preserving execution authority inside `.agentic-workspace/planning/state.toml` and `docs/execplans/`.

## Use When

- a GitHub issue, Linear ticket, Jira task, Notion task, or internal task note should become checked-in planning
- the repo needs a tracker-agnostic intake path
- an agent should preserve source metadata without copying the whole upstream thread into planning

## Do Not Use When

- the task is already active and fully routed through `todo.active_items` plus an execplan
- the work is a bounded review pass rather than an accepted planning item
- the real need is durable subsystem knowledge rather than active or candidate planning

## Workflow

1. Read `AGENTS.md`, `.agentic-workspace/planning/state.toml`, and `docs/upstream-task-intake.md`.
2. Read the upstream task or issue that is being ingested.
3. Normalize it into a compact summary:
   - source system
   - source identifier or URL
   - title
   - problem summary
   - product-first reasoning when relevant
4. Decide the smallest correct routing target:
   - dismiss
   - `docs/reviews/`
   - `roadmap` in `.agentic-workspace/planning/state.toml`
   - `todo.active_items` in `.agentic-workspace/planning/state.toml`
   - `todo.active_items` plus `docs/execplans/`
5. Preserve the upstream source reference in the chosen planning surface.
6. Keep execution detail in checked-in planning, not in the upstream tracker.

## Output Expectations

Report:

- upstream source used
- chosen planning destination
- files updated
- whether the work stayed inactive or became active

If the task becomes active planned work, ensure the execplan includes an `## Intake Source` section with compact source metadata.

## Guardrails

- Keep the contract tracker-agnostic even when the current intake source is GitHub.
- Do not treat the upstream tracker as the source of truth after promotion.
- Do not paste full issue bodies into `roadmap`, `todo.active_items`, or execplans.
- Prefer one-paragraph normalized summaries over copied tracker prose.
