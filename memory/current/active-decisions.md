# Active Decisions

## Status

Active

## Scope

Current high-impact decisions for root orchestration and package boundaries.

## Load when

- Updating root orchestration, CI routing, or ownership contracts.
- Deciding whether package-level changes should run through root-owned systems.

## Review when

- Root check entrypoints or CI routing behavior changes.
- Ownership boundaries between root and package systems are updated.

## Failure signals

- Root and package workflows disagree on operational ownership.
- CI or local checks run against the wrong sync lane.

## Current decisions

- Root owns one installed memory system and one installed planning system.
- Package-local fixtures or payload copies in packages/memory and packages/planning are not operational authorities.
- Use merged root dependency sync for day-to-day work and package-scoped sync lanes for package validation.
- Keep the workspace-orchestrator contract and ownership ledger as the shared source for managed-surface rules.

## Verify

- TODO.md
- .agentic-workspace/WORKFLOW.md
- .agentic-workspace/OWNERSHIP.toml
- Makefile
- .github/workflows/ci.yml

## Last confirmed

2026-04-05 during root system consolidation
