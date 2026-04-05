# agentic-workspace

Monorepo host for two distributable packages:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

If you are landing here for the first time, the important question is usually not "how does the monorepo work?" but "which module should I use in my repo?"

## Start Here

Choose the package that matches the problem you are trying to solve:

| If you want to add... | Use... | Start with... |
| --- | --- | --- |
| Shared durable repo memory for agents and humans | `agentic-memory-bootstrap` | `packages/memory/README.md` |
| Checked-in execution planning surfaces for active work | `agentic-planning-bootstrap` | `packages/planning/README.md` |
| Both together inside this monorepo or a composed workspace flow | `agentic-workspace` | this README, then the package READMEs |

Package maturity today:

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: alpha

The root `agentic-workspace` CLI is a thin composition layer. It is useful when one workflow needs to coordinate both modules, but the package READMEs are still the best entrypoint for understanding what gets installed and why.

## Purpose

This repository is the monorepo host for `agentic-memory-bootstrap` and
`agentic-planning-bootstrap`, with shared workspace-level orchestration,
validation, and dogfooding of the shipped packages.

## What The Modules Do

| Module | Primary job | Owns | Does not own |
| --- | --- | --- | --- |
| `agentic-memory-bootstrap` | Preserve durable repo knowledge | invariants, runbooks, decisions, recurring failures, routed context | active task sequencing and backlog state |
| `agentic-planning-bootstrap` | Keep active execution aligned | roadmap candidates, active queue state, execplans, completion criteria | durable subsystem knowledge and long-lived technical memory |
| `agentic-workspace` | Compose modules at the workspace level | shared lifecycle entrypoints, preset selection, integrated status | package-internal domain logic |

Memory and planning are meant to complement each other, not absorb each other.

## Quick Start

For most external users, start with one package directly:

```bash
# Shared repository memory
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt install --target /path/to/repo

# Checked-in execution planning
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target /path/to/repo
```

Use `prompt install` when you want an agent-friendly, no-local-install entrypoint. Use `adopt` instead of `install` when the target repository already has related docs or workflow surfaces and you want a conservative merge.

If you are evaluating the combined model rather than one module in isolation, read both package READMEs first. The workspace layer is intentionally thin and assumes the module boundaries stay explicit.

## Layout

- `packages/memory/` - package workspace for `agentic-memory-bootstrap`
- `packages/planning/` - package workspace for `agentic-planning-bootstrap`
- `docs/execplans/` - active and archived execution plans
- `.github/workflows/` - unified monorepo CI workflows

## Current Status

Workspace orchestration is stable.

Root planning and memory systems own monorepo operation, package-scoped validation lanes are in place, and CI runs through root orchestration targets.

For a newcomer, the important implication is: this repository is both the packaging source and the live dogfooding environment. Some docs describe target-repository behavior, while root docs also describe how this monorepo runs itself.

## Architecture Stance

This repo currently treats two domains as standalone distributable products:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

The workspace layer composes those products, owns shared managed-surface orchestration, and provides the integrated monorepo operating model.

Routing and checks are important cross-cutting capabilities, but they are not yet treated as standalone packages. Keep them as contracts and implementation seams inside the existing products and workspace layer until dogfooding shows stable schemas, clear ownership, and repeated reuse pressure that justify extraction.

## Boundary Guide

Use these ownership tests when deciding where a feature belongs:

- Memory: durable knowledge that outlives the current task and is expensive to reconstruct quickly.
- Planning: active execution state, what matters now, what comes next, and what counts as done.
- Routing: how an agent decides what to read, trust, run, and validate for a task class.
- Checks: drift, liveness, shape, and consistency validation for installed workflow surfaces.
- Workspace: install, adopt, upgrade, uninstall, presets, integrated status, and multi-package composition.

Treat routing and checks as capabilities first, not packages by default. Extraction is warranted only when the boundary is stable enough to stand alone without leaning on sibling-package internals.

