# Archive-Plan Cleanup Hardening

## Goal

- Make `agentic-planning-bootstrap archive-plan --apply-cleanup` reliably clear completed active work from the repo's compact `TODO.md` queue shape so plan archival does not leave manual planning residue.

## Non-Goals

- No issue-tracker integration.
- No broad redesign of TODO parsing or planning summary semantics.
- No roadmap or review workflow expansion beyond the cleanup defect.

## Active Milestone

- ID: archive-plan-cleanup-hardening
- Status: completed
- Scope: extend archive cleanup to support the compact `## Now` plus `## Action` TODO shape, add regression coverage, refresh the root install, and validate the full local lane before commit.
- Ready: ready
- Blocked: none

## Immediate Next Action

- Archive this completed plan with `archive-plan --apply-cleanup`, verify that the active queue returns to idle automatically, then commit the fix.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `.agentic-workspace/planning/execplans/archive-plan-cleanup-hardening-2026-04-09.md`
- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/tests/test_installer.py`

## Invariants

- Planning remains issue-tracker agnostic.
- `archive-plan --apply-cleanup` stays narrow and file-native.
- Root, payload, and source copies stay aligned before the repo relies on the fix.

## Validation Commands

- `cd packages/planning && uv run pytest`
- `cd packages/memory && uv run pytest`
- `uv run pytest`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run python scripts/check/check_memory_freshness.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- Archiving a completed execplan with `--apply-cleanup` removes compact active queue residue from `TODO.md`.
- Planning package regression coverage proves the compact TODO cleanup path.
- Full local tests and validation pass before commit.
- Active planning state returns to idle after the fix lands.

## Drift Log

- 2026-04-09: Promoted immediately from dogfooded archive cleanup residue after the front-door defaults tranche.
- 2026-04-09: Completed the cleanup fix, regression coverage, root refresh, and full local validation lane.
