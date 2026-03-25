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
- Harden the product boundary between canonical checked-in docs and assistive memory so stable guidance does not drift into shadow documentation.

## Recent meaningful progress

- Repositioned `memory/current/project-state.md` as a compact overview note rather than a planning surface.
- Tightened the shared workflow guidance so current-state notes stay aggressively summary-shaped instead of ledger-like.
- Clarified that closed work should only move into durable notes when the detail is still hard to recover from code, docs, or tooling.
- Added a permanent checked-in `memory-upgrade` core skill under `memory/skills/` as the stable repo-local entrypoint for "upgrade memory".
- Repositioned bundled `bootstrap-upgrade` as the packaged implementation behind that checked-in entrypoint instead of the only normal upgrade surface.
- Added manifest-level canonicality and task-relevance metadata plus an opt-in doctor audit for core-doc ownership boundaries.

## Blockers

- None currently noted.

## High-level notes

- Optional local scratch conventions are outside the core bootstrap contract.
- `memory/current/project-state.md` is the overview note; `memory/current/task-context.md` is the current-work compression note.
- Current-state notes should stay short: current focus, recent meaningful progress, blockers, and a few high-value notes only.
- Closed transitions and operational residue belong in durable notes only when they still add hard-to-recover value.
- `memory/system/WORKFLOW.md` is now a compact policy shim rather than a workflow handbook.
- Normal upgrade intent should route through the checked-in `memory-upgrade` skill, which stays minimal and stable while the bundled implementation can evolve.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- The note starts to read like a ledger, backlog, tranche history, or changelog.
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
- `bootstrap/README.md`

## Last confirmed

2026-03-25 during canonical-doc boundary hardening
