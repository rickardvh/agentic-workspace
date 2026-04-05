# agentic-bootstrap-monorepo

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

Phase 0/1 scaffold created.

Code import, history-preserving migration, and CI/release cutover are pending.
