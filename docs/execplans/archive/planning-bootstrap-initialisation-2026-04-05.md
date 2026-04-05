# Planning Bootstrap Initialisation

## Goal

- Turn this repository into the packaged and self-hosted reference implementation for the planning bootstrap.

## Non-Goals

- Full parity with `agentic-memory-bootstrap` on the first pass.
- Repo-specific workflow routing beyond the generic planning bootstrap contract.

## Active Milestone

- Status: completed
- Scope: landed the first packaged execution-facing helpers, stronger checker diagnostics, and the supporting tests/docs for the self-hosted planning bootstrap.
- Ready: false
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed execplan once no active surfaces still reference it.

## Blockers

- None.

## Touched Paths

- `bootstrap/`
- `src/repo_planning_bootstrap/`
- `scripts/`
- `tools/`
- `tests/`

## Invariants

- `TODO.md` remains the active queue surface.
- Active execplans remain the execution-contract surface.
- `ROADMAP.md` remains the inactive strategic candidate surface.
- The packaged payload stays generic even when this repo self-hosts it.

## Validation Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run python scripts/render_agent_docs.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap doctor --target .`
- `uv run agentic-planning-bootstrap summary --target . --format json`

## Completion Criteria

- The package installs the planning payload into a target repository.
- This repo contains a self-hosted instance of the planning payload.
- Baseline tests cover the installer and planning checker.
- The package exposes `summary`, `promote-to-plan`, and `archive-plan` as file-native helpers.
- Doctor output provides actionable remediation for common planning-surface drift.
- Checker output and tests cover the new advisory diagnostics without introducing a second schema.

## Drift Log

- 2026-04-05: Initial plan created.
- 2026-04-05: Expanded the active milestone to cover helper flows and checker diagnostics after the initial bootstrap landed.
- 2026-04-05: Recorded the current pass mid-implementation to bring the remaining work back under the checked-in execution contract.
- 2026-04-05: Completed the helper, checker, testing, and documentation pass for the first execution-facing productization layer.
