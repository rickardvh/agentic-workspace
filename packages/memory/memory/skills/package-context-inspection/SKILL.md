---
name: package-context-inspection
description: Re-check a package context note without turning it into a workflow dump. Use when memory doctor reports package-context overlap or procedural drift for the planning or memory package notes.
---

# Package Context Inspection

Use this skill when working in `packages/memory/` or `packages/planning/` and you need the compact package-context checklist.

## Checklist

1. Confirm which package is actually being edited.
2. Read only that package's `AGENTS.md`, README, source, bootstrap payload, and tests.
3. Re-check the matching package-context note for durable boundaries only.
4. Move repeatable checklist content out of the note and keep it here or in the companion runbook.
5. If root operational symptoms reveal a product issue, route that signal into planning, docs, or memory instead of widening the package-context note.

## Typical surfaces

- `packages/memory/AGENTS.md`
- `packages/planning/AGENTS.md`
- `packages/memory/src/`
- `packages/planning/src/`
- `packages/memory/tests/`
- `packages/planning/tests/`
