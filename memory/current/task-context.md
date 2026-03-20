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

- Reduce routine token overhead by shrinking the always-read doc surface, biasing the local contract toward targeted checks, and keeping the product boundary language unambiguous.

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

## Notes

- The upgrade runbook is now obsolete; upgrade guidance should come from the prompt-driven CLI flow plus the temporary local bootstrap skill.
- Prompt output should choose one no-install runner command instead of printing both `uvx` and `pipx run` together.
- File ownership and skill-surface boundaries have been tightened; the remaining expectation is that all bootstrap and memory-facing docs keep those statements aligned.
- The top-level bundled `skills/` tree should contain only bootstrap lifecycle skills plus its catalogue README; empty or memory-skill directories there are drift.
- The current doc pass is implementing the temporary TODO backlog by folding the highest-value items into shared docs and examples rather than adding new mandatory files.

## Failure signals

- Agents are still implicitly encouraged to read `memory/system/WORKFLOW.md` on every task.
- `memory/index.md` keeps expanding into a mini handbook instead of a routing file.
- Repo-local instructions keep growing instead of deferring repeatable logic to tools or skills.

## Verify

- Run pytest and the freshness audit.
- Run doctor, upgrade, and verify-payload against this repo.
- Confirm the installed repo reports the new payload version, that `verify-payload` catches version drift, and that the installed `memory/` tree only differs from payload where the contract allows.
- Confirm the new workflow, index, and README guidance stays compact enough to preserve the small default working set.

## Last confirmed

2026-03-20 during core-guidance hardening and optional-pattern documentation
