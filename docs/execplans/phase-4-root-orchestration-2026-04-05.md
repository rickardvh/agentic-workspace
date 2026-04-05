# Phase 4 Root Orchestration

## Goal

- Close out root-orchestration migration work with root-owned planning and memory surfaces as the only operational authority.

## Non-Goals

- Reintroduce package-local installed planning or memory systems.
- Redesign package release boundaries or CLI names.

## Active Milestone

- Status: in-progress
- Scope: finalise planning-surface guardrails and migration close-out conditions after package-root uninstall cleanup.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Align root planning surfaces so the checked-in planning validator reports no active drift warnings for this tranche.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- AGENTS.md
- docs/execplans/
- docs/migration/monorepo-migration-plan.md

## Invariants

- Root planning and memory installs remain the only monorepo operational authority.
- Package-local tests may rely on shipped payload fixtures but not on package-local installed runtime systems.
- Active work must point from TODO.md to a live execplan under docs/execplans/.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make check-all

## Completion Criteria

- Root planning validator reports no TODO, ROADMAP, or startup-policy drift warnings for the active tranche.
- Root TODO points at a live execplan for active work.
- ROADMAP candidate entries each carry an explicit promotion trigger.

## Drift Log

- 2026-04-05: Plan created to close out root orchestration planning drift after package-root uninstall cleanup stabilized.
