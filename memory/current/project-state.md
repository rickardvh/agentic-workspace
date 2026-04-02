# Project State

## Status

Active

## Scope

- Lightweight current overview for `agentic-memory-bootstrap`.

## Applies to

- `AGENTS.md`
- `README.md`
- `memory/index.md`
- `.agentic-memory/SKILLS.md`
- `.agentic-memory/WORKFLOW.md`
- `.agentic-memory/VERSION.md`
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
- Make `memory/manifest.toml` plus the shipped memory skills the default routing and maintenance interface.
- Keep the managed `.agentic-memory/` surface clearly separate from repo-owned `memory/`.

## Recent meaningful progress

- Added a new `.agentic-memory/` managed-root model for bootstrap-managed files, plus explicit migration support for legacy installs.
- Shifted upgrade, install, and adopt flows onto the same `.agentic-memory/` ownership model.
- Tightened `doctor`, upgrade, and manifest behaviour so legacy-layout repos migrate cleanly and repo-owned notes stay separate.
- Brought the repo’s own managed files and checks back into sync with the payload.

## Blockers

- None currently noted.

## High-level notes

- `memory/current/project-state.md` is the overview note; `memory/current/task-context.md` is optional continuation compression only.
- Durable facts should have one primary home, with short references instead of repeated summaries.
- Route through `memory/index.md`, `memory/manifest.toml`, and the shipped memory skills before broad note reading.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- The note starts to read like a ledger, backlog, tranche history, or changelog.
- Shared workflow guidance drifts back into `AGENTS.md` instead of `.agentic-memory/WORKFLOW.md`.

## Verify

- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm `README.md`, `AGENTS.md`, and the relevant `.agentic-memory/` docs still exist and remain the correct orientation set.

## Verified against

- `AGENTS.md`
- `README.md`
- `memory/index.md`
- `.agentic-memory/SKILLS.md`
- `.agentic-memory/WORKFLOW.md`
- `.agentic-memory/VERSION.md`
- `bootstrap/README.md`

## Last confirmed

2026-04-02 during managed-root migration work
