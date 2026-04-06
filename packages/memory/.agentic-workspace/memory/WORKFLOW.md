# Workflow Rules

## Purpose

This file defines the compact shared operating model for memory use.

Keep it concise, repo-agnostic, and non-procedural.

## Operating split

- `AGENTS.md` = local bootstrap contract
- repository planning/status surface = external owner of active execution state
- built-in agent planning = short-horizon planning and execution
- checked-in docs outside `/memory` = canonical repo docs and user-facing engineering guidance
- `/memory` = assistive durable technical knowledge and lightweight shared context
- `memory/current/project-state.md` = lightweight repo overview
- `memory/current/task-context.md` = optional checked-in continuation compression
- `memory/current/routing-feedback.md` = optional routing calibration note for concrete missed-note or over-routing cases
- skills = optional repeatable procedures over checked-in knowledge
- local notes = optional scratch context only

## Interoperability contract

- Memory owns durable repo knowledge: invariants, authority boundaries, recurring failure modes, routing hints, and operator runbooks.
- The repository's active planning/status surface owns active intent and sequencing: current goal, next action, done criteria, milestone status, and backlog state.
- Memory may keep a small continuation note for interrupted multi-session work, but that note is only re-orientation support for the next session.
- Memory complements planning by reducing re-orientation cost and preserving durable lessons; it must never compete with the planning system for ownership of active work.
- Memory is also a pressure layer: if a note exists because the repo is awkward to understand, operate, or change safely, use the note to suggest the code, docs, tooling, test, or refactor change that would let the note shrink, move, or disappear.

## Core rules

- Keep durable facts, invariants, runbooks, recurring failures, and lightweight shared context in checked-in files.
- Keep repeatable workflow-like actions in skills.
- Use `memory/index.md` as the routing layer; do not bulk-load `/memory`.
- Prefer the smallest useful working set.
- Default to `memory/index.md` plus at most 2 additional notes unless the task clearly justifies more.
- Treat low-confidence routing as a calibration signal: if routing relies on index or high-level fallbacks instead of direct manifest matches, capture the missed note rather than silently widening the default read set.
- Optimise for deletion and consolidation, not just capture.
- Prefer editing, merging, or removing existing notes over accumulating near-duplicates.
- When referenced behaviour changes, update the note, mark it `Needs verification`, or remove it in the same change.
- Memory is a reasoning aid and hint layer; it does not replace checking code, tests, or canonical docs when they are the source of truth.

## Note maintenance rule

- Update a note when its primary home is still correct and the guidance is still valuable.
- Prune a note when it is obsolete, duplicated, low-value, or easier to recover directly from code or tooling.
- Move closed work into a durable note only when the detail remains hard to recover from code, docs, or tooling.
- Move procedure-heavy prose into a skill when the durable fact should stay in files but the repeated workflow should become optional execution guidance.
- Prefer one primary home for the durable fact and a short cross-reference elsewhere rather than parallel note copies.
- Ask what repo change would eliminate or shrink the note: canonical docs, stronger tests, validation, a script, a skill, or a clearer design boundary.
- Ask whether the note should still exist at all after that repo change; prefer a stub, short residue note, or deletion over carrying full prose forward by default.

## Metadata

- Keep strong note metadata so routing and future skills remain reliable.
- Use statuses such as `Stable`, `Active`, `Needs verification`, and `Deprecated`.
- Use ISO dates for `Last confirmed`.
- Prefer `memory/manifest.toml` for machine-readable note typing, routing, and freshness triggers when the repository maintains that file.
- Use manifest fields such as `audience`, `canonicality`, `task_relevance`, `routes_from`, and `stale_when` to distinguish note classes, promotion candidates, routing relevance, and freshness pressure.
- Optional manifest fields such as `memory_role`, `symptom_of`, `preferred_remediation`, `improvement_candidate`, `improvement_note`, and `elimination_target` can capture why a note exists and what kind of upstream improvement it may be pointing toward.
- Keep calibration artefacts distinct from durable notes: `memory/current/routing-feedback.md` should stay optional, agent-only, and free of broad routing metadata or durable-truth claims.

