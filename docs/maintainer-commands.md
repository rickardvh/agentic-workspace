# Maintainer Commands

This page is the single-source command index for routine repo maintenance.

Use this page when you need the canonical command to run, not the broader routing, ownership, or workflow-history context.

## Setup

| Command | Purpose |
| --- | --- |
| `make setup` | Sync the shared root environment and install local git hooks |
| `make install-hooks` | Reinstall the repo-managed local git hooks for this clone |
| `make sync-all` | Sync the shared root environment for all workspace packages |

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

- The repo-managed pre-commit Git hook formats staged Ruff-managed files, stages those formatter edits, and then runs the configured lint, branch-specific test gate, and absolute-path checks.
- Reinstall hooks with `make install-hooks`; do not use `uv run pre-commit install` directly unless you intentionally want the stock pre-commit wrapper instead of the repo-managed hook behavior.
- `make test`, `make test-workspace`, `make test-memory`, `make test-planning`, and the package `make test` lanes run pytest with xdist (`-n auto`) by default; override `PYTEST_PARALLEL_ARGS` when you need a different worker count or a serial run.
- Full tests should run in CI and in explicit local validation runs such as `make check-all`.
- Use `python scripts/check/check_maintainer_surfaces.py` when you want the aggregate maintainer wrapper directly; it includes the planning maintainer checks and the boundary checker when that checker exists in the repo.
- Prefer `make maintainer-surfaces` when a change touches generated maintainer docs, startup routing, either package's installed contract surfaces, or the source/payload/root-install boundary.
- Use `docs/generated-surface-trust.md` for the canonical source and freshness rules behind generated maintainer surfaces.
