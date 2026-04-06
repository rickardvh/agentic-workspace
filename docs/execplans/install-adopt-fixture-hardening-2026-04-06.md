# Install/Adopt Fixture Hardening

## Goal

- Prove conservative planning and workspace lifecycle behavior across representative repository shapes so install and adopt decisions are backed by fixture coverage instead of optimistic assumptions.

## Non-Goals

- Redesign the root lifecycle command model.
- Expand module scope beyond memory and planning.
- Turn fixture work into a broad integration-test matrix for every package command.

## Active Milestone

- Status: in-progress
- Scope: define the missing representative repo shapes, add the first bounded fixture tranche for docs-heavy and partially pre-owned repositories, and tighten preserve-versus-manage expectations where current tests are still too synthetic.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Add the next fixture for mixed module ownership so adoption coverage exercises cross-module ambiguity, not just single-module residue.

## Blockers

- None.

## Touched Paths

- docs/
- packages/planning/
- tests/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Adoption must remain conservative when ownership is ambiguous.
- Fixture realism matters more than raw case count.
- Package-local lifecycle logic should keep owning preserve-versus-manage decisions.
- Validation should stay narrow and representative rather than exploding into an uncurated matrix.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces
- cd packages/planning && uv run pytest
- uv run pytest tests/test_workspace_cli.py

## Completion Criteria

- Representative docs-heavy and partially pre-owned repository shapes are covered by focused planning or workspace fixtures.
- Adoption expectations are explicit about preserved existing surfaces, managed updates, and manual-review paths.
- The new coverage exercises realistic ambiguity rather than only synthetic happy-path installs.
- Dogfooding lessons from the fixture work are fed back into the active plan or roadmap before closeout.

## Drift Log

- 2026-04-06: Promoted after the execution-scaling tranche landed and the next maturity risk remained adoption realism rather than lifecycle wording.
- 2026-04-06: The first audit showed planning adoption coverage was still thin compared with memory; the highest-value immediate gap was a docs-heavy existing-repo shape that exercises preserved root surfaces plus generated helper installation.
- 2026-04-06: Added the first docs-heavy adoption fixtures in both the planning package and workspace CLI so preserved root surfaces and generated helper installation are now exercised against a more realistic existing-repo shape.
- 2026-04-06: The next audit pass showed planning still lacked explicit partial-managed-state coverage, so the next milestone now targets orphaned planning surfaces and pre-existing manifest state rather than another docs-preservation variant.
- 2026-04-06: Added partial-managed-state fixtures for pre-existing planning manifest state and orphaned planning surfaces; current conservative behavior passed both, so the next realism gap is mixed module ownership rather than single-module residue.