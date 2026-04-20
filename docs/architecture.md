# Architecture

This page describes the current ecosystem shape.

Use `docs/design-principles.md` as the higher-level rule set for why this shape exists and what future changes must preserve.

## Public Shape

```mermaid
flowchart TD
    W[agentic-workspace\nthin workspace layer] --> M[Agentic Memory\nagentic-memory-bootstrap]
    W --> P[Agentic Planning\nagentic-planning-bootstrap]
    P --> R[Target-repo planning install\n.agentic-workspace/planning/state.toml • docs/execplans/\n.agentic-workspace/planning/]
    M --> N[Target-repo memory install\nmemory/ • .agentic-workspace/memory/]
    P --> G[Generated maintainer docs\ntools/agent-manifest.json\nAGENT_QUICKSTART.md\nAGENT_ROUTING.md]
    G --> C[Maintainer liveness path\nmake maintainer-surfaces\nscripts/check/check_maintainer_surfaces.py]
```

## Current Module Roles

- Agentic Memory owns durable repo knowledge.
- Agentic Planning owns active execution state.
- `agentic-workspace` coordinates module selection and shared lifecycle verbs.
- The module registry now exposes first-class capabilities, compatibility metadata, and result-contract guarantees; see `docs/module-capability-contract.md`.
- Generated docs and checks support the package contracts, but are not standalone products.
- The public extension boundary is still first-party only; see `docs/extension-boundary.md`.

## Monorepo Operating Boundary

In this monorepo:

- Root planning and memory installs are authoritative for live monorepo operation.
- `packages/memory/` and `packages/planning/` are package workspaces for source, payloads, tests, and fixtures.
- Package directories should not grow new package-local operational installs.
- `docs/source-payload-operational-install.md` names the maintainer boundary between package source, payload, and the root install, and `make maintainer-surfaces` now checks that boundary directly.

## Why The Workspace Layer Stays Thin

The workspace layer exists to compose modules, not to absorb domain logic.
It should stay quiet in ordinary use: visible machinery should justify itself, and compact selectors or module-owned surfaces should carry the detail whenever they can do so safely.

Default rule:

- new module-specific lifecycle flags or domain rules should land in the package CLI first
- add them to the workspace layer only when there is a clear cross-module reason
