# Roadmap

Last reviewed: 2026-04-05

## Purpose

Inactive long-horizon migration and post-migration candidate work.

## Active Handoff

- Monorepo scaffold is in place.
- No active execution tranche is currently promoted.
- Promote the next candidate only when the scope is bounded enough for a short execplan and a narrow validation story.

## Next Candidate Queue

- Shared tooling extraction: evaluate a common checker core when the first stable monorepo release exposes repeated maintenance friction across duplicated scripts.
- Unified integration lane: add a dual-bootstrap coexistence smoke-test harness when release dry-runs show the monorepo install topology is stable enough to freeze expectations.
- Contributor onboarding: add package ownership CODEOWNERS and contributor playbooks when migration close-out is complete and package boundaries are no longer shifting.

## Reopen Conditions

- Reopen roadmap planning when active queue completes or a new migration decision gate appears.

## Promotion Rules

- Promote candidate items only when active tranche dependencies are clear and bounded.
- Keep detailed execution in `docs/migration/monorepo-migration-plan.md` once promoted.
