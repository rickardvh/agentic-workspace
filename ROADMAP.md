# Roadmap

Last reviewed: 2026-04-05

## Purpose

Inactive long-horizon migration and post-migration candidate work.

## Active Handoff

- Monorepo scaffold is in place.
- Next active tranche is history-preserving import and package-root validation.

## Next Candidate Queue

- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.
- Workspace orchestrator and fenced managed surfaces: move product-managed startup guidance, generated planning assets, and ownership metadata under `.agentic-workspace/`, with a top-level orchestrator file plus fenced managed insertions in `AGENTS.md`, when the post-migration layout is stable enough to refactor installer ownership rules safely.
- Unified integration lane: add a dual-bootstrap coexistence smoke-test harness when release dry-runs show the monorepo install topology is stable enough to freeze expectations.
- Contributor onboarding: add package ownership CODEOWNERS and contributor playbooks when migration close-out is complete and package boundaries are no longer shifting.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new migration decision gate appears.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/migration/monorepo-migration-plan.md` once promoted.
