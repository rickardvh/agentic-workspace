# Active Decisions

## Status

Active

## Scope

- Current high-impact technical and operational decisions for `agentic-memory-bootstrap`.

## Applies to

- `bootstrap/`
- `README.md`
- `AGENTS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/SKILLS.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `src/repo_memory_bootstrap/cli.py`
- `src/repo_memory_bootstrap/installer.py`

## Load when

- Choosing implementation strategy across major subsystems.
- Deciding which source of truth to trust during a refactor.

## Review when

- Architecture boundaries change.
- Public interfaces or core operating modes change.

## Failure signals

- Conflicting plans reference different sources of truth.
- A change proposal depends on an unconfirmed default or stale assumption.

## Rule or lesson

- Record only the active decisions that materially affect implementation choices.
- Move mature, long-lived rationale into `memory/decisions/` when it no longer belongs in a current-orientation note.
- Keep repo-local scope and guardrails in `AGENTS.md`; keep reusable operating rules in `memory/system/WORKFLOW.md`.
- Keep skills optional and specialised; the core operating model must remain usable from checked-in docs alone.

## How to recognise it

- You are making a trade-off that affects multiple subsystems.
- You need to know which current boundary or contract is intentional.

## Verify

- Check the active architecture docs, contracts, or decision records referenced in `## Applies to`.
- Confirm that older decisions have been moved out if they are no longer current.

## Verified against

- `AGENTS.md`
- `bootstrap/README.md`
- `src/repo_memory_bootstrap/cli.py`
- `src/repo_memory_bootstrap/installer.py`
- `memory/system/SKILLS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `README.md`

## What to do

- Keep this file current and compact.
- Prefer one line per active decision unless more detail is required for safe implementation.

## Current decisions

- `bootstrap/` is the source of truth for installed payload files; packaging should mirror it rather than fork from it.
- Shared operating rules belong in `memory/system/WORKFLOW.md`; `AGENTS.md` should stay local, short, and repo-specific.
- The bootstrap product boundary is memory-only and task-system agnostic.
- `memory/current/project-state.md` is a lightweight overview file and must not become a task list.
- `memory/current/task-context.md` is the checked-in current-work compression note and must not become a backlog, detailed plan, or history log.
- `upgrade` may replace shared repo-agnostic files automatically, but must continue to treat `AGENTS.md` and customised starter notes conservatively.
- Skills are an optional extension layer for specialised procedures and should not be bundled into the mandatory bootstrap payload.

## Last confirmed

2026-03-17 during task-context contract implementation
