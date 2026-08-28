# Planning Package Context

## Status

Active

## Purpose

Capture durable context for the planning bootstrap package and its package-local authority.

## Durable boundaries

- Planning owns active execution custody through bounded execplan, lane/decomposition, issue-relation, and integration records. Current-owner selection is worktree-local and aggregate queue/roadmap views are derived.
- `.agentic-workspace/planning/state.toml` is legacy upgrade input, not ongoing authority; fresh installs omit it and upgrades retire it after bounded migration.
- Memory remains an optional companion for durable technical context and should not own active execution custody.
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

2026-08-28 after replacing checked-in aggregate planning state with owner-scoped records and derived views
