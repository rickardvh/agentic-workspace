# Automatic Skill Selection Routing

## Goal

- Let the workspace recommend the right bundled or repo-owned skills from task text so users can ask for outcomes without needing to know skill names.

## Non-Goals

- Build a generic LLM runtime inside the workspace CLI.
- Treat loose directory scanning as enough for skill selection quality.
- Collapse bundled and repo-owned skills into one undifferentiated authority class.

## Active Milestone

- Status: completed
- Scope: add explicit task-matching metadata to skill registries, expose a workspace recommendation path on top of the registry-backed discovery surface, document the selection contract, and prove the routing with narrow tests.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and ready to archive.

## Blockers

- None.

## Touched Paths

- `src/agentic_workspace/`
- `packages/planning/`
- `packages/memory/`
- `memory/skills/`
- `docs/`
- `README.md`
- `TODO.md`

## Invariants

- Users should be able to ask for outcomes without knowing skill ids.
- Skill recommendation must remain registry-backed and explainable.
- Bundled package skills and repo-owned skills must stay distinct in selection output and ownership metadata.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py tests/test_workspace_lifecycle.py`
- `cd packages/planning && uv run pytest tests/test_installer.py tests/test_skills_catalog.py`
- `cd packages/memory && uv run pytest tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Skill registries carry explicit activation hints suitable for task matching.
- `agentic-workspace skills` can recommend likely skills for a task description and explain why they matched.
- The installed planning and memory surfaces preserve the same recommendation contract after upgrade.

## Drift Log

- 2026-04-08: Promoted after confirming that explicit skill names should be optional expert overrides, not the normal operating mode for users or agents.
- 2026-04-08: Completed by adding activation hints to bundled and repo-owned skill registries, teaching `agentic-workspace skills --task ...` to rank likely matches with reasons, and refreshing the installed planning and memory surfaces so the root workspace exposes the same recommendation contract.
