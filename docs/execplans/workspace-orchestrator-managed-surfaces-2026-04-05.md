# Workspace Orchestrator And Managed Surfaces

## Goal

- Establish `.agentic-workspace/` as the single product-managed enclave with a top-level orchestrator file, explicit ownership metadata, and module-local managed assets so shared guidance stays clean, fenced, and uninstallable.

## Non-Goals

- Move repo-owned execution surfaces such as `TODO.md`, `ROADMAP.md`, `docs/execplans/`, or repo-owned `/memory` notes under `.agentic-workspace/`.
- Hide active execution state or durable repo knowledge behind product-managed indirection.
- Ship mixed-ownership prose in `AGENTS.md` or other repo-owned files without visible managed fences.

## Active Milestone

- Status: in-progress
- Scope: define the target ownership model, then move planning-managed startup assets behind a workspace-level orchestrator and explicit fences without blurring repo-owned authority.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Specify the target `.agentic-workspace/` layout and ownership ledger format so installer, upgrade, verify, and uninstall all use the same source of truth before any file moves begin.

## Blockers

- None.

## Touched Paths

- AGENTS.md
- TODO.md
- ROADMAP.md
- docs/execplans/
- .agentic-workspace/
- tools/
- scripts/
- packages/memory/
- packages/planning/

## Invariants

- Repo-owned execution surfaces remain root-visible, human-editable, and outside product-managed module directories.
- Product-managed additions must live either under `.agentic-workspace/` or inside explicit managed fences in repo-owned files.
- `AGENTS.md` remains a thin repo entrypoint and must not accumulate mixed-ownership workflow prose.
- Install, upgrade, verify, and uninstall must read from one ownership definition instead of inferring ownership from scattered heuristics.
- The system should stay quiet and orderly in normal use: efficient, predictable, and low-ceremony for repo owners.
- Normal development here is product dogfooding and should emit explicit improvement signals.
- Dogfooding changes must generalise beyond this monorepo.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- uv run pytest packages/memory/tests/test_installer.py
- uv run pytest packages/planning/tests
- uv run --project . agentic-memory-bootstrap init --target <temp-repo> --dry-run
- uv run --project . agentic-planning-bootstrap install --target <temp-repo> --dry-run
- make check-all

## Completion Criteria

- `.agentic-workspace/WORKFLOW.md` exists as the shared product-managed startup contract.
- `AGENTS.md` is reduced to a thin repo-owned entrypoint plus explicit managed fences only.
- Planning-managed routing assets and helper scripts live under `.agentic-workspace/planning/` or are generated from there.
- A checked-in ownership manifest or equivalent ledger defines every managed path, owning module, and uninstall policy.
- Installer, upgrade, verify, and uninstall flows for both packages use the same ownership source and no longer rely on scattered path heuristics.
- Package and root docs clearly distinguish repo-owned surfaces from product-managed surfaces.

## Drift Log

- 2026-04-05: Plan created by promoting the workspace-orchestrator and fenced-managed-surface candidate from ROADMAP into an active execution contract.
- 2026-04-05: Added package-local `AGENTS.md` entrypoints under `packages/memory/` and `packages/planning/` so package work starts from explicit source-vs-payload-vs-root-authority boundaries before the broader orchestrator refactor begins.
- 2026-04-05: Root contract updated to make dogfooding explicit: development here is live package testing, agents should capture friction as improvement signals, and changes should generalise beyond this monorepo.