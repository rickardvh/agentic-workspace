---
name: memory-capture
description: Capture durable lessons into checked-in repository memory. Use when a task has revealed a reusable invariant, recurring failure, subsystem boundary, operator procedure, or other fact that should survive the current session and be written into the right memory note instead of left in chat or local scratch.
---

# Memory Capture

Use this skill to turn a solved issue or discovered rule into the smallest correct checked-in memory update.

It operates on durable memory files. It does not create a separate storage layer.

## Workflow

1. Read the repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
   - `memory/current/project-state.md` if present
   - `memory/current/task-context.md` if present
2. Identify the durable lesson:
   - what fact should survive this task
   - why it is likely to matter again
   - which files, commands, or surfaces it applies to
3. Decide whether it belongs in memory at all.
   - Do not capture one-off troubleshooting steps, temporary task notes, or backlog state.
4. Choose the primary home:
   - `memory/domains/` for subsystem knowledge
   - `memory/invariants/` for things that must remain true
   - `memory/runbooks/` for durable operating procedures
   - `memory/mistakes/recurring-failures.md` for repeated failure patterns
   - `memory/decisions/` for longer-lived rationale when a README note is no longer enough
5. Prefer editing an existing note over creating a new one.
6. Update note metadata and routing in the same change:
   - `Status`
   - `Applies to`
   - `Load when`
   - `Review when`
   - `Failure signals`
   - `Verify`
   - `Last confirmed`
7. If the note set changed materially, update `memory/index.md`.
8. Update `memory/current/project-state.md` or `memory/current/task-context.md` only when the new memory changes current shared orientation.

## Capture test

Capture the lesson only if most of these are true:

- another contributor could hit the same confusion or failure
- the fact affects future code changes, operations, or review
- the note will save future re-orientation time
- the information can be kept concise and verifiable

If not, leave it out of `/memory`.

## Guardrails

- Keep durable knowledge in checked-in files so the result stays visible in git.
- Do not create a new note when an existing note can be tightened instead.
- Do not put task state, backlog items, or one-off implementation history into memory.
- Mark uncertain claims `Needs verification` instead of presenting them as settled.
- Keep `project-state.md` and `task-context.md` short; they are shared orientation notes, not archives.

## Typical outputs

- an updated invariant, domain note, runbook, or recurring-failures note
- a new memory note when no suitable home exists
- refreshed note metadata and `Last confirmed`
- an updated `memory/index.md` when routing changed
