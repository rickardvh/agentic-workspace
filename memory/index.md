# Memory Index

## Purpose

- `/memory` is the durable repository memory layer for this repo.
- Planning remains primary for active execution state: `TODO.md`, active execplans, and `ROADMAP.md`.
- Use memory only for durable routed knowledge, current orientation, and compact continuation context.
- Start here only after identifying the task from the planning surface or explicit user request.

## Loading rule

- Do not load all of `/memory` by default.
- Start from `memory/index.md` plus the smallest relevant bundle below.
- Load `memory/current/task-context.md` only when it materially reduces restart cost.
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

## One-home rule

- planning surfaces own active execution state
- `/memory` owns durable routed knowledge
- canonical docs own stable general guidance
- skills own repeatable operational workflows when prose would otherwise sprawl

## Repo notes

- This repo packages the planning bootstrap and is intentionally complementary to `agentic-memory`.
- The important durable boundary is that memory must not compete with planning for ownership of active work.
- If a memory note starts carrying execution detail, move that detail back to the planning surface and keep only the durable lesson.
