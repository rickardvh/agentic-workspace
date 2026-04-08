# Review-Promotion Threshold

## Goal

- Define a small canonical rule for when repeated review findings or repeated dogfooding friction should graduate into `ROADMAP.md` candidate work instead of remaining captured-only signals.

## Non-Goals

- Add a new review system, scoring matrix, or checker.
- Blur the boundary between review capture, roadmap candidates, and active execution.
- Expand into broader review-portfolio design or review-mode tooling.

## Active Milestone

- Status: completed
- Scope: aligned the review contract and roadmap language on one explicit threshold rule for promoting repeated findings into roadmap candidates while keeping activation into `TODO.md` plus an execplan separate.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Archived after the canonical review contract and roadmap wording were aligned and validated.

## Blockers

- None.

## Touched Paths

- `docs/reviews/`
- `ROADMAP.md`
- `TODO.md`

## Invariants

- Review capture, roadmap candidates, and active execution must remain separate stages.
- The rule must lower ambiguity without adding process weight to one-off findings.
- Friction-confirmed signals must remain higher-trust than pure static-analysis findings.

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The canonical review docs state when a repeated finding stays captured-only and when it becomes a roadmap candidate.
- `ROADMAP.md` no longer carries this threshold gap as an open candidate once the rule lands.
- The resulting contract still requires explicit selection before promotion into `TODO.md` plus an execplan.

## Drift Log

- 2026-04-08: Promoted from `ROADMAP.md` after repeated review artifacts and repo-maintenance passes converged on the same missing threshold rule.
- 2026-04-08: Added the explicit threshold to `docs/reviews/README.md`, aligned the review template and roadmap wording with the same rule, and removed the now-resolved candidate from `ROADMAP.md`.
