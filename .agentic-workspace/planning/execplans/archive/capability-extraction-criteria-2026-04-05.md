# Capability Extraction Criteria

## Goal

- Define the promotion bar for when a cross-cutting capability such as routing or checks should graduate into a standalone package.

## Non-Goals

- Extract a new package in this tranche.
- Lock the repo into a five-package taxonomy regardless of dogfooding evidence.
- Add new runtime code beyond documentation and planning-surface updates.

## Active Milestone

- Status: completed
- Scope: document the extraction criteria in the root architecture guidance and then clear the roadmap candidate.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and remove the finished capability-extraction-criteria candidate from the roadmap queue.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- README.md
- .agentic-workspace/planning/execplans/

## Invariants

- The current architecture stance remains: memory and planning are the standalone products, and the workspace layer owns orchestration.
- Routing and checks remain capabilities first, not packages by default.
- The extraction bar must be evidence-based and compatible with selective adoption.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Completion Criteria

- Root architecture guidance states when a capability is mature enough to become a standalone package.
- The criteria include stable ownership, schema/adapter seams, independent adoption value, and reuse pressure.
- The roadmap no longer carries a separate open capability-extraction-criteria candidate.

## Drift Log

- 2026-04-05: Plan activated after the boundary-charter docs tranche cleared, using the already-committed root architecture stance as the base contract.
- 2026-04-05: Milestone complete: the root architecture guidance now defines the evidence-based promotion bar for extracting cross-cutting capabilities into standalone packages.