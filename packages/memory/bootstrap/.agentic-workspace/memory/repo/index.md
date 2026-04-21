# Memory Index

## Purpose

- `/memory` is the anti-rediscovery layer for durable repo knowledge and lightweight shared context.
- It is not a task tracker, issue mirror, or broad fallback handbook.
- Checked-in repo docs remain the canonical documentation layer.
- The repository planning/status surface remains the owner of active intent and sequencing.
- Read this file after identifying the work from the repository's active planning/status surface or the user's request.
- Load only the notes relevant to the task at hand.
- If `.agentic-workspace/memory/repo/manifest.toml` exists, use it as the machine-readable routing and freshness companion to this file.

For shared memory policy, note hygiene, and ownership rules, read `.agentic-workspace/memory/WORKFLOW.md` instead of expanding this index.

## Common task bundles

- ordinary-work first pull: `.agentic-workspace/memory/repo/index.md` first, then at most 2 additional route-matched durable notes; load `.agentic-workspace/memory/repo/current/project-state.md` only when re-orientation is genuinely useful
- current-state refresh: `.agentic-workspace/memory/repo/current/project-state.md` plus `.agentic-workspace/memory/repo/current/task-context.md` when needed
- live decision review: the active planning slice plus `.agentic-workspace/memory/repo/decisions/README.md`
- monorepo memory-package work: `.agentic-workspace/memory/repo/domains/memory-package-context.md` plus `.agentic-workspace/memory/repo/decisions/installed-system-consolidation-2026-04-05.md`
- monorepo planning-package work: `.agentic-workspace/memory/repo/domains/planning-package-context.md` plus `.agentic-workspace/memory/repo/decisions/installed-system-consolidation-2026-04-05.md`
- workspace ownership or package-boundary change: `.agentic-workspace/memory/repo/decisions/installed-system-consolidation-2026-04-05.md` plus `.agentic-workspace/memory/repo/decisions/workspace-orchestrator-ownership-ledger-2026-04-05.md`
- root check or CI routing change: the active planning slice plus `.agentic-workspace/memory/repo/current/project-state.md`

## Task routing

Prefer the smallest bundle that still covers the task surface.

- If touching `packages/memory/**`, load `.agentic-workspace/memory/repo/domains/memory-package-context.md`.
- If touching `packages/planning/**`, load `.agentic-workspace/memory/repo/domains/planning-package-context.md`.
- If touching root orchestration files, load the most relevant decision note plus the active planning slice when it exists.
- If calibrating routing quality, load `.agentic-workspace/memory/repo/current/routing-feedback.md`.

## Loading rule

- Do not load all of `/memory` by default.
- Start from the smallest useful working set.
- Default to `.agentic-workspace/memory/repo/index.md` plus at most 2 additional notes unless the task clearly justifies more.
- Treat that default bundle as the ordinary-work cheap path for durable understanding and repo-specific interpretive norms, not as a reason to read current-context notes by reflex.
- Load `.agentic-workspace/memory/repo/current/project-state.md` or `.agentic-workspace/memory/repo/current/task-context.md` only when they reduce re-orientation cost for the current task.
- Use touched files, modules, commands, or surfaces to decide which notes to load first.

## One-home reminder

- `domains/` = subsystem context
- `decisions/` = durable rationale and accepted boundaries
- `runbooks/` = repeatable operator procedures
- `mistakes/` = recurring failure patterns
- `current/` = lightweight re-orientation only

Do not use this index as a second workflow guide or knowledge file.
