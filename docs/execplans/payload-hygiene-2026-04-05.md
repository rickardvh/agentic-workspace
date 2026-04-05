# Payload Hygiene

## Goal

- Remove generated artefacts such as `__pycache__` files from the packaged payload and prove that self-refresh no longer tries to install them.

## Non-Goals

- Redesign the packaging layout.
- Add unrelated lifecycle features while fixing payload hygiene.
- Broaden this into a general build-system cleanup.

## Active Milestone

- Status: in-progress
- Scope: identify how generated artefacts are entering the payload, exclude them from package copy/install flows, and verify the self-hosted adopt path stays clean.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Inspect the payload discovery/copy path and the repo packaging config to locate where `__pycache__` artefacts are being picked up, then apply the smallest robust exclusion.

## Blockers

- None.

## Touched Paths

- `src/repo_planning_bootstrap/`
- `pyproject.toml`
- `tests/`
- `README.md`

## Invariants

- The packaged payload should include only intentional checked-in surfaces.
- Generated artefacts must not be copied into adopting repositories.
- Self-hosted refresh should remain a safe conservative operation.
- The payload rules should be explicit in code or packaging config, not dependent on local cleanup habits.

## Validation Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run agentic-planning-bootstrap adopt --target .`
- `uv run agentic-planning-bootstrap verify-payload`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- Generated artefacts no longer appear in `list-files`, `adopt`, or payload verification output.
- Tests cover the exclusion of generated artefacts from the payload/install flow.
- The self-hosted refresh workflow stays clean after the change.

## Drift Log

- 2026-04-05: Plan created after the canonical self-refresh workflow reported `scripts/__pycache__/render_agent_docs.cpython-314.pyc` as part of the payload.
