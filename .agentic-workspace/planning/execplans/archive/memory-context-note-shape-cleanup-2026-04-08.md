# Memory Context Note-Shape Cleanup

## Goal

- Reduce the remaining overlap and procedural drift in repo-owned memory context notes so memory stays cheap to scan, subordinate to planning, and focused on anti-rediscovery value rather than repeatable operator procedure.

## Non-Goals

- Redesign the memory package.
- Re-open broad memory authority framing work.
- Move active execution state out of planning.

## Active Milestone

- Status: completed
- Scope: use the current memory doctor and freshness signals to tighten the package-context notes, extract any repeatable inspection procedure into a better home, and clear the remaining roadmap residue.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the runbook extraction, note-shape cleanup, and final planning pass landed.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/memory/repo/`
- `docs/`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- Planning remains the owner of active-now execution state.
- Durable memory should keep one primary home per concern.
- Repeatable procedure belongs in a runbook or skill before it turns a context note into a workflow notebook.

## Validation Commands

- `uv run agentic-memory-bootstrap doctor --target .`
- `uv run python scripts/check/check_memory_freshness.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The remaining package-context overlap warning is reduced or eliminated.
- Procedural drift is extracted out of the context note into a more appropriate home when needed.
- The roadmap queue is empty after the remaining memory cleanup lands.

## Drift Log

- 2026-04-08: Promoted after the earlier direct memory note cleanup reduced noise but still left one package-context overlap/procedure warning as the final bounded roadmap candidate.
- 2026-04-08: Completed after wiring a package-context inspection runbook into memory, tightening the current and package-context notes, and reducing the remaining memory overlap/procedure signal enough to leave the roadmap empty.
