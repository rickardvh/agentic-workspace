# Installed-Contract Design Checklist

## Goal

- Give package authors a short checklist for evaluating new installed surfaces against concurrent git workflows, canonical-source boundaries, lifecycle clarity, and collaboration-safe file shape.

## Non-Goals

- Create new package-scaffolding automation.
- Expand the workspace layer's ownership.
- Replace the existing package READMEs with maintainer-only process docs.

## Active Milestone

- Status: completed
- Scope: added one canonical package-authoring checklist and routed maintainers to it from the existing workflow docs without scattering duplicate policy prose.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Revisit shared-tooling extraction only when repeated checker maintenance friction is proven in real use.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- The checklist must stay short and actionable.
- Canonical-source and write-authority rules must remain consistent with the integration contract.
- Package authorship guidance should not become a new top-level policy layer.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces

## Completion Criteria

- A maintainer can review a proposed installed surface against collaboration-safe criteria without reverse-engineering prior chat context.
- Existing maintainer docs point to the checklist instead of rephrasing the same rules in multiple places.

## Drift Log

- 2026-04-06: Activated the installed-contract collaboration design checklist tranche after completing the cross-module collaboration contract docs.
- 2026-04-06: Completed the tranche after adding a canonical checklist and routing maintainers to it from the existing workflow docs.