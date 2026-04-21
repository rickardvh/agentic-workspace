# Contract-Integrity Review Mode

## Goal

- Add and ship one canonical `contract-integrity` review mode so repo maintainers have an explicit review path for broken references, missing canonical surfaces, docs-code drift, and promise-versus-enforcement gaps that create avoidable cross-checking cost.

## Non-Goals

- Redesign the whole review system or add multiple new review modes at once.
- Re-run broad product-state review work beyond what is needed to define and validate this mode.
- Fold active maintainer-surface implementation work back into this review slice.

## Active Milestone

- Status: completed
- Scope: define the `contract-integrity` review mode in shipped review docs and template surfaces, add narrow validation for it, and leave the roadmap cleanly promoted.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the review docs, payload assertions, and planning surfaces all passed the narrow validation lane.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/reviews/`
- `packages/planning/`
- `tests/`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- Review modes stay bounded, named, and cheaper than the confusion they prevent.
- Review guidance remains canonical in shipped review surfaces rather than drifting into chat-only doctrine.
- This slice adds one mode without expanding the review layer into parallel planning overhead.

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The shipped review README defines `contract-integrity` as a canonical mode with clear inputs, target failures, and promotion destination.
- The shipped review template can record a `contract-integrity` review without ad hoc wording.
- Narrow validation covers the new review-mode contract and the promoted planning surfaces remain clean.

## Drift Log

- 2026-04-08: Promoted after repeated maintainer-surface and docs-contract drift showed the repo still lacked one explicit review path for promise-versus-enforcement gaps and missing canonical surfaces.
- 2026-04-08: Completed after making the `contract-integrity` mode guidance explicit enough to use directly and adding a payload assertion for its core failure classes.
