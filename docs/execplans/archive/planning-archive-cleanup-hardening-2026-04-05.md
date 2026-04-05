# Planning Archive Cleanup Hardening

## Goal

- Reduce manual residue after `archive-plan --apply-cleanup` by making the planning package clean completed roadmap and TODO references more reliably.

## Non-Goals

- Rework the full planning surface model.
- Introduce new planning surface types.
- Generalize cleanup behavior beyond clearly plan-linked residue in this tranche.

## Active Milestone

- Status: completed
- Scope: improve archive cleanup heuristics and tests for completed plan linkage in roadmap and TODO surfaces.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and remove the finished planning archive cleanup hardening candidate from the roadmap queue.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/
- packages/planning/src/
- packages/planning/tests/

## Invariants

- Archive cleanup must stay conservative and should not delete unrelated roadmap content.
- Completed TODO references linked to the archived plan should still be removable automatically when `--apply-cleanup` is used.
- The planning checker should remain green after archive cleanup runs.

## Validation Commands

- uv run pytest packages/planning/tests/test_installer.py
- uv run python scripts/check/check_planning_surfaces.py

## Completion Criteria

- The planning archive cleanup logic removes the recently observed plan-linked roadmap residue without manual follow-up edits.
- Coverage exists for the new cleanup behavior in planning package tests.
- The roadmap no longer carries a separate open `Planning archive cleanup hardening` candidate.

## Drift Log

- 2026-04-05: Plan activated after repeated archive flows showed that roadmap residue still sometimes needed manual cleanup even when `--apply-cleanup` was requested.
- 2026-04-05: Milestone complete: archive cleanup now removes matching candidate-queue residue as well as active handoff residue, with regression coverage in the planning package tests.