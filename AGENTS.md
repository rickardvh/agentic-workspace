# Agent Instructions

<!-- agentic-memory:workflow:start -->
Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.
<!-- agentic-memory:workflow:end -->

Local bootstrap contract for agents working in this monorepo.

## Precedence

Resolve instruction conflicts in this order:

1. Explicit user request.
2. Active plan in `docs/migration/` when the task belongs to migration work.
3. `AGENTS.md`.
4. Package-local `AGENTS.md` under `packages/*/` once imported.
5. Routed memory or canonical repo docs when present.

## Startup Procedure

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read the active feature plan in `docs/execplans/` when the TODO surface points there.
4. Read `docs/migration/monorepo-migration-plan.md` when migration work is active or the task belongs to migration execution.
5. Read `ROADMAP.md` only when promoting work.
6. Load package-local docs only for the package being edited.

Do not start coding from chat context alone when the same information exists in checked-in files.
Do not bulk-read all planning surfaces.

## Sources Of Truth

- Active queue: `TODO.md`
- Migration execution contract: `docs/migration/monorepo-migration-plan.md`
- Long-horizon candidate work: `ROADMAP.md`

## Product Direction

This repository exists to build agent-first workspace infrastructure: systems that make coding agents more capable, more reliable, and easier to trust in real repositories.

Work in this repo should steer toward these goals:

- Build for agents first, while keeping the result legible and useful to humans.
- Treat development work in this repo as live testing of the shipped packages and workflows.
- Dogfood every major capability here before treating it as mature.
- Continuously evaluate friction, reliability gaps, confusing ownership, and handoff failures during normal work.
- Feed meaningful friction and improvement signals back into the active plan, roadmap, or routed memory instead of leaving them in chat-only residue.
- Prefer repository-native state over chat-only or tool-local state.
- Give agents durable context, explicit execution state, clear routing, narrow validation, and cheap handoff.
- Optimise for continuity across sessions, tools, models, and contributors.
- Keep systems modular, portable, and selectively adoptable in other repos.
- Preserve strict boundaries between concerns; do not let planning, memory, routing, checks, or workspace orchestration blur together.
- Treat internal use as a proving ground, not a licence for repo-specific hacks.
- Generalise only after a feature works under real autonomous use here.
- Avoid overfitting to this monorepo when shaping package behavior; prefer solutions that remain broadly useful in other repositories.
- Favour mechanisms that reduce rediscovery, drift, and manual supervision.

The standard for success is not novelty. It is giving agents real operating leverage in a repo: faster restart, safer execution, better continuity, and less wasted context.

## Repo Rules

- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.
- Use history-preserving import for both source repositories.
- Do not archive source repositories until release dry-runs and install/upgrade smoke tests pass.

## Validation

- Run the narrowest validation that proves a change.
- Prefer package-local checks after package import.
- Add monorepo-wide checks only when cross-package integration changes.
