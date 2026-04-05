# Project State

## Status

Workspace-orchestrator cleanup complete; active queue clear

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

- Keep the workspace-orchestrator layout stable while using normal development here as product dogfooding.
- Bound the next tranche around workspace-level lifecycle orchestration so install/adopt/upgrade/uninstall flows can converge above the module packages.
- Preserve package boundaries and independent release tracks while continuing to generalise from repo use without overfitting to this monorepo.

## Recent meaningful progress

- Consolidated path namespace: refactored both memory and planning bootstraps to use `.agentic-workspace/` parent directory.
- Added a root `agentic-workspace` CLI that orchestrates shared lifecycle verbs across selected modules and introduced root validation coverage for that wrapper layer.
- Updated all path constants, templates, docstrings, and test fixtures across both packages (156/158 memory tests, 25/25 planning tests passing).
- Verified end-to-end: both bootstraps successfully generate install plans targeting new consolidated structure.
- Fixed syntax warnings and package escape sequences in installers and test fixtures.
- Migrated current repo's installed systems from old dotfiles to new consolidated structure.
- Seeded the workspace-level orchestrator contract and initial ownership ledger so future installer cleanup can converge on one source of truth.
- Moved planning-owned manifest and helper scripts under `.agentic-workspace/planning/`, kept root scripts as compatibility wrappers, and regenerated root `tools/` routing surfaces from the managed planning manifest.
- Restored wrapper compatibility for module-level overrides such as `REPO_ROOT`, which package tests and downstream tooling rely on when loading helper scripts as Python modules.
- Switched both package installers to derive module-managed roots from the shared ownership ledger, using packaged ownership mirrors as distribution fallbacks.
- Closed the workspace-orchestrator execplan and cleared the active TODO surface after validation passed for both packages and the root planning checker.

## Blockers

- None currently noted.

## High-level notes

- Package-local runtime fixtures or payload copies should not become operational authorities.
- Use root memory domain notes for package-origin context after package-local uninstall cleanup.
- Product-managed additions should stay visibly fenced off from repo-owned instructions; a thin pointer block in `AGENTS.md` is preferred over mixed ownership prose.
- Improvement signals from dogfooding should become plan updates, roadmap candidates, or memory pressure notes rather than staying implicit in ad hoc experience.
- `.agentic-workspace/WORKFLOW.md` now owns the shared startup contract; root `AGENTS.md` should continue shrinking toward a thin repo entrypoint.

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

2026-04-05 after closing the workspace-orchestrator execution tranche
