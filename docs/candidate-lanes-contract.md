# Candidate Lanes Contract

The `roadmap` section in `.agentic-workspace/planning/state.toml` stays the single module-managed surface for inactive future work.
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

## Machine-Readable Projection

`agentic-workspace summary --format json` exposes candidate lanes through `roadmap.candidate_lanes` and keeps a flattened `roadmap.candidates` compatibility view for older callers.

`agentic-planning-bootstrap report --format json` may surface lane counts in module status, but active execution state still belongs to `planning_record`, `active_contract`, `resumable_contract`, and `hierarchy_contract`.
