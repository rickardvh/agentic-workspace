# Memory Index

## Purpose

- `/memory` is the durable repository memory layer.
- Read this file immediately after `TODO.md`.
- Load only the notes relevant to the task at hand.
- Treat memory as maintained working knowledge, not a documentation archive.
- Treat memory as a cache of reusable knowledge, not an archive of everything learned.
- Shared workflow rules live in `memory/system/WORKFLOW.md`; `AGENTS.md` points there directly.
- `memory/system/` contains bootstrap system docs and version markers rather than routed task memory.

## How to use memory

- Use built-in agent planning and memory for task execution.
- Use `/memory` for shared, durable, and repo-specific knowledge.
- Start with always-relevant files, then follow task routing.
- Do not load the entire memory tree.

## Always relevant

- `memory/current/project-state.md`
- `memory/current/active-decisions.md`

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
- Start with always-relevant files, then load only what is needed for the current task.
- When notes include an `Applies to` section, use touched files, modules, commands, or surfaces to decide which notes to load first.
- Prefer a small, precise working set over broad context loading.

## Memory freshness rules

When editing code, configuration, runtime surfaces, tests, commands, or behaviour described in `/memory`, check whether any memory notes reference the changed components.

If a note is affected:

- update it in the same change
- or mark it `Needs verification`
- or deprecate or remove it if it no longer applies

Do not leave contradicted memory behind.

Memory must evolve with the code.

## Memory admission rule

Only store information in `/memory` if it is likely to matter again.

Good candidates:

- recurring failures
- invariants or contracts
- repeatable procedures
- subsystem boundaries that are easy to misunderstand

Do not add memory for:

- one-off discoveries
- temporary task details
- implementation steps specific to a single task

Use local working notes only if helpful; do not rely on them as part of the system.

## One-home rule

Each durable idea must have one primary home.

- `domains/` for subsystem knowledge
- `invariants/` for things that must remain true
- `runbooks/` for procedures
- `mistakes/` for recurring failures
- `TODO.md` for milestone state

Do not duplicate the same guidance across multiple files.  
Use short references instead.

## Memory pruning rules

When updating `/memory`:

- prefer editing an existing note over creating a new one
- merge overlapping notes
- remove notes that are no longer true
- shorten notes that contain history with no operational value
- move architectural background into `decisions/` when that is a better fit

Bias toward cleanup:

- prefer delete or merge over keeping near-duplicates
- prefer a shorter current rule over a longer historical narrative

If a note cannot currently be verified:

- mark it `Needs verification`
- add a short explanation of what needs to be checked

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

## Memory hygiene

Agents should periodically review `/memory` to keep it accurate.

Typical maintenance actions:

- merge duplicate notes
- remove deprecated knowledge
- refresh `Last confirmed`
- split oversized files
- update trigger metadata
- mark uncertain notes `Needs verification`
- delete notes that no longer improve future task execution

## Suggested maintenance cadence

As periodic upkeep, review `/memory` roughly every 2-3 months to:

- run the freshness audit
- prune deprecated notes
- merge duplicates
- refresh confirmations
- trim oversized files
