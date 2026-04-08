# Memory Package Context

## Status

Active

## Purpose

Capture durable context imported from the previous package-local memory install so root memory ownership can replace package-local installs.

## Consolidated from

- Previous package-local current-memory notes under packages/memory/memory/current/.

## Durable context

- The memory package remains memory-only and planning-system agnostic.
- Package source of truth lives under `packages/memory/bootstrap/`; the repo root is only the operational install used for dogfooding.
- Shared memory workflow guidance lives in `.agentic-workspace/memory/WORKFLOW.md`; repo-local `AGENTS.md` stays a pointer surface.
- Primary proof surface for package contract changes: `packages/memory/tests/` plus payload verification.
- Main workflow probes for package behavior: `route`, `route-review`, `route-report`, `promotion-report`, and `sync-memory`.

## Monorepo adaptation note

Root ownership now contains the installed memory system. For the owning rationale, load `memory/decisions/installed-system-consolidation-2026-04-05.md` instead of expanding this context note.

## Load when

- Editing files under packages/memory.
- Updating memory bootstrap package boundaries or workflow guidance.

## Review when

- The memory package README or bootstrap payload layout changes materially.
- Memory bootstrap workflow ownership changes between root and package surfaces.

## Failure signals

- Package-memory work starts from root operational symptoms and skips the package payload, installer, or tests.
- Package behavior diverges from the package source, bootstrap payload, or contract assertions captured here.

## Verify

- `packages/memory/README.md`
- `packages/memory/bootstrap/`
- `packages/memory/src/`
- `packages/memory/tests/`

## Last confirmed

2026-04-08 after improvement-targeting workflow verification
