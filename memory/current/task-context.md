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

- Harden the bootstrap adoption and populate handoff so a fresh install is audit-clean and the next agent step is obvious.

## Active surfaces

- `README.md`
- `bootstrap/memory/current/project-state.md`
- `bootstrap/memory/current/task-context.md`
- `memory/current/project-state.md`
- `memory/index.md`
- `memory/current/task-context.md`
- `skills/README.md`
- `skills/bootstrap-adoption/SKILL.md`
- `skills/bootstrap-populate/SKILL.md`
- `src/repo_memory_bootstrap/cli.py`
- `src/repo_memory_bootstrap/installer.py`
- `tests/test_installer.py`

## Key constraints

- Keep the product memory-only and task-system agnostic.
- `task-context.md` is a checked-in compression note, not a task list, detailed plan, or historical log.
- Adoption alone must leave starter notes in a freshness-audit-clean state.
- Keep `bootstrap-populate` as a skill-driven follow-up rather than a semantic write command in the CLI.
- Self-hosted verification must exercise the installed tool path against this repo, not just the source files.

## Relevant memory

- `memory/current/project-state.md`
- `memory/current/active-decisions.md`
- `memory/system/UPGRADE.md`

## Notes

- The shipped current-memory starter notes now need real install-time `Last confirmed` dates rather than audit-breaking placeholders.
- The adoption prompt and summary should hand off to `prompt populate` without implying the CLI can semantically fill repo context by itself.
- The smoke flow to preserve is: adopt -> freshness audit -> doctor -> prompt populate.

## Failure signals

- Fresh adoption leaves invalid `Last confirmed` metadata or placeholder-heavy current-memory files.
- Adoption output fails to make the populate follow-up obvious.
- AGENTS pointer patching still introduces awkward spacing or unclear manual-review guidance.

## Verify

- Run pytest, ruff, ty, and the freshness audit.
- Run doctor, upgrade --dry-run, and verify-payload against this repo.
- Smoke-test adopt -> audit -> doctor -> prompt populate in a temporary repo.

## Last confirmed

2026-03-18 during adoption/populate hardening
