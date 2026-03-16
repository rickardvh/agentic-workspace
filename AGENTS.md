# Agent instructions

This file is the bootstrap contract for any agent working in this repository.

Keep it short, stable, and high-signal. Put durable technical knowledge, recurring traps, invariants, and runbooks under `/memory`, not here.

## Before doing any work

1. Read `TODO.md`.
2. Read `memory/index.md`.
3. Read only the memory files relevant to the subsystem you will touch.
4. Read any repo docs explicitly referenced by those files.

Do not rely on transient chat context when the same knowledge should exist in checked-in files.

`memory/index.md` is the routing layer for the memory system.  
Use it to decide which memory files to load; do not read the entire memory tree by default.

## Repo scope

This repository produces and maintains a reusable bootstrap system that adds agent memory, planning, and working-context conventions to other repositories.

The repo contains:

- a reusable `bootstrap/` payload that can be copied into a target repo
- a CLI installer intended for later use via `uvx`
- templates and helper tooling for durable memory, `TODO.md`, and local agent scratch space
- optional workflow fragments for integrating the system into common repo workflows

Treat this repo as both:

- a normal software project
- the reference implementation of the memory/planning system it distributes

## Workspace guardrails

- Execute commands from this repo root.
- Do not edit sibling repos unless explicitly requested.
- When changing the bootstrap payload, preserve repo-agnostic behaviour unless the task explicitly asks for source-repo-specific customisation.
- Avoid leaking source-repo-specific details into generic bootstrap files.

## Design goals

Prioritise these goals when making changes:

1. simplicity
2. portability
3. safe repeatability
4. low maintenance burden
5. agent-agnostic behaviour

When trade-offs appear, prefer the simplest design that is safe to apply repeatedly to existing repositories.

## Bootstrap-system rules

The bootstrap payload must remain:

- repo-agnostic by default
- conservative about overwriting user files
- easy to inspect as plain files
- suitable for incremental adoption in an existing repo
- suitable for clean bootstrap in an empty repo

Changes to files under `bootstrap/` affect future installations of the system.  
Keep these files repo-agnostic unless a change is explicitly intended to alter the bootstrap behaviour.

The installer must remain:

- conservative by default
- explicit about overwrites
- safe on repeated runs
- simple in its merge behaviour
- suitable for later `uvx` use

## Local scratch policy

`.agent-work/` is local scratch working context.

- It is not durable technical memory.
- It should be git-ignored.
- Durable lessons belong in `/memory`.
- Milestone state belongs in `TODO.md`.

Do not turn `.agent-work/` into a checked-in knowledge store.

## Runtime and tooling

- Use the project’s existing Python tooling and packaging conventions.
- Prefer simple, standard-library-heavy implementations unless a dependency clearly earns its cost.
- For the installer, prefer straightforward file operations and text-based merge logic over elaborate abstractions.
- Use `pathlib` for filesystem work.
- Keep CLI behaviour compact and predictable.

## Style

- Use British English for agent-authored English text unless reproducing a source verbatim.
- Keep user-facing templates concise and practical.
- Prefer explicit placeholders over vague prose in bootstrap files.
- Keep bootstrap files self-contained so they can be copied by script with minimal extra logic.

## Packaging and installer guidance

When working on the installer:

- treat the packaged `bootstrap/` directory as the source of truth for installed payload files
- avoid assumptions about the caller’s working directory
- do not guess aggressively in monorepos or nested repos
- prefer explicit `--target` handling when repo-root detection is ambiguous
- keep dry-run output clear and trustworthy
- avoid destructive behaviour unless explicitly requested

## TODO discipline

`TODO.md` is the single source of truth for milestone status and pending work.

- Before planning or implementation, read `TODO.md`.
- Write plans into the relevant milestone section before touching code.
- Update `TODO.md` immediately after finishing implementation.
- Leave enough context for another agent to resume with minimal friction.
- Keep it short; prune completed noise.
- Keep `TODO.md` execution-focused: milestones, next actions, blockers, and short handoff context only.
- Do not store durable technical lessons, subsystem behaviour, invariants, or runbooks in `TODO.md`; move those to `/memory`.
- Collapse stale implementation detail into a short outcome note instead of preserving a full activity log.
- If a section no longer changes future execution, delete it or reduce it to a one-line summary.
- Each open item should answer one of these clearly: what is next, what is blocked, or what decision is pending. If it answers none of them, prune it.

## Memory discipline

Durable project knowledge belongs under `/memory`.

Use this split:

- `AGENTS.md`: bootstrap policy and stable operating rules
- `TODO.md`: milestone state, active plan, short execution handoff
- `/memory`: durable subsystem knowledge, invariants, recurring failures, runbooks, decisions
- `.agent-work/`: temporary task-local working notes

Update `/memory` when you discover:

- a non-obvious issue likely to recur
- an invariant future edits could break
- a repeatable fix or maintenance procedure
- a boundary or contract that is easy to misunderstand
- an installer safety rule that future work could accidentally violate

## Memory admission rule

Only create a new memory note when the information is likely to matter again.

Good candidates:

- recurring failures
- subsystem boundaries that are easy to misunderstand
- invariants future edits could break
- repeatable operational procedures

Do not create memory notes for one-off discoveries or temporary task details.  
Prefer `.agent-work/` or `TODO.md` for short-lived context.

## Memory statuses

Use these statuses consistently in durable notes:

- `Stable`: recently verified and safe to rely on
- `Active`: currently relevant but likely to change
- `Needs verification`: do not trust without checking
- `Deprecated`: kept temporarily for transition; do not rely on for new work

## Memory freshness rule

When you touch code, docs, tests, commands, packaging, or installer behaviour referenced by an existing memory note, check whether that note still matches reality.

If it no longer matches:

- update it in the same change
- or mark it `Needs verification`
- or deprecate/remove it if it no longer applies

Do not leave contradicted memory behind.

## Memory routing

Use `memory/index.md` to decide what to load.

Do not load all of `/memory` by default.

Examples:

- bootstrap payload work: load memory about templates, payload structure, and portability rules
- installer work: load CLI, merge behaviour, safety, and packaging notes
- workflow integration work: load notes about optional fragments and maintenance hooks
- documentation or repo-shaping work: load current project-state and active decisions first

## Before ending a task

1. Update `TODO.md`.
2. Check whether your changes affected any existing memory notes.
3. Update, deprecate, or remove those notes as needed.
4. Add new durable memory only if it is likely to matter again.
5. Prefer updating an existing memory file over creating a near-duplicate.
6. Leave a short handoff note if work is incomplete.
7. Keep durable notes concise, factual, and de-duplicated.
