# Planning Package Context

## Status

Active

## Purpose

Capture durable context for the planning bootstrap package and its package-local authority.

## Durable boundaries

- Planning owns active execution state through `.agentic-workspace/planning/state.toml` and `.agentic-workspace/planning/execplans/`.
- Memory remains an optional companion for durable technical context and should not own active queue state.
- Package planning contract includes review artifacts, upstream-task intake, generated routing surfaces, and compatibility views.
- Package planning source of truth lives under `packages/planning/src/`, `packages/planning/bootstrap/`, and `packages/planning/tests/`; the repo root is only the operational install used for dogfooding.

## Companion skill

Use `.agentic-workspace/memory/repo/skills/package-context-inspection/SKILL.md` for the repeatable package-inspection checklist instead of growing this note.

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
- .agentic-workspace/memory/repo/skills/package-context-inspection/SKILL.md

## Last confirmed

2026-04-08 after narrowing package-context notes and moving the repeatable checklist into a checked-in skill
