# Contributor Onboarding

## Goal

- Add package ownership metadata and a contributor playbook so new work can route to the right package and validation lane with less rediscovery.

## Non-Goals

- Define a full maintainer process beyond the current package boundaries.
- Add automation around reviewer assignment in this tranche.
- Rewrite package READMEs or AGENTS contracts beyond what is needed for onboarding references.

## Active Milestone

- Status: completed
- Scope: add a root `CODEOWNERS` file and a concise contributor playbook aligned with the current package and orchestration boundaries.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and remove the finished contributor-onboarding candidate from the roadmap queue.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- .agentic-workspace/planning/execplans/
- docs/
- .github/
- README.md

## Invariants

- Ownership metadata must match the current package and workspace boundaries.
- The playbook should route contributors toward the smallest relevant validation lane.
- The onboarding guidance should reinforce the current architecture stance instead of implying more packages than the repo actually ships.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Completion Criteria

- A root `CODEOWNERS` file exists with package-aware ownership boundaries.
- A contributor playbook exists with startup, routing, and validation guidance for this monorepo.
- The roadmap no longer carries a separate open contributor-onboarding candidate.

## Drift Log

- 2026-04-05: Plan activated once package boundaries and the root lifecycle entrypoint were stable enough to freeze contributor guidance without guessing ownership.
- 2026-04-05: Milestone complete: the repo now has package-aware CODEOWNERS metadata and a contributor playbook that routes contributors to the right package and validation lane.