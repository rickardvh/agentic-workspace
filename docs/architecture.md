# Architecture

This page describes the current ecosystem shape.

## Public Shape

```mermaid
flowchart TD
    A[Target Repository] --> B[Agentic Memory\nagentic-memory-bootstrap]
    A --> C[Agentic Planning\nagentic-planning-bootstrap]
    B --> D[memory/\n.agentic-workspace/memory/]
    C --> E[TODO.md\nROADMAP.md\ndocs/execplans/\n.agentic-workspace/planning/]
    C --> F[Generated routing docs\ntools/AGENT_QUICKSTART.md\ntools/AGENT_ROUTING.md]
    C --> G[Planning liveness checks\nscripts/check/check_planning_surfaces.py]
    H[agentic-workspace CLI] --> B
    H --> C
```

## Current Module Roles

- Agentic Memory owns durable repo knowledge.
- Agentic Planning owns active execution state.
- `agentic-workspace` coordinates module selection and shared lifecycle verbs.
- Routing and checks are important capabilities, but are not standalone packages yet.

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