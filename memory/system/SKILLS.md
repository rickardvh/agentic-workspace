# Skills Model

## Purpose

This document defines the boundary between checked-in memory and skills in `agentic-memory-bootstrap`.

## Layer boundary

Use two product layers inside a repo:

- checked-in files = durable shared knowledge and lightweight shared context
- skills = repeatable procedures that operate on those files

The bootstrap contract remains the always-on minimal file structure that keeps the system understandable even without skills.

## Keep in checked-in docs

Keep these in `AGENTS.md`, the repo's chosen task system, or `/memory`:

- repo purpose
- local constraints and guardrails
- architecture facts and invariants
- milestone or task state
- lightweight current-task context that should stay visible in checked-in memory

If something is a durable fact about the repo, store it in files.

The core operating model must remain visible and useful even when skills are unavailable.

## Promote into skills

Use a skill when the behaviour is:

- reusable across tasks or repos
- optional rather than mandatory
- triggerable from a clear request
- procedural or operational
- too detailed for the core repo contract

If something is a repeatable workflow over checked-in files, it is a strong skill candidate.

Good fits:

- memory hygiene
- memory capture
- memory refresh
- memory router
- bootstrap adoption
- bootstrap upgrade
- docs alignment
- release or packaging checks

## First skills to ship

Prioritise a small set of concrete skills:

- `memory-hygiene`
  - run freshness checks
  - detect stale or duplicated notes
  - suggest merges, deletions, or verification updates
- `memory-capture`
  - turn a solved issue or discovered invariant into the right checked-in memory note
- `memory-refresh`
  - inspect changed files and suggest which notes should be updated or marked `Needs verification`
- `memory-router`
  - given touched files or surfaces, identify the smallest relevant memory set to load
- `bootstrap-upgrade`
  - update installed memory scaffolding conservatively

These are now the first shipped product skills. Keep the set concrete and narrow, and avoid vague skills that overlap with generic planning or coding behaviour.

## Avoid first

Do not start with fuzzy skills that overlap heavily with built-in agent behaviour, such as:

- generic planning
- generic coding
- vague "use memory better" instructions

## Distribution stance

For now:

- keep the product's bundled skills in this repository under `skills/`
- do not install skills into target repos by default
- treat them as bundled product assets that capable runtimes can auto-discover
- keep the mandatory bootstrap payload understandable and useful without them
- use manual installation only as a fallback when a runtime does not auto-discover packaged skills
- during development, treat the repo's `skills/` paths as canonical and any bundled installed copies as potentially stale until the package is explicitly reinstalled
