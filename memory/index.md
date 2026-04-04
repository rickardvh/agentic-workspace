# Memory Index

## Purpose

- `/memory` is the durable repository memory layer.
- Checked-in repo docs remain the canonical documentation layer.
- Read this file after identifying the work from the repository's active planning/status surface or the user's request.
- Load only the notes relevant to the task at hand.
- If `memory/manifest.toml` exists, use it as the machine-readable routing and freshness companion to this file.
- Routing quality matters more than memory volume: good memory systems should help an agent read less, not more.

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

## Loading rule

- Do not load all of `/memory` by default.
- Start from the smallest useful working set.
- Default to `memory/index.md` plus at most 2 additional notes unless the task clearly justifies more.
- Load `memory/current/project-state.md` or `memory/current/task-context.md` only when they will reduce re-orientation cost for the current task.
- Load `memory/current/routing-feedback.md` only when calibrating routing against a concrete missed-note or over-routing case.
- Use touched files, modules, commands, or surfaces to decide which notes to load first.

## Memory admission rule

Only store information in `/memory` if it is likely to matter again.

High-value memory tends to capture boundaries, invariants, operator sequences, recurring failures, or routing hints that are expensive to reconstruct.
Low-value memory tends to restate code that is easy to inspect directly or to preserve one-off task details.
Prefer durable consequences, constraints, exceptions, and recurring traps over merely recent state.
If guidance is stabilising into normal repo documentation, promote it there and leave memory as a short pointer, stub, or residue note.

Do not add memory for:

- one-off discoveries
- temporary task details
- implementation steps specific to a single task
- milestone status
- next-step checklists
- backlog state
- execution logs

If a recurring procedure is reusable but not itself durable repo knowledge, prefer a skill over a new memory note.

## One-home rule

Each durable idea must have one primary home.

- `domains/` for subsystem knowledge
- `invariants/` for things that must remain true
- `runbooks/` for procedures
- `mistakes/` for recurring failures
- the external planning/status surface or explicit user request for task state and dependencies

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

Memory files should normally stay under ~200 lines, with tighter expectations for specific note types.

- invariants: target <= 80 lines
- domains: target <= 160 lines
- runbooks: target <= 140 lines
- recurring-failures: target <= 140 lines
- decisions: target <= 160 lines
- `memory/current/project-state.md`: target <= 100 lines
- `memory/current/task-context.md`: target <= 80 lines

Large memory files degrade selective loading and retrieval quality.

## Token-efficiency rule

- Memory is a net token saver when it prevents repeated rediscovery of boundaries, invariants, operator steps, or routing context.
- Memory is likely overhead when it merely restates code, repeats task chatter, or forces broad re-reading.
- Keep the working set small enough that reading the notes is cheaper than re-deriving the same facts.
- Favour smaller, sharper routing packets over broad bundles of possibly relevant notes.

## Canonicality rule

- Prefer checked-in docs first when a note says the canonical truth lives elsewhere.
- Use `memory/manifest.toml` metadata such as `canonicality`, `canonical_home`, and `task_relevance` to distinguish required task-correctness docs from optional memory context.

## Index compactness rule

`memory/index.md` is a routing layer, not a knowledge file.

Keep it short.  
Do not summarise note contents beyond what is needed for routing.
Update this index in the same change when the memory structure changes.
Prefer the smallest bundle that still covers the task surface.
