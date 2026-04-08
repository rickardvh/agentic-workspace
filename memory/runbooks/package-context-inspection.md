# Package Context Inspection

## Purpose

Keep repeatable package-context inspection steps out of the durable package-context notes.

Use this runbook when memory doctor or normal work suggests the package context notes have become stale, overly procedural, or overlapping.

## Load when

- Editing files under `packages/memory/` or `packages/planning/`.
- Memory doctor reports package-context overlap or procedural drift.

## Review when

- Package layout, validation surfaces, or package-context routing changes materially.

## Steps

1. Confirm which package is being edited and load only that package's `AGENTS.md`, README, source, bootstrap payload, and tests.
2. Re-check the corresponding package-context note for durable facts only.
3. Move repeatable verification procedure into this runbook instead of adding it to the package-context note.
4. If root operational symptoms reveal a product problem, route that signal into planning, docs, or memory instead of expanding the context note.

## Failure signals

- A package-context note starts carrying step-by-step workflow.
- Both package-context notes keep repeating the same generic boundary language.
- Package work depends on root operational symptoms more than package source, payload, or tests.

## Verify

- `packages/memory/README.md`
- `packages/planning/README.md`
- `packages/memory/tests/`
- `packages/planning/tests/`

## Last confirmed

2026-04-08 during final roadmap cleanup
