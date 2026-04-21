# Delegated Judgment Front-Door Contract

## Goal

- Ship a front-door delegated-judgment contract that makes the "hand the agent direction and leave it to execute" model explicit in both canonical docs and machine-readable defaults.

## Non-Goals

- Do not add vendor-specific model routing.
- Do not create a separate planner or autonomy subsystem.
- Do not widen this slice into implementing every remaining long-horizon capability.

## Active Milestone

- ID: delegated-judgment-front-door-contract
- Status: completed
- Scope: Add the canonical delegated-judgment contract, ship it in the planning payload, expose it through workspace defaults, and align the front-door docs around that contract.
- Ready: false
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and clear the active queue residue.

## Blockers

- None.

## Touched Paths

- `docs/delegated-judgment-contract.md`
- `packages/planning/bootstrap/docs/delegated-judgment-contract.md`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`
- `packages/planning/src/repo_planning_bootstrap/installer.py`
- `packages/planning/tests/test_installer.py`
- `README.md`
- `docs/default-path-contract.md`
- `packages/planning/README.md`
- `llms.txt`

## Invariants

- Keep the contract quiet, tool-agnostic, and bounded.
- Humans set direction and constraints; agents may improve local means.
- Agents must not silently widen requested ends, owned surface, or time horizon.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- The repo has a canonical delegated-judgment contract doc.
- The planning payload ships that doc.
- `agentic-workspace defaults --format json` exposes the same contract in machine-readable form.
- Front-door docs point at the contract as the normal answer for direction, local authority, and escalation.

## Drift Log

- 2026-04-09: Created to turn bounded delegated judgment from capability model into a shipped front-door contract.
- 2026-04-09: Completed by shipping the delegated-judgment contract doc, exposing it through `agentic-workspace defaults --format json`, and aligning the front-door docs and payload with the same rule.
