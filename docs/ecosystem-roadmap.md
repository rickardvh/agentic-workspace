# Ecosystem Roadmap

Last doctrinal review: 2026-04-13

This page records the current ecosystem stance without turning it into a promise of more top-level packages.

For the broader long-horizon capability map behind that stance, see `docs/agent-os-capabilities.md`.

When the current stance changes, update this page and move any concrete next work into `ROADMAP.md` instead of accumulating latent backlog prose here.
Use a doctrine-refresh review when the current ecosystem stance may have drifted from actual shipped behavior or extraction discipline.

## Role Boundary

This page owns current ecosystem stance:

- what is shipped externally today
- what remains internal for now
- what evidence is required before extraction

It does not own:

- the full capability taxonomy
- the bounded future-work queue
- current maturity labels

Route those concerns to:

- `docs/agent-os-capabilities.md` for the capability map
- `ROADMAP.md` for bounded next candidates
- `docs/maturity-model.md` for maturity framing

## Refresh Triggers

Update this page directly when any of the following happens:

- a new first-party shipped module appears
- an internal capability clearly moves toward or away from extraction
- the extraction discipline changes enough that current stance would otherwise become stale
- another doctrine page starts carrying ecosystem-packaging claims that belong here instead

## Current Stable External Products

- Agentic Memory, distributed today as `agentic-memory-bootstrap`
- Agentic Planning, distributed today as `agentic-planning-bootstrap`

## Current Composition Layer

- `agentic-workspace` is the thin workspace-level composition layer for shared lifecycle verbs.
- External module or plugin extension is not yet a supported public contract; see `docs/extension-boundary.md`.

## Current Portability Read

- Proven now: the current first-party pair is portable across clean repos through the shared workspace lifecycle front door. Fresh `memory`, `planning`, and `full` installs have current clean-room proof, and selective adoption is real for those first-party shapes.
- Not yet proven: broader ecosystem portability beyond that first-party pair. The repo does not yet have evidence for third-party extension, non-core module composition, or a wider module ecosystem that keeps the same guarantees outside closely related first-party contracts.

## Important Internal Capabilities

- Routing
- Checks / liveness validation

These capabilities matter, but they are not standalone packages yet. Keep the fuller capability taxonomy in `docs/agent-os-capabilities.md`; keep this page focused on ecosystem stance and extraction discipline.

## Evidence Required Before Extraction

Consider extraction only when dogfooding shows all of the following:

- repeated maintenance friction that is hard to solve inside the current modules
- stable schemas or manifests that do not rely on sibling internals
- clear owners and boundaries
- independent value in selectively adopted repos

## What Should Stay Internal For Now

- module-specific installer helpers
- workspace glue that only exists to compose the current first-party pair or still depends on sibling internals
- checks that still derive their real behavior from one module's internal contract

## Discipline Rule

Prefer sharper documentation, liveness checks, and consistency hardening over adding new top-level concepts unless real reuse pressure proves otherwise.

Current stance on shared tooling:

- prefer one managed source over new shared helpers when one module still clearly owns the behavior
- extract broader shared tooling only after cross-module reuse and maintenance cost are both clearly proven
