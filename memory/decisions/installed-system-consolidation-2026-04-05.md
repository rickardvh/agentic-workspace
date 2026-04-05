# Decision: Root-Owned Installed Systems

## Status

Accepted

## Date

2026-04-05

## Load when

- Deciding operational ownership between root and package-local systems.
- Reviewing root-orchestration changes that affect planning or memory routing.

## Review when

- Root orchestration, CI validation, or package cleanup strategy changes.

## Failure signals

- Duplicate installed systems become operational authorities again in package roots.
- Root and package workflows diverge on where planning or memory ownership lives.

## Decision

Use a single root-owned installed memory system and a single root-owned installed planning system for the monorepo, then remove package-local installed systems from packages/memory and packages/planning.

## Why

- Duplicate installed systems create conflicting ownership for routing, workflow entrypoints, and current-state notes.
- uv workspace resolution remains workspace-wide from member directories, so cwd alone does not provide robust system isolation.
- Root orchestration and CI are easier to reason about when operational systems are owned once at root.

## Consequences

- Package knowledge and planning context must be intentionally preserved in root-owned notes before package-local operational copies are removed.
- Package-level validation still runs through package-scoped sync/check lanes.
- Package-local installed-system files are no longer authoritative for monorepo operations.

## Follow-through

- Keep package context summaries in memory/domains/memory-package-context.md and memory/domains/planning-package-context.md.
- Use uninstall commands in package roots to clean package-local installed-system surfaces.

## Verify

- TODO.md
- Makefile
- .github/workflows/ci.yml

## Last confirmed

2026-04-05 during root consolidation and package cleanup
