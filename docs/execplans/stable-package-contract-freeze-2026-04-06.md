# Stable Package Contract Freeze

## Goal

- Define and freeze the installed planning and memory surfaces that should stop changing shape casually so future work can refine the products without quietly invalidating adopters.

## Non-Goals

- Promise permanent stability for every generated or helper surface immediately.
- Redesign lifecycle orchestration or module boundaries from scratch.
- Replace fixture hardening with a formal semantic-versioning system in one pass.

## Active Milestone

- Status: in-progress
- Scope: identify the installed planning and memory surfaces that now behave like compatibility contract surfaces, document their expected stability, and tighten validation or docs where the current promise is still ambiguous.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Decide whether the stable-contract tranche should stop after runtime and workspace reporting proof, or whether maintainer-facing docs should add one short note explaining that root doctor already exposes the package contract boundaries through nested module reports.

## Blockers

- None.

## Touched Paths

- ROADMAP.md
- docs/
- packages/memory/
- packages/planning/
- src/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Compatibility promises must stay narrower than the total payload.
- Generated mirrors should only inherit stability from their canonical sources when that relationship is explicit.
- Planning and memory must remain selectively adoptable with clear module boundaries.
- Validation should prove the declared contract rather than relying on informal maintainer memory.
- The frozen contract should reduce ambiguity for adopters without adding new ceremony for simple lifecycle work.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces
- cd packages/planning && uv run pytest
- cd packages/memory && uv run pytest

## Completion Criteria

- Planning and memory each have an explicit shortlist of installed surfaces that count as compatibility contract files.
- Lower-stability helpers and generated mirrors are clearly distinguished from those contract surfaces.
- Validation or package docs reflect the frozen contract boundaries rather than relying on implication.
- The resulting contract is narrow enough to be believable and stable enough to be useful.

## Drift Log

- 2026-04-06: Promoted once lifecycle wording, adoption realism, and design-principles guidance were stable enough that compatibility drift became the next maturity risk.
- 2026-04-06: Declared explicit planning and memory compatibility-contract shortlists, separated lower-stability helpers, and documented that boundary in package READMEs and installer tests.
- 2026-04-06: Surfaced the contract shortlists in planning and memory doctor and verify-payload output, then proved the root workspace doctor JSON already preserves those module-level summaries without adding a new top-level schema.
- 2026-04-06: Normalized workspace adapter path serialization for dataclass-based module actions so nested planning and memory report paths now share the same target-relative shape.
- 2026-04-06: Confirmed the default root doctor text output already shows the contract shortlists via module report lines, so adding another top-level contract summary layer would mostly duplicate existing output.