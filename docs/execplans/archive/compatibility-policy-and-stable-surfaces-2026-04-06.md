# Compatibility Policy and Stable Surfaces

## Goal

- Define a compact compatibility policy that names which workspace, package, and generated surfaces are stable today, which remain mutable, and what counts as a breaking change for installed repo surfaces, manifests, generated docs, lifecycle behavior, and module metadata.

## Non-Goals

- Redesign the module contract itself.
- Expand the public extension boundary.
- Promise immutability for surfaces that are still intentionally in flux.

## Active Milestone

- Status: completed
- Scope: define the stable-surface promise and upgrade expectations without overcommitting to surfaces that are still intentionally moving.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and move the repository-stewardship milestone into active execution.

## Blockers

- None.

## Touched Paths

- docs/
- README.md
- AGENTS.md
- docs/maintainer-commands.md
- docs/contributor-playbook.md
- docs/installed-contract-design-checklist.md

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Stable surfaces must be named once and treated consistently across docs and report payloads.
- The policy must stay narrower than the boundary docs and not re-litigate settled ownership rules.
- Breaking changes need a clear definition for adopters without promising immutability where the repo is still moving.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake so the compatibility promise could be promoted after the module-registry tranche finished.
- 2026-04-06: Milestone complete: the repo now has a canonical compatibility-policy doc plus short references from the adopter and maintainer guidance surfaces.

## Completion Criteria

- Adopters can tell which surfaces are stable and which are still moving.
- Breaking changes have a clear definition for the surfaces that matter.
- The policy stays compact enough to remain readable as a promise rather than a second roadmap.

## Follow-On Work Not Pulled In

- Doctor/status integration that prints compatibility classes.
- Versioned compatibility attestations for generated reports.
- Any plugin-contract work that depends on stable first-party module promises.