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

## Repo Rules

- Keep package boundaries explicit.
- Preserve independent package versioning and CLI entry points.
- Use history-preserving import for both source repositories.
- Do not archive source repositories until release dry-runs and install/upgrade smoke tests pass.

## Validation

- Run the narrowest validation that proves a change.
- Prefer package-local checks after package import.
- Add monorepo-wide checks only when cross-package integration changes.
