# Planning Collaboration Safety

## Goal

- Strengthen the installed Agentic Planning contract for larger git-heavy teams by making active planning surfaces more merge-friendly, more explicitly status-driven, and safer to archive or replace instead of mutating indefinitely.

## Non-Goals

- Redesign the memory package in this tranche.
- Expand the workspace layer into a new product surface.
- Add speculative new planning schemas beyond the existing TODO and execplan contract.

## Active Milestone

- Status: completed
- Scope: tightened planning templates, docs, and planning-surface checks around active-set size, completed-plan residue, merge-friendly file shape, and archive-over-accumulation guidance.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Promote the memory collaboration-safety tranche when its contract and check scope is bounded.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- .agentic-workspace/planning/execplans/
- .agentic-workspace/planning/scripts/check/
- packages/planning/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Planning must remain useful without memory being installed.
- Execplans must stay contract-shaped rather than becoming journals or branch-local notebooks.
- Archive-over-accumulation should stay the default for completed planning state.
- The workspace layer must remain thinner than the planning package contract it ships.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run pytest packages/planning/tests/test_check_planning_surfaces.py packages/planning/tests/test_installer.py
- make check-planning

## Completion Criteria

- The shipped execplan template explicitly guides merge-friendly, status-driven active planning edits.
- Planning checks catch more collaboration hazards such as completed plans left active or active-plan set pressure.
- Planning docs describe branch-local versus durable planning state more explicitly for adopters.
- The planning package payload and tests stay in sync with the tightened contract.

## Drift Log

- 2026-04-06: Activated the planning collaboration-safety tranche from the new roadmap candidate set.
- 2026-04-06: Completed the planning collaboration-safety tranche and archived the execplan after validation.