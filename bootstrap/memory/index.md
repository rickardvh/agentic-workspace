# Memory Index

## Purpose

- `/memory` is the durable repository memory layer.
- Read this file after identifying the work from the repo's task system or the user's request.
- Load only the notes relevant to the task at hand.
- If `memory/manifest.toml` exists, use it as the machine-readable routing and freshness companion to this file.
- Use checked-in files for durable facts and lightweight shared context.
- Use skills for repeatable workflow operations on that knowledge.

## Task routing

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
- Use touched files, modules, commands, or surfaces to decide which notes to load first.

## Note type split

- `domains/` = orientation notes about subsystem behaviour, boundaries, and traps.
- `decisions/` = longer-lived rationale or trade-offs that are still worth remembering but are no longer current-orientation notes.
- `runbooks/` = repeatable operational procedures, recovery steps, and verification sequences.
- `current/` = lightweight current overview and optional current-task compression, not historical records.

## Memory admission rule

Only store information in `/memory` if it is likely to matter again.

Good candidates:

- recurring failures
- invariants or contracts
- durable runbooks that should remain visible in git
- subsystem boundaries that are easy to misunderstand

High-value memory tends to capture boundaries, invariants, operator sequences, recurring failures, or routing hints that are expensive to reconstruct.
Low-value memory tends to restate code that is easy to inspect directly or to preserve one-off task details.

Do not add memory for:

- one-off discoveries
- temporary task details
- implementation steps specific to a single task

If a recurring procedure is reusable but not itself durable repo knowledge, prefer a skill over a new memory note.

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
- Update a note when its primary home is still correct and the content is still useful.
- Merge or delete near-duplicates.
- Remove or deprecate notes that are no longer true.
- If a note is mostly repeated procedure, keep the durable fact in files and move the procedure into a skill.
- Mark uncertain notes `Needs verification` instead of guessing.

## Memory size limits

Memory files should normally stay under ~200 lines.

Large memory files degrade selective loading and retrieval quality.

## Token-efficiency rule

- Memory is a net token saver when it prevents repeated rediscovery of boundaries, invariants, operator steps, or routing context.
- Memory is likely overhead when it merely restates code, repeats task chatter, or forces broad re-reading.
- Keep the working set small enough that reading the notes is cheaper than re-deriving the same facts.

## Small routing examples

Example: API contract work

- `memory/domains/api.md`
- `memory/invariants/response-contracts.md`

Example: deployment incident

- `memory/runbooks/deploy-recovery.md`
- `memory/domains/runtime.md`

Example: architecture trade-off review

- `memory/decisions/README.md`
- `memory/current/project-state.md`

## Index compactness rule

`memory/index.md` is a routing layer, not a knowledge file.

Keep it short.  
Do not summarise note contents beyond what is needed for routing.
Update this index in the same change when the memory structure changes.
