# Boundary Charter Hardening

## Goal

- Make the package-level documentation reflect the repo’s checked-in ownership tests and anti-blur rules so boundary guidance is visible where day-to-day package work happens.

## Non-Goals

- Introduce new top-level packages.
- Change runtime package behavior or installer semantics.
- Rework the root architecture stance beyond what is already committed.

## Active Milestone

- Status: completed
- Scope: add concise ownership and anti-blur guidance to the memory and planning package docs, then clear the corresponding roadmap candidate.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and remove the finished boundary-charter hardening candidate from the roadmap queue.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- .agentic-workspace/planning/execplans/
- packages/memory/README.md
- packages/planning/README.md

## Invariants

- Root README remains the canonical cross-package boundary summary.
- Package docs should restate only the guidance relevant to their own ownership boundary.
- Package-local docs must reinforce selective adoption rather than imply full-stack dependence.

## Validation Commands

- uv run pymarkdown -d md013,md024 scan packages/memory/README.md
- uv run python scripts/check/check_planning_surfaces.py

## Completion Criteria

- `packages/memory/README.md` states what memory owns and what it does not own.
- `packages/planning/README.md` states what planning owns and what it does not own.
- The package docs align with the root boundary charter and selective-adoption stance.
- The roadmap no longer carries a separate open boundary-charter hardening candidate.

## Drift Log

- 2026-04-05: Plan activated after the lifecycle-orchestrator tranche cleared, using the already-committed root boundary charter as the source of truth for package-level follow-through.
- 2026-04-05: Milestone complete: package READMEs now restate ownership and anti-blur rules locally, so boundary guidance is visible at the package entrypoints instead of only at the root.