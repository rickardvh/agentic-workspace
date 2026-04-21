# Unified Integration Lane

## Goal

- Add a coexistence smoke-test lane that proves memory and planning can be installed together through the root workspace entrypoint.

## Non-Goals

- Add a full release pipeline.
- Expand the smoke test into exhaustive lifecycle coverage for every command.
- Replace package-local tests that already cover module-specific behavior.

## Active Milestone

- Status: completed
- Scope: add one root-level integration smoke test that installs both modules into the same temp repo through `agentic-workspace` and verifies the expected combined surfaces.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and remove the finished unified-integration-lane candidate from the roadmap queue.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- .agentic-workspace/planning/execplans/
- tests/
- README.md

## Invariants

- The smoke test should stay narrow and complement package-local tests rather than duplicating them.
- It should exercise the workspace entrypoint, not bypass it.
- The combined install should preserve the current two-package architecture without assuming future package extraction.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py
- uv run ruff check src tests
- uv run ty check src

## Completion Criteria

- A root integration smoke test exists for combined memory and planning installation through `agentic-workspace`.
- The README or test naming makes the purpose of that integration lane clear.
- The roadmap no longer carries a separate open unified-integration-lane candidate.

## Drift Log

- 2026-04-05: Plan activated after the root lifecycle entrypoint and preset support were stable enough to justify a combined-install smoke test.
- 2026-04-05: Milestone complete: the root workspace test suite now exercises combined memory and planning installation through the `full` lifecycle preset.