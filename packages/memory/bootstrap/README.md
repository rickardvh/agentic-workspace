# Bootstrap Package

This package ships the installed Agentic Memory contract for target repositories: anti-rediscovery knowledge, route metadata, optional routing-calibration guidance, freshness auditing, and the managed workflow surfaces that support them.

Memory owns durable repo knowledge. The repository's active planning/status surface owns active intent and sequencing. Memory complements planning by preserving durable lessons and reducing re-orientation cost, but it must never compete with the planning surface for ownership of active work.
Good memory systems should help an agent read less, not more.
Memory is also a pressure layer: if a note exists because the repo is awkward to understand or operate, the note should help the agent suggest the code, docs, tests, tooling, or refactor that would let the note shrink, move, or disappear.
Treat recurring-failures as anti-trap memory for repeated or high-likelihood mistakes, not as issue triage or a bug backlog.

Treat the CLI as the installer and maintenance entrypoint for this contract, not as the full definition of the product.

Its package lifecycle supplies selected static support and initial templates for:

- `AGENTS.md` as the slim local bootstrap entrypoint
- `.agentic-workspace/memory/repo/` as durable checked-in technical memory
- `.agentic-workspace/memory/repo/manifest.toml` as optional machine-readable memory metadata
- `.agentic-workspace/memory/bootstrap/` as a temporary bootstrap workspace for install and adopt completion
- `.agentic-workspace/memory/skills/` as bootstrap-managed shared memory skills
- `.agentic-workspace/memory/WORKFLOW.md` as the shared reusable memory workflow rules
- `.agentic-workspace/memory/SKILLS.md` as the shared skill-boundary guidance
- `.agentic-workspace/memory/VERSION.md` as the installed bootstrap version marker
- create `.agentic-workspace/memory/repo/current/routing-feedback.md` only when you have concrete missed-note or over-routing cases to calibrate
- `.agentic-workspace/memory/repo/templates/` as starter note templates for the first real repo-specific notes
- an advisory memory freshness audit
- optional workflow fragments for common contribution flows

The packaged files are the durable memory layer, not the repository's full canonical documentation layer. Stable human-facing policies and procedures should live in normal checked-in docs outside `.agentic-workspace/memory/repo/`, with memory kept as assistive residue, routing help, or short stubs when needed.

Repeatable workflow-like actions should live in optional skills rather than expanding the mandatory payload indefinitely.

Temporary bootstrap workspace files are part of the payload so install and adopt can hand off to repo-local lifecycle skills. They are meant to be removed after bootstrap work is complete.

The CLI around this payload can also inspect legacy current-memory residue, route through manifest metadata and the shipped memory skills, resolve upgrade source from the product-managed `.agentic-workspace/memory/UPGRADE-SOURCE.toml` record, and verify payload consistency for maintainers and agent workflows.

Treat the packaged memory notes as a starting cache of reusable operating knowledge, not an archive to expand without limit.
Use them when they save rediscovery cost; avoid adding notes that merely restate code or transient task chatter.
Optimise for deletion and consolidation, not just capture.
If a memory note stabilises into canonical repo guidance, promote it into checked-in docs and leave a short replacement note instead of duplicate truth.
Prefer compact residue-oriented notes: pitfalls, routing hints, traps, operator context, and short fallback summaries.
Memory is git-native, not multi-writer safe. Keep notes focused enough that unrelated branches do not edit the same broad durable surface. When a note becomes large, repeatedly collides in merges, or lacks routing metadata, split it by subsystem, decision, invariant, or runbook; if the stable guidance belongs in user-facing docs, promote it there and leave Memory as a stub or backlink.
Memory is a reasoning aid and constraint layer; it does not replace checking the codebase when the codebase is the source of truth.
Use memory in two modes:

- durable truth: invariants, authority boundaries, recurring traps, operator constraints, and other hard-to-rediscover facts that should stay visible
- improvement signal: notes that exist because the repo still needs clearer docs, stronger tests, better tooling, better automation, or simpler structure

Preserve the first kind. Use the second kind to suggest upstream repo improvements instead of treating memory as the default answer to repo complexity.
Use the explicit improvement-targeting workflow: symptom captured -> remediation target chosen -> follow-up routed -> remediation lands -> note retained, shrunk, stubbed, or deleted.
Do not assume memory volume should follow one universal trend across repositories or development stages; judge memory by whether it justifies its cost and reduces rediscovery.
The bootstrap may diagnose, classify, prioritise, and suggest concrete repo-owned remediation targets, but it should remain advisory outside the managed bootstrap surface rather than autonomously rewriting repo-owned docs, tests, scripts, or code.
If a remediation suggestion starts depending on repo-shape-specific judgement, prefer a clearer handoff into repo-owned work over making the bootstrap itself more invasive.

