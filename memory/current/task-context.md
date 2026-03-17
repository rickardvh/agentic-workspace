# Task Context

## Status

Active

## Scope

- Lightweight checked-in current-task context compression for `agentic-memory-bootstrap`.

## Applies to

- `AGENTS.md`
- `README.md`
- `memory/current/project-state.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `bootstrap/AGENTS.md`
- `bootstrap/README.md`

## Load when

- Continuing active work after a break.
- Re-orienting on the current change without re-reading the whole repo.

## Review when

- The active work changes materially.
- The active surfaces or key constraints change.
- The note no longer reduces re-orientation cost.

## Current focus

- Add `memory/current/task-context.md` to the shipped bootstrap contract and align the workflow docs, installer, and tests with that model.

## Active surfaces

- `bootstrap/AGENTS.md`
- `bootstrap/memory/current/task-context.md`
- `bootstrap/memory/index.md`
- `bootstrap/memory/system/WORKFLOW.md`
- `README.md`
- `memory/current/project-state.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `src/repo_memory_bootstrap/cli.py`
- `src/repo_memory_bootstrap/installer.py`
- `tests/test_installer.py`

## Key constraints

- Keep the product memory-only and task-system agnostic.
- `task-context.md` is a checked-in compression note, not a task list, detailed plan, or historical log.
- Do not reintroduce `TODO.md`, Beads, or `.agent-work/` as core contract surfaces.
- Update this repo's own installed memory version with the payload change.

## Relevant memory

- `memory/current/project-state.md`
- `memory/current/active-decisions.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `memory/system/UPGRADE.md`

## Notes

- The payload and source repo should both treat `task-context.md` as an optional but first-class current-memory note.
- Shared bootstrap docs must stop implying that `memory/current/active-decisions.md` is part of the installed baseline.

## Failure signals

- `task-context.md` starts acting like a backlog or implementation log.
- Shared docs refer to `active-decisions.md` as a mandatory installed note.
- Installer or tests miss the new file or fail to bump the contract version.

## Verify

- Confirm `task-context.md` appears in the packaged payload and installer previews.
- Confirm the shared workflow and index docs describe the overview/task-context split consistently.

## Last confirmed

2026-03-17 during task-context contract implementation
