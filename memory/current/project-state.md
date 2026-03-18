# Project State

## Status

Active

## Scope

- Lightweight current overview for `agentic-memory-bootstrap`.

## Applies to

- `AGENTS.md`
- `README.md`
- `memory/index.md`
- `memory/system/SKILLS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `bootstrap/README.md`

## Load when

- Starting work and needing a short current overview.
- Returning to the repository after a break.

## Review when

- The product boundary changes.
- The current focus, recent meaningful progress, or blockers change materially.
- Main orientation docs move or change role.

## Current focus

- Keep the always-read surface small: `AGENTS.md` plus `memory/index.md` by default, with other docs loaded on demand.

## Recent meaningful progress

- Removed task-management guidance from the core payload and installer.
- Repositioned `memory/current/project-state.md` as the overview note rather than a planning surface.
- Shipped the first bundled product skill set for memory and bootstrap workflows.
- Removed repo-local Beads and task-tracking expectations from this source repository.
- Promoted `memory/current/task-context.md` as the checked-in current-work compression note.
- Added agent-facing memory ergonomics to the CLI for current-memory inspection, routing, sync suggestions, and payload verification.
- Clarified that the base system must remain understandable and maintainable even when skills are unavailable.
- Clarified that `skills/` is the product's bundled skills catalogue, not a separate source-repo-only layer.
- Added bundled `memory-capture`, `memory-refresh`, and `memory-router` skills alongside the existing hygiene and bootstrap skills.
- Added `bootstrap-populate` as the conservative post-adoption skill for filling new current-memory files from repo evidence.
- Shifted the product model toward bundled auto-discoverable skills, with manual installation only as fallback guidance.
- Trimmed `AGENTS.md`, `memory/system/WORKFLOW.md`, and `memory/index.md` toward a lower-token, skill-first operating surface.

## Blockers

- None currently noted.

## High-level notes

- Optional local scratch conventions are outside the core bootstrap contract.
- `memory/current/project-state.md` is the overview note; `memory/current/task-context.md` is the current-work compression note.
- Skills are the execution layer for repeatable memory workflows, not the storage layer for durable repo knowledge.
- The current bundled skill catalogue now covers hygiene, capture, refresh, routing, adoption, and upgrade workflows.
- `memory/system/WORKFLOW.md` is now a compact policy shim rather than a workflow handbook.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- Shared workflow guidance drifts back into `AGENTS.md` instead of `memory/system/WORKFLOW.md`.

## Verify

- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm `README.md`, `AGENTS.md`, and the relevant `memory/system/` docs still exist and remain the correct orientation set.

## Verified against

- `AGENTS.md`
- `README.md`
- `memory/index.md`
- `memory/system/SKILLS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `bootstrap/README.md`

## Last confirmed

2026-03-18 during token-saving workflow pass
