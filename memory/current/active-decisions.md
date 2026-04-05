# Active Decisions

## Status

Active

## Scope

Current high-impact decisions for monorepo migration and root orchestration.

## Load when

- Updating root orchestration, CI routing, or migration contracts.
- Deciding whether package-level changes should run through root-owned systems.

## Review when

- Migration milestones, root check entrypoints, or CI routing behavior changes.
- Ownership boundaries between root and package systems are updated.

## Failure signals

- Root and package workflows disagree on operational ownership.
- CI or local checks run against the wrong sync lane.

## Current decisions

- Root owns one installed memory system and one installed planning system.
- Package-local installed systems in packages/memory and packages/planning are cleanup targets after root population.
- Use merged root dependency sync for day-to-day work and package-scoped sync lanes for package validation.
- Keep migration execution contract in docs/migration/monorepo-migration-plan.md until migration closes.

## Verify

- TODO.md
- docs/migration/monorepo-migration-plan.md
- Makefile
- .github/workflows/ci.yml

## Last confirmed

2026-04-05 during root system consolidation
