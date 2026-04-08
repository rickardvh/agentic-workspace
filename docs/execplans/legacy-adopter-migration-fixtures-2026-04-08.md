# Legacy-Adopter Migration Fixtures

## Goal

- Add representative migration fixtures for older standalone installs, partial conversions, and stale residue so upgrade paths detect incomplete state and preserve user-owned content.

## Non-Goals

- Redesign install, adopt, or upgrade semantics from scratch.
- Expand the work into a full lifecycle matrix replacement.
- Add broad end-to-end automation across every package command.

## Active Milestone

- Status: in-progress
- Scope: define the first realistic migration fixture tranche and add focused upgrade-path coverage for legacy installs, partial managed state, and stale residue across the workspace and package layers.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Inspect the current upgrade and doctor coverage in the workspace, planning package, and memory package to identify the missing legacy-adopter fixture shapes before adding the first test tranche.

## Blockers

- None.

## Touched Paths

- `tests/`
- `packages/planning/tests/`
- `packages/memory/tests/`
- `docs/`

## Invariants

- Migration fixtures must preserve user-owned content while tightening package-managed state.
- The first slice should exercise realistic legacy and partial-managed states, not synthetic happy paths.
- Validation should stay focused on migration and incomplete-state detection rather than reopening the full lifecycle contract.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `cd packages/planning && uv run pytest`
- `cd packages/memory && uv run pytest`

## Completion Criteria

- Define fixture coverage for at least one legacy standalone install shape, one partial conversion shape, and one stale-residue shape.
- Add regression tests that prove upgrade or doctor flows detect incomplete state and preserve user-owned content.
- Keep the fixtures bounded enough that future migration bugs can reuse them instead of inventing new ad hoc setups.

## Drift Log

- 2026-04-08: Promoted from ROADMAP after upstream intake, packaging artifact validation, lifecycle matrix hardening, and selective-adoption proof work had already landed and archived.
