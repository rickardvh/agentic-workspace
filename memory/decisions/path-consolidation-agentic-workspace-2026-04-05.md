# Decision: Consolidate Installed Systems Under .agentic-workspace/

## Status

Accepted

## Date

2026-04-05

## Load when

- Deciding how to namespace installed bootstrap systems to avoid bloating target repos with many dotfiles.
- Reviewing ergonomic improvements to multibootstrap installations.

## Review when

- New bootstraps are added and need to define their install paths.
- Namespace conflicts or layout challenges surface during adoption.

## Failure signals

- Target repos accumulate many `.agentic-*` directories, making the root directory cluttered.
- New bootstraps introduce conflicting naming schemes or separate structural conventions.

## Decision

Move both memory and planning installed systems from `.agentic-memory/` and `.agentic-planning/` to `.agentic-workspace/memory/` and `.agentic-workspace/planning/` respectively. This consolidates all bootstrap-managed files under a single parent.

## Why

- Cleaner namespace when multiple bootstraps target the same repository.
- Single organizational convention (`.agentic-workspace/`) scales better than per-bootstrap dotfiles.
- Reserves `.agentic-workspace/` as a reserved namespace for Agentic Systems projects.

## Consequences

- Major version bump for both agentic-memory-bootstrap and agentic-planning-bootstrap (installer path constants changed).
- Existing installations remain at old paths; users must run upgrade to migrate.
- Unified documentation and bootstrap-adoption workflows now reference single parent directory.

## Landed evidence

- Both bootstrap packages now use `.agentic-workspace/{memory,planning}/` path constants.
- Bootstrap payloads and test fixtures were updated to the consolidated paths.
- End-to-end CLI verification confirmed install plans at the new locations.

## Verify

- packages/memory/tests/test_installer.py: 156/158 passing
- packages/planning/tests/test_upgrade_source.py: 25/25 passing
- agentic-memory-bootstrap init --dry-run output shows `.agentic-workspace/memory/` copies
- agentic-planning-bootstrap install --dry-run output shows `.agentic-workspace/planning/` copies

## Last confirmed

2026-04-05 during path consolidation refactor and end-to-end CLI testing
