# Project State

## Status

Active docs and collaboration-safety hardening in progress

## Scope

- Lightweight current overview for the monorepo host.

## Applies to

- AGENTS.md
- TODO.md
- .agentic-workspace/WORKFLOW.md
- .agentic-workspace/OWNERSHIP.toml
- memory/index.md
- docs/execplans/
- tools/agent-manifest.json

## Load when

- Starting work and needing a short current overview.
- Returning to the repository after a break.

## Review when

- The repo's current focus changes materially.
- Recent meaningful progress or blockers change.
- Main orientation docs move or change role.

## Current focus

- Keep the root workspace thin while hardening the shipped planning and memory contracts for collaboration-heavy repos.
- Preserve package boundaries and selective adoption while using this monorepo as the dogfooding surface.
- Favor liveness checks and merge-safe installed contracts over new top-level layers.

## Recent meaningful progress

- Completed the planning collaboration-safety tranche and archived it after adding active-set and completed-plan drift checks.
- Tightened the shipped memory contract so `memory/current/` is weak-authority context rather than canonical durable knowledge.
- Kept the docs ecosystem tranche active while folding in maintainer-surface and collaboration-safety follow-on work.

## Blockers

- None currently noted.

## High-level notes

- Package-local runtime fixtures or payload copies should not become operational authorities.
- Durable package and architecture facts belong in canonical memory notes or docs, not in `memory/current/`.
- Product-managed additions should stay visibly fenced off from repo-owned instructions.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- The note drifts away from the current repository reality.

## Verify

- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm the current focus, recent progress, and blockers still reflect the repo.
- Confirm root and CI entrypoints still map to merged and package-scoped sync lanes.

## Verified against

- `memory/index.md`
- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/OWNERSHIP.toml`
- `.agentic-workspace/memory/WORKFLOW.md`
- `AGENTS.md`
- `TODO.md`
- `README.md`
- `Makefile`
- `.github/workflows/ci.yml`

## Last confirmed

2026-04-06 after the planning and memory collaboration-safety tranches
