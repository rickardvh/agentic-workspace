# Memory Index

## Purpose

- `/memory` is the durable repository memory layer.
- Read this file after identifying the work from the repo's task system or the user's request.
- Load only the notes relevant to the task at hand.
- `memory/system/` contains bootstrap system docs and version markers rather than routed task memory.
- Use checked-in files for durable facts and lightweight shared context.
- Use skills for repeatable workflow operations on that knowledge.

## Task routing

### If choosing an approach across multiple subsystems in this repository

- `memory/current/active-decisions.md`
- `memory/decisions/README.md`

### If touching runtime or deployment

- `memory/domains/<runtime-or-deployment-note>.md`
- `memory/runbooks/<relevant-operator-runbook>.md`

### If touching API contracts or tool behaviour

- `memory/domains/<api-or-interface-note>.md`
- `memory/invariants/<response-or-contract-note>.md`

### If touching retrieval or search

- `memory/domains/<retrieval-or-search-note>.md`
- `memory/invariants/<retrieval-contract-note>.md`
- `memory/mistakes/recurring-failures.md`

### If touching tests or validation

- `memory/domains/<testing-or-validation-note>.md`
- `memory/mistakes/recurring-failures.md`

### If touching data model or architecture

- `memory/domains/<data-model-or-architecture-note>.md`
- `memory/invariants/<relevant-invariant-note>.md`
- `memory/decisions/README.md`

Delete unused routing examples once the repository has concrete notes.

## Loading rule

- Do not load all of `/memory` by default.
- Start from the smallest useful working set.
- Load `memory/current/project-state.md` or `memory/current/task-context.md` only when they will reduce re-orientation cost for the current task.
- When notes include an `Applies to` section, use touched files, modules, commands, or surfaces to decide which notes to load first.
- Prefer a small, precise working set over broad context loading.

## Memory admission rule

Only store information in `/memory` if it is likely to matter again.

Good candidates:

- recurring failures
- invariants or contracts
- durable runbooks that should remain visible in git
- subsystem boundaries that are easy to misunderstand

Do not add memory for:

- one-off discoveries
- temporary task details
- implementation steps specific to a single task

If a recurring procedure is reusable but not itself durable repo knowledge, prefer a skill over a new memory note.

Use local working notes only if helpful; do not rely on them as part of the system.

## One-home rule

Each durable idea must have one primary home.

- `domains/` for subsystem knowledge
- `invariants/` for things that must remain true
- `runbooks/` for procedures
- `mistakes/` for recurring failures
- the external task system or explicit user request for task state and dependencies

Do not duplicate the same guidance across multiple files.  
Use short references instead.

## Pruning rule

- Prefer editing an existing note over creating a new one.
- Merge or delete near-duplicates.
- Remove or deprecate notes that are no longer true.
- Mark uncertain notes `Needs verification` instead of guessing.

## Memory size limits

Memory files should normally stay under ~200 lines.

If a file grows beyond that:

- split it by subsystem or topic
- move procedures into `runbooks/`
- move architectural context into `decisions/`
- remove duplicated material

Large memory files degrade selective loading and retrieval quality.

## Index compactness rule

`memory/index.md` is a routing layer, not a knowledge file.

Keep it short.  
Do not summarise note contents beyond what is needed for routing.

## Index maintenance

When creating, renaming, splitting, or significantly repurposing memory files, update this index in the same change.

The index must always reflect the real memory structure.

