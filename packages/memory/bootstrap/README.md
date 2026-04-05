# Bootstrap Package

This package is a repo-agnostic bootstrap for agent memory and lightweight checked-in coordination notes.

Memory owns durable repo knowledge. The repository's active planning/status surface owns active intent and sequencing. Memory complements planning by preserving durable lessons and reducing re-orientation cost, but it must never compete with the planning surface for ownership of active work.
Good memory systems should help an agent read less, not more.
Memory is also a pressure layer: if a note exists because the repo is awkward to understand or operate, the note should help the agent suggest the code, docs, tests, tooling, or refactor that would let the note shrink, move, or disappear.

It is intended to be copied into an existing repository to provide:

- `AGENTS.md` as the slim local bootstrap entrypoint
- `memory/` as durable checked-in technical memory
- `memory/manifest.toml` as optional machine-readable memory metadata
- `.agentic-memory/bootstrap/` as a temporary bootstrap workspace for install and adopt completion
- `.agentic-memory/skills/` as bootstrap-managed shared memory skills
- `.agentic-memory/WORKFLOW.md` as the shared reusable memory workflow rules
- `.agentic-memory/SKILLS.md` as the shared skill-boundary guidance
- `.agentic-memory/VERSION.md` as the installed bootstrap version marker
- `memory/current/project-state.md` as a weak-authority current overview
- `memory/current/task-context.md` as optional weak-authority continuation compression
- an advisory memory freshness audit
- optional workflow fragments for common contribution flows

The packaged files are the durable memory layer, not the repository's full canonical documentation layer. Stable human-facing policies and procedures should live in normal checked-in docs outside `memory/`, with memory kept as assistive residue, routing help, or short stubs when needed.

Repeatable workflow-like actions should live in optional skills rather than expanding the mandatory payload indefinitely.

Temporary bootstrap workspace files are part of the payload so install and adopt can hand off to repo-local lifecycle skills. They are meant to be removed after bootstrap work is complete.

The CLI around this payload can also inspect the current-memory surface, route through manifest metadata and the shipped memory skills, resolve upgrade source from the product-managed `.agentic-memory/UPGRADE-SOURCE.toml` record, and verify payload consistency for maintainers and agent workflows.

Treat the packaged memory notes as a starting cache of reusable operating knowledge, not an archive to expand without limit.
Use them when they save rediscovery cost; avoid adding notes that merely restate code or transient task chatter.
Optimise for deletion and consolidation, not just capture.
If a memory note stabilises into canonical repo guidance, promote it into checked-in docs and leave a short replacement note instead of duplicate truth.
Prefer compact residue-oriented notes: pitfalls, routing hints, traps, operator context, and short fallback summaries.
Memory is a reasoning aid and constraint layer; it does not replace checking the codebase when the codebase is the source of truth.
Use memory in two modes:

- durable truth: invariants, authority boundaries, recurring traps, operator constraints, and other hard-to-rediscover facts that should stay visible
- improvement signal: notes that exist because the repo still needs clearer docs, stronger tests, better tooling, better automation, or simpler structure

Preserve the first kind. Use the second kind to suggest upstream repo improvements instead of treating memory as the default answer to repo complexity.
Do not assume memory volume should follow one universal trend across repositories or development stages; judge memory by whether it justifies its cost and reduces rediscovery.
The bootstrap may diagnose, classify, prioritise, and suggest concrete repo-owned remediation targets, but it should remain advisory outside the managed bootstrap surface rather than autonomously rewriting repo-owned docs, tests, scripts, or code.
If a remediation suggestion starts depending on repo-shape-specific judgement, prefer a clearer handoff into repo-owned work over making the bootstrap itself more invasive.

When maintaining this repository, treat `bootstrap/` as the source of truth for installed files. The packaged wheel payload is built from this directory.

## Copy targets

Copy as-is:

- `AGENTS.md`
- `memory/`
- `scripts/check/check_memory_freshness.py`

Merge or append:

- `optional/pull_request_template.fragment.md`
- `optional/CONTRIBUTING.fragment.md`
- `optional/Makefile.fragment.mk`

Do not install maintainer-only repo docs or implementation notes by default.

## Recommended installation order

