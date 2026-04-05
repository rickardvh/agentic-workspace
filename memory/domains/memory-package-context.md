# Memory Package Context

## Status

Active

## Purpose

Capture durable context imported from the previous package-local memory install so root memory ownership can replace package-local installs.

## Consolidated from

- Previous package-local current-memory notes under packages/memory/memory/current/.

## Durable context

- The memory package remains memory-only and planning-system agnostic.
- Keep bootstrap-managed files under .agentic-memory and repo-owned durable notes under memory.
- Keep shared memory workflow guidance in .agentic-memory/WORKFLOW.md and keep AGENTS.md repo-local.
- Keep memory/current/project-state.md as a short orientation note, not a task tracker.
- Keep task-context optional and sparse, only for active cross-session continuation compression.
- Prefer route, route-review, route-report, and sync-memory for memory workflow operations before broad note reading.

## Monorepo adaptation note

Root ownership now contains the installed memory system. Package-local installed memory systems should be removed after this context is preserved.

## Load when

- Editing files under packages/memory.
- Updating memory bootstrap package boundaries or workflow guidance.

## Review when

- The memory package README or bootstrap payload layout changes materially.
- Memory bootstrap workflow ownership changes between root and package surfaces.

## Failure signals

- Contributors route package-memory work to root-only notes and miss package-specific constraints.
- Package behavior diverges from the assumptions captured in this context note.

## Verify

- packages/memory/README.md
- packages/memory/bootstrap/
- packages/memory/src/
- packages/memory/tests/

## Last confirmed

2026-04-05 during monorepo installed-system consolidation
