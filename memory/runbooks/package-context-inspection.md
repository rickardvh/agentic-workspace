# Package Context Inspection

## Purpose

Keep the durable reason for package-context inspection separate from the executable checklist.

Use `memory/skills/package-context-inspection/SKILL.md` for the actual inspection flow.

## Load when

- Editing files under `packages/memory/` or `packages/planning/`.
- Memory doctor reports package-context overlap or procedural drift.

## Review when

- Package layout, validation surfaces, or package-context routing changes materially.

## Rule

The durable package-context note should explain only package-specific authority and boundaries. If an agent needs a checklist, route it to the checked-in skill instead of adding steps here.

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

2026-04-08 after adding the checked-in package-context inspection skill
