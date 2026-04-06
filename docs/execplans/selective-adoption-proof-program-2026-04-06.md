# Selective Adoption Proof Program

## Goal

- Prove that memory-only, planning-only, and composed installs work cleanly outside the monorepo with explicit evidence instead of assuming full-stack adoption is the only meaningful path.

## Non-Goals

- Build the public plugin boundary.
- Require every proof to run in CI immediately.
- Overfit validation to the monorepo’s exact layouts.

## Deliverables

- A supported adoption-shape matrix for memory-only, planning-only, and composed installs.
- A validation strategy that combines fixtures and at least one real external-repo style proof.
- Clear evidence criteria for when selective adoption is considered proven enough.
- Documentation hooks that tell adopters which shapes are intentionally supported.

## Canonical Inputs

- docs/design-principles.md
- docs/integration-contract.md
- docs/boundary-and-extraction.md
- docs/maturity-model.md
- docs/dogfooding-feedback.md
- docs/installed-contract-design-checklist.md

## Active Milestone

- Status: planned
- Scope: define the proof matrix and validation evidence so selective adoption is treated as a first-class acceptance path.
- Ready: not-started
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Hold this until the compatibility and lifecycle guidance is stable enough to anchor the proof matrix.

## Blockers

- None.

## Invariants

- The proof program must keep memory-only and planning-only adoption shapes first-class.
- Validation evidence must not collapse into a full-stack-only success story.
- External-repo-style proofs should remain representative rather than monorepo-specific.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake to keep selective adoption queued after the compatibility and lifecycle threads.

## Touched Paths

- tests/
- docs/
- README.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- docs/ecosystem-roadmap.md

Keep this as a scope guard, not a broad file inventory.

## Validation

- Verify the matrix includes memory-only, planning-only, and composed adoption shapes.
- Check that evidence criteria are explicit and reproducible.
- Confirm the proof program does not collapse into a full-stack-only validation story.

## Completion Criteria

- Selective adoption shapes are documented and testable.
- The repo has a clear evidence bar for external-repo-style proofs.
- Future work can reuse the matrix instead of redefining adoption assumptions.

## Follow-On Work Not Pulled In

- Third-party extension validation.
- A full CI matrix if the proof program does not justify it yet.
- Registry or composition redesign beyond adoption evidence.
