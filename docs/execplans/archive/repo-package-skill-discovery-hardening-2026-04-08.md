# Repo/Package Skill Discovery Hardening

## Goal

- Make bundled package skills explicitly registered on install or upgrade, keep repo-owned skills on a separate registry surface, and expose a trustworthy workspace discovery surface before falling back to raw `SKILL.md` walking.

## Non-Goals

- Invent a global runtime plugin system for arbitrary skills.
- Treat repo-owned skills as package-managed payload.
- Make filesystem scanning the primary discovery contract again.

## Active Milestone

- Status: completed
- Scope: add explicit skill registries for bundled and repo-owned skills, update the workspace and memory discovery surfaces to use them, document the separation clearly, and validate the result with package and workspace tests.
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
- `TODO.md`
- `ROADMAP.md`

## Invariants

- Package-managed bundled skills and repo-owned skills must stay separate in ownership and discovery output.
- Explicit registries should be the primary discovery contract; directory scanning is fallback only.
- The workspace layer may aggregate skill discovery, but package-owned skill metadata should remain package-local.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py tests/test_workspace_lifecycle.py`
- `cd packages/planning && uv run pytest tests/test_installer.py tests/test_skills_catalog.py`
- `cd packages/memory && uv run pytest tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Bundled package skills ship with explicit registries that survive install or upgrade.
- Repo-owned skills have a separate checked-in registry path.
- The workspace exposes a trustworthy skills discovery surface that prefers registries over raw filesystem scanning.

## Drift Log

- 2026-04-08: Promoted after an explicit request to use the installed planning autopilot skill failed because the session skill registry and repo/package skill surfaces were not reconciled by one explicit discovery contract.
- 2026-04-08: Completed by shipping explicit bundled-skill and repo-owned skill registries, adding `agentic-workspace skills`, and refreshing the root install so the installed planning and memory surfaces expose the same contract.
