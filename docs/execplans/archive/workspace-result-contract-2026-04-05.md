# Workspace Result Contract

## Goal

- Make the root orchestrator consume module results through an explicit adapter layer instead of ad hoc shape compensation inside the CLI.

## Non-Goals

- Change module package installer result types in this tranche.
- Add new module families beyond memory and planning.
- Expand the root lifecycle CLI into a richer orchestration engine before the result seam is stabilized.

## Active Milestone

- Status: completed
- Scope: extract root result normalization into an explicit adapter layer and cover the supported result shapes with tests.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and remove the finished workspace result contract candidate from the roadmap queue.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/
- src/agentic_workspace/
- tests/

## Invariants

- The root lifecycle CLI must remain a thin orchestrator.
- The adapter layer must tolerate current module result differences without forcing immediate upstream package churn.
- JSON and text output must remain stable for current supported module operations.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py
- uv run ruff check src tests
- uv run ty check src
- uv run agentic-workspace status --format json

## Completion Criteria

- The root orchestrator has a dedicated result adapter or normalization module.
- The adapter supports both current module action/result shapes without special-case code scattered through the CLI.
- Root tests cover the supported result normalization behavior.
- The roadmap no longer carries a separate open `Workspace result contract` candidate.

## Drift Log

- 2026-04-05: Plan activated after the roadmap finding was captured from real wrapper friction while orchestrating memory and planning module results.
- 2026-04-05: Milestone complete: result normalization now flows through a dedicated adapter module that handles the current module action and warning shapes without ad hoc logic in the CLI body.