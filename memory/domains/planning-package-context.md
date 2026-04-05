# Planning Package Context

## Status

Active

## Purpose

Capture durable context for the planning bootstrap package and how it fits into the root-owned planning and memory systems.

## Durable context

- Planning owns active execution state through TODO.md, ROADMAP.md, and docs/execplans.
- Memory remains an optional companion for durable technical context and should not own active queue state.
- Keep planning and memory ownership boundaries explicit in agent startup and routing docs.
- Package planning active queue was empty at consolidation time.
- Package planning roadmap previously carried a candidate to pin UPGRADE-SOURCE metadata to immutable releases when release cadence stabilises.

## Monorepo adaptation note

Root ownership contains the installed planning and memory systems. Package-local payloads and tests should stay package-scoped and should not become operational authorities.

## Load when

- Editing files under packages/planning.
- Updating planning bootstrap package ownership, validation, or payload behavior.

## Review when

- Planning package README, bootstrap payload, or validation surfaces change materially.
- Root planning orchestration changes how package context is routed.

## Failure signals

- Package-planning work misses package-specific execution assumptions.
- Package context drifts away from the actual bootstrap payload, source, or tests.

## Verify

- packages/planning/README.md
- packages/planning/bootstrap/
- packages/planning/src/
- packages/planning/tests/

## Last confirmed

2026-04-05 after repository reference cleanup
