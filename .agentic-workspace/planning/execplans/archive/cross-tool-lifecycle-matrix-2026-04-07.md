# Cross-Tool Lifecycle Matrix Hardening

## Goal

Define and test the install/adopt/upgrade/uninstall/idempotence contract for all three bootstrap packages (root workspace, planning, memory) to ensure critical lifecycle transitions are safe, predictable, and non-destructive. Prevent silent adoption failures and upgrade breakage by validating state transitions at the CLI and package level.

## Non-Goals

- Full end-to-end orchestration tests (delegate to integration test suite)
- User manual/documentation (lifecycle behavior is self-evident if contract is sound)
- Artifact signing or cryptographic verification
- Multi-repo coordination logic

## Active Milestone

- Status: completed
- Scope:
  - Define lifecycle scenarios for each package (install, adopt, upgrade, uninstall, idempotence checks)
  - Implement test suite for each package validating state transitions
  - Verify upgrade paths preserve durable state (memory, planning, workspace config)
  - Validate uninstall leaves repository clean (no orphaned files or symlinks)
  - Test idempotence: running install/adopt twice leaves same state
  - Test cross-package sequencing: install planning, then memory; verify no conflicts
- Ready: Packaging tests passing; CLI interfaces available in each package
- Blocked: None
- optional_deps: (none)

## Immediate Next Action

Archived after the narrow lifecycle validation passed.

## Blockers

- None.

## Touched Paths

- `packages/planning/tests/`
- `packages/memory/tests/`
- `tests/` (root)

## Invariants

- All lifecycle operations are idempotent: running twice produces same state as running once.
- Install must be safe on clean repository; must fail gracefully on existing payload.
- Adopt must preserve durable user state (existing memory, planning notes).
- Upgrade must preserve all user-written content and only update bootstrap infrastructure.
- Uninstall must remove all bootstrap-managed content without touching user content.
- Cross-package install order must not matter (planning then memory = memory then planning).

## Validation Commands

```bash
# Root workspace lifecycle
pytest tests/test_workspace_lifecycle.py -v

# Planning package lifecycle
pytest packages/planning/tests/test_lifecycle.py -v

# Memory package lifecycle
pytest packages/memory/tests/test_lifecycle.py -v

# All combined
pytest tests/test_*lifecycle*.py packages/*/tests/test_*lifecycle*.py -v
```

## Completion Criteria

- [x] Lifecycle test suite created for root workspace, planning, and memory packages
- [x] All install/adopt/upgrade/uninstall scenarios covered
- [x] All lifecycle tests passing on clean repository state
- [x] Idempotence validated: running twice produces same state
- [x] Cross-package sequencing tested (planning+memory install order independence)
- [x] Upgrade scenario tests state preservation (memory, planning, config)
- [x] Uninstall scenario tests clean removal (no orphaned files)
- [x] All tests committed as milestone

## Drift Log

- 2026-04-07: Initial plan created; activating from ROADMAP promotion.
- 2026-04-08: Completed after root workspace, planning, and memory lifecycle tests passed in the narrow validation lane.
