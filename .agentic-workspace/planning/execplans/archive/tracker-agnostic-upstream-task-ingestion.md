# Execplan: Tracker-Agnostic Upstream Task Ingestion

## Goal

Define and ship the minimal planning contract for ingesting upstream tasks from external trackers into checked-in planning without making the upstream tracker the execution authority.

The first-class outcome is a tracker-agnostic workflow that lets agents normalize upstream work, preserve source metadata, and promote accepted work into `ROADMAP.md`, `TODO.md`, and execplans while still executing from repo-owned planning surfaces.

## Non-Goals

- Do not make GitHub Issues the required or preferred tracker.
- Do not make external task systems an execution surface.
- Do not build a full automation or synchronization system in the first slice.
- Do not collapse planning intake, review capture, and active execution into one surface.

## Active Milestone

- Status: completed
- Scope: Define the upstream-intake planning contract, land the canonical docs and package surfaces for it, and prove the flow against the GitHub issue that triggered promotion.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/execplans/tracker-agnostic-upstream-task-ingestion.md`
- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/upstream-task-intake.md`
- `packages/planning/`
- `docs/`

## Invariants

- Checked-in planning surfaces remain the execution authority after intake.
- The contract must stay tracker-agnostic across GitHub Issues and other upstream systems.
- Upstream source links and essential metadata must be preservable without making the upstream tracker authoritative.
- Intake, triage, promotion, and execution must remain distinct steps.
- The first slice should prefer contract and guidance over automation.

## Validation Commands

- `make planning-surfaces`
- `uv run pytest packages/planning`

## Completion Criteria

- The repo has a canonical contract for upstream task intake into checked-in planning.
- The contract clearly defines what upstream metadata is preserved and where it lives.
- The promotion path from upstream task to `ROADMAP.md`, `TODO.md`, and execplan is explicit.
- The resulting workflow remains neutral across GitHub Issues and other external trackers.
- The promoted GitHub issue is representable by the new contract without relying on chat-only context.

## Intake Source

- System: GitHub Issues
- ID: `#2`
- URL: <https://github.com/rickardvh/agentic-workspace/issues/2>
- Title: `[Planning]: Support tracker-agnostic upstream task ingestion into checked-in planning`
- Captured reason: explicit upstream planning signal promoted into checked-in work so the repo can prove a tracker-agnostic intake contract without executing from the issue thread itself

## Drift Log

- 2026-04-07: Promoted from GitHub issue `#2` into active planned work so the upstream-task intake path can be defined as a checked-in planning contract instead of remaining issue-only.
- 2026-04-07: Landed the upstream-task intake contract, bundled intake skill, manifest routing updates, and installed planning surfaces; archived after package and planning checks passed.
