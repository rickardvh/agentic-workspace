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
- Long-term lifecycle UX should converge toward one workspace-level orchestrator that installs and manages modules, rather than leaving each module with a separate standalone bootstrap entrypoint.
- The root `agentic-workspace` CLI is the shared lifecycle entrypoint for common workspace verbs; module CLIs remain authoritative for module-specific logic and advanced flags.
- Treat routing and checks as cross-cutting capabilities for now, not standalone packages by default.
- Promote routing or checks into first-class packages only when dogfooding establishes stable schemas, clear ownership boundaries, and reuse pressure beyond one module's internal implementation.
- Use ownership tests when placing new work: durable knowledge -> memory, live execution state -> planning, task-class read/run/validate policy -> routing, drift/liveness validation -> checks, install/orchestration/composition -> workspace.
- Prefer schemas, manifests, generated artifacts, adapters, and explicit capability detection over implicit coupling between package internals.

## Verify

- TODO.md
- .agentic-workspace/WORKFLOW.md
- .agentic-workspace/OWNERSHIP.toml
- Makefile
- .github/workflows/ci.yml

## Last confirmed

2026-04-05 during root system consolidation
