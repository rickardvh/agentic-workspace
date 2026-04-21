# Intent Continuity Across Slices

## Goal

- Make planning preserve larger intended outcomes across multiple bounded slices so a safe first slice cannot archive cleanly without explicit continuation when the parent intent is still unfinished.

## Non-Goals

- Do not turn planning into a broad epic tracker.
- Do not add retrospective status logs to active plans.
- Do not require every task to become a multi-slice program.

## Intent Continuity

- Larger intended outcome: planning should carry the parent user intent until the real requested outcome is done, not just the current safe slice.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate `Intent continuity follow-through`

## Active Milestone

- ID: intent-continuity-across-slices
- Status: completed
- Scope: add intent-continuity fields to the execplan contract, teach archive to block incomplete larger intent without a continuation surface, and update the planning checker and template accordingly.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed slice now that the broader intent is explicitly carried forward in `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/execplans/README.md`
- `.agentic-workspace/planning/execplans/TEMPLATE.md`
- `packages/planning/bootstrap/.agentic-workspace/planning/execplans/README.md`
- `packages/planning/bootstrap/.agentic-workspace/planning/execplans/TEMPLATE.md`
- `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/tests/test_check_planning_surfaces.py`
- `packages/planning/tests/test_installer.py`

## Invariants

- Keep bounded slices cheap and valid.
- Preserve one explicit owner for unfinished larger intent after a slice completes.
- Do not allow archive to silently erase unfinished parent intent.

## Validation Commands

- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py`
- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- Active execplans carry explicit larger-intent and continuation fields.
- Planning checks warn when intent continuity is under-specified.
- Archive flow blocks completed slices that leave larger intent unfinished without an explicit continuation surface.
- Root install is refreshed and the active queue can archive cleanly after the slice lands.

## Drift Log

- 2026-04-09: Promoted after dogfooding showed that bounded first slices can still be archived as if the real requested outcome were complete.
- 2026-04-09: Landed intent-continuity fields, checker enforcement, archive gating, and an explicit roadmap continuation for the broader parent-intent problem.
