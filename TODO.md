# TODO

Last pruned: 2026-04-06

## Purpose

Active queue for repository work.

## Now

- migration-fixtures: Define migration fixture scenarios (legacy adopters, partial conversions, stale residue) and add test suite for upgrade paths. Surface: docs/execplans/legacy-adopter-migration-fixtures-2026-04-07.md

## Action

- Define scenarios representing older standalone installs.
- Implement test suite validating upgrade paths preserve or safely migrate state.
- Test warning detection for incomplete state.

## Done

- packaging-tests: Completed ✅ (wheel/sdist artifact validation for all 3 packages)
- lifecycle-matrix: Completed ✅ (install/adopt/upgrade/uninstall/idempotence for all 3 packages)
