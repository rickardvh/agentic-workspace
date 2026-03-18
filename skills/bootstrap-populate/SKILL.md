---
name: bootstrap-populate
description: Populate newly installed current-memory files conservatively after bootstrap adoption. Use when a repository has just gained `memory/current/project-state.md` or `memory/current/task-context.md` and the agent should fill them from existing repo docs and visible repo state without inventing deeper memory notes.
---

# Bootstrap Populate

Use this skill after bootstrap adoption to make the new current-memory files useful without expanding the memory tree speculatively.

It populates checked-in overview/context notes from existing repo evidence. It does not invent broad architecture memory.

## Workflow

1. Read the target repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
2. Inspect existing repo evidence:
   - top-level README or equivalent orientation docs
   - visible repo structure
   - recent active files or obvious current work, if any
3. Populate `memory/current/project-state.md` conservatively:
   - current focus
   - recent meaningful progress
   - blockers
   - a few high-level notes
4. Populate `memory/current/task-context.md` only if there is active work worth preserving across sessions.
   - yes: the repo shows a clearly active change, investigation, or ongoing implementation that another session would need to resume quickly
   - no: there is no obvious active work, or the current context would just repeat the overview note
5. Keep both notes short and factual.
6. If the repo clearly has durable material that should become deeper memory later, report it as a candidate follow-up instead of creating it automatically.
7. Run the memory freshness audit when available.

## Guardrails

- Use only existing repo docs and visible repo state.
- Do not invent subsystem notes, invariants, or runbooks with weak evidence.
- Do not turn `project-state.md` into a task list.
- Do not turn `task-context.md` into a plan, journal, or backlog.
- Leave the audit-clean starter note in place when there is no clear active work to capture.
- Prefer leaving a field brief over filling it with speculation.

## Typical outputs

- a populated `memory/current/project-state.md`
- an optional populated `memory/current/task-context.md`
- a short note about possible future memory candidates, if any
