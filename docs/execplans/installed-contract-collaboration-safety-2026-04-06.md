# Installed-Contract Collaboration Safety

## Goal

- Make installed Agentic Memory and Agentic Planning contracts safer and clearer for multi-branch, multi-agent repositories by tightening the interaction model, package framing, and liveness coverage around collaboration-sensitive surfaces.

## Non-Goals

- Introduce a new top-level package or orchestration layer.
- Rework module ownership boundaries that are already explicit and stable.
- Turn planning or memory into a broad project-management or documentation platform.

## Active Milestone

- Status: in-progress
- Scope: finish the installed-contract collaboration tranche by hardening merge-safe installed templates and checks, broadening maintainer liveness coverage, and then validating and archiving the tranche.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Run the broadened maintainer lane and package regression coverage.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/
- packages/memory/
- packages/planning/
- scripts/check/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Memory and planning must remain selectively adoptable.
- The workspace layer must stay thin and orchestration-only.
- Installed contracts should become more merge-friendly under concurrent branch work, not more stateful or harder to reason about.
- Package READMEs should present product capability first and installer mechanics second.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- make maintainer-surfaces
- uv run pytest packages/memory/tests packages/planning/tests

## Completion Criteria

- One compact integration contract states how Memory, Planning, generated routing docs, and checks are expected to interact in adopter repos.
- Installed templates and collaboration-oriented checks explicitly prefer merge-safe shapes for multi-branch, multi-agent work.
- Liveness coverage is stronger for generated or semi-authoritative surfaces that can silently drift.
- Package README framing presents each package primarily as a product capability, not merely a CLI.

## Drift Log

- 2026-04-06: Promoted from maintainer feedback after the docs ecosystem tranche established clearer external entrypoints, architecture, and package boundaries.
- 2026-04-06: Tightened the integration contract into a more compact interaction model and reframed the memory docs around product capability first, installer second.
- 2026-04-06: Added collaboration-safe payload guidance checks for shipped planning and memory templates and broadened the maintainer lane to verify both package contracts.
