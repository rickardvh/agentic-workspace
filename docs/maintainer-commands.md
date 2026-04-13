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
| `python scripts/check/check_maintainer_surfaces.py` | Run the aggregate maintainer-surface checker directly |
| `make format` | Apply Ruff formatting across workspace and packages |
| `make lint` | Run lint checks across workspace and packages |
| `make typecheck` | Run type checks across workspace and packages |
| `make render-agent-docs` | Regenerate routing docs from the planning manifest |
| `python scripts/check/check_source_payload_operational_install.py` | Run advisory checks for source/payload/root-install boundary drift |
| `make maintainer-surfaces` | Run the maintainer-surface liveness path for generated docs, startup-policy consistency, packaged payload contracts, and source/payload/root-install boundary drift |
| `make planning-surfaces` | Run the underlying planning-surface audit directly |

## Validation Lanes

| Command | Purpose |
| --- | --- |
| `make check` | Root validation lane |
| `make check-memory` | Memory package lane |
| `make check-planning` | Planning package lane |
| `make check-all` | Memory and planning package lanes |

## Policy

- Pre-commit is for formatting and lint, and also runs `make test` for commits on `master`.
- `make test`, `make test-workspace`, `make test-memory`, `make test-planning`, and the package `make test` lanes run pytest with xdist (`-n auto`) by default; override `PYTEST_PARALLEL_ARGS` when you need a different worker count or a serial run.
- Full tests should run in CI and in explicit local validation runs such as `make check-all`.
- Use `python scripts/check/check_maintainer_surfaces.py` when you want the aggregate maintainer wrapper directly; it includes the planning maintainer checks and the boundary checker when that checker exists in the repo.
- Prefer `make maintainer-surfaces` when a change touches generated maintainer docs, startup routing, either package's installed contract surfaces, or the source/payload/root-install boundary.
- Use `docs/generated-surface-trust.md` for the canonical source and freshness rules behind generated maintainer surfaces.
