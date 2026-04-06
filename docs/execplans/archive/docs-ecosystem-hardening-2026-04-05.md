# Docs Ecosystem Hardening

## Goal

- Tighten external and maintainer-facing documentation for the current memory/planning/workspace ecosystem while adding cheap liveness checks for the repeated startup and generated-routing contracts.

## Non-Goals

- Extract new standalone packages.
- Redesign package CLI behavior beyond documentation and liveness-check support.
- Replace the current planning or memory product contracts.

## Active Milestone

- Status: completed
- Scope: implemented the documentation tranche for naming clarification, chooser guidance, canonical policy docs, generated-doc markings, compatibility framing, maturity guidance, and maintainer-surface liveness checks.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Promote installed-contract collaboration safety, with emphasis on merge-safe adopter behavior and a more compact cross-module interaction model.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- README.md
- Makefile
- AGENTS.md
- docs/*.md
- scripts/check/
- tools/*.md
- .agentic-workspace/planning/scripts/check/
- .agentic-workspace/planning/scripts/render_agent_docs.py
- .agentic-workspace/planning/agent-manifest.json
- packages/memory/
- packages/planning/

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Root README should stay primarily an external entrypoint rather than the full maintainer manual.
- Workspace-layer guidance must continue to treat the root CLI as thin and keep module-specific behavior in package CLIs by default.
- Generated routing docs under tools/ remain derived surfaces, not hand-edited sources of truth.
- Planning and memory must remain selectively adoptable.

Keep invariants contract-shaped and brief.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py
- uv run python scripts/render_agent_docs.py
- uv run pre-commit run --all-files

## Completion Criteria

- Root README points external adopters quickly to memory, planning, or both with less maintainer/policy load.
- Canonical policy docs exist for boundaries, principles, ecosystem roadmap, collaboration safety, and maintainer commands.
- Package docs and maintainer docs reflect the clarified naming, maturity, partial-adoption, and package-workspace boundaries.
- Generated routing docs are visibly marked as generated and validated against their manifest source.
- Startup-path and generated-doc drift checks exist and pass.

## Drift Log

- 2026-04-05: Initial plan created for the documentation and liveness hardening tranche.
- 2026-04-06: Extended the tranche with a repo-maintainer `make maintainer-surfaces` path, an explicit integration contract, and dogfooding-feedback capture guidance.
- 2026-04-06: Archived after the docs ecosystem work landed and the next pressure shifted to installed-contract collaboration safety.
