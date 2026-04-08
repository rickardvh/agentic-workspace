# Planning Package Context

## Status

Active

## Purpose

Capture durable context for the planning bootstrap package and how it fits into the root-owned planning and memory systems.

## Durable context

- Planning owns active execution state through TODO.md, ROADMAP.md, and docs/execplans.
- Memory remains an optional companion for durable technical context and should not own active queue state.
- Keep planning and memory ownership boundaries explicit in agent startup and routing docs.
- Package planning contract includes review artifacts, upstream-task intake, and generated routing surfaces in addition to TODO/ROADMAP/execplans.
- Package planning source of truth lives under `packages/planning/src/`, `packages/planning/bootstrap/`, and `packages/planning/tests/`; the repo root is only the operational install used for dogfooding.

## Monorepo adaptation note

Root ownership contains the installed planning and memory systems. For the owning rationale, load `memory/decisions/installed-system-consolidation-2026-04-05.md` instead of expanding this context note.

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
- packages/planning/src/
- packages/planning/bootstrap/
- packages/planning/tests/
- memory/runbooks/package-context-inspection.md

## Last confirmed

2026-04-08 after extension-boundary and composition-contract cleanup
