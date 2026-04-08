# Capability-Aware Execution Contract

## Goal

- Define the first planning/workflow contract for classifying task capability fit so agents can choose cheap direct execution, stronger planning, delegation, or escalation without hard-coded vendor or model assumptions.

## Non-Goals

- Build automatic model routing.
- Hard-code vendor-specific or model-specific execution matrices.
- Replace the direct-task versus execplan boundary with a heavier new planning layer.

## Active Milestone

- Status: completed
- Scope: add one canonical planning contract for task-shape capability fit, wire it into planning package docs and shipped payload surfaces, and prove the new contract with narrow planning-package and root-surface validation.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and ready to archive.

## Blockers

- None.

## Touched Paths

- `packages/planning/`
- `docs/`
- `TODO.md`

## Invariants

- The contract must stay task-shape based rather than vendor-specific.
- Direct task versus execplan remains the primary planning boundary; capability fit should sharpen that decision rather than replace it.
- Delegation and stronger-agent guidance must remain optional so the contract still works for a single agent operating alone.

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py tests/test_packaging.py tests/test_skills_catalog.py`
- `uv run pytest tests/test_workspace_cli.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- One canonical planning/workflow doc defines capability-fit dimensions and recommendation categories.
- Planning package docs and shipped payload surfaces point to that contract instead of scattering partial rules.
- The planning package tests and root planning-surface checks prove the new shipped contract is present and wired correctly.

## Drift Log

- 2026-04-08: Promoted directly from GitHub issue `#9` after the issue identified a planning-level gap between direct-task/execplan guidance and durable capability-fit guidance for escalation, delegation, and cheaper execution paths.
- 2026-04-08: Completed by shipping `docs/capability-aware-execution.md` in the planning payload, wiring the planning README, shipped AGENTS, manifest-generated quickstart/routing, and maintainer playbook back to that contract, and refreshing the root install from the updated package payload.
