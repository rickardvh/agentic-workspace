---
name: populate
description: Populate newly created current-memory files conservatively after bootstrap installation.
---

# Populate

Use this skill after bootstrap installation when `.agentic-workspace/memory/repo/current/project-state.md` or `.agentic-workspace/memory/repo/current/task-context.md` was newly created.

## Workflow

1. Read:
   - `AGENTS.md`
   - `.agentic-workspace/memory/repo/index.md`
   - `.agentic-workspace/memory/WORKFLOW.md` only when the policy boundary is unclear
2. Inspect existing repo evidence:
   - top-level README or equivalent orientation docs
   - visible repo structure
   - obvious active work, if any
3. Populate `.agentic-workspace/memory/repo/current/project-state.md` conservatively.
4. Populate `.agentic-workspace/memory/repo/current/task-context.md` only when there is clearly active work worth preserving across sessions.
5. Keep both notes short and factual.
6. When populate work is complete, prefer `agentic-memory-bootstrap bootstrap-cleanup --target <repo>` if no more bootstrap work remains.

## Guardrails

- Use only existing repo docs and visible repo state.
- Do not invent subsystem notes, invariants, or runbooks with weak evidence.
- Do not turn `project-state.md` into a task list.
- Do not turn `task-context.md` into a plan, journal, backlog, or execution log.

## Typical outputs

- a populated `.agentic-workspace/memory/repo/current/project-state.md`
- an optional populated `.agentic-workspace/memory/repo/current/task-context.md`
- a follow-up to `bootstrap-cleanup` when bootstrap work is complete
