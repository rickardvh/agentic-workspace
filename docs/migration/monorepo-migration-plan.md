# Monorepo Migration Plan

## Goal

- Migrate `agentic-memory` and `agentic-planning` into a new monorepo while preserving independent distributable packages, independent versioning, and CLI continuity.

## Non-Goals

- Unify package codebases into one package.
- Change package names or CLI command names.
- Archive source repositories before release dry-runs and smoke tests pass.

## Active Milestone

- Status: in-progress
- Scope: establish root-level orchestration and CI coverage for both imported packages using package-local validation contracts, including uv dependency install routing and installed planning/memory system consolidation.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Redirect package test fixtures to root-owned planning/memory systems as the primary test home, while retaining only a minimal package-local payload-contract lane.

## Monorepo Lessons (2026-04-05)

- uv workspace resolution is workspace-wide: invoking uv commands from `packages/memory/` or `packages/planning/` still includes both workspace members.
- Shared dependency-group names (currently `dev` in both packages) are effectively merged in root `uv sync --all-groups`, which is useful for one monorepo dev environment but hides package ownership boundaries.
- The monorepo root must be marked non-package (`[tool.uv] package = false`) to avoid editable build failures for the workspace host.
- Package-local validation should be routed through explicit package-scoped commands when isolation matters, rather than relying on current working directory.
- Imported package roots currently contain checked-in installed systems, not only package payload source: `packages/memory/` has an installed memory system and `packages/planning/` has both installed memory and planning systems.
- Keeping those installed systems active in both package roots duplicates ownership for routing, current-state notes, and workflow entrypoints; monorepo operation should converge to one root installation per system.
- Consolidation is a content migration problem (merge and route existing memory/planning notes), not only a tooling install problem.
- Running uninstall against package roots removes files that package test suites still import directly (for example package-level planning checker and memory routing fixtures), so full deletion is not yet safe.
- Current stable model: root-owned systems are authoritative for monorepo orchestration; package-local systems remain package-owned fixture/dev surfaces used by package-local checks.

## Follow-Up Work Queue

- Define dependency-group routing strategy for monorepo workflows:
	- keep a merged root developer environment for day-to-day work;
	- add package-scoped sync entrypoints for memory/planning lanes.
- Add root Make targets for package-scoped uv sync/check flows and call those from CI matrix jobs.
- Document install topology and command expectations in root and package READMEs so contributors understand when environments are shared vs scoped.
- Add a regression check that asserts package-lane commands do not accidentally depend on unrelated package dev dependencies.
- Consolidate installed systems into root-owned surfaces:
	- run conservative root adoption for memory and planning systems;
	- populate root memory/planning content from package-local installed notes;
	- define conflict resolution policy for duplicate current-state and decision notes.
- Add explicit routing rules in root planning/memory entrypoints so package-specific execution and durable knowledge remain discoverable after merge.
- Decide post-consolidation status for package-local installed-system files (remove, archive, or retain only as package test fixtures) and enforce with checks.
- Add explicit labeling and docs that package-local planning/memory surfaces are package-fixture lanes, not monorepo orchestration authorities.
- Implement fixture-lane hardening for package-local systems:
	- mark package-local planning/memory surfaces as package-owned test/dev fixtures in package docs and AGENTS contracts;
	- add a root check that warns when root orchestration points at package-local operational surfaces;
	- add a migration gate that fails if fixture surfaces expand unexpectedly without plan updates.
- Redirect package tests to root fixture home where appropriate:
	- move routing/checker fixture reads in package tests to root-owned planning/memory paths;
	- keep package-local tests only for payload integrity (install/uninstall/verify-payload) against shipped package sources;
	- add CI split so root-fixture behavior and package payload-contract behavior are both covered explicitly.

## Blockers

- None.

## Touched Paths

- `packages/memory/`
- `packages/planning/`
- `docs/migration/`
- `.github/workflows/`
- `README.md`
- `AGENTS.md`
- `TODO.md`
- `ROADMAP.md`
- `Makefile`
- `pyproject.toml`

## Invariants

- Keep package-local boundaries clear and enforceable.
- Preserve independent package versioning and release tracks.
- Preserve CLI entry point names: `agentic-memory-bootstrap` and `agentic-planning-bootstrap`.
- Keep managed hidden surfaces separate (`.agentic-memory/` vs `.agentic-planning/`).
- Do not complete cutover until release dry-runs and coexistence smoke tests pass.

## Validation Commands

- `make import-checklist`
- `make check-memory`
- `make check-planning`
- `make check-all`

## Completion Criteria

- Root entrypoints can run package-local validations deterministically.
- CI enforces package-specific validation for both imports.
- Remaining path/tooling mismatches are fixed or explicitly queued in active planning.
- Dependency routing behavior is explicit, documented, and exercised by root/CI entrypoints.
- A single root-owned installed planning system and memory system are in place, with package knowledge and execution context merged and routed.
- Package-local system files are either removed or explicitly retained as package test/dev fixtures with clear non-authoritative status.
- Most package tests execute against root-owned fixture systems; package-local operational reads are limited to explicit payload-contract tests.

## Drift Log

- 2026-04-05: Plan created in new monorepo host as Phase 0/1 implementation start.
- 2026-04-05: Imported `agentic-memory` and `agentic-planning` via `git subtree` into `packages/` and shifted active work to package-local validation.
- 2026-04-05: Verified checker execution from package roots; migration now tracks package-root path assumptions explicitly (not monorepo-root execution).
- 2026-04-05: Fixed planning package import regressions (stale helper imports and payload script contract mismatch) so package-local test/lint/check suites pass from monorepo paths.
- 2026-04-05: Added root Make targets and CI matrix jobs to enforce package-local validation from monorepo orchestration surfaces.
- 2026-04-05: Confirmed uv workspace dependency behavior is workspace-wide from any member cwd; queued dependency merge/routing work and documentation follow-ups.
- 2026-04-05: Confirmed package imports include duplicated installed planning/memory systems; queued root-adopt plus populate consolidation work.
- 2026-04-05: Implemented root memory and planning adoption, populated root memory and imported package planning archives, added root sync lane routing in Make and CI, and validated package checks from root entrypoints.
- 2026-04-05: Exercised uninstall flows under package subdirectories; discovered package test suites still depend on certain package-local planning/memory files, so package-local systems are now tracked as fixture-owned surfaces rather than immediate deletion targets.
- 2026-04-05: Follow-up direction updated to prefer redirecting tests to root-owned fixture homes, with package-local coverage narrowed to payload-contract validation.
- 2026-04-05: Implemented uninstall-safe redirection: planning checker tests and root/package check targets now resolve root-owned scripts, memory installer tests use fixture templates for routing baselines, and uninstall apply runs in both package directories complete with root validation passing.
- 2026-04-05: Removed remaining package-root manual-review uninstall residue files and patched memory tests to source project-state/task-context templates from root/payload helpers so post-cleanup validation stays stable.
