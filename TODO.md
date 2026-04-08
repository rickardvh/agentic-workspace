# TODO

Last pruned: 2026-04-08

## Purpose

Active queue for repository work.

## Now

- migration-fixtures: Define representative migration fixtures for legacy adopters, partial conversions, and stale residue so upgrade paths detect incomplete state and preserve user-owned content. Surface: docs/execplans/legacy-adopter-migration-fixtures-2026-04-08.md

## Action

- Define fixture shapes for older standalone installs, partial managed state, and stale residue.
- Add focused upgrade-path tests in the workspace and package layers.
- Validate warning and migration behavior without broadening into a full lifecycle redesign.

## Done

- packaging-tests: Completed (wheel/sdist artifact validation for all 3 packages)
- lifecycle-matrix: Completed (install/adopt/upgrade/uninstall/idempotence for all 3 packages)
- lifecycle-matrix: Completed (root workspace, planning, and memory lifecycle tests passed; archived execplan)
