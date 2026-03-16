# Agent Instructions

This file is the bootstrap contract for agents working in this repository.

Keep it short, stable, and high-signal. Durable technical knowledge belongs in `/memory`, not here.

## Before doing work

1. Read `TODO.md`.
2. Read `memory/index.md`.
3. Load only the memory files relevant to the task.
4. Read any repository docs referenced by those files.

Do not rely on transient chat context when the same knowledge should exist in checked-in files.

`memory/index.md` is the routing layer for the memory system.  
Use it to decide which notes to load; do not read the entire memory tree by default.

## Repo scope

Replace the placeholders below with repository-specific details.

- Project purpose: `<PROJECT_PURPOSE>`
- Key repository docs: `<KEY_REPO_DOCS>`
- Key commands: `<PRIMARY_BUILD_COMMAND>`, `<PRIMARY_TEST_COMMAND>`, `<OTHER_KEY_COMMANDS>`
- Key subsystems: `<KEY_SUBSYSTEMS>`

This section should remain short and high-level.

## Workspace guardrails

- Work from the repository root.
- Do not edit sibling repositories unless explicitly requested.
- Prefer the existing project tooling, layout, and conventions.
- Avoid introducing new tooling or structure unless it clearly improves maintainability.

## TODO discipline

`TODO.md` is the single source of truth for milestone status and pending work.

- Read it before planning or implementation.
- Write the plan into it before implementation when the work is non-trivial.
- Update it immediately after finishing work or changing scope.
- Keep it execution-focused: milestones, next actions, blockers, and short handoff context only.
- Do not store durable technical memory in `TODO.md`.
- Collapse stale implementation detail into short outcome notes.
- Prune anything that does not affect what happens next.
- Each open item should answer: what is next, what is blocked, or what decision is pending.

## Memory discipline

Use this split:

- `AGENTS.md`: bootstrap policy and stable operating rules
- `TODO.md`: milestone state and current execution plan
- `/memory`: durable technical knowledge
- `.agent-work/`: temporary task working context

`.agent-work/` is local scratch space and should normally be git-ignored.

## Memory admission rule

Only create a new memory note when the information is likely to matter again.

Good candidates:

- recurring failures
- subsystem boundaries that are easy to misunderstand
- invariants future edits could break
- repeatable operational procedures

Do not create memory notes for one-off discoveries or temporary task details.

Prefer `.agent-work/` or `TODO.md` for short-lived context.

## Memory statuses

Durable notes use these statuses:

- `Stable`
- `Active`
- `Needs verification`
- `Deprecated`

## Memory freshness rule

When code, docs, tests, commands, or runtime behaviour referenced in memory changes, the note must be:

- updated
- marked `Needs verification`
- or removed or deprecated

Do not leave contradicted memory behind.

## Memory routing

Use `memory/index.md` to determine which notes are relevant.

Do not load all memory by default.

## Before ending a task

1. Update `TODO.md`.
2. Check whether any memory notes were affected.
3. Update, deprecate, or remove those notes as needed.
4. Add new durable memory only if it is likely to matter again.
5. Prefer updating existing notes over creating duplicates.
6. Leave a short handoff note if work is incomplete.
7. Keep durable notes concise and de-duplicated.
