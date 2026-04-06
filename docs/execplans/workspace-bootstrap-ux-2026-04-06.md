# Workspace Bootstrap UX

## Goal

- Implement the root `agentic-workspace` bootstrap and lifecycle UX so adopters can start with one obvious `init` command, select modules or presets, get conservative behavior in existing repos, and receive a structured report plus repo-specific handoff prompt when mechanical bootstrap is not enough.

## Non-Goals

- Reimplement memory or planning package domain rules inside the workspace layer.
- Remove direct module CLIs for maintainers or power users.
- Turn the workspace layer into a monolithic owner of planning or memory semantics.

## Active Milestone

- Status: in-progress
- Scope: ship the root lifecycle contract from the UX spec across planning surfaces, root CLI behavior, report/prompt aggregation, regression coverage, and adopter-facing docs.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Decide whether the current workspace bootstrap tranche is complete enough to archive, or whether one more pass is needed to tighten root lifecycle docs and real-world fixture coverage beyond the current CLI regression suite.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/
- src/agentic_workspace/
- tests/
- README.md

Keep this as a scope guard, not a broad file inventory.

## Invariants

- The root workspace layer must stay thin and compose module installers instead of duplicating their logic.
- `init` must default to a full install while preserving conservative adopt behavior when existing workflow surfaces are present.
- The workspace report and prompt must be derived from actual repo detection and module results, not generic boilerplate.
- Module-specific CLIs remain valid and documented as advanced or package-local paths.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py
- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces

## Completion Criteria

- The root CLI exposes `init`, `status`, `doctor`, `upgrade`, and `uninstall` with preset/module selection rules that match the spec.
- `init` classifies target repos into clean install, conservative adopt, or high-ambiguity adopt and routes module commands accordingly.
- Workspace JSON output includes the required bootstrap report fields, and text output includes the required summary plus prompt requirement level.
- The workspace layer can print and/or write a repo-specific handoff prompt based on actual detection results.
- Adopter docs recommend the root `agentic-workspace init` path first while keeping direct module CLIs available as advanced options.

## Drift Log

- 2026-04-06: Promoted from the workspace bootstrap UX specification so the public entrypoint, report contract, and handoff workflow become explicit product behavior instead of an implicit thin wrapper.
- 2026-04-06: Dogfooding the root CLI showed that `init` had a useful top-level summary but the other lifecycle verbs still exposed mostly raw module reports, so the first hardening milestone standardized those summary categories before pushing further into adopt heuristics.
- 2026-04-06: Tightening messy-repo `init` coverage showed that partial-state detection and ownership-reconciliation warnings need to travel together in high-ambiguity cases, so the regression suite now exercises both instead of pretending they are separate concerns.
