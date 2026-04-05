# Monorepo Migration Plan

## Goal

- Migrate `agentic-memory` and `agentic-planning` into a new monorepo while preserving independent distributable packages, independent versioning, and CLI continuity.

## Non-Goals

- Unify package codebases into one package.
- Change package names or CLI command names.
- Archive source repositories before release dry-runs and smoke tests pass.

## Active Milestone

- Status: in-progress
- Scope: complete history-preserving import of both source repositories into package workspaces and validate package-local execution.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Import `agentic-memory` into `packages/memory/` with history-preserving strategy and record source commit anchors in `docs/migration/import-map.md`.

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
- package-local tests/lint after each import (to be run once packages are imported)

## Completion Criteria

- Both source repositories are imported with traceable provenance.
- Package-local tests and lint pass for both package directories.
- Root docs and migration map identify source commit anchors and rollback points.

## Drift Log

- 2026-04-05: Plan created in new monorepo host as Phase 0/1 implementation start.
