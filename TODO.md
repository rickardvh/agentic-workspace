# TODO

`TODO.md` is the single source of truth for milestone status, pending work, and short handoff context.

Use it for:

- what is next
- what is in progress
- what is blocked
- what decision is pending

Do not use it for durable technical memory. Put subsystem knowledge, runbooks, invariants, and recurring failures in `/memory`.

Keep this file execution-focused only. Collapse completed detail into short outcome notes.

## Current focus

- Keep repository housekeeping files aligned with current workspace needs.

## Active milestones

### Milestone: Git Ignore Baseline

Status: done

- [x] Expand `.gitignore` beyond `.agent-work/` to cover local Python artefacts in this repo.
- [x] Verify the resulting ignore rules match the current workspace state.

Progress notes:

- 2026-03-16: Existing `.gitignore` already ignores `.agent-work/`; repo still exposes local `.venv/` and Python cache artefacts.
- 2026-03-16: `.gitignore` now also ignores `.venv/`, `__pycache__/`, `*.py[cod]`, and common Python tool caches; `git status --short` no longer shows local cache or virtualenv noise.

## Blocked / pending decisions

- None.

## Handoff notes

- No open follow-up for this task.

## Recurring maintenance

- review `/memory`
- prune stale TODO detail
