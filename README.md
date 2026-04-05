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
- `.github/workflows/` - unified monorepo CI workflows

## Current Status

Phase 4 orchestration and migration close-out.

History-preserving package imports are complete. Root planning and memory systems now own monorepo operation, package-scoped dependency lanes are in place, and CI runs through root orchestration targets.

## Environment Routing

Use one shared root environment for daily monorepo work and package validation.

- Merged root lane (both packages): `make sync-all`
- Memory check lane alias: `make sync-memory`
- Planning check lane alias: `make sync-planning`

Validation entrypoints:

- `make check-memory`
- `make check-planning`
- `make check-all`

`make check-memory` and `make check-planning` each perform a consolidated root dev sync first so checks remain repeatable from one workspace environment.

Root planning and memory installs are authoritative for monorepo operation.
Package directories now keep package source, bootstrap payloads, and test fixtures only; package-local installed runtime systems have been removed.
