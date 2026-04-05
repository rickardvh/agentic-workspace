# Project State

## Status

Phase-4 root orchestration complete; migration foundation stabilized

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

- Consolidate bootstrap namespace: move `.agentic-memory/` and `.agentic-planning/` to `.agentic-workspace/{memory,planning}/`.
- Ensure both bootstraps work end-to-end with new paths and pass all validation tests.
- Maintain package boundaries and independent release tracks while converging on unified namespace convention.
- Define the next cleanup tranche: a workspace-owned orchestrator file and fenced product-managed insertions so shared guidance stops blending into repo-owned `AGENTS.md` prose.

## Recent meaningful progress

- Consolidated path namespace: refactored both memory and planning bootstraps to use `.agentic-workspace/` parent directory.
- Updated all path constants, templates, docstrings, and test fixtures across both packages (156/158 memory tests, 25/25 planning tests passing).
- Verified end-to-end: both bootstraps successfully generate install plans targeting new consolidated structure.
- Fixed syntax warnings and package escape sequences in installers and test fixtures.
- Migrated current repo's installed systems from old dotfiles to new consolidated structure.

## Blockers

- None currently noted.

## High-level notes

- Keep migration execution in docs/migration/monorepo-migration-plan.md while consolidation is active.
- Package-local installed systems are migration residue and should not remain operational authorities.
- Imported package planning history is preserved under docs/execplans/archive/imported-planning-package/.
- Use root memory domain notes for package-origin context after package-local uninstall cleanup.
- Product-managed additions should stay visibly fenced off from repo-owned instructions; a thin pointer block in `AGENTS.md` is preferred over mixed ownership prose.

## Failure signals

- The overview becomes a task list instead of a short current-state note.
- The note drifts away from the current repository reality.

## Verify

- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm the current focus, recent progress, and blockers still reflect the repo.
- Confirm root and CI entrypoints still map to merged and package-scoped sync lanes.

## Verified against

- `memory/index.md`
- `.agentic-workspace/memory/WORKFLOW.md`
- `AGENTS.md`
- `TODO.md`
- `docs/migration/monorepo-migration-plan.md`
- `README.md`
- `Makefile`
- `.github/workflows/ci.yml`

## Last confirmed

2026-04-05 during root installed-system consolidation
