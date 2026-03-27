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

- Make "upgrade memory" resolve through a permanent checked-in repo-local skill instead of relying on bundled-skill discovery or prompt ceremony.

## Active surfaces

- `AGENTS.md`
- `bootstrap/AGENTS.md`
- `bootstrap/memory/skills/README.md`
- `bootstrap/memory/system/SKILLS.md`
- `README.md`
- `memory/current/project-state.md`
- `memory/current/task-context.md`
- `memory/index.md`
- `memory/skills/README.md`
- `memory/system/SKILLS.md`
- `memory/system/VERSION.md`
- `memory/system/WORKFLOW.md`
- `src/repo_memory_bootstrap/installer.py`
- `src/repo_memory_bootstrap/cli.py`
- `tests/test_installer.py`

## Key constraints

- Keep the product memory-only and task-system agnostic.
- `task-context.md` is a checked-in compression note, not a task list, detailed plan, or historical log.
- The default read path should stay close to `AGENTS.md` plus `memory/index.md`.
- Shared policy must remain available, but not mandatory to load on every task.
- Prefer targeted command output over broad file reads when it materially reduces context cost.
- Self-hosted verification must exercise the installed tool path against this repo, not just the source files.
- Package version and bootstrap payload version are separate; Git-based upgrade visibility depends on bumping `pyproject.toml`.
- The checked-in upgrade skill must stay minimal and invariant; evolving upgrade choreography belongs in the packaged implementation, not in the repo-local entrypoint.

## Relevant memory

- `memory/current/project-state.md`
- `memory/current/active-decisions.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`

## Notes

- `memory/skills/memory-upgrade/` is now the stable repo-local entrypoint for "upgrade memory".
- Bundled `skills/bootstrap-upgrade/` remains the packaged implementation surface and can evolve independently.
- Prompt and README text should steer normal upgrade intent toward the checked-in skill rather than making bundled-skill discovery the primary path.
- Upgrade should not broaden into generic repo-memory maintenance unless the user explicitly asks for that follow-up.

## Failure signals

- Agents are still implicitly encouraged to read `memory/system/WORKFLOW.md` on every task.
- `memory/index.md` keeps expanding into a mini handbook instead of a routing file.
- Repo-local instructions keep growing instead of deferring repeatable logic to tools or skills.

## Verify

- Run pytest and the freshness audit.
- Run doctor, upgrade, and verify-payload against this repo.
- Confirm the installed repo reports the new payload version, that `verify-payload` catches version drift, and that the installed `memory/` tree only differs from payload where the contract allows.
- Confirm that `prompt upgrade` now points to the checked-in `memory-upgrade` entrypoint and that the local skill exists in the installed payload.

## Last confirmed

2026-03-24 during checked-in upgrade-skill hardening
