# Unified Lifecycle Orchestrator

## Goal

- Converge shared lifecycle entrypoints behind one workspace-level orchestrator that installs and manages selected modules without collapsing module ownership boundaries.

## Non-Goals

- Replace module-specific advanced flags or domain-specific maintenance commands in this tranche.
- Extract routing or checks into standalone packages before their contracts are proven.
- Remove the standalone module CLIs before the workspace-level entrypoint proves itself in dogfooding.

## Active Milestone

- Status: completed
- Scope: make default module selection lifecycle-aware so maintenance verbs target installed modules by default while install/adopt remain explicit composition entrypoints.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and promote the next roadmap candidate only if it can be bounded cleanly.

## Blockers

- None.

## Touched Paths

- TODO.md
- .agentic-workspace/planning/execplans/
- README.md
- Makefile
- pyproject.toml
- src/
- tests/

## Invariants

- Workspace lifecycle orchestration must compose module installers rather than reimplement module-owned domain logic.
- Module packages keep ownership of their payloads, schemas, advanced flags, and validation semantics.
- Partial adoption remains valid: the orchestrator must support selecting only the installed or desired modules.
- Repo planning surfaces stay compact and reflect the active tranche accurately.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py
- uv run ruff check src tests
- uv run ty check src
- uv run agentic-workspace modules --format json

## Completion Criteria

- A root `agentic-workspace` CLI exists for shared `install`, `adopt`, `upgrade`, `uninstall`, `doctor`, and `status` flows.
- The root CLI accepts explicit module selection and defaults to the current shared module set.
- Root validation covers the new workspace CLI.
- Repo docs describe the root CLI as the shared lifecycle entrypoint while keeping module-specific logic inside the module packages.

## Drift Log

- 2026-04-05: Plan activated from the roadmap to converge lifecycle UX above the module packages before more extraction work expands the surface area.
- 2026-04-05: Milestone 1 complete: added a thin root `agentic-workspace` CLI for shared install/adopt/upgrade/uninstall/doctor/status verbs, wired root validation around it, and documented it as the shared lifecycle entrypoint while keeping module-specific logic inside the module packages.