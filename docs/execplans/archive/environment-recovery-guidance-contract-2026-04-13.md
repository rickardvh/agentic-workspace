# Environment Recovery Guidance Contract

## Goal

- Define one canonical planning-side contract for environment assumptions and recovery paths so restartable execution no longer depends on scattered prose.

## Non-Goals

- Turn planning into a general runbook system.
- Replace module-local operational docs or durable memory notes.
- Change the execplan schema beyond clarifying how existing fields carry recovery guidance.

## Intent Continuity

- Larger intended outcome: Remove the remaining planning beta blocker around missing explicit recovery guidance so planning can be treated as a more complete execution contract.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Active Milestone

- Status: completed
- Scope: add the canonical recovery contract to planning, align the package and installed docs, and close the queued roadmap candidate
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None; slice is complete and archived.

## Blockers

- None.

## Touched Paths

- `docs/environment-recovery-contract.md`
- `packages/planning/bootstrap/docs/environment-recovery-contract.md`
- planning package installer/tests/readme/bootstrap routing surfaces
- `TODO.md`
- `ROADMAP.md`
- `docs/maturity-model.md`

## Invariants

- Recovery guidance stays compact and task-local rather than becoming a second runbook system.
- Existing planning fields remain the canonical place to express recovery state; this slice does not add a new required execplan section.
- Durable subsystem environment knowledge continues to live in module docs or memory, not in planning residue.

## Validation Commands

- `cd packages/planning && uv run pytest tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `make render-agent-docs`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- The planning package ships a canonical environment/recovery contract surface.
- Generated planning routing surfaces mention that contract.
- The root repo is refreshed to the latest checked-in planning package contract.
- The roadmap candidate is removed and the planning maturity explanation reflects the closed blocker.

## Execution Summary

- Outcome delivered: Added `docs/environment-recovery-contract.md` as the canonical planning-side recovery contract, wired it into the package payload and generated routing surfaces, refreshed the root repo to that contract, and removed the roadmap candidate.
- Validation confirmed: `cd packages/planning && uv run pytest tests/test_installer.py`; `uv run python scripts/check/check_planning_surfaces.py`; `make render-agent-docs`; `uv run agentic-planning-bootstrap upgrade --target .`
- Follow-on routed to: none; the recovery-guidance candidate is complete
- Resume from: No further action in this plan; continue from the next bounded roadmap candidate if planning-facing follow-through reopens later.

## Drift Log

- 2026-04-13: Promoted the queued recovery-guidance candidate, kept the change inside existing planning field semantics, and closed the candidate after package plus root-contract alignment.
