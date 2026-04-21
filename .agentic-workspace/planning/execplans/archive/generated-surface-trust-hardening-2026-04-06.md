# Generated Surface Trust Hardening

## Goal

- Make generated surfaces boringly trustworthy by tightening canonical-source declarations, rerender expectations, generated-file markings, and liveness checks across maintainer-facing paths.

## Non-Goals

- Invent new generated artifacts without need.
- Duplicate the compatibility-policy work.
- Turn every drift warning into a hard failure.

## Active Milestone

- Status: completed
- Scope: harden generated-surface trust without duplicating the compatibility policy or boundary docs.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and leave `TODO.md` empty until a new roadmap candidate is explicitly promoted.

## Blockers

- None.

## Touched Paths

- docs/
- scripts/
- tests/
- README.md
- tools/
- .agentic-workspace/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Canonical sources should remain named once and referenced consistently.
- Generated-file markings must stay obvious and non-manual.
- Liveness checks should stay quiet when nothing changed.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake so generated-surface trust could follow the stable-surface and lifecycle docs.
- 2026-04-06: Milestone complete: the repo now has a canonical generated-surface trust doc plus maintainer references for canonical sources, rerendering, and freshness checks.

## Completion Criteria

- Generated surfaces are clearly derived and easy to trust.
- Drift detection is explicit and quiet when nothing changed.
- Maintainer-facing documentation reflects one canonical trust model.

## Follow-On Work Not Pulled In

- Expanding the generated-surface matrix beyond the surfaces already under contract pressure.
- Compatibility-policy machinery.
- Any new generated artifacts that do not already have a clear canonical source.