# Memory Package Context

## Status

Active

## Purpose

Durable context for `packages/memory/`.

## Durable context

- The memory package remains memory-only and planning-system agnostic.
- Package source of truth lives under `packages/memory/src/`, `packages/memory/bootstrap/`, and `packages/memory/tests/`; the repo root is only the dogfooded install.
- Primary proof surface for package contract changes is `packages/memory/tests/` plus payload verification.
- Repeatable inspection steps belong in `memory/runbooks/package-context-inspection.md`, not in this context note.

## Monorepo adaptation note

Root ownership now contains the installed memory system. For the owning rationale, load `memory/decisions/installed-system-consolidation-2026-04-05.md` instead of expanding this context note.

## Load when

- Editing files under `packages/memory/`.

## Review when

- The memory package source, payload, or test layout changes materially.

## Failure signals

- The note starts carrying workflow steps instead of package facts.

## Verify

- `packages/memory/README.md`
- `packages/memory/bootstrap/`
- `packages/memory/tests/`
- `memory/runbooks/package-context-inspection.md`

## Last confirmed

2026-04-08 after moving repeatable inspection procedure into a runbook
