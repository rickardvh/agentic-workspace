---
name: populate
description: Populate newly created current-memory files conservatively after bootstrap installation.
---

# Populate

Use this skill after bootstrap installation when `memory/current/project-state.md` or `memory/current/task-context.md` was newly created.

## Workflow

1. Read:
   - `AGENTS.md`
   - `memory/index.md`
   - `.agentic-memory/WORKFLOW.md`
2. Inspect existing repo evidence:
   - top-level README or equivalent orientation docs
   - visible repo structure
   - obvious active work, if any
3. Populate `memory/current/project-state.md` conservatively.
4. Populate `memory/current/task-context.md` only when there is clearly active work worth preserving across sessions.
5. Keep both notes short and factual.
6. When populate work is complete, prefer `agentic-memory-bootstrap bootstrap-cleanup --target <repo>` if no more bootstrap work remains.

## Guardrails

- Use only existing repo docs and visible repo state.
- Do not invent subsystem notes, invariants, or runbooks with weak evidence.
- Do not turn `project-state.md` into a task list.
- Do not turn `task-context.md` into a plan, journal, or backlog.

## Typical outputs

- a populated `memory/current/project-state.md`
- an optional populated `memory/current/task-context.md`
- a follow-up to `bootstrap-cleanup` when bootstrap work is complete