## Boundary Rules

- Memory must not become a task tracker or backlog mirror.
- Planning must not become a durable knowledge base.
- Routing must not become a shadow planning or memory system.
- Checks must not become the hidden policy owner for source-of-truth content.
- Workspace must orchestrate domain packages without absorbing their internal domain logic.

Prefer explicit seams:

- schemas and manifests
- generated artifacts derived from canonical sources
- adapters over private cross-package imports
- explicit capability detection for partial adoption

Avoid implicit cross-package assumptions, duplicated ownership of the same state, or sibling-package dependence on private internals.

## Extraction Criteria

A cross-cutting capability should become its own package only when all of the following are true:

- it has a stable ownership boundary that is not already better explained as part of memory, planning, or workspace orchestration
- it exposes explicit seams such as schemas, manifests, adapters, or generated artifacts instead of depending on sibling-package internals
- it is independently useful in selective-adoption repos rather than only as internal glue inside this monorepo
- dogfooding shows repeated reuse pressure or maintenance friction that is better solved by extraction than by keeping the capability internal

Do not extract a new package when the capability is still mostly one module's helper logic, when the boundary is still moving, or when the result would create a shell package whose real behavior still lives elsewhere.

## Selective Adoption

The ecosystem should support partial adoption. Today that means `agentic-memory-bootstrap` and `agentic-planning-bootstrap` can each stand alone while the workspace layer composes them for this monorepo.

If routing or checks are extracted later, they should preserve that property: no domain package should assume the full stack is present.

## Shared Lifecycle Entrypoint

Use `agentic-workspace` for shared lifecycle verbs that span module selection:

- `install`
- `adopt`
- `upgrade`
- `uninstall`
- `doctor`
- `status`

This root CLI is intentionally thin. It orchestrates selected modules through one workspace-level entrypoint while leaving module-specific logic and advanced flags inside the module packages.

When `--module` is omitted, `install` and `adopt` default to the current shared module set. Maintenance verbs such as `status`, `doctor`, `upgrade`, and `uninstall` default to the modules already detected in the target repo.

Supported presets:

- `full` -> `memory` + `planning`
- `memory` -> memory only
- `planning` -> planning only

## Contributing

See `docs/contributor-playbook.md` for package routing, ownership, and the smallest validation lane to run for common change types.

For agent maintainers, the primary operating path is:

1. `AGENTS.md` for startup and precedence
2. `TODO.md` for the active queue
3. one active execplan when the task is planned
4. `docs/contributor-playbook.md` for ownership and validation routing
5. `tools/AGENT_QUICKSTART.md` and `tools/AGENT_ROUTING.md` for compact generated guidance

This repo is maintained as an agent-first system. Human-readable docs matter, but the maintainer contract should stay optimized for agents that need explicit startup order, narrow validation, durable state, and cheap handoff.

Generated planning routing docs under `tools/` are mirrors of `.agentic-workspace/planning/agent-manifest.json`. Update the managed manifest and rerender those docs instead of editing the mirrors by hand.

## Environment Routing

Use one shared root environment for daily monorepo work and package validation.

The root workspace test suite includes a combined-install smoke test for the `full` lifecycle preset so the shared entrypoint is exercised against both modules together.

- Merged root lane (both packages): `make sync-all`
- Memory check lane alias: `make sync-memory`
- Planning check lane alias: `make sync-planning`

Validation entrypoints:

- `make test`
- `make lint`
- `make typecheck`
- `make format-check`
- `make verify`
- `make check`
- `make check-memory`
- `make check-planning`
- `make check-all`

`make check-memory` and `make check-planning` each perform a consolidated root dev sync first so checks remain repeatable from one workspace environment. For package-local test or lint runs, sync once from the root first, then run the package command from its package directory.

Root planning and memory installs are authoritative for monorepo operation.
Package directories now keep package source, bootstrap payloads, and test fixtures only; package-local installed runtime systems have been removed.
