# Memory Index

## Purpose

- `/memory` is the durable repository memory layer.
- Read this file immediately after `TODO.md`.
- Load only the notes relevant to the task at hand.
- Treat memory as maintained working knowledge, not as a documentation archive.

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

Delete unused routing examples once the target repository has concrete notes.

## Loading rule

- Do not load all of `/memory` by default.
- Start with the always-relevant files, then load only the notes needed for the current task.

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

Use `.agent-work/` for temporary working context.

## One-home rule

Each durable idea must have one primary home.

- `domains/` for subsystem knowledge
- `invariants/` for things that must remain true
- `runbooks/` for procedures
- `mistakes/` for recurring failures
- `TODO.md` for milestone state
- `.agent-work/` for temporary working context

Do not duplicate the same guidance across multiple files.
Use short references instead.

## Memory pruning rules

When updating `/memory`:

- prefer editing an existing note over creating a new one
- merge overlapping notes
- remove notes that are no longer true
- shorten notes that contain history with no operational value
- move architectural background into `decisions/` when that is a better fit
- do not preserve stale operational advice just because it might be useful later

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
Do not summarise the contents of notes beyond what is needed for routing.
If a section becomes crowded, split the underlying memory files rather than expanding index prose.

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

## Suggested maintenance cadence

As periodic upkeep, review `/memory` roughly every 2-3 months to:

- run the freshness audit
- prune deprecated notes
- merge duplicates
- refresh confirmations
- trim oversized files
