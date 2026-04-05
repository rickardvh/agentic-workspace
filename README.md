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

## Architecture Stance

This repo currently treats two domains as standalone distributable products:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

The workspace layer composes those products, owns shared managed-surface orchestration, and provides the integrated monorepo operating model.

Routing and checks are important cross-cutting capabilities, but they are not yet treated as standalone packages. Keep them as contracts and implementation seams inside the existing products and workspace layer until dogfooding shows stable schemas, clear ownership, and repeated reuse pressure that justify extraction.

## Boundary Guide

Use these ownership tests when deciding where a feature belongs:

- Memory: durable knowledge that outlives the current task and is expensive to reconstruct quickly.
- Planning: active execution state, what matters now, what comes next, and what counts as done.
- Routing: how an agent decides what to read, trust, run, and validate for a task class.
- Checks: drift, liveness, shape, and consistency validation for installed workflow surfaces.
- Workspace: install, adopt, upgrade, uninstall, presets, integrated status, and multi-package composition.

Treat routing and checks as capabilities first, not packages by default. Extraction is warranted only when the boundary is stable enough to stand alone without leaning on sibling-package internals.

## Boundary Rules

- Memory must not become a task tracker or backlog mirror.
- Planning must not become a durable knowledge base.
- Routing must not become a shadow planning or memory system.
- Checks must not become the hidden policy owner for source-of-truth content.
- Workspace must orchestrate domain packages without absorbing their internal domain logic.

Prefer explicit seams:

- schemas and manifests
- generated artifacts derived from canonical sources
- adapters over private cross-package imports
- explicit capability detection for partial adoption

Avoid implicit cross-package assumptions, duplicated ownership of the same state, or sibling-package dependence on private internals.

## Extraction Criteria

A cross-cutting capability should become its own package only when all of the following are true:

- it has a stable ownership boundary that is not already better explained as part of memory, planning, or workspace orchestration
- it exposes explicit seams such as schemas, manifests, adapters, or generated artifacts instead of depending on sibling-package internals
- it is independently useful in selective-adoption repos rather than only as internal glue inside this monorepo
- dogfooding shows repeated reuse pressure or maintenance friction that is better solved by extraction than by keeping the capability internal

Do not extract a new package when the capability is still mostly one module's helper logic, when the boundary is still moving, or when the result would create a shell package whose real behavior still lives elsewhere.

## Selective Adoption

The ecosystem should support partial adoption. Today that means `agentic-memory-bootstrap` and `agentic-planning-bootstrap` can each stand alone while the workspace layer composes them for this monorepo.

If routing or checks are extracted later, they should preserve that property: no domain package should assume the full stack is present.

## Shared Lifecycle Entrypoint

Use `agentic-workspace` for shared lifecycle verbs that span module selection:

- `install`
- `adopt`
- `upgrade`
- `uninstall`
- `doctor`
- `status`

This root CLI is intentionally thin. It orchestrates selected modules through one workspace-level entrypoint while leaving module-specific logic and advanced flags inside the module packages.

When `--module` is omitted, `install` and `adopt` default to the current shared module set. Maintenance verbs such as `status`, `doctor`, `upgrade`, and `uninstall` default to the modules already detected in the target repo.

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
