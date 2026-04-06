# Generated Surface Trust Hardening

## Goal

- Make generated surfaces boringly trustworthy by tightening canonical-source declarations, rerender expectations, generated-file markings, and liveness checks across maintainer-facing paths.

## Non-Goals

- Invent new generated artifacts without need.
- Duplicate the compatibility-policy work.
- Turn every drift warning into a hard failure.

## Deliverables

- A clear inventory of canonical sources for generated surfaces.
- Rerender and freshness expectations that are explicit across the root and package-level surfaces.
- Markings that make generated files obviously generated and non-manual.
- A validation path for startup/routing consistency across maintainer surfaces.

## Canonical Inputs

- docs/installed-contract-design-checklist.md
- docs/collaboration-safety.md
- docs/workflow-contract-changes.md
- docs/design-principles.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- docs/ecosystem-roadmap.md

## Active Milestone

- Status: planned
- Scope: harden generated-surface trust without duplicating the compatibility policy or boundary docs.
- Ready: not-started
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Keep this queued behind compatibility policy work so the generated-surface hardening can reuse the same stable-surface vocabulary.

## Blockers

- None.

## Invariants

- Canonical sources should remain named once and referenced consistently.
- Generated-file markings must stay obvious and non-manual.
- Liveness checks should stay quiet when nothing changed.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake so generated-surface trust can follow the stable-surface and lifecycle docs.

## Touched Paths

- docs/
- scripts/
- tests/
- README.md
- tools/
- .agentic-workspace/

Keep this as a scope guard, not a broad file inventory.

## Validation

- Check that canonical sources are named once and referenced consistently.
- Verify generated-file markings and freshness checks stay aligned.
- Confirm maintainer surfaces point to the same render and liveness expectations.

## Completion Criteria

- Generated surfaces are clearly derived and easy to trust.
- Drift detection is explicit and quiet when nothing changed.
- Maintainer-facing documentation reflects one canonical trust model.

## Follow-On Work Not Pulled In

- Expanding the generated-surface matrix beyond the surfaces already under contract pressure.
- Compatibility-policy machinery.
- Any new generated artifacts that do not already have a clear canonical source.
