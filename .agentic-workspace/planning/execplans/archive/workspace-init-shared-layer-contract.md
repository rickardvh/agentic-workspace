# Execplan: Workspace Init Shared-Layer Contract

## Goal

Make `agentic-workspace init --preset full` install and validate the shared workspace layer instead of composing only planning and memory module installs.

The resulting full-init contract should seed `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/OWNERSHIP.toml`, and a coherent root `AGENTS.md` entrypoint that reflects the installed workspace plus module boundaries.

## Non-Goals

- Do not move planning or memory domain logic into the workspace layer.
- Do not bypass package-local installers for planning or memory.
- Do not solve unrelated memory-hygiene advisories in adopter repositories.
- Do not treat repo-specific install drift as fixed if the product still cannot reproduce the correct state in a clean repo.

## Active Milestone

- Status: completed
- Scope: defined the shared-layer requirements, implemented them in the root workspace init path, and added coverage that fails when full init omits or mis-shapes the shared workspace layer.
- Ready: completed
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Archived after the workspace layer became a first-class root contract.

## Blockers

- None.

## Touched Paths

- `src/agentic_workspace/`
- `tests/test_workspace_cli.py`
- `docs/`
- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/execplans/workspace-init-shared-layer-contract.md`

## Invariants

- The workspace layer stays thin and orchestration-only.
- Full init must leave one coherent startup path rather than competing module-local entrypoints.
- Shared workspace-layer requirements must be enforced by product behavior and tests, not only by docs.
- Planning and memory installers remain the owners of their package-local surfaces.
- Adopter repos should not need manual cleanup to discover missing workspace-layer files after a nominally successful full init.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run pytest packages/planning/tests`
- `uv run pytest packages/memory/tests`
- `uv run ruff check src tests packages/planning packages/memory`

## Completion Criteria

- Clean full init creates `.agentic-workspace/WORKFLOW.md` and `.agentic-workspace/OWNERSHIP.toml`.
- The root CLI reports those workspace-layer files as part of the installed composed contract.
- Full init produces a coherent root `AGENTS.md` entrypoint for composed installs.
- Tests fail if the shared workspace layer is omitted or if full init regresses to module-only composition.
- The radiatorvvs-calculator failure mode is explainable as a closed product bug rather than an undocumented adopter cleanup step.

## Evidence

- A real adopter repo ended up with planning and memory installed but no `.agentic-workspace/WORKFLOW.md` or `.agentic-workspace/OWNERSHIP.toml`.
- A clean-room `agentic-workspace init --preset full` reproduction shows the same omission, so the gap is product behavior, not only repo-local drift.

## Drift Log

- 2026-04-07: Promoted after dogfooding found that full init can report healthy module installs while omitting the shared workspace layer and leaving AGENTS composition incoherent.
- 2026-04-07: Completed after the root CLI gained packaged workspace-layer sources, composed AGENTS handling, and shared-layer status/doctor coverage.
