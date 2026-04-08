# Memory Index

## Purpose

- `/memory` is the durable repository memory layer.
- Checked-in repo docs remain the canonical documentation layer.
- Read this file after identifying the work from the repository's active planning/status surface or the user's request.
- Load only the notes relevant to the task at hand.
- If `memory/manifest.toml` exists, use it as the machine-readable routing and freshness companion to this file.

For shared memory policy, note hygiene, and ownership rules, read `.agentic-workspace/memory/WORKFLOW.md` instead of expanding this index.

## Common task bundles

- current-state refresh: `memory/current/project-state.md` plus `memory/current/task-context.md` when needed
- live decision review: `memory/current/active-decisions.md` plus `memory/decisions/README.md`
- monorepo memory-package work: `memory/domains/memory-package-context.md` plus `memory/current/active-decisions.md`
- monorepo planning-package work: `memory/domains/planning-package-context.md` plus `memory/current/active-decisions.md`
- workspace ownership or package-boundary change: `memory/decisions/installed-system-consolidation-2026-04-05.md` plus `memory/current/active-decisions.md`
- root check or CI routing change: `memory/current/active-decisions.md` plus `memory/current/project-state.md`

## Task routing

Prefer the smallest bundle that still covers the task surface.

- If touching `packages/memory/**`, load `memory/domains/memory-package-context.md`.
- If touching `packages/planning/**`, load `memory/domains/planning-package-context.md`.
- If touching root orchestration files, load `memory/current/active-decisions.md` and the most relevant decision note.
- If calibrating routing quality, load `memory/current/routing-feedback.md`.

## Loading rule

- Do not load all of `/memory` by default.
- Start from the smallest useful working set.
- Default to `memory/index.md` plus at most 2 additional notes unless the task clearly justifies more.
- Load `memory/current/project-state.md` or `memory/current/task-context.md` only when they reduce re-orientation cost for the current task.
- Use touched files, modules, commands, or surfaces to decide which notes to load first.

## One-home reminder

- `domains/` = subsystem context
- `decisions/` = durable rationale and accepted boundaries
- `runbooks/` = repeatable operator procedures
- `mistakes/` = recurring failure patterns
- `current/` = lightweight re-orientation only

Do not use this index as a second workflow guide or knowledge file.
