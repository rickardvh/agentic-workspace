# Selective Adoption Proof Program

## Goal

- Prove that memory-only, planning-only, and composed installs work cleanly outside the monorepo with explicit evidence instead of assuming full-stack adoption is the only meaningful path.

## Non-Goals

- Build the public plugin boundary.
- Require every proof to run in CI immediately.
- Overfit validation to the monorepo’s exact layouts.

## Active Milestone

- Status: completed
- Scope: define the proof matrix and validation evidence so selective adoption is treated as a first-class acceptance path.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and move the generated-surface trust milestone into active execution.

## Blockers

- None.

## Touched Paths

- tests/
- docs/
- README.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- docs/ecosystem-roadmap.md

Keep this as a scope guard, not a broad file inventory.

## Invariants

- The proof program must keep memory-only and planning-only adoption shapes first-class.
- Validation evidence must not collapse into a full-stack-only success story.
- External-repo-style proofs should remain representative rather than monorepo-specific.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake to keep selective adoption queued after the compatibility and lifecycle threads.
- 2026-04-06: Milestone complete: the chooser page now includes an explicit proof bar and the planning package README states that selective adoption must remain valid.

## Completion Criteria

- Selective adoption shapes are documented and testable.
- The repo has a clear evidence bar for external-repo-style proofs.
- Future work can reuse the matrix instead of redefining adoption assumptions.

## Follow-On Work Not Pulled In

- Third-party extension validation.
- A full CI matrix if the proof program does not justify it yet.
- Registry or composition redesign beyond adoption evidence.