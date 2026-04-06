# Compatibility Policy and Stable Surfaces

## Goal

- Define a compact compatibility policy that names which workspace, package, and generated surfaces are stable today, which remain mutable, and what counts as a breaking change for installed repo surfaces, manifests, generated docs, lifecycle behavior, and module metadata.

## Non-Goals

- Redesign the module contract itself.
- Expand the public extension boundary.
- Promise immutability for surfaces that are still intentionally in flux.

## Deliverables

- A canonical compatibility-policy doc that separates stable, mutable, and generated surfaces.
- A breaking-change matrix for installed surfaces, manifests, generated docs, lifecycle commands, and module metadata.
- Short references from the maintainer surfaces that need to point at the policy.
- A later follow-on path for doctor/status/report integration if the policy needs machine-readable surfacing.

## Canonical Inputs

- docs/design-principles.md
- docs/integration-contract.md
- docs/installed-contract-design-checklist.md
- docs/maturity-model.md
- docs/ecosystem-roadmap.md
- docs/workflow-contract-changes.md

## Active Milestone

- Status: in-progress
- Scope: define the stable-surface promise and upgrade expectations without overcommitting to surfaces that are still intentionally moving.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Draft the canonical compatibility-policy doc, then add short references from the maintainer and adopter surfaces that need to point at it.

## Blockers

- None.

## Invariants

- Stable surfaces must be named once and treated consistently across docs and report payloads.
- The policy must stay narrower than the boundary docs and not re-litigate settled ownership rules.
- Breaking changes need a clear definition for adopters without promising immutability where the repo is still moving.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake so the compatibility promise can be promoted after the module-registry tranche finishes.

## Touched Paths

- docs/
- README.md
- AGENTS.md
- docs/maintainer-commands.md
- docs/contributor-playbook.md
- docs/installed-contract-design-checklist.md

Keep this as a scope guard, not a broad file inventory.

## Validation

- Review the doc against the stable-surface list in the installed-contract design checklist.
- Check that maintainer guidance and root documentation point to one canonical policy.
- Verify the policy does not duplicate already-settled boundary docs.

## Completion Criteria

- Adopters can tell which surfaces are stable and which are still moving.
- Breaking changes have a clear definition for the surfaces that matter.
- The policy stays compact enough to remain readable as a promise rather than a second roadmap.

## Follow-On Work Not Pulled In

- Doctor/status integration that prints compatibility classes.
- Versioned compatibility attestations for generated reports.
- Any plugin-contract work that depends on stable first-party module promises.
