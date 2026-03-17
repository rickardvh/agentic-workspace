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

- Keep the bootstrap payload and installer aligned with the memory-only, task-system-agnostic product boundary, with current-task compression living in checked-in memory rather than local scratch.

## Recent meaningful progress

- Removed task-management guidance from the core payload and installer.
- Repositioned `memory/current/project-state.md` as the overview note rather than a planning surface.
- Reduced the shipped skill set to memory and bootstrap maintenance workflows.
- Removed repo-local Beads and task-tracking expectations from this source repository.
- Promoted `memory/current/task-context.md` as the checked-in current-work compression note.

## Blockers

- None currently noted.

## High-level notes

- Optional local scratch conventions are outside the core bootstrap contract.
- `memory/current/project-state.md` is the overview note; `memory/current/task-context.md` is the current-work compression note.

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

2026-03-17 during local repo cleanup after the memory-only boundary refactor
