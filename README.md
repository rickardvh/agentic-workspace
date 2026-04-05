# agentic-workspace

Monorepo host for two distributable packages:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

This repository is the packaging source and dogfooding home for two external products:

- Agentic Memory, currently distributed as `agentic-memory-bootstrap`
- Agentic Planning, currently distributed as `agentic-planning-bootstrap`

## Start Here

If you are landing here for the first time, start with the chooser page:

- `docs/which-package.md`

Short version:

| If you want to add... | Use... | Start with... |
| --- | --- | --- |
| Shared durable repo memory for agents and humans | Agentic Memory | `packages/memory/README.md` |
| Checked-in execution planning surfaces for active work | Agentic Planning | `packages/planning/README.md` |
| Both together | Both packages, optionally composed through `agentic-workspace` | `docs/which-package.md` |

## Product Names

The stable ecosystem names in docs are:

- Agentic Memory
- Agentic Planning

The current package and CLI names remain:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

Treat `-bootstrap` as the current distribution identity for the checked-in contract installers, not as the only human-facing product name.

## Quick Start

For most adopters, install one package directly:

```bash
# Agentic Memory
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt install --target /path/to/repo

# Agentic Planning
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target /path/to/repo
```

Use `prompt install` for a clean bootstrap and `adopt` for conservative merge into an existing repo.

If you adopt both modules together, use `agentic-workspace` as the thin composition layer and see `docs/architecture.md` plus `docs/integration-contract.md` for the package-to-workspace boundary.

## Maturity Today

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: alpha

See `docs/maturity-model.md` for what `alpha` and `beta` mean here.

## Docs Map

For adopters:

- `docs/which-package.md`
- `docs/architecture.md`
- `docs/integration-contract.md`
- `docs/maturity-model.md`

For boundaries and ecosystem policy:

- `docs/boundary-and-extraction.md`
- `docs/ecosystem-roadmap.md`
- `docs/design-principles.md`

For maintainers:

- `docs/contributor-playbook.md`
- `docs/maintainer-commands.md`
- `docs/collaboration-safety.md`
- `docs/dogfooding-feedback.md`
- `docs/workflow-contract-changes.md`

For agent maintainers, the primary operating path is `AGENTS.md`, `TODO.md`, the active execplan, and `docs/contributor-playbook.md`.

For maintainer workflow, command routing, and generated-surface checks, go straight to `docs/contributor-playbook.md` and `docs/maintainer-commands.md`.
