# Architecture

This page describes the current ecosystem shape.

Use `docs/design-principles.md` as the higher-level rule set for why this shape exists and what future changes must preserve.

## Public Shape

```mermaid
flowchart TD
    W[agentic-workspace\nthin workspace layer] --> M[Agentic Memory\nagentic-memory-bootstrap]
    W --> P[Agentic Planning\nagentic-planning-bootstrap]
    P --> R[Target-repo planning install\nTODO.md • ROADMAP.md • docs/execplans/\n.agentic-workspace/planning/]
    M --> N[Target-repo memory install\nmemory/ • .agentic-workspace/memory/]
    P --> G[Generated maintainer docs\ntools/agent-manifest.json\nAGENT_QUICKSTART.md\nAGENT_ROUTING.md]
    G --> C[Maintainer liveness path\nmake maintainer-surfaces\nscripts/check/check_maintainer_surfaces.py]
```

## Current Module Roles

- Agentic Memory owns durable repo knowledge.
- Agentic Planning owns active execution state.
- `agentic-workspace` coordinates module selection and shared lifecycle verbs.
- Generated docs and checks support the package contracts, but are not standalone products.

## Monorepo Operating Boundary

In this monorepo:

- Root planning and memory installs are authoritative for live monorepo operation.
- `packages/memory/` and `packages/planning/` are package workspaces for source, payloads, tests, and fixtures.
- Package directories should not grow new package-local operational installs.

## Why The Workspace Layer Stays Thin

The workspace layer exists to compose modules, not to absorb domain logic.

Default rule:

- new module-specific lifecycle flags or domain rules should land in the package CLI first
- add them to the workspace layer only when there is a clear cross-module reason
