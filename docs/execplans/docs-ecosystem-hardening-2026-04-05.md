# Docs Ecosystem Hardening

## Goal

- Tighten external and maintainer-facing documentation for the current memory/planning/workspace ecosystem while adding cheap liveness checks for the repeated startup and generated-routing contracts.

## Non-Goals

- Extract new standalone packages.
- Redesign package CLI behavior beyond documentation and liveness-check support.
- Replace the current planning or memory product contracts.

## Active Milestone

- Status: in-progress
- Scope: implement the current roadmap documentation tranche, including naming clarification, chooser guidance, canonical policy docs, generated-doc markings, compatibility/maturity guidance, and maintainership liveness checks.
- Ready: ready
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Validate the updated startup-path and generated-doc drift checks.

Keep exactly one immediate action by default; avoid multi-step mini-plans here.

## Blockers

- None.

## Touched Paths

- README.md
- AGENTS.md
- docs/contributor-playbook.md
- docs/*.md
- tools/*.md
- .agentic-workspace/planning/scripts/check/check_planning_surfaces.py
- .agentic-workspace/planning/scripts/render_agent_docs.py
- .agentic-workspace/planning/agent-manifest.json
- packages/memory/README.md
- packages/planning/README.md
- packages/memory/AGENTS.md
- packages/planning/AGENTS.md

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