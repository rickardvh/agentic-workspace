# Task Context

## Status

Active

## Scope

- Lightweight checked-in current-task context compression for `agentic-memory-bootstrap`.

## Applies to

- `AGENTS.md`
- `README.md`
- `memory/current/project-state.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `bootstrap/AGENTS.md`
- `bootstrap/README.md`

## Load when

- Continuing active work after a break.
- Re-orienting on the current change without re-reading the whole repo.

## Review when

- The active work changes materially.
- The active surfaces or key constraints change.
- The note no longer reduces re-orientation cost.

## Current focus

- Reduce routine token overhead by shrinking the always-read doc surface and biasing the local contract toward targeted checks.

## Active surfaces

- `AGENTS.md`
- `bootstrap/AGENTS.md`
- `bootstrap/memory/index.md`
- `bootstrap/memory/system/WORKFLOW.md`
- `README.md`
- `memory/current/project-state.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `memory/current/task-context.md`
- `src/repo_memory_bootstrap/installer.py`

## Key constraints

- Keep the product memory-only and task-system agnostic.
- `task-context.md` is a checked-in compression note, not a task list, detailed plan, or historical log.
- The default read path should stay close to `AGENTS.md` plus `memory/index.md`.
- Shared policy must remain available, but not mandatory to load on every task.
- Prefer targeted command output over broad file reads when it materially reduces context cost.
- Self-hosted verification must exercise the installed tool path against this repo, not just the source files.
- Package version and bootstrap payload version are separate; Git-based upgrade visibility depends on bumping `pyproject.toml`.

## Relevant memory

- `memory/current/project-state.md`
- `memory/current/active-decisions.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `memory/system/UPGRADE.md`

## Notes

- The biggest remaining token sinks were long local instructions and repeated explanatory lines in `memory/index.md` and `WORKFLOW.md`.
- The installed contract should still explain the boundary, but not teach whole workflows in prose.
- This pass preserves routing and policy while cutting habitual over-reading.
- The packaged-tool update path also needs explicit versioning discipline so `uv tool upgrade` can see changes from Git installs.

## Failure signals

- Agents are still implicitly encouraged to read `memory/system/WORKFLOW.md` on every task.
- `memory/index.md` keeps expanding into a mini handbook instead of a routing file.
- Repo-local instructions keep growing instead of deferring repeatable logic to tools or skills.

## Verify

- Run pytest, ruff, ty, and the freshness audit.
- Run doctor, upgrade --dry-run, and verify-payload against this repo.
- Confirm the installed repo now reports version 12 and that the slimmer guidance is present through the tool path.

## Last confirmed

2026-03-18 during package-versioning fix
