# Memory Index

## Purpose

- `.agentic-workspace/memory/repo/` is the anti-rediscovery layer for durable repo knowledge.
- It is not a task tracker, issue mirror, execution log, or broad fallback handbook.
- Checked-in repo docs remain the canonical documentation layer.
- Active work belongs in the repository's planning, issue, status, or local scratch surface.
- Load only notes relevant to the task at hand.
- Use `.agentic-workspace/memory/repo/manifest.toml` as the machine-readable routing and freshness companion when it exists.

For shared memory policy, note hygiene, and ownership rules, read `.agentic-workspace/memory/WORKFLOW.md` instead of expanding this index.

## Task routing

Prefer the smallest bundle that still covers the touched surface.

- Start from this file.
- Use touched files, modules, commands, or explicit user surfaces to choose relevant notes.
- Load at most a few route-matched notes unless the task clearly justifies more.
- Treat `.agentic-workspace/memory/repo/current/` as optional routing calibration or migration residue, not active state.
- Create repo-specific notes only from local evidence in the target repository.

## Starter templates

- `.agentic-workspace/memory/repo/templates/memory-note.template.md`
- `.agentic-workspace/memory/repo/templates/invariant.template.md`
- `.agentic-workspace/memory/repo/templates/runbook.template.md`

## One-home reminder

- `domains/` = subsystem context
- `decisions/` = durable rationale and accepted boundaries
- `runbooks/` = repeatable operator procedures
- `mistakes/` = recurring failure patterns
- `current/` = optional routing calibration only

Do not use this index as a second workflow guide or knowledge file.
