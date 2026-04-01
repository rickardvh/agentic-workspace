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
- skills = optional repeatable procedures over checked-in knowledge
- local notes = optional scratch context only

## Interoperability contract

- Memory owns durable repo knowledge: invariants, authority boundaries, recurring failure modes, routing hints, and operator runbooks.
- The repository's active planning/status surface owns active intent and sequencing: current goal, next action, done criteria, milestone status, and backlog state.
- Memory may keep a small continuation note for interrupted multi-session work, but that note is only re-orientation support for the next session.
- Memory complements planning by reducing re-orientation cost and preserving durable lessons; it must never compete with the planning system for ownership of active work.

## Core rules

- Keep durable facts, invariants, runbooks, recurring failures, and lightweight shared context in checked-in files.
- Keep repeatable workflow-like actions in skills.
- Use `memory/index.md` as the routing layer; do not bulk-load `/memory`.
- Prefer the smallest useful working set.
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

## Metadata

- Keep strong note metadata so routing and future skills remain reliable.
- Use statuses such as `Stable`, `Active`, `Needs verification`, and `Deprecated`.
- Use ISO dates for `Last confirmed`.
- Prefer `memory/manifest.toml` for machine-readable note typing, routing, and freshness triggers when the repository maintains that file.
- Use manifest fields such as `audience`, `canonicality`, `task_relevance`, `routes_from`, and `stale_when` to distinguish note classes, promotion candidates, routing relevance, and freshness pressure.

## Canonical-doc boundary

- Prefer checked-in canonical docs first and memory second when stable policies, procedures, or engineering guidance already have a natural home in `README.md`, `docs/`, or equivalent repo docs.
- Treat memory as assistive residue by default: short lessons, pitfalls, routing hints, operator context, and compact shared state.
- If a memory note becomes stable guidance for humans, mark it as a promotion candidate, move the canonical truth into checked-in docs, then leave a short memory stub or fallback note instead of duplicate prose.
- Do not make core repo docs depend on memory unless the repository explicitly chooses that policy boundary.

## Current-context files

- `memory/current/project-state.md` is a short overview only.
- `memory/current/task-context.md` is optional continuation compression only.
- Neither file should become a task list, detailed plan, journal, backlog, ledger, tranche history, or duplicated memory summary.
- A good `project-state.md` normally covers current focus, recent meaningful progress, blockers, and a few high-value notes only.
- Keep `project-state.md` aggressively summary-shaped; if it starts reading like a changelog, history log, or backlog, compress it.
- A good `task-context.md` normally covers the active goal, touched surfaces, blocking assumptions, and next validation only.
- Do not let `task-context.md` become a shadow task board, execution log, sequencing surface, or duplicate planner.

## Ownership boundary

- `memory/system/` is product-managed shared guidance; treat it as upgrade-replaceable unless the repository is intentionally changing the shared bootstrap contract itself.
- The shipped core skills under `memory/skills/` are also product-managed and may be replaced on upgrade.
- Other checked-in `/memory` notes are repo-owned working knowledge and are expected to diverge from the starter payload over time.
- Runtime-local or user-local mirrored skill copies are cache-only convenience copies, not a durable source of truth.
- When a repo needs local procedure changes, add a new sibling skill under `memory/skills/` instead of customising the shipped core skills in place.
- If a local note or skill is meant to survive upgrades unchanged, do not place that repo-specific content in `memory/system/` or in the shipped core skill directories.

## Skills boundary

- Skills operate on memory; they do not replace it.
- `memory/skills/` is reserved for skills whose primary purpose is operating on checked-in memory or maintaining the memory system, not for general repo workflows.
- If prose starts describing a repeatable maintenance, routing, refresh, capture, hygiene, or upgrade workflow, that is usually a skill candidate.
- Checked-in repo-local skills should take precedence over runtime-local mirrors or cached user copies when both exist.
- The base memory system must remain understandable without skills.

## Stale-note pressure

- Review notes not only by age, but also when they become large, frequently touched, cross-domain, or hard to route cleanly.
- Pay extra attention to oversized or stale current-state surfaces such as `memory/current/project-state.md` and `memory/current/task-context.md`.
- Freshness review should consider semantic drift as well as age: linked code, commands, authority boundaries, or expected routing surfaces may have changed even when metadata still looks current.
- If a note keeps growing through unrelated edits, split it by primary home or move repeated procedure into a skill.

## Capture threshold

- Write to memory only when the fact is hard to recover quickly from code, tests, tooling, or the repository's active planning/status surface.
- Good memory captures include invariants, authority boundaries, recurring failure modes, routing hints, operator runbooks, durable consequences, and still-relevant rejected-path boundaries.
- Do not store milestone status, next-step checklists, backlog state, or execution logs in memory; those belong in the planning/status surface.
- Keep user-specific preferences, collaboration habits, and stylistic defaults out of repo memory unless they are explicitly adopted as shared technical policy.

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
