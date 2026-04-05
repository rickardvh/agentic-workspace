# Agent Instructions

<!-- agentic-workspace:workflow:start -->
Read `../../AGENTS.md` first, then apply this package-specific contract.
<!-- agentic-workspace:workflow:end -->

Package-local contract for work under `packages/planning/`.

## Scope

- This package contains the reusable `agentic-planning-bootstrap` source, shipped planning payload, helper rendering/check logic, and tests.
- Treat `bootstrap/` as packaged target-repository content, not as the active planning system of this monorepo.
- Treat the root `TODO.md`, `ROADMAP.md`, `docs/execplans/`, and root tooling as the operational authority for this repository.

## Start Here

1. Read `README.md`.
2. Read `pyproject.toml` when changing packaging, CLI entry points, or metadata.
3. Read only the relevant files under `src/repo_planning_bootstrap/`, `bootstrap/`, `skills/`, or `tests/` for the task.
4. When the task affects planning ownership, startup routing, or generated agent docs, re-check `../../AGENTS.md`, `../../TODO.md`, and the active execplan.

## Sources Of Truth

- Package behavior and user contract: `README.md`
- Packaging and CLI entry point: `pyproject.toml`
- Installer, rendering, and upgrade logic: `src/repo_planning_bootstrap/`
- Shipped target-repository payload: `bootstrap/`
- Package-local bootstrap skills: `skills/`
- Regression coverage: `tests/`

## Package Rules

- Keep a clear distinction between package source, shipped payload, and this repo's active planning surfaces.
- Do not confuse payload files under `bootstrap/` with the root planning system that drives current work in this monorepo.
- Preserve generated-doc and manifest relationships when changing planning routing or helper tooling.
- Prefer updating tests when installer paths, generated outputs, or ownership rules change.

## Validation

- Run the narrowest package-local validation that proves the change.
- Prefer `uv run pytest packages/planning/tests` for behavior changes.
- Prefer `uv run ruff check packages/planning` for lint validation.
- Run `uv run python scripts/check/check_planning_surfaces.py` when a change also affects the root planning contract.
- Escalate to `make check-planning` or `make check-all` only when the change crosses package or root orchestration boundaries.