When maintaining this repository, treat `bootstrap/` as the source of truth for installed files. The packaged wheel payload is built from this directory.
Keep it structural: directory `README.md`, `AGENTS.template.md`, `*.template.md`, schemas, and managed `.agentic-workspace/` payload only.

## Installation boundary

Follow the canonical workspace startup/setup skill and the selected artifact's
actual owner operations. Do not copy whole module trees into a lived-in target.
The standalone `agentic-memory` entrypoint is a module maintenance surface;
it does not replace the ordinary native Workspace procedure or grant domain
mutation, effect, retention or completion authority.

Only exact package-owned static support is refreshable/removable. Existing human
instructions and durable Memory/Planning/local state remain with their owners.
Report a missing canonical workspace bootstrap instead of inventing a second
startup manual. A successful query alone does not reconcile or retain a finding.

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
When adding the first repo-specific note of a class, start from `.agentic-workspace/memory/repo/templates/memory-note.template.md`, `.agentic-workspace/memory/repo/templates/invariant.template.md`, or `.agentic-workspace/memory/repo/templates/runbook.template.md` instead of copying old prose by hand.

`AGENTS.md` should stay short and point to `.agentic-workspace/skills/workspace-startup/SKILL.md` for the canonical procedure. Memory-specific references do not replace it.
Bootstrap should modify `AGENTS.md` only through the managed workflow pointer block. Repo-specific `AGENTS.md` prose outside that block is repo-owned and should not be treated as shared upgradeable guidance.

This bootstrap is planning-system agnostic. The installed `.agentic-workspace/memory/repo/` tree owns durable repo knowledge, `.agentic-workspace/memory/repo/current/` is optional routing calibration and legacy current-memory migration review, repo-specific memory skills can live under `.agentic-workspace/memory/repo/skills/`, and only the specifically declared static support files inside `.agentic-workspace/memory/` are package-managed. The enclosing domain root remains repository-owned. Keep the managed package home concentrated there instead of spreading package-managed machinery through wider repo roots.
When planning is installed too, the combined install should be cheaper than either one alone: planning should borrow durable context from memory, and completed planning work should promote durable residue back into memory or canonical docs instead of re-explaining it forever.

Bundled product skills should stay limited to bootstrap lifecycle operations. Repo-local memory procedures should live in repo-owned `.agentic-workspace/memory/repo/skills/`. General non-memory skills should not.

Ownership split:

- bootstrap-managed and upgrade-replaceable: the explicit workflow pointer fence and declared static support files; never the whole Memory or Planning root
- repo-owned and expected to diverge: `AGENTS.md` content outside the managed pointer fence, durable records and notes, local owner state and repo-added skills under `.agentic-workspace/memory/repo/skills/`

Legacy `.agentic-workspace/memory/repo/current/project-state.md` and `task-context.md` files should be migrated out of shared memory: durable facts move into primary memory notes or canonical docs, active state moves back to planning/status, and transient context moves to local-only scratch.

Small routing layers work better than summary-heavy indexes. A good `.agentic-workspace/memory/repo/index.md` points to a few likely-relevant notes rather than trying to restate them.
Treat `.agentic-workspace/memory/skills/memory-router/` as the normal entrypoint for day-to-day note selection, with `.agentic-workspace/memory/repo/index.md` and `.agentic-workspace/memory/repo/manifest.toml` providing the visible routing contract behind it.
When `.agentic-workspace/memory/repo/manifest.toml` marks a note as `canonical_elsewhere`, routing should prefer the canonical checked-in doc and keep the memory note as optional fallback context.
Planning/status surfaces identify touched paths or surfaces; memory routing returns the smallest relevant durable note set.
If the same note keeps being routed for safe work on one subsystem, that is often a cue to suggest clearer docs, stronger validation, or refactor review.
If the same note keeps appearing in merge conflicts, treat it as a note-design smell: split durable facts, add route metadata, or promote stable guidance to docs rather than teaching agents to keep resolving the same catch-all file.
In combined installs, memory should reduce what planning has to restate, not become a second plan explanation layer.
Use `.agentic-workspace/memory/repo/manifest.toml` to make that improvement pressure legible: optional fields such as `memory_role`, `preferred_remediation`, `improvement_note`, `elimination_target`, and `retention_justification` explain whether a note is durable truth or a symptom pointing at upstream docs, tests, skills, scripts, validation, or refactor work.

Common task bundles:

- current-state refresh: use the repo's planning/status surface, not shared memory
- live decision review: the active planning slice plus `.agentic-workspace/memory/repo/decisions/README.md`
- runtime or deployment change: `.agentic-workspace/memory/repo/domains/<runtime-or-deployment-note>.md` plus `.agentic-workspace/memory/repo/runbooks/<relevant-operator-runbook>.md`
- API or interface change: `.agentic-workspace/memory/repo/domains/<api-or-interface-note>.md` plus `.agentic-workspace/memory/repo/invariants/<response-or-contract-note>.md`
- retrieval or search change: `.agentic-workspace/memory/repo/domains/<retrieval-or-search-note>.md` plus `.agentic-workspace/memory/repo/invariants/<retrieval-contract-note>.md` plus `.agentic-workspace/memory/repo/mistakes/recurring-failures.md`
- tests or validation work: `.agentic-workspace/memory/repo/domains/<testing-or-validation-note>.md` plus `.agentic-workspace/memory/repo/mistakes/recurring-failures.md`
- architecture or data-model work: `.agentic-workspace/memory/repo/domains/<data-model-or-architecture-note>.md` plus `.agentic-workspace/memory/repo/invariants/<relevant-invariant-note>.md` plus `.agentic-workspace/memory/repo/decisions/README.md`

Optional repo pattern only: keep short-horizon task execution in the repo's chosen planning/status surface, keep long-horizon roadmap or epic planning separate, and use checked-in current-context notes only for concise re-orientation. Current notes should stay easy to compress, replace, or delete rather than becoming a second durable knowledge layer.

Interoperability pattern catalogue:

- loose coupling: planner first, memory routed on demand
- handoff compression: planner primary, memory holds minimal cross-session continuation context
- durable capture on close: planner closes work, memory updates only if durable knowledge changed
- Combined-install leverage: plans borrow durable context from memory, and repeated plan prose becomes a signal that memory or canonical docs should improve

## Current Decisions

- keep live architectural or cross-cutting decisions in the repo's active planning/status surface while they still steer execution
- move a decision into `.agentic-workspace/memory/repo/decisions/` once it no longer changes implementation choices and is only worth keeping as durable rationale
- preserve decisions at the level of consequence or still-relevant rejected-path boundaries, not meeting history
- do not keep completed transitions or operational residue in the current decision note

## Improvement Paths

- recurring mistake -> consider a regression test, validation, or lint rule
- prose-heavy runbook -> consider a checked-in skill first, then a repo-owned script or command if the workflow stays mechanical
- stable human-facing guidance -> consider promoting it into canonical docs and leaving memory as a stub or backlink
- note that repeatedly explains one hard subsystem -> consider refactor review or clearer module boundaries
- routing crutch used for one awkward area -> consider naming, structure, or ownership cleanup in the repo

If a note is mainly a symptom rather than durable truth, record the expected post-remediation shape too:

- `shrink` when the note should get smaller after upstream improvement
- `promote` when the durable truth should move into canonical docs
- `automate` when a script or skill should replace the repeated prose
- `refactor_away` when a design or boundary change should remove the need for the note entirely

## When to write to memory

- store: invariants, authority boundaries, recurring failure modes, routing hints, operator runbooks, and other facts that are hard to recover quickly from code, tests, tooling, or the planning/status surface
- store: durable consequences and still-relevant rejected-path boundaries when they still constrain future choices

## When not to write to memory

- do not store: milestone status, next-step checklists, backlog state, execution logs, or plan content already owned by the planning/status surface
- do not store: archived planning history
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

`.agentic-workspace/memory/VERSION.md` is the machine-readable version marker used for deterministic upgrades.

## Upgrade model

Use the canonical workspace procedure and exact operations exposed by the selected
artifact. Standalone module maintenance retains its existing install/adopt/upgrade/
uninstall boundary over declared static payload, without owning whole domain roots.
Inspect proposed changes and preserve repository-specific meaning. Use explicit
entrypoint patching only for the package's managed fence; unrelated human prose
remains repository-owned. Repeating refresh should leave current bytes unchanged.

Current runtime decisions and semantic owner changes belong to the native owners.
This package README is descriptive support, not another operating procedure or
permission to modify managed records directly.
