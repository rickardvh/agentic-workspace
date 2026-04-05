# agentic-workspace

Monorepo host for two distributable packages:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

## Purpose

This repository is the migration target that will consolidate the current
`agentic-memory` and `agentic-planning` repositories into one workspace while
keeping package boundaries, independent versioning, and independent release
artifacts.

## Layout

- `packages/memory/` - package workspace for `agentic-memory-bootstrap`
- `packages/planning/` - package workspace for `agentic-planning-bootstrap`
- `docs/migration/` - migration decision log, import mapping, and checkpoints
- `.github/workflows/` - unified CI/release workflows (to be completed)

## Current Status

Phase 4 orchestration in progress.

History-preserving package imports are complete. Current work is consolidating root runtime systems (planning and memory), dependency routing lanes, and root CI orchestration.

## Environment Routing

Use one shared root environment for daily monorepo work, and package-scoped lanes when validating package boundaries.

- Merged root lane (both packages): `make sync-all`
- Memory package lane: `make sync-memory`
- Planning package lane: `make sync-planning`

Validation entrypoints:

- `make check-memory`
- `make check-planning`
- `make check-all`

`make check-memory` and `make check-planning` each perform their own package-scoped sync first so lane checks remain isolated and repeatable.

Root planning and memory installs are authoritative for monorepo operation.
Package-local planning and memory files under `packages/*` are currently retained as package-owned fixture/dev surfaces because package test suites still depend on them.
