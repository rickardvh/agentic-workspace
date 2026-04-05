# Memory Index

## Purpose

- `/memory` is the durable repository memory layer for this repo.
- Planning remains primary for active execution state: `TODO.md`, active execplans, and `ROADMAP.md`.
- Use memory only for durable routed knowledge, current orientation, and compact continuation context.
- Start here only after identifying the task from the planning surface or explicit user request.
- If `memory/manifest.toml` exists, use it as the machine-readable routing and freshness companion to this file.
- Routing quality matters more than memory volume: good memory systems should help an agent read less, not more.

## Loading rule

- Do not load all of `/memory` by default.
- Start from `memory/index.md` plus the smallest relevant bundle below.
- Default to `memory/index.md` plus at most 2 additional notes unless the task clearly justifies more.
- Load `memory/current/project-state.md` or `memory/current/task-context.md` only when they materially reduce restart cost.
- Load `memory/current/routing-feedback.md` only when calibrating routing against a concrete missed-note or over-routing case.
- Load `.agentic-memory/WORKFLOW.md` only when the task touches memory, planning/memory boundaries, or bootstrap workflow policy.

## Common task bundles

- package or bootstrap orientation:
  `memory/current/project-state.md`
- planning-memory boundary change:
  `memory/current/project-state.md`
  `.agentic-memory/WORKFLOW.md`
  `memory/decisions/README.md`
- installer or packaged payload change:
  `memory/current/project-state.md`
  `memory/mistakes/recurring-failures.md`
- memory-system maintenance or routing calibration:
  `memory/current/project-state.md`
  `memory/current/routing-feedback.md`
  `.agentic-memory/WORKFLOW.md`

## Admission rule

Store only information that is likely to matter again and is expensive to re-derive from code or docs.

Good candidates:

- planning versus memory ownership boundaries
- recurring bootstrap mistakes
- durable installer contracts
- routing hints that save startup cost

Do not store:

- task lists
- backlog state
- milestone status
- execution logs
- one-off implementation chatter

If a recurring procedure is reusable but not itself durable repo knowledge, prefer a skill over a new memory note.

## One-home rule

- planning surfaces own active execution state
- `/memory` owns durable routed knowledge
- canonical docs own stable general guidance
- skills own repeatable operational workflows when prose would otherwise sprawl

Use short references instead of repeating the same guidance in multiple notes.

## Index compactness rule

`memory/index.md` is a routing layer, not a knowledge file.

Keep it short.
Do not summarise note contents beyond what is needed for routing.
Update this index in the same change when the memory structure changes.

## Repo notes

- This repo packages the planning bootstrap and is intentionally complementary to `agentic-memory`.
- The important durable boundary is that memory must not compete with planning for ownership of active work.
- If a memory note starts carrying execution detail, move that detail back to the planning surface and keep only the durable lesson.
