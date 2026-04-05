# Planning Bootstrap Initialisation

## Goal

- Turn this repository into the packaged and self-hosted reference implementation for the planning bootstrap.

## Non-Goals

- Full parity with `agentic-memory-bootstrap` on the first pass.
- Repo-specific workflow routing beyond the generic planning bootstrap contract.

## Active Milestone

- Status: in-progress
- Scope: land the packaged payload, installer CLI, self-hosted repo surfaces, and baseline tests.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Stabilise the copied payload, wire the installer to it, and prove the baseline flows with tests.

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
- `uv run python scripts/render_agent_docs.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The package installs the planning payload into a target repository.
- This repo contains a self-hosted instance of the planning payload.
- Baseline tests cover the installer and planning checker.

## Drift Log

- 2026-04-05: Initial plan created.
