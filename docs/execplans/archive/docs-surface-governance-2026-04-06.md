# Docs Surface Governance

## Goal

- Keep the repo's growing docs and checks ecosystem sharp, low-drift, and adopter-friendly by tightening Agentic Memory product framing and clarifying how rich docs surfaces should stay distinct, generated where appropriate, and cheap to maintain.

## Non-Goals

- Introduce new top-level product concepts or another meta-layer for docs.
- Collapse distinct docs surfaces that still have a clear role.
- Redesign package CLI behavior beyond documentation, liveness, and routing support.

## Active Milestone

- Status: completed
- Scope: completed the docs-governance tranche by strengthening Agentic Memory first-screen framing, clarifying docs-map and maintainer-doc roles, and adding a root maintainer-surface role-drift check with focused regression coverage.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Promote the next candidate only when a bounded follow-on tranche is clearly justified by real maintenance pressure.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- README.md
- docs/
- packages/memory/
- scripts/check/
- tests/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Memory and planning must remain selectively adoptable.
- The workspace layer must stay thin and orchestration-only.
- Docs should become easier to route and keep fresh, not more sprawling or more redundant.
- Maintainer-facing pages should keep one clear role each instead of drifting into a second manual.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces
- uv run pytest tests/test_maintainer_surfaces.py
- cd packages/memory && uv run pymarkdown -d md013,md024 scan README.md bootstrap skills
- cd packages/memory && uv run pytest
- cd packages/planning && uv run pytest

## Completion Criteria

- The Agentic Memory README opening frames the package first as a durable product capability and only second as an installer or CLI.
- The root docs map and maintainer-facing pages express clearer non-overlapping roles, reducing docs-map cognitive load.
- Drift-prone docs surfaces gain stronger generation, validation, or role-clarity checks where that meaningfully reduces sprawl risk.

## Drift Log

- 2026-04-06: Promoted from maintainer feedback after the integration contract and installed-contract collaboration tranche closed the earlier boundary and adopter-safety gaps.
- 2026-04-06: Strengthened the Agentic Memory README opening and rewrote the root docs map around page-specific roles.
- 2026-04-06: Tightened maintainer-doc scope language and added a root maintainer-surface role-drift check with focused regression coverage.
- 2026-04-06: Completed the tranche after `make maintainer-surfaces`, focused root checker tests, memory markdown lint, and both package test suites passed.