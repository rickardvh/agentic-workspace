# Front-Door Defaults Tranche

## Goal

- Make the normal adoption and operating path feel obvious and light by compressing front-door docs, exposing the default route in machine-readable form, and capturing the remaining default-path and cheap-execution audits in shipped review artifacts.

## Non-Goals

- No new module or automatic routing feature.
- No broad docs rewrite across every repo surface.
- No removal of legitimate advanced or package-local workflows.

## Active Milestone

- ID: front-door-defaults
- Status: completed
- Scope: refine root and package-facing start-here surfaces, add a machine-readable default-route contract to the workspace CLI, and ship bounded audit artifacts for default-path and cheap-execution friction.
- Ready: ready
- Blocked: none

## Immediate Next Action

- Archive this completed tranche and close GitHub issues `#14` through `#18` against the landed docs, CLI, and review surfaces.

## Blockers

- None.

## Touched Paths

- `README.md`
- `docs/which-package.md`
- `docs/default-path-contract.md`
- `docs/reviews/default-path-audit-2026-04-09.md`
- `docs/reviews/machine-readable-over-prose-audit-2026-04-09.md`
- `docs/reviews/cheap-execution-defaults-audit-2026-04-09.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`
- `packages/planning/README.md`
- `packages/memory/README.md`
- `ROADMAP.md`

## Invariants

- `agentic-workspace` remains the default public lifecycle entrypoint.
- Machine-readable structure should answer recurring route questions before prose grows further.
- Advanced, maintainer-only, and package-local paths remain available but clearly secondary.
- Cheap execution should become easier by reducing interpretation, not by adding a new auto-routing feature.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`

## Completion Criteria

- Front-door docs make the default adoption path obvious with advanced routes clearly secondary.
- A machine-readable default-route contract is available from the workspace CLI.
- Default-path and cheap-execution audits are captured as bounded review artifacts with concrete findings and promotion guidance.
- The active planning state returns to idle and issues `#14` through `#18` can be closed with landed evidence.

## Drift Log

- 2026-04-09: Promoted from GitHub issues `#14`-`#18` for one bounded implementation tranche by explicit maintainer choice.
- 2026-04-09: Completed the front-door compression pass, added `agentic-workspace defaults`, captured bounded audit artifacts, and validated the resulting route contract.
