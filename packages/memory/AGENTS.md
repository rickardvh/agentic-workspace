# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `../../AGENTS.md` first, then apply this package-specific contract.
<!-- agentic-workspace:workflow:end -->

Package-local contract for work under `packages/memory/`.

## Scope

- This package contains the reusable `agentic-memory-bootstrap` source, shipped payload, package-local skills, and tests.
- Treat `bootstrap/` as packaged payload content for target repositories, not as the active memory system of this monorepo.
- Treat the root `memory/` tree and root planning surfaces as the operational authority for this repository.

## Start Here

1. Read `README.md`.
2. Read `pyproject.toml` when changing packaging, CLI entry points, or dependency metadata.
3. Read only the relevant files under `src/repo_memory_bootstrap/`, `bootstrap/`, `skills/`, or `tests/` for the task.
4. When the task affects shared workflow or ownership boundaries, re-check `../../AGENTS.md`, `../../TODO.md`, and the active execplan.

## Sources Of Truth

- Package behavior and user contract: `README.md`
- Packaging and CLI entry point: `pyproject.toml`
- Installer and runtime logic: `src/repo_memory_bootstrap/`
- Shipped payload for target repositories: `bootstrap/`
- Package-local bootstrap skills: `skills/`
- Regression coverage: `tests/`

## Package Rules

- Keep a clear distinction between package source, shipped payload, and target-repository installed surfaces.
- Do not treat files under `bootstrap/` as repo-owned monorepo workflow surfaces; they are package output.
- Do not recreate package-local operational installs in this monorepo; root memory/planning installs remain authoritative here.
- Preserve CLI behavior and upgrade semantics unless the active task explicitly changes them.
- Prefer updating tests when installer paths, ownership rules, or payload contracts change.

## Validation

- Run the narrowest package-local validation that proves the change.
- Prefer `uv run pytest packages/memory/tests` for behavior changes.
- Prefer `uv run ruff check packages/memory` for lint validation.
- Escalate to `make check-memory` or `make check-all` only when the change crosses package or root orchestration boundaries.
