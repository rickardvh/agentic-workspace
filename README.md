# agentic-workspace

Monorepo host for two distributable packages:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

## Purpose

This repository is the monorepo host for `agentic-memory-bootstrap` and
`agentic-planning-bootstrap`, with shared workspace-level orchestration,
validation, and dogfooding of the shipped packages.

## Layout

- `packages/memory/` - package workspace for `agentic-memory-bootstrap`
- `packages/planning/` - package workspace for `agentic-planning-bootstrap`
- `docs/execplans/` - active and archived execution plans
- `.github/workflows/` - unified monorepo CI workflows

## Current Status

Workspace orchestration is stable.

Root planning and memory systems own monorepo operation, package-scoped validation lanes are in place, and CI runs through root orchestration targets.

## Environment Routing

Use one shared root environment for daily monorepo work and package validation.

- Merged root lane (both packages): `make sync-all`
- Memory check lane alias: `make sync-memory`
- Planning check lane alias: `make sync-planning`

Validation entrypoints:

- `make test`
- `make lint`
- `make typecheck`
- `make format-check`
- `make verify`
- `make check`
- `make check-memory`
- `make check-planning`
- `make check-all`

`make check-memory` and `make check-planning` each perform a consolidated root dev sync first so checks remain repeatable from one workspace environment.

Root planning and memory installs are authoritative for monorepo operation.
Package directories now keep package source, bootstrap payloads, and test fixtures only; package-local installed runtime systems have been removed.
