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

- Decide whether verify-payload or doctor output should surface the frozen contract shortlist explicitly instead of leaving it only in code and README guidance.

## Blockers

- None.

## Touched Paths

- ROADMAP.md
- docs/
- packages/memory/
- packages/planning/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Compatibility promises must stay narrower than the total payload.
- Generated mirrors should only inherit stability from their canonical sources when that relationship is explicit.
- Planning and memory must remain selectively adoptable with clear module boundaries.
- Validation should prove the declared contract rather than relying on informal maintainer memory.

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

- 2026-04-06: Promoted after lifecycle wording, adoption realism, and cross-module ambiguity hardening all landed cleanly enough that the next maturity risk became compatibility drift rather than missing behavior proof.
- 2026-04-06: The initial audit showed memory already had richer internal contract metadata than planning, so the first milestone now makes both packages expose an explicit compatibility-contract shortlist and distinguish it from lower-stability helpers in tests and README guidance.
- 2026-04-06: Added explicit contract shortlists for both packages, documented them in the READMEs, and locked them in with installer tests; the next question is whether runtime verification output should expose that shortlist directly for maintainers.