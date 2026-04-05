# Project State

## Status

Active

## Scope

- Lightweight current overview for the monorepo host.

## Applies to

- AGENTS.md
- TODO.md
- docs/migration/monorepo-migration-plan.md
- memory/index.md
- .agentic-memory/WORKFLOW.md
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

- Complete migration from package-local installed systems to root-owned planning and memory systems.
- Keep package boundaries and independent release tracks intact while centralising operational routing at root.
- Enforce deterministic root and package-scoped validation entrypoints through Make and CI.

## Recent meaningful progress

- Root memory system adopted conservatively and populated with package-context summaries.
- Root planning system adopted conservatively and populated with imported planning archives from packages/planning.
- Root sync entrypoints now distinguish merged all-package sync from package-scoped sync lanes.
- CI now routes package checks through root make entrypoints.

## Blockers

- None currently noted.

## High-level notes

- Keep migration execution in docs/migration/monorepo-migration-plan.md while consolidation is active.
- Package-local installed systems are migration residue and should not remain operational authorities.
- Imported package planning history is preserved under docs/execplans/archive/imported-planning-package/.
- Use root memory domain notes for package-origin context after package-local uninstall cleanup.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- The note drifts away from the current repository reality.

## Verify

- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm the current focus, recent progress, and blockers still reflect the repo.
- Confirm root and CI entrypoints still map to merged and package-scoped sync lanes.

## Verified against

- `memory/index.md`
- `.agentic-memory/WORKFLOW.md`
- `AGENTS.md`
- `TODO.md`
- `docs/migration/monorepo-migration-plan.md`
- `README.md`
- `Makefile`
- `.github/workflows/ci.yml`

## Last confirmed

2026-04-05 during root installed-system consolidation
