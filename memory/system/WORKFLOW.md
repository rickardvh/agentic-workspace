# Workflow Rules

## Purpose

This file defines the shared workflow for memory use and lightweight checked-in coordination notes.

Keep it concise, operational, and repo-agnostic.

## Operating split

- `AGENTS.md` = local bootstrap contract
- task system = external to this bootstrap
- built-in agent planning = short-horizon planning and execution
- `/memory` = durable, shared technical knowledge
- `memory/current/project-state.md` = lightweight repo overview
- `memory/current/task-context.md` = optional checked-in current-task compression
- local notes = optional scratch context only

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

## Overview file

- `memory/current/project-state.md` is a lightweight human-readable overview.
- Use it for current focus, recent meaningful progress, blockers, and short high-level notes.
- Do not turn it into a task list or implementation log.

## Task-context file

- `memory/current/task-context.md` is optional but recommended when it reduces re-orientation cost across sessions.
- Use it to compress the current focus, active surfaces, key constraints, relevant memory, and a few short continuation notes.
- Do not use it as a task list, detailed plan, or historical log.
- Shrink or clear stale detail once it no longer helps the next session continue quickly.

## Skills note

Specialised repeatable procedures may live in skills, but the core operating model must stay in checked-in docs.

## Local working notes (optional)

Local scratch notes may be used when helpful:

- for temporary planning
- for tracking findings
- for handoff context during complex work

They are optional and should not be required for normal operation.

Do not treat them as durable memory.

## Before ending a task

1. Check whether memory notes were affected.
2. Update or remove stale memory in the same change.
3. Update `memory/current/project-state.md` if the repo overview changed materially.
4. Refresh `memory/current/task-context.md` if it would materially reduce re-orientation cost for the next session.
5. Shrink or clear stale current-task context when it no longer helps.
