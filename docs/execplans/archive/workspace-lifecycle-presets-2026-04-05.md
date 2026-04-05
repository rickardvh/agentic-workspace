# Workspace Lifecycle Presets

## Goal

- Add preset-based module selection to the root lifecycle CLI so common workspace operations do not need repeated `--module` combinations.

## Non-Goals

- Replace explicit `--module` selection.
- Add new module families in this tranche.
- Broaden the workspace CLI beyond current lifecycle verbs.

## Active Milestone

- Status: completed
- Scope: add preset selection to the root CLI, document the supported presets, and cover the behavior with tests.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and keep the broader unified lifecycle follow-through candidate open for later composition work.

## Blockers

- None.

## Touched Paths

- TODO.md
- docs/execplans/
- README.md
- src/agentic_workspace/
- tests/

## Invariants

- The root CLI remains a thin orchestrator.
- Explicit `--module` selection must remain available.
- Presets should only encode module combinations that already make sense under the current two-package architecture.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py
- uv run ruff check src tests
- uv run ty check src

## Completion Criteria

- The root lifecycle CLI supports preset-based module selection for common cases.
- README guidance mentions the supported presets.
- Tests cover preset resolution and conflicts with explicit `--module` selection.

## Drift Log

- 2026-04-05: Plan activated as the next bounded ergonomics step under the broader unified lifecycle orchestrator follow-through candidate.
- 2026-04-05: Milestone complete: the root lifecycle CLI now supports preset-based module selection while preserving explicit `--module` control.