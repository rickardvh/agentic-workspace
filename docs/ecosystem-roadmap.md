# Ecosystem Roadmap

This page records the current ecosystem stance without turning it into a promise of more top-level packages.

## Current Stable External Products

- Agentic Memory, distributed today as `agentic-memory-bootstrap`
- Agentic Planning, distributed today as `agentic-planning-bootstrap`

## Current Composition Layer

- `agentic-workspace` is the thin workspace-level composition layer for shared lifecycle verbs.
- External module or plugin extension is not yet a supported public contract; see `docs/extension-boundary.md`.

## Important Internal Capabilities

- Routing
- Checks / liveness validation

These capabilities matter, but they are not standalone packages yet.

## Evidence Required Before Extraction

Consider extraction only when dogfooding shows all of the following:

- repeated maintenance friction that is hard to solve inside the current modules
- stable schemas or manifests that do not rely on sibling internals
- clear owners and boundaries
- independent value in selectively adopted repos

## What Should Stay Internal For Now

- module-specific installer helpers
- workspace glue that only exists to compose memory and planning in this monorepo
- checks that still derive their real behavior from one module's internal contract

## Discipline Rule

Prefer sharper documentation, liveness checks, and consistency hardening over adding new top-level concepts unless real reuse pressure proves otherwise.

Current stance on shared tooling:

- prefer one managed source over new shared helpers when one module still clearly owns the behavior
- extract broader shared tooling only after cross-module reuse and maintenance cost are both clearly proven
