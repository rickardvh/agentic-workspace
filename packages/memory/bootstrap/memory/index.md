# Memory Index

## Purpose

- `/memory` is the anti-rediscovery layer for durable repo knowledge and lightweight shared context.
- It is not a task tracker, issue mirror, or broad fallback handbook.
- Checked-in repo docs remain the canonical documentation layer.
- The repository planning/status surface remains the owner of active intent and sequencing.
- Read this file after identifying the work from the repository's active planning/status surface or the user's request.
- Load only the notes relevant to the task at hand.
- If `memory/manifest.toml` exists, use it as the machine-readable routing and freshness companion to this file.
- Use checked-in files for durable facts and lightweight shared context.
- Use skills for repeatable workflow operations on that knowledge.
- Planning identifies touched paths or surfaces; routing returns the smallest relevant durable note set.
- Routing quality matters more than memory volume: good memory systems should help an agent read less, not more.

## Interoperability patterns

- loose coupling: planning/status surface is primary, memory is routed on demand from touched files or surfaces
- handoff compression: planning/status surface stays primary, memory keeps only minimal cross-session continuation context
- durable capture on close: planning/status surface closes the work, memory updates only if durable knowledge changed
- combined install: planning owns active-now state, memory provides the smallest durable context bundle, and completed planning residue promotes only the durable lessons that future work should not have to rediscover

## Common task bundles

- current-state refresh: `memory/current/project-state.md` plus `memory/current/task-context.md` when needed
- live decision review: optional repo-owned `memory/current/active-decisions.md` when the repo keeps one, plus `memory/decisions/README.md`
- runtime or deployment change: `memory/domains/<runtime-or-deployment-note>.md` plus `memory/runbooks/<relevant-operator-runbook>.md`
- API or interface change: `memory/domains/<api-or-interface-note>.md` plus `memory/invariants/<response-or-contract-note>.md`
- retrieval or search change: `memory/domains/<retrieval-or-search-note>.md` plus `memory/invariants/<retrieval-contract-note>.md` plus `memory/mistakes/recurring-failures.md`
- tests or validation work: `memory/domains/<testing-or-validation-note>.md` plus `memory/mistakes/recurring-failures.md`
- architecture or data-model work: `memory/domains/<data-model-or-architecture-note>.md` plus `memory/invariants/<relevant-invariant-note>.md` plus `memory/decisions/README.md`

## Task routing

Delete unused routing examples once the repository has concrete notes.
Prefer the smallest bundle that still covers the task surface.

## Loading rule

- Do not load all of `/memory` by default.
- Start from the smallest useful working set.
- Default to `memory/index.md` plus at most 2 additional notes unless the task clearly justifies more.
- Load `memory/current/project-state.md` or `memory/current/task-context.md` only when they will reduce re-orientation cost for the current task.
- Load `memory/current/routing-feedback.md` only when calibrating routing against a concrete missed-note or over-routing case.
- When a repository has bootstrap-managed shared skills, check `.agentic-memory/skills/README.md` before inventing a new shared memory-operational procedure.
- Use touched files, modules, commands, or surfaces to decide which notes to load first.
- When planning is installed, start from the active planning surface and borrow only the smallest memory bundle needed for durable context; do not read both systems broadly by default.

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
Prefer durable consequences, constraints, exceptions, and recurring traps over merely recent state.
If guidance is stabilising into normal repo documentation, promote it there and leave memory as a short pointer, stub, or residue note.
Treat recurring-failures as anti-trap memory for repeated or high-likelihood mistakes, not as issue triage or a general bug list.

Store example: `Firestore sync is explicit and not implied by local rebuilds.`
Do not store example: `Milestone 2 requires rerunning the publish step tomorrow.`

Do not add memory for:

- one-off discoveries
- temporary task details
- implementation steps specific to a single task
- milestone status
- next-step checklists
- backlog state
- execution logs

If a recurring procedure is reusable but not itself durable repo knowledge, prefer a skill over a new memory note.
If a completed plan leaves behind durable residue, decide whether the primary home should be memory, canonical docs, or nowhere; do not let archived plans become the long-term memory layer by default.

## One-home rule

Each durable idea must have one primary home.

- `domains/` for subsystem knowledge
- `invariants/` for things that must remain true
- `runbooks/` for procedures
- `mistakes/` for recurring failures
- the external planning/status surface or explicit user request for task state and dependencies

Do not duplicate the same guidance across multiple files.  
Use short references instead.

## Integration checklist

An adopting repo should decide:

- what its active planning/status surface is
- whether `memory/current/task-context.md` is used for optional continuation compression
- how memory freshness is checked
- who updates memory when durable knowledge changes
- which manifest routing metadata fields it will maintain

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
- If the repository enables the doc-ownership audit, core docs should not depend on memory for stable policy or procedure.

## Small routing examples

Example: API contract work

- `memory/domains/api.md`
- `memory/invariants/response-contracts.md`

Example: deployment recovery

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
