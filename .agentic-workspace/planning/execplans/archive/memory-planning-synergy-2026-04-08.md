# Memory/Planning Synergy

## Goal

- Define the first explicit combined-install contract so Planning can borrow durable context from Memory, completed planning work can promote durable residue cleanly, and combined installs reduce restart cost more obviously than either module alone.

## Non-Goals

- No new module or orchestration feature.
- No requirement that either module depend on the other.
- No broad cross-link-everything guidance.

## Active Milestone

- ID: combined-install-synergy-contract
- Status: completed
- Scope: refine the integration contract plus shipped planning and memory workflow docs so combined installs have an explicit lightweight borrow/promote/restart model without blurring ownership.
- Ready: ready
- Blocked: none

## Immediate Next Action

- Update the integration contract and shipped planning/memory guidance to encode when planning should borrow from memory, when durable plan residue should promote into memory or canonical docs, and what counts as a missing-synergy signal.

## Blockers

- None.

## Touched Paths

- `docs/integration-contract.md`
- `docs/contributor-playbook.md`
- `packages/planning/README.md`
- `packages/planning/bootstrap/.agentic-workspace/planning/execplans/README.md`
- `packages/memory/README.md`
- `packages/memory/bootstrap/.agentic-workspace/memory/WORKFLOW.md`
- `packages/memory/bootstrap/.agentic-workspace/memory/repo/index.md`
- `packages/planning/tests/test_installer.py`
- `packages/memory/tests/test_installer.py`

## Invariants

- Planning remains the owner of active execution state.
- Memory remains the owner of durable anti-rediscovery knowledge.
- Combined installs should reduce restart cost without making either module mandatory for the other.
- Repeated plan prose or restart friction should become improvement signals, not a reason to blur planning and memory ownership.

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py`
- `cd packages/memory && uv run pytest tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make maintainer-surfaces`
- `uv run agentic-planning-bootstrap upgrade --target .`
- `uv run agentic-memory-bootstrap upgrade --target .`

## Completion Criteria

- The integration contract explicitly defines how planning borrows from memory in combined installs.
- The shipped planning and memory payloads explain how durable plan residue should promote into memory or canonical docs.
- The docs explicitly treat repeated plan re-explanation or restart friction as missing-synergy signals.
- Regression tests prove the refined combined-install contract is present in the shipped payloads.
- Issue `#11` can be closed with landed surfaces and validation evidence.

## Drift Log

- 2026-04-08: Promoted from GitHub issue `#11` for immediate implementation by explicit maintainer choice.
- 2026-04-08: Completed by refining the integration contract plus shipped planning and memory guidance so combined installs explicitly borrow durable context, promote durable residue cleanly, and treat repeated plan re-explanation as a missing-synergy signal.
