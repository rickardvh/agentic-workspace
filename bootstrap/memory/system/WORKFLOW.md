# Workflow Rules

## Purpose

This file defines the shared workflow for planning, memory usage, and task handoff.

Keep it concise, operational, and repo-agnostic.

## Operating split

- `AGENTS.md` = local bootstrap contract
- `TODO.md` = cross-task execution state and milestone continuity
- `/memory` = durable, shared technical knowledge
- local notes (e.g. `.agent-work/`) = optional scratch context

Use built-in agent planning and memory for short-horizon task execution.

## TODO discipline

- Read `TODO.md` before planning or implementation.
- Write the active plan into `TODO.md` before non-trivial work.
- Update `TODO.md` immediately after finishing work or changing scope.
- Keep it execution-focused: next actions, blockers, decisions, and short handoff context only.
- Collapse completed detail into short outcome notes.
- Prune anything that does not affect what happens next.

`TODO.md` is for cross-task continuity, not detailed step-by-step reasoning.

## Memory discipline

- Treat `/memory` as a maintained cache of reusable knowledge, not an archive.
- Use `memory/index.md` to route to relevant notes instead of bulk-loading memory.
- Prefer editing existing notes over creating near-duplicates.
- Merge or delete stale material instead of accumulating it.

## Memory admission rule

Only add memory that is likely to matter again, such as:

- recurring failures
- subsystem boundaries that are easy to misunderstand
- invariants future edits could break
- repeatable procedures

Do not store one-off discoveries or temporary task details in `/memory`.

## Memory statuses

Use these statuses:

- `Stable`
- `Active`
- `Needs verification`
- `Deprecated`

Use ISO dates for `Last confirmed`, for example `2026-03-17`.

## Memory freshness rule

When code, docs, tests, commands, packaging, or behaviour referenced in memory changes:

- update the note in the same change
- or mark it `Needs verification`
- or remove or deprecate it

Do not leave contradicted memory behind.

## Memory routing rule

- `memory/index.md` is the routing layer for durable knowledge.
- Keep the index compact.
- Load only the notes relevant to the files, interfaces, or behaviour you are touching.

## Local working notes (optional)

Local scratch notes (for example `.agent-work/`) may be used when helpful:

- for temporary planning
- for tracking findings
- for handoff context during complex work

They are optional and should not be required for normal operation.

Do not treat them as durable memory.

## Before ending a task

1. Update `TODO.md`.
2. Check whether memory notes were affected.
3. Update or remove stale memory in the same change.
4. Leave a short handoff note if work is incomplete.