1. Copy `AGENTS.md`.
2. Copy `memory/`, including `memory/current/project-state.md` and `memory/current/task-context.md`.
3. Copy `.agentic-memory/`.
4. Optionally merge the workflow fragments.
5. Run `scripts/check/check_memory_freshness.py`.

For CI-style enforcement, run `scripts/check/check_memory_freshness.py --strict`.

## Placeholder replacement

`<PROJECT_NAME>` is filled by the installer when possible.

Review and replace repo-specific placeholders such as:

- `<PROJECT_PURPOSE>`
- `<KEY_REPO_DOCS>`
- `<KEY_SUBSYSTEMS>`
- `<PRIMARY_BUILD_COMMAND>`
- `<PRIMARY_TEST_COMMAND>`

The installer can also fill these placeholders when you pass the matching explicit CLI flags.

Delete unused routing examples once the target repository has concrete notes.

`AGENTS.md` should stay short and point to `.agentic-memory/WORKFLOW.md` for the shared operating model.
Bootstrap should modify `AGENTS.md` only through the managed workflow pointer block. Repo-specific `AGENTS.md` prose outside that block is repo-owned and should not be treated as shared upgradeable guidance.

This bootstrap is planning-system agnostic. `/memory` owns durable technical knowledge, `memory/current/project-state.md` is the overview note, `memory/current/task-context.md` is optional checked-in continuation compression, repo-owned memory skills can live under `memory/skills/`, and `.agentic-memory/` is the bootstrap-managed surface for shared workflow rules, shipped skills, and temporary bootstrap workspace files.

Bundled product skills should stay limited to bootstrap lifecycle operations. Repo-local memory procedures should live in repo-owned `memory/skills/`. General non-memory skills should not.

Ownership split:

- bootstrap-managed and upgrade-replaceable: the workflow pointer block in `AGENTS.md`, `.agentic-memory/`, and other shared replaceable payload files
- repo-owned and expected to diverge: `AGENTS.md` content outside the managed pointer block, repo-added sibling skills under `memory/skills/`, and ordinary notes outside the product-managed shared directories

`memory/current/project-state.md` should stay aggressively summary-shaped and weak-authority: current focus, recent meaningful progress, blockers, and a few high-value notes are usually enough. If a fact becomes durable, move it into a primary home and leave only a short pointer or remove it.

Small routing layers work better than summary-heavy indexes. A good `memory/index.md` points to a few likely-relevant notes rather than trying to restate them.
Treat `.agentic-memory/skills/memory-router/` as the normal entrypoint for day-to-day note selection, with `memory/index.md` and `memory/manifest.toml` providing the visible routing contract behind it.
When `memory/manifest.toml` marks a note as `canonical_elsewhere`, routing should prefer the canonical checked-in doc and keep the memory note as optional fallback context.
Planning/status surfaces identify touched paths or surfaces; memory routing returns the smallest relevant durable note set.
If the same note keeps being routed for safe work on one subsystem, that is often a cue to suggest clearer docs, stronger validation, or refactor review.

Common task bundles:

- current-state refresh: `memory/current/project-state.md` plus `memory/current/task-context.md` only when active continuation context is genuinely needed
- live decision review: optional repo-owned `memory/current/active-decisions.md` when the repo keeps one, plus `memory/decisions/README.md`
- runtime or deployment change: `memory/domains/<runtime-or-deployment-note>.md` plus `memory/runbooks/<relevant-operator-runbook>.md`
- API or interface change: `memory/domains/<api-or-interface-note>.md` plus `memory/invariants/<response-or-contract-note>.md`
- retrieval or search change: `memory/domains/<retrieval-or-search-note>.md` plus `memory/invariants/<retrieval-contract-note>.md` plus `memory/mistakes/recurring-failures.md`
- tests or validation work: `memory/domains/<testing-or-validation-note>.md` plus `memory/mistakes/recurring-failures.md`
- architecture or data-model work: `memory/domains/<data-model-or-architecture-note>.md` plus `memory/invariants/<relevant-invariant-note>.md` plus `memory/decisions/README.md`

Optional repo pattern only: keep short-horizon task execution in the repo's chosen planning/status surface, keep long-horizon roadmap or epic planning separate, and use checked-in current-context notes only for concise re-orientation. Current notes should stay easy to compress, replace, or delete rather than becoming a second durable knowledge layer.

