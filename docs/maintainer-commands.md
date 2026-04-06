# Maintainer Commands

This page is the single-source command index for routine repo maintenance.

Use this page when you need the canonical command to run, not the broader routing, ownership, or workflow-history context.

## Setup

| Command | Purpose |
| --- | --- |
| `make sync-all` | Sync the shared root environment for all workspace packages |
| `uv run pre-commit install` | Install the local format and lint hooks |

## Local Maintenance

| Command | Purpose |
| --- | --- |
| `make format` | Apply Ruff formatting across workspace and packages |
| `make lint` | Run lint checks across workspace and packages |
| `make typecheck` | Run type checks across workspace and packages |
| `make render-agent-docs` | Regenerate routing docs from the planning manifest |
| `make maintainer-surfaces` | Run the maintainer-surface liveness path for generated docs, startup-policy consistency, and both packaged payload contracts |
| `make planning-surfaces` | Run the underlying planning-surface audit directly |

## Validation Lanes

| Command | Purpose |
| --- | --- |
| `make check` | Root validation lane |
| `make check-memory` | Memory package lane |
| `make check-planning` | Planning package lane |
| `make check-all` | Memory and planning package lanes |

## Policy

- Pre-commit is for formatting and lint.
- Full tests should run in CI and in explicit local validation runs such as `make check-all`.
- Prefer `make maintainer-surfaces` when a change touches generated maintainer docs, startup routing, or either package's installed contract surfaces.
