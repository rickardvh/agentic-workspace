# Handoff And Execution Summary Contract

## Goal

- Ship the first bounded planning-side execution-summary contract so completed slices leave one compact checked-in outcome summary before archive.

## Non-Goals

- Move durable technical residue into planning.
- Solve the broader environment and recovery guidance problem in this slice.
- Turn execplans into retrospective notebooks or changelogs.

## Intent Continuity

- Larger intended outcome: Make planning continuation cheap enough that completed bounded slices do not rely on chat or ad hoc prose for later resumption.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate `Environment and recovery guidance contract`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: The next planning-facing tranche should reduce remaining restart and recovery friction after execution-summary shape is explicit.

## Active Milestone

- Status: completed
- Scope: define the execution-summary contract, add it to the shipped planning docs and templates, require it before archive, and cover the contract with checker and installer tests.
- Ready: ready
- Blocked: no
- optional_deps: none

## Immediate Next Action

- Archive this completed slice and leave the remaining environment/recovery gap queued for the next planning-facing tranche.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execution-summary-contract.md`
- `.agentic-workspace/planning/execplans/`
- `packages/planning/`

## Invariants

- Keep the summary compact and completion-shaped.
- Do not duplicate memory or drift-log content in the summary contract.
- Require explicit summary shape before archive only for completed plans.

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- Planning ships one canonical execution-summary contract doc.
- Execplan README and template encode the section explicitly.
- Archive fails closed when completed execplans omit or leave placeholder execution-summary fields.
- Checker and installer tests cover the new contract.

## Execution Summary

- Outcome delivered: Shipped a canonical execution-summary contract, added `Execution Summary` to the execplan template and README, and made archive/check behavior fail closed when completed plans leave outcome state implicit.
- Validation confirmed: `uv run pytest packages/planning/tests/test_installer.py`; `uv run pytest packages/planning/tests/test_check_planning_surfaces.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `make check`
- Follow-on routed to: `ROADMAP.md` candidate `Environment and recovery guidance contract`
- Resume from: No further action in this plan; start from the queued recovery-guidance candidate when the next planning-facing slice is selected.

## Drift Log

- 2026-04-09: Plan created after the planning beta-readiness review identified execution-summary shape as the clearest remaining planning maturity gap.
- 2026-04-09: Completed after the shipped docs, template, archive gate, checker, payload verification, and full repo validation lane all passed.
