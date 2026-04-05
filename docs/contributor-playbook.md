# Contributor Playbook

## Purpose

Use this playbook to choose the right package, planning surface, and validation lane before making changes in `agentic-workspace`.

## Start Here

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. If `TODO.md` points at an active execplan, read that plan before editing code.
4. Load package-local docs only for the package you will touch.

## Ownership Map

- Root workspace: shared lifecycle orchestration, root planning surfaces, shared memory notes, root validation entrypoints, and the thin `agentic-workspace` CLI.
- `packages/memory/`: reusable `agentic-memory-bootstrap` source, packaged payload, package skills, and memory-specific tests.
- `packages/planning/`: reusable `agentic-planning-bootstrap` source, packaged payload, planning helpers, and planning-specific tests.

## Pick The Right Surface

- Use root planning surfaces for active work, roadmap candidates, and execplans.
- Use root memory notes for durable repo knowledge, decisions, and recurring failure modes.
- Edit package code only when the change belongs to that package's shipped behavior or tests.
- Keep the root `agentic-workspace` CLI thin; push module-specific lifecycle logic back into the module packages.

## Validation Lanes

Run the narrowest lane that proves the change.

- Root workspace CLI changes: `uv run pytest tests/test_workspace_cli.py`, `uv run ruff check src tests`, `uv run ty check src`
- Memory package changes: `cd packages/memory && uv run pytest`, `cd packages/memory && uv run ruff check .`
- Planning package changes: `cd packages/planning && uv run pytest`, `cd packages/planning && uv run ruff check .`
- Planning-surface changes: `uv run python scripts/check/check_planning_surfaces.py`
- Memory note/current-state changes: `uv run python scripts/check/check_memory_freshness.py`

Escalate to `make check-memory`, `make check-planning`, or `make check-all` only when the change crosses package or root orchestration boundaries.

## Common Routes

- Lifecycle orchestration or root CLI: start at `src/agentic_workspace/` and `README.md`.
- Memory bootstrap behavior: start at `packages/memory/AGENTS.md`, then `packages/memory/README.md` and `packages/memory/src/`.
- Planning bootstrap behavior: start at `packages/planning/AGENTS.md`, then `packages/planning/README.md` and `packages/planning/src/`.
- Planning contract or archive behavior: start at `TODO.md`, the active execplan, and `packages/planning/src/repo_planning_bootstrap/installer.py`.

## Review Expectations

- Preserve package boundaries and independent CLI entrypoints.
- Prefer explicit adapters, manifests, and generated artifacts over private cross-package assumptions.
- Capture meaningful follow-up work in `ROADMAP.md`, `TODO.md`, or an execplan instead of leaving it in chat-only residue.