## Canonical-doc boundary

- Prefer checked-in canonical docs first and memory second when stable policies, procedures, or engineering guidance already have a natural home in `README.md`, `docs/`, or equivalent repo docs.
- Treat memory as assistive residue by default: short lessons, pitfalls, routing hints, operator context, and compact shared state.
- If a memory note becomes stable guidance for humans, mark it as a promotion candidate, move the canonical truth into checked-in docs, then leave a short memory stub or fallback note instead of duplicate prose.
- If a note is already marked `canonical_elsewhere`, keep it visibly smaller than the canonical doc and resist turning fallback context back into a second handbook.
- Do not make core repo docs depend on memory unless the repository explicitly chooses that policy boundary.

## Current-context files

- `memory/current/project-state.md` is a short overview only.
- `memory/current/task-context.md` is optional continuation compression only.
- `memory/current/routing-feedback.md` is optional routing calibration only.
- Do not treat routing-feedback as durable knowledge; it is temporary calibration input and should be compressed or removed once the route is tuned.
- Neither file should become a task list, detailed plan, journal, backlog, ledger, tranche history, or duplicated memory summary.
- A good `project-state.md` normally covers current focus, recent meaningful progress, blockers, and a few high-value notes only.
- Keep `project-state.md` aggressively summary-shaped; if it starts reading like a changelog, history log, or backlog, compress it.
- A good `task-context.md` normally covers status, scope, active goal, touched surfaces, blocking assumptions, next validation, resume cues, and last confirmed only.
- Do not let `task-context.md` become a shadow task board, execution log, sequencing surface, or duplicate planner.
- Keep `routing-feedback.md` compact and review-shaped: record only concrete missed-note or over-routing cases, then compress or remove resolved entries.
- Bias calibration toward missed-note capture first; over-routing cases are useful, but they are more subjective and should stay especially high-signal.
- Treat planner-like headings such as backlog, roadmap, completed tasks, timeline, sprint, action items, or next steps as suspicion signals that the current note may be drifting.

## Ownership boundary

- bootstrap-managed surface in a repo = the workflow pointer block in `AGENTS.md`, `.agentic-memory/`, and other files the installer classifies as shared replaceable
- repo-owned surface in a repo = customised `AGENTS.md` content outside the workflow pointer block, repo-added sibling skills under `memory/skills/`, and ordinary notes outside product-managed shared directories
- `.agentic-memory/` is product-managed shared guidance and workflow support; treat it as upgrade-replaceable unless the repository is intentionally changing the shared bootstrap contract itself.
- The shipped core skills under `.agentic-memory/skills/` are also product-managed and may be replaced on upgrade.
- Other checked-in `/memory` notes are repo-owned working knowledge and are expected to diverge from the starter payload over time.
- Runtime-local or user-local mirrored skill copies are cache-only convenience copies, not a durable source of truth.
- When a repo needs local procedure changes, add a new sibling skill under `memory/skills/` instead of customising the shipped core skills in place.
- If a local note or skill is meant to survive upgrades unchanged, do not place that repo-specific content in `.agentic-memory/`.
- Shared guidance about how to use memory skills belongs in product-managed memory files, not in repo-specific `AGENTS.md` prose outside the managed workflow pointer block.

## Skills boundary

- Skills operate on memory; they do not replace it.
- `memory/skills/` is reserved for skills whose primary purpose is operating on checked-in memory or maintaining the memory system, not for general repo workflows.
- When a repository has shipped shared memory skills, treat `.agentic-memory/skills/README.md` as the discovery surface for those skills instead of expanding `AGENTS.md` with more shared trigger prose.
- If prose starts describing a repeatable maintenance, routing, refresh, capture, hygiene, or upgrade workflow, that is usually a skill candidate.
- If a domain or decision note starts accumulating command-heavy repeatable steps, split the procedure into a runbook or checked-in skill before broadening the note further.
- Checked-in repo-local skills should take precedence over runtime-local mirrors or cached user copies when both exist.
- The base memory system must remain understandable without skills.

## Stale-note pressure

- Review notes not only by age, but also when they become large, frequently touched, cross-domain, or hard to route cleanly.
- Pay extra attention to oversized or stale current-state surfaces such as `memory/current/project-state.md` and `memory/current/task-context.md`.
- Freshness review should consider semantic drift as well as age: linked code, commands, authority boundaries, or expected routing surfaces may have changed even when metadata still looks current.
- If a note keeps growing through unrelated edits, split it by primary home or move repeated procedure into a skill.
- Use note-type-aware size pressure: keep invariants especially tight, keep runbooks procedural, and keep current-context files very small.
- Watch for multi-home drift early: procedures do not belong in domain notes, invariants do not belong in runbooks, and durable rationale should not stay buried in operational checklists.

## Capture threshold

- Write to memory only when the fact is hard to recover quickly from code, tests, tooling, or the repository's active planning/status surface.
- Good memory captures include invariants, authority boundaries, recurring failure modes, routing hints, operator runbooks, durable consequences, and still-relevant rejected-path boundaries.
- Do not store milestone status, next-step checklists, backlog state, or execution logs in memory; those belong in the planning/status surface.
- Keep user-specific preferences, collaboration habits, and stylistic defaults out of repo memory unless they are explicitly adopted as shared technical policy.

## Improvement pressure

- Treat durable truth and improvement signals differently.
- Durable truth should remain visible in memory when it is genuinely expensive to rediscover and not better owned elsewhere.
- Improvement signals are notes that exist because the repo still needs clearer docs, better tests, stronger validation, better tooling, cleaner automation, or simpler design.
- Improvement-signal notes should declare either a remediation path or a short retention justification explaining why the note still belongs in memory.
- Do not assume memory volume should trend downward across all repos or stages; some systems genuinely need more durable memory for a time.
- Judge memory by whether it justifies its cost and reduces rediscovery, not by whether the note count falls.
- Do not let improvement-signal notes become permanent substitutes for repo improvements when those improvements are feasible.
- If the same note keeps being needed for safe work on one subsystem, consider whether the repo needs docs promotion, a skill, a script, a regression test, stronger validation, or refactor review.
- Apply that pressure during normal task work, not only during explicit maintenance passes.
- When routing or syncing memory exposes repeated friction, note sprawl, or recurring workarounds, propose or make the smallest upstream improvement that would reduce the note when it is safe and in scope.
- Prefer emitting a concrete remediation target over a vague hint: suggest where the docs, skill, script, test, validation, or refactor should land, then keep the memory note only as residue, a stub, or a short fallback summary.
- Treat `promotion-report` as the main elimination workflow: use it to decide the upstream target and the intended post-remediation memory shape before expanding the note further.
- If remediation lands, explicitly re-evaluate whether the note should shrink, become a stub, or disappear instead of assuming it remains justified.
- Keep the package advisory outside managed bootstrap surfaces: it may diagnose, classify, prioritise, and suggest concrete repo-owned targets, but it must not autonomously rewrite repo-owned docs, tests, scripts, or code outside the managed bootstrap surface.
- If remediation suggestions become too repo-shape-specific, prefer a clearer handoff into repo-owned work over making the bootstrap itself more invasive.

## Remediation paths

- recurring mistakes -> consider regression tests, validation, or lint rules
- prose-heavy procedures -> consider a checked-in skill first, then a repo-owned script or command if the workflow remains mechanical
- stable human-facing guidance -> consider canonical docs, with memory left as a stub or backlink
- large orientation notes for one code area -> consider refactor review or clearer boundaries
- repeated routing crutches for one awkward area -> consider naming, structure, or ownership cleanup

## Anti-patterns

- turning memory into a task tracker
- copying plan content into durable notes
- storing rediscoverable facts that are easier to inspect directly
- coupling freshness checks to a specific planner or planning file
- forcing repositories to adopt the memory taxonomy inside their planning system

## Local notes

- Local scratch is optional only.
- It must not become required shared knowledge or hidden task state.

## Before ending a task

1. Update or remove stale memory in the same change.
2. Update `memory/current/project-state.md` only if the shared overview changed materially.
3. Refresh `memory/current/task-context.md` only if it will reduce re-orientation cost for the next session.
