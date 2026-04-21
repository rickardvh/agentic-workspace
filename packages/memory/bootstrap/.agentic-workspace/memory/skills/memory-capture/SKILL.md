---
name: memory-capture
description: Capture durable lessons into checked-in repository memory. Use when a task has revealed a reusable invariant, recurring failure, subsystem boundary, operator procedure, or other fact that should survive the current session and be written into the right memory note instead of left in chat or local scratch.
---

# Memory Capture

This is a bootstrap-managed core skill shipped with the payload under `.agentic-workspace/memory/skills/`. Add repo-specific sibling skills under `.agentic-workspace/memory/repo/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill to turn a solved issue or discovered rule into the smallest correct checked-in memory update.

It operates on durable memory files. It does not create a separate storage layer.

## Workflow

1. Read the repo's local contract:
   - `AGENTS.md`
   - `.agentic-workspace/memory/repo/index.md`
   - `.agentic-workspace/memory/SKILLS.md` when deciding whether a repo-specific skill should be created
2. Identify the durable lesson:
   - what fact should survive this task
   - why it is likely to matter again
   - which files, commands, or surfaces it applies to
3. Decide whether it belongs in memory at all.
   - Do not capture one-off troubleshooting steps, temporary task notes, or backlog state.
4. Choose the primary home:
   - `.agentic-workspace/memory/repo/domains/` for subsystem knowledge
   - `.agentic-workspace/memory/repo/invariants/` for things that must remain true
   - `.agentic-workspace/memory/repo/runbooks/` for durable operating procedures
   - `.agentic-workspace/memory/repo/mistakes/recurring-failures.md` for repeated failure patterns
   - `.agentic-workspace/memory/repo/decisions/` for longer-lived rationale when a README note is no longer enough
5. Prefer editing an existing note over creating a new one.
6. Update note metadata and routing in the same change:
   - `Status`
   - `Applies to`
   - `Load when`
   - `Review when`
   - `Failure signals`
   - `Verify`
   - `Last confirmed`
   - `.agentic-workspace/memory/repo/manifest.toml` when used
7. If the note set changed materially, update `.agentic-workspace/memory/repo/index.md`.
8. If the repeated procedure is repo-specific rather than a durable fact, create a new repo-specific checked-in skill under `.agentic-workspace/memory/repo/skills/` instead of growing this core skill.
9. Treat `.agentic-workspace/memory/WORKFLOW.md` as reference policy only when the capture touches the memory contract or policy boundary.
10. Update `.agentic-workspace/memory/repo/current/project-state.md` or `.agentic-workspace/memory/repo/current/task-context.md` only when the new memory changes current shared orientation.
11. If the lesson is better understood as friction than durable truth, record that with manifest metadata and prefer an upstream remediation target over training contributors to depend on an ever-growing note.

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
- an updated `.agentic-workspace/memory/repo/index.md` or `.agentic-workspace/memory/repo/manifest.toml` when routing changed
