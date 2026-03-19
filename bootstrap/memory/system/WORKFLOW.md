# Workflow Rules

## Purpose

This file defines the compact shared operating model for memory use.

Keep it concise, repo-agnostic, and non-procedural.

## Operating split

- `AGENTS.md` = local bootstrap contract
- task system = external to this bootstrap
- built-in agent planning = short-horizon planning and execution
- `/memory` = durable, shared technical knowledge
- `memory/current/project-state.md` = lightweight repo overview
- `memory/current/task-context.md` = optional checked-in current-task compression
- skills = optional repeatable procedures over checked-in knowledge
- local notes = optional scratch context only

## Core rules

- Keep durable facts, invariants, runbooks, recurring failures, and lightweight shared context in checked-in files.
- Keep repeatable workflow-like actions in skills.
- Use `memory/index.md` as the routing layer; do not bulk-load `/memory`.
- Prefer the smallest useful working set.
- Prefer editing, merging, or removing existing notes over accumulating near-duplicates.
- When referenced behaviour changes, update the note, mark it `Needs verification`, or remove it in the same change.

## Metadata

- Keep strong note metadata so routing and future skills remain reliable.
- Use statuses such as `Stable`, `Active`, `Needs verification`, and `Deprecated`.
- Use ISO dates for `Last confirmed`.
- Prefer `memory/manifest.toml` for machine-readable note typing, routing, and freshness triggers when the repository maintains that file.

## Current-context files

- `memory/current/project-state.md` is a short overview only.
- `memory/current/task-context.md` is short current-context compression only.
- Neither file should become a task list, detailed plan, journal, or duplicated memory summary.

## Ownership boundary

- `memory/system/` is product-managed shared guidance; treat it as upgrade-replaceable unless the repository is intentionally changing the shared bootstrap contract itself.
- The shipped core skills under `memory/skills/` are also product-managed and may be replaced on upgrade.
- Other checked-in `/memory` notes are repo-owned working knowledge and are expected to diverge from the starter payload over time.
- When a repo needs local procedure changes, add a new sibling skill under `memory/skills/` instead of customising the shipped core skills in place.
- If a local note or skill is meant to survive upgrades unchanged, do not place that repo-specific content in `memory/system/` or in the shipped core skill directories.

## Skills boundary

- Skills operate on memory; they do not replace it.
- `memory/skills/` is reserved for skills whose primary purpose is operating on checked-in memory or maintaining the memory system, not for general repo workflows.
- If prose starts describing a repeatable maintenance, routing, refresh, capture, hygiene, or upgrade workflow, that is usually a skill candidate.
- The base memory system must remain understandable without skills.

## Local notes

- Local scratch is optional only.
- It must not become required shared knowledge or hidden task state.

## Before ending a task

1. Update or remove stale memory in the same change.
2. Update `memory/current/project-state.md` only if the shared overview changed materially.
3. Refresh `memory/current/task-context.md` only if it will reduce re-orientation cost for the next session.
