# Config-Driven Autonomy And Agnostic Improvements

Date: 2026-04-18

## Goal

Close the unfinished `config-driven-autonomy-and-agnostic-improvements` tranche by:

- moving workspace config loading and validation into a reusable package module
- making config discovery work from subdirectories without forcing repeated `--target`
- relaxing local-only schema handling so unknown fields surface as warnings during reporting instead of breaking ordinary recovery
- consolidating compact workspace-owned integrity checks into `agentic-workspace doctor`

## Scope

- Extract shared config parsing and delegation-outcome helpers out of `src/agentic_workspace/cli.py`.
- Add a workspace-owned `doctor` helper module for checks that belong above ad hoc scripts.
- Preserve existing CLI contracts, test helpers, and emitted source labels.
- Keep the result advisory and agent-agnostic; do not turn config into a scheduler.

## Proof

- `agentic-workspace config --format json` now discovers the workspace root correctly from a nested subdirectory.
- `agentic-workspace config --format json` now carries config warnings for unknown local-only fields instead of failing fast during routine reporting.
- `agentic-workspace doctor --target . --format json` now includes upstream workspace-owned contract checks.
- The refactor no longer breaks the existing CLI compatibility tests.

## Validation

- `uv run pytest tests/test_workspace_cli.py tests/test_contract_tooling.py -q`
- `uv run python scripts/check/check_contract_tooling_surfaces.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `Push-Location src\\agentic_workspace; uv run agentic-workspace config --format json; Pop-Location`
- `uv run agentic-workspace doctor --target . --format json`

## Outcome

Completed. The workspace layer now owns reusable config loading and doctor-side integrity checks without leaving a half-extracted CLI refactor behind, and the roadmap lane can return to idle history.
