# TODO

`TODO.md` is the single source of truth for milestone status, pending work, and short handoff context.

Use it for:

- what is next
- what is in progress
- what is blocked
- what decision is pending

Do not use it for durable technical memory. Put subsystem knowledge, runbooks, invariants, and recurring failures in `/memory`.

Keep this file execution-focused only. Replace completed detail with short outcome notes once it no longer affects next actions.

## Current focus

- Keep repository housekeeping files aligned with current workspace needs.
- Keep repository and bootstrap documentation aligned with the upgrade system and current maintainer workflow.

## Active milestones

### Milestone: Deterministic Upgrade System

Status: done

Outcome:

- Added deterministic bootstrap versioning, doctor/adopt/upgrade flows, conservative upgrade rules, clearer installer documentation, and smarter optional-append detection for equivalent `Makefile` targets.

### Milestone: Workflow Document Split

Status: done

Outcome:

- Split reusable workflow rules into `memory/system/WORKFLOW.md` and reduced `AGENTS.md` to a local entrypoint in both the repo and bootstrap payload.

### Milestone: Memory System Hardening

Status: done

Outcome:

- Tightened memory hygiene rules, standardised note templates, and improved installer safety around nested targets and payload inspection.

### Milestone: Git Ignore Baseline

Status: done

Outcome:

- Expanded `.gitignore` to cover the repo's local Python artefacts as well as `.agent-work/`.

## Blocked / pending decisions

- None.

## Handoff notes

- No open follow-up for this task.

## Recurring maintenance

- review `/memory`
- prune stale TODO detail
