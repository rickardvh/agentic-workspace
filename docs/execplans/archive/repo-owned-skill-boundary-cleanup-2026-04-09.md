# Repo-Owned Skill Boundary Cleanup

## Goal

- Move repo-owned general contract and checking skills into the general repo skill home so `memory/skills/` is reserved for genuinely memory-shaped workflows.

## Non-Goals

- Do not redesign bundled planning or memory skill sets.
- Do not add new skills in this slice.
- Do not change the workspace recommendation algorithm beyond what the registry-path move requires.

## Active Milestone

- ID: repo-owned-skill-boundary-cleanup
- Status: completed
- Scope: move general repo-owned skills from `memory/skills/` into `tools/skills/`, keep only memory-shaped skills under `memory/skills/`, and align registries, docs, and discovery tests with the new ownership boundary.
- Ready: ready
- Blocked: none

## Immediate Next Action

- Archive this execplan and leave the roadmap empty until fresh skill-system friction justifies another bounded slice.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/repo-owned-skill-boundary-cleanup-2026-04-09.md`
- `docs/skill-discovery-contract.md`
- `memory/skills/README.md`
- `memory/skills/REGISTRY.json`
- `tools/skills/README.md`
- `tools/skills/REGISTRY.json`
- `tools/skills/*/SKILL.md`
- `tests/test_workspace_cli.py`

## Invariants

- `memory/skills/` stays reserved for repo-owned skills whose primary purpose is operating on checked-in memory or maintaining the memory system.
- General repo-owned contract and checking skills belong under `tools/skills/`.
- Workspace skill discovery must keep repo-owned general and memory skill registries separate and queryable.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`

## Completion Criteria

- General repo-owned skills no longer live under `memory/skills/`.
- `tools/skills/REGISTRY.json` exists and enumerates the moved general skills.
- `memory/skills/REGISTRY.json` lists only genuinely memory-shaped repo-owned skills.
- Workspace skill discovery output reflects the split correctly.

## Drift Log

- 2026-04-09: Promoted from the skill-system review after the repo-owned arsenal was found to mix general contract checks into the memory-specific skill home.
- 2026-04-09: Completed by moving the general repo-owned contract skills into `tools/skills/`, leaving only memory-shaped repo skills under `memory/skills/`, and adding workspace discovery coverage for the split.