Interoperability pattern catalogue:

- loose coupling: planner first, memory routed on demand
- handoff compression: planner primary, memory holds minimal cross-session continuation context
- durable capture on close: planner closes work, memory updates only if durable knowledge changed

## Current Decisions

- if the repo keeps `memory/current/active-decisions.md`, use it for live architectural or cross-cutting decisions only
- move a decision into `memory/decisions/` once it no longer changes implementation choices and is only worth keeping as durable rationale
- preserve decisions at the level of consequence or still-relevant rejected-path boundaries, not meeting history
- do not keep completed transitions or operational residue in the current decision note

## Improvement Paths

- recurring mistake -> consider a regression test, validation, or lint rule
- prose-heavy runbook -> consider a checked-in skill first, then a repo-owned script or command if the workflow stays mechanical
- stable human-facing guidance -> consider promoting it into canonical docs and leaving memory as a stub or backlink
- note that repeatedly explains one hard subsystem -> consider refactor review or clearer module boundaries
- routing crutch used for one awkward area -> consider naming, structure, or ownership cleanup in the repo

## When to write to memory

- store: invariants, authority boundaries, recurring failure modes, routing hints, operator runbooks, and other facts that are hard to recover quickly from code, tests, tooling, or the planning/status surface
- store: durable consequences and still-relevant rejected-path boundaries when they still constrain future choices

## When not to write to memory

- do not store: milestone status, next-step checklists, backlog state, execution logs, or plan content already owned by the planning/status surface
- do not store: user-specific preferences, collaboration habits, or stylistic defaults unless they are shared technical policy

Ask one more question before expanding a note: what repo change would let this note shrink, move, or disappear?

## Anti-patterns

- turning memory into a task tracker
- copying plan content into durable notes
- storing rediscoverable facts
- coupling freshness checks to a specific planner or planning file
- forcing repositories to adopt the memory taxonomy in their planning system
- mixing user-specific memory with repo-specific technical truth
- treating memory as the endpoint when it is really signalling missing docs, missing tests, weak tooling, or awkward architecture

## Minimal Adoption Checklist

- choose the active planning/status surface
- decide whether current-context compression is used
- decide how memory freshness is checked
- decide who updates memory when durable knowledge changes
- decide which routing metadata fields the repo will maintain

`.agentic-memory/VERSION.md` is the machine-readable version marker used for deterministic upgrades.

## Upgrade model

Prefer this flow for existing or older installs:

1. Run `agentic-memory-bootstrap doctor --target <repo>`.
2. Run `agentic-memory-bootstrap upgrade --dry-run --target <repo>`.
3. Apply the minimal-safe upgrade plan.
4. Use `--apply-local-entrypoint` only when you want the installer to patch `AGENTS.md`.

Upgrade is normally triggered through the checked-in `memory-upgrade` skill under `.agentic-memory/skills/`, which runs the packaged upgrade implementation using the resolved source record in `.agentic-memory/UPGRADE-SOURCE.toml`. Temporary bootstrap workspace files are for install and adopt lifecycle completion, not the primary upgrade path.

Use `agentic-memory-bootstrap list-files` to preview the packaged files that the installer exposes.
Use `agentic-memory-bootstrap promotion-report --target <repo>` to identify notes that should likely be promoted into canonical docs or reviewed as elimination candidates.
Use `agentic-memory-bootstrap promotion-report --mode remediation --target <repo>` to focus on medium/high-confidence remediation targets for shrinking or removing memory.
Use `agentic-memory-bootstrap doctor --strict-doc-ownership --target <repo>` to force doc-ownership and shadow-doc audits before adopting stricter repo policy.
Use `--policy-profile strict-doc-ownership` with `install`, `adopt`, or `upgrade` to set `forbid_core_docs_depend_on_memory = true` in `memory/manifest.toml`.

## Automation notes

A later automation script should:

- copy stable files as-is
- merge append-only fragments into existing files
- replace placeholders or leave them for a human to fill in
- avoid overwriting existing repo-specific memory notes blindly
- treat `.agentic-memory/VERSION.md` as the installed system version marker
- run the freshness audit after installation
- optionally enforce repo-local policy that core docs must not depend on memory
