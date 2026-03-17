# Agent instructions

This file is the local bootstrap contract for agents working in this repository.

Keep it short, stable, and repo-specific. Shared workflow rules live in `memory/system/WORKFLOW.md`.

<!-- agentic-memory:workflow:start -->
Read `memory/system/WORKFLOW.md` for shared workflow rules.
<!-- agentic-memory:workflow:end -->

## Before doing any work

1. Read `TODO.md`.
2. Read `memory/index.md`.
3. Read `memory/system/WORKFLOW.md`.
4. Read only the memory files relevant to the subsystem you will touch.
5. Read any repo docs explicitly referenced by those files.
6. Declare your working set in `.agent-work/current-task.md` or an equivalent local note before coding.

Do not rely on transient chat context when the same knowledge should exist in checked-in files.

`memory/index.md` is the routing layer for task-relevant durable knowledge.  
`memory/system/WORKFLOW.md` defines the shared planning, memory, freshness, and handoff rules.

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

- Use the project's existing Python tooling and packaging conventions.
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
- avoid assumptions about the caller's working directory
- do not guess aggressively in monorepos or nested repos
- prefer explicit `--target` handling when repo-root detection is ambiguous
- keep dry-run output clear and trustworthy
- avoid destructive behaviour unless explicitly requested

## Before ending a task

1. Update `TODO.md`.
2. Check whether your changes affected any existing memory notes or workflow docs.
3. Update, deprecate, or remove those notes as needed.
4. Keep durable notes concise, factual, and de-duplicated.
