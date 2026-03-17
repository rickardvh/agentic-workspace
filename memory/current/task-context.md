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

- Reduce the default documentation surface and push repeatable workflow logic out of always-read prose and into the skill boundary.

## Active surfaces

- `AGENTS.md`
- `README.md`
- `bootstrap/AGENTS.md`
- `bootstrap/README.md`
- `memory/current/project-state.md`
- `memory/current/active-decisions.md`
- `memory/index.md`
- `memory/system/SKILLS.md`
- `skills/README.md`
- `skills/memory-capture/SKILL.md`
- `skills/memory-refresh/SKILL.md`
- `skills/memory-router/SKILL.md`
- `memory/system/WORKFLOW.md`
- `bootstrap/AGENTS.md`
- `bootstrap/memory/index.md`
- `bootstrap/memory/system/WORKFLOW.md`

## Key constraints

- Keep the product memory-only and task-system agnostic.
- `task-context.md` is a checked-in compression note, not a task list, detailed plan, or historical log.
- Keep the base memory system usable without skills.
- Do not reintroduce `TODO.md`, Beads, or `.agent-work/` as core contract surfaces.
- Do not blur the line between bundled product skills and the mandatory bootstrap payload.
- Keep the default read path close to `AGENTS.md` and `memory/index.md`.

## Relevant memory

- `memory/current/project-state.md`
- `memory/current/active-decisions.md`
- `memory/index.md`
- `memory/system/SKILLS.md`
- `memory/system/WORKFLOW.md`
- `memory/system/UPGRADE.md`

## Notes

- Shared docs should make the files-vs-skills boundary explicit without turning the bootstrap into a skills dependency.
- The first wave of shipped memory skills should stay narrow and operate on visible checked-in outcomes.
- Bundled skills should be discoverable from the installed product without becoming part of the repo payload.
- `skills/` should be treated as the optional product skill catalogue, not a separate local-only layer for this source repo.
- `memory/system/WORKFLOW.md` and `memory/index.md` should keep rules and routing, not long repeatable procedures.

## Failure signals

- Shared docs blur durable memory and procedural workflows.
- Skills start acting like hidden storage instead of executable procedures.
- The shipped contract becomes harder to understand without the skills layer.
- The product docs describe skills as available, but do not explain how to install them.
- Agents are told to read more than `AGENTS.md` plus `memory/index.md` by default.

## Verify

- Confirm the shared docs describe the files-vs-skills split consistently.
- Confirm the shipped skills remain optional and are not treated as installed payload.
- Validate the new skills with the skill validator in the repo dev environment.
- Confirm `AGENTS.md` and `memory/index.md` now form the default read path.

## Last confirmed

2026-03-17 during token-saving workflow pass
