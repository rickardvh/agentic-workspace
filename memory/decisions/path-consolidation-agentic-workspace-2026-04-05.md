# Decision: Consolidate Installed Systems Under `.agentic-workspace/`

## Status

Accepted

## Date

2026-04-05

## Load when

Read this note when deciding how installed bootstrap systems should be namespaced in target repos, or when path-related lifecycle changes could reopen the directory-layout question.

## Review when

Review this note if a new bootstrap needs an install path, if namespace conflicts appear, or if adoption friction suggests the current layout is no longer the cleanest shared convention.

## Failure signals

Failure looks like target repos growing multiple top-level `.agentic-*` directories again, or new bootstraps inventing incompatible path conventions.

## Decision

Both memory and planning installed systems live under `.agentic-workspace/`, specifically `.agentic-workspace/memory/` and `.agentic-workspace/planning/`, instead of separate `.agentic-memory/` and `.agentic-planning/` roots.

## Why

One shared namespace is cleaner for multi-bootstrap repos, scales better than one dot-directory per module, and makes `.agentic-workspace/` the explicit reserved home for Agentic Workspace managed assets.

## Consequences

This path move required coordinated package-version updates, payload updates, and migration-aware upgrade behavior. Existing installs can remain on old paths until upgraded, but the shared contract now assumes the consolidated layout.

## Durable evidence

The package constants, payloads, and test fixtures were updated to the consolidated paths, and end-to-end CLI verification confirmed install plans at the new locations. Use [path-consolidation-check](../../tools/skills/path-consolidation-check/SKILL.md) for the repeatable validation workflow instead of expanding this decision note.

## Verify

Confirm the memory and planning package docs, payloads, and install/upgrade tests still point at `.agentic-workspace/{memory,planning}/`.

## Last confirmed

2026-04-05 during path consolidation refactor and end-to-end CLI testing
