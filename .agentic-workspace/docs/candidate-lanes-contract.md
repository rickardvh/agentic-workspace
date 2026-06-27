# Candidate Lanes Contract

The `roadmap` section in `.agentic-workspace/planning/state.toml` stays the single planning-managed surface for inactive future work. Its surface shape and lifecycle are owned by the Planning module; the accepted candidate work recorded inside it is repo-owned planning content.
When a flat candidate bullet is too weak, use a native candidate lane inside that same file instead of inventing ad hoc queue prose or a second backlog file.

## Purpose

Candidate lanes preserve grouped, ordered, promotable deferred work without activating it.

Use a lane when you need to keep:

- one broader intended outcome
- related issues or references
- an explicit relative order
- a promotion trigger
- a suggested first bounded slice

Do not use a lane for:

- active execution state
- milestone sequencing
- broad product-management bookkeeping
- durable technical memory

## Sequential Execution

When a user asks to implement several ordered lanes, keep the lane boundary intact:

1. Inspect the ordered candidate lanes from `agentic-workspace summary --format json`.
2. Promote the next lane only.
3. Create one or more execplans scoped to that lane.
4. Implement, prove, close, and archive the lane-scoped slice or slices.
5. Return to the roadmap for the next lane.

Do not create one combined execplan for unrelated lanes. A lane is the broader intent owner; execplans are bounded implementation slices under one lane.

For a new lane or major stacked PR group, prefer a fresh session seeded by the lane refs and a compact digest. Keep long shaping in issue comments, docs, or review artifacts; chat should carry current decisions, not durable lane storage.

## Shape

Keep candidate lanes under `roadmap.lanes` in `.agentic-workspace/planning/state.toml`.

Each lane should be one top-level bullet with compact indented fields:

```md
## Candidate Lanes

- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: second
  Issues: #96, #97, #98, #99, #100
  Outcome: make Memory cheaper to trust, inspect, and clean up.
  Why later: wait until the current planning slice lands.
  Promotion signal: promote when the current planning slice completes.
  Suggested first slice: start with evidence-backed note trust states.
```

## Required Fields

- `Lane`
- `ID`
- `Priority`
- `Outcome`
- `Promotion signal`
- `Suggested first slice`

## Optional Fields

- `Issues`
- `Why now`
- `Why later`

Use either `Why now` or `Why later` as the compact reason field.

## Rules

- Keep order meaningful; earlier lanes are higher priority unless stated otherwise.
- Keep each field compact and promotion-shaped.
- Keep active execution detail and near-term same-thread queue items in `todo.active_items` and execplans, not here.
- Keep durable background knowledge in canonical docs or memory, not here.
- Prefer one lane per broader intended outcome rather than many tiny backlog bullets.
- Preserve sequential lane execution for ordered roadmap work; "first four lanes" means repeat the lane workflow four times, not one four-lane execplan.

## Machine-Readable Projection

`agentic-workspace summary --format json` exposes candidate lanes through `roadmap.candidate_lanes` and keeps a flattened `roadmap.candidates` compatibility view for older callers.

`agentic-workspace planning report --format json` may surface lane counts in module status, but active execution state still belongs to `planning_record`, `active_contract`, `resumable_contract`, and `hierarchy_contract`.
