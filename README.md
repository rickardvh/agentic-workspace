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

## Workspace Layer

`agentic-workspace` is the thin composition layer for shared lifecycle verbs when a repository uses both modules.

Rule of thumb:

- add module-specific lifecycle flags or domain rules to the package CLI first
- add them to the workspace layer only when there is a clear cross-module reason

## Maturity Today

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: alpha

See `docs/maturity-model.md` for what `alpha` and `beta` mean here.

## Purpose

This repository is the monorepo host for `agentic-memory-bootstrap` and
`agentic-planning-bootstrap`, with shared workspace-level orchestration,
validation, and dogfooding of the shipped packages.

## Layout

- `packages/memory/` - package workspace for `agentic-memory-bootstrap`
- `packages/planning/` - package workspace for `agentic-planning-bootstrap`
- `docs/execplans/` - active and archived execution plans
- `.github/workflows/` - unified monorepo CI workflows

## Current Status

Workspace orchestration is stable.

Root planning and memory systems own monorepo operation, package-scoped validation lanes are in place, and CI runs through root orchestration targets.

Some docs describe target-repository behavior, while root docs also describe how this monorepo runs itself.

## Docs Map

For adopters:

- `docs/which-package.md`
- `docs/architecture.md`
- `docs/maturity-model.md`

For boundaries and ecosystem policy:

- `docs/boundary-and-extraction.md`
- `docs/ecosystem-roadmap.md`
- `docs/design-principles.md`

For maintainers:

- `docs/contributor-playbook.md`
- `docs/maintainer-commands.md`
- `docs/collaboration-safety.md`

## Contributing

For agent maintainers, the primary operating path is: `AGENTS.md` -> `TODO.md` -> one active execplan -> `docs/contributor-playbook.md`.

Use `docs/contributor-playbook.md` for routing and `docs/maintainer-commands.md` for the command index.

Generated planning routing docs under `tools/` are derived from `.agentic-workspace/planning/agent-manifest.json`; rerender them instead of editing by hand.
