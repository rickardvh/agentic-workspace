# Contributor Playbook

## Purpose

Use this playbook to choose the right package, planning surface, and validation lane before making changes in `agentic-workspace`.

This playbook is primarily for maintainers operating as coding agents. Human contributors can use it too, but it is intentionally optimized for explicit routing, bounded reads, and narrow validation.

## Agent Maintainer Path

Default startup path for an agent maintainer:

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read one active execplan only when `TODO.md` points to it.
4. Read package-local `AGENTS.md` only for the package you will edit.
5. Use this playbook to pick the right ownership surface and narrow validation lane.

Prefer repository-native state over chat-only context. If a follow-up matters after the current turn, record it in planning or memory instead of relying on conversational residue.

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

As a maintainer rule of thumb:

- if the fact should survive the current task, it probably belongs in memory or canonical docs
- if the fact changes what is active now or what must happen next, it probably belongs in planning
- if the behavior is package-specific, keep it in that package rather than teaching the workspace layer too much

## Validation Lanes

Run the narrowest lane that proves the change.

- Root workspace CLI changes: `uv run pytest tests/test_workspace_cli.py`, `uv run ruff check src tests`, `uv run ty check src`
- Memory package changes: `make sync-memory` once, then `cd packages/memory && uv run pytest` or `cd packages/memory && uv run ruff check .`; escalate to `make check-memory` for the full package lane
- Planning package changes: `make sync-planning` once, then `cd packages/planning && uv run pytest` or `cd packages/planning && uv run ruff check .`; escalate to `make check-planning` for the full package lane
- Planning-surface changes: `make planning-surfaces`; rerun `make render-agent-docs` when the planning manifest or generated routing docs change
- Memory note/current-state changes: `uv run python scripts/check/check_memory_freshness.py`

Escalate to `make check-memory`, `make check-planning`, or `make check-all` only when the change crosses package or root orchestration boundaries.

## Common Routes

- Lifecycle orchestration or root CLI: start at `src/agentic_workspace/` and `README.md`.
- Memory bootstrap behavior: start at `packages/memory/AGENTS.md`, then `packages/memory/README.md` and `packages/memory/src/`.
- Planning bootstrap behavior: start at `packages/planning/AGENTS.md`, then `packages/planning/README.md` and `packages/planning/src/`.
- Planning contract or archive behavior: start at `TODO.md`, the active execplan, and `packages/planning/src/repo_planning_bootstrap/installer.py`.

Generated guidance lives under `tools/`, but the source of truth for that guidance is `.agentic-workspace/planning/agent-manifest.json`. When routing docs drift, update the managed manifest and rerender instead of editing generated files directly.

## Review Expectations

- Preserve package boundaries and independent CLI entrypoints.
- Prefer explicit adapters, manifests, and generated artifacts over private cross-package assumptions.
- Capture meaningful follow-up work in `ROADMAP.md`, `TODO.md`, or an execplan instead of leaving it in chat-only residue.
