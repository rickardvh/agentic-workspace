# TODO

Last pruned: 2026-04-06

## Purpose

Active queue for repository work.

## Now

- lifecycle-matrix: Define and test install/adopt/upgrade/uninstall/idempotence contract for all 3 bootstrap packages. Surface: docs/execplans/cross-tool-lifecycle-matrix-2026-04-07.md

## Action

- Create execplan defining lifecycle scenarios.
- Implement test suite for root, planning, and memory lifecycle transitions.
- Validate all scenarios pass (no broken install/upgrade paths).

## Done

- packaging-tests: Completed ✅ (all 3 packages have wheel/sdist artifact tests passing)
