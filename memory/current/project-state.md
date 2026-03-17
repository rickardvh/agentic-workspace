# Project State

## Status

Active

## Scope

- Repository orientation and document map for `agentic-memory`.

## Applies to

- `TODO.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `<KEY_REPO_DOCS>`

## Load when

- Starting work and confirming where milestone truth and operating docs live.
- Returning to the repository after a break.

## Review when

- Repository-level operating docs change.
- Bootstrap instructions change where agents should read first.
- Shared workflow rules move between `AGENTS.md` and `memory/system/WORKFLOW.md`.

## Failure signals

- Contributors use the wrong file as the source of milestone truth.
- Shared workflow guidance drifts back into `AGENTS.md` instead of `memory/system/WORKFLOW.md`.

## Rule or lesson

- `agentic-memory` exists for `<PROJECT_PURPOSE>`.
- `TODO.md` is the single source of truth for milestone status and pending work.
- Main repository docs live in `<KEY_REPO_DOCS>`.
- Keep this note short; it is an orientation note, not a changelog.

## How to recognise it

- You need a fast start point before touching code.
- You need to know which document owns status, procedure, or interface reference.

## Verify

- Read `TODO.md` and confirm the active milestones still match reality.
- Read `memory/index.md` and confirm the routing still matches the memory structure.
- Confirm `<KEY_REPO_DOCS>` still exist and are the correct orientation docs.

## Verified against

- `TODO.md`
- `memory/index.md`
- `memory/system/WORKFLOW.md`
- `memory/system/VERSION.md`
- `memory/system/UPGRADE.md`
- `README.md`

## What to do

- Start from `TODO.md`, then `memory/index.md`, then only task-relevant notes.
- Keep reusable workflow rules in `memory/system/WORKFLOW.md`, not `AGENTS.md`.

## Last confirmed

2026-03-17 during upgrade system review
