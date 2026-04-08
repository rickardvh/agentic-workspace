# Source, Payload, And Root Install Boundary

This page is the canonical maintainer guide for work that crosses package source, shipped payload, and the root operational install in this monorepo.

Use it when one change touches more than one of these layers and you need to keep the ownership boundary explicit instead of fixing only the currently visible copy.

## Layers

| Layer | Purpose | Typical paths |
| --- | --- | --- |
| Source | Reusable package logic and tests that define shipped behavior | `packages/planning/src/`, `packages/planning/tests/`, `packages/memory/src/`, `packages/memory/tests/` |
| Payload | Files the package installs into a target repo | `packages/planning/bootstrap/`, `packages/memory/bootstrap/` |
| Root operational install | The live installed workflow surfaces this monorepo actually uses | `AGENTS.md`, `TODO.md`, `ROADMAP.md`, `.agentic-workspace/`, `memory/`, `tools/`, `scripts/check/` |

## Default Rule

- Fix the authoritative layer first.
- When behavior is shipped, keep source and payload aligned before or alongside the root operational install.
- Do not patch the root install alone when the next package upgrade would overwrite the fix.

## Maintainer Workflow

1. Identify which layer owns the behavior you are changing.
2. If the change is shipped package behavior, update package source and payload together.
3. Refresh the root operational install to the latest checked-in package version when the root repo depends on that shipped behavior.
4. Run the narrowest package-local validation first, then the root maintainer lane when the change affects generated docs, startup routing, or installed contract surfaces.

## Root Maintainer Lane

- `python scripts/check/check_source_payload_operational_install.py` checks for source/payload/root-install boundary drift directly.
- `python scripts/check/check_maintainer_surfaces.py` is the aggregate maintainer wrapper: it runs the planning maintainer checks and includes the boundary checker when that checker exists in the repo.
- `make maintainer-surfaces` is the normal repo-maintainer lane for generated docs, startup-policy consistency, payload contract verification, and boundary drift.

## Failure Modes To Avoid

- Updating package source without updating shipped payload.
- Updating shipped payload without refreshing the live root install when the monorepo depends on it.
- Treating root operational files as the canonical source when they are really installed copies.
- Claiming a maintainer lane covers a boundary that the actual wrapper or command path does not execute.
