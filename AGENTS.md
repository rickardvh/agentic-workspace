# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.
<!-- agentic-workspace:workflow:end -->

Local bootstrap contract for agents working in this monorepo.

## Precedence

Resolve instruction conflicts in this order:

1. Explicit user request.
2. `AGENTS.md`.
3. Package-local `AGENTS.md` under `packages/*/` once imported.
4. Routed memory or canonical repo docs when present.

## Startup Procedure

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read the active feature plan in `docs/execplans/` when the TODO surface points there.
4. Read `ROADMAP.md` only when promoting work.
5. Load package-local docs only for the package being edited.

Do not start coding from chat context alone when the same information exists in checked-in files.
Do not bulk-read all planning surfaces.

## Sources Of Truth

- Active queue: `TODO.md`
- Long-horizon candidate work: `ROADMAP.md`
- Design constraints for future changes: `docs/design-principles.md`

## Product Direction

This repository exists to build agent-first workspace infrastructure: systems that make coding agents more capable, more reliable, and easier to trust in real repositories.

Work in this repo should steer toward these goals:

- Build for agents first, while keeping the result legible and useful to humans.
- Treat development work in this repo as live testing of the shipped packages and workflows.
- Dogfood every major capability here before treating it as mature.
- Continuously evaluate friction, reliability gaps, confusing ownership, and handoff failures during normal work.
- Feed meaningful friction and improvement signals back into the active plan, roadmap, or routed memory instead of leaving them in chat-only residue.
- When internal use reveals repeated friction, prefer fixing the shipped package or contract over adding repo-local workaround guidance.
- Prefer repository-native state over chat-only or tool-local state.
- Give agents durable context, explicit execution state, clear routing, narrow validation, and cheap handoff.
- Optimise for continuity across sessions, tools, models, and contributors.
- Keep systems modular, portable, and selectively adoptable in other repos.
- Preserve strict boundaries between concerns; do not let planning, memory, routing, checks, or workspace orchestration blur together.
- Treat internal use as a proving ground, not a licence for repo-specific hacks.
- Generalise only after a feature works under real autonomous use here.
- Avoid overfitting to this monorepo when shaping package behavior; prefer solutions that remain broadly useful in other repositories.
- Favour mechanisms that reduce rediscovery, drift, and manual supervision.
- Keep the system quiet in normal use: prefer structure that lowers reading and reasoning cost over workflow ceremony.
- Leave the repository cleaner than you found it within the touched scope, and record broader cleanup as follow-up instead of silently expanding the task.
- Preserve one primary owner per concern so planning, memory, routing, checks, and orchestration do not drift into duplicated authority.
- Treat selective adoption as a product requirement, not a nice-to-have: each module should remain useful alone.
- Keep lifecycle centralized and domain logic package-local so workspace convenience does not erase module responsibility.

The standard for success is not novelty. It is giving agents real operating leverage in a repo: faster restart, safer execution, better continuity, and less wasted context.

When changing product shape, ownership boundaries, lifecycle behavior, or maintainer workflow, re-check `docs/design-principles.md` and make sure the change still passes those design tests.

## Repo Rules

- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.

## Validation

- Run the narrowest validation that proves a change.
- Prefer package-local checks after package import.
- Add monorepo-wide checks only when cross-package integration changes.
