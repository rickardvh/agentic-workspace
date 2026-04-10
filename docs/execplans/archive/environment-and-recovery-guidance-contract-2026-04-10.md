# Environment And Recovery Guidance Contract

## Goal

- Ship one compact environment and recovery contract so agents can recover from repo-state ambiguity, lifecycle warnings, or interrupted bootstrap/maintenance work without rediscovering the right surfaces each time.

## Non-Goals

- Build a broad troubleshooting manual.
- Rework module-specific install logic in this slice.
- Turn planning into a general incident-response system.

## Intent Continuity

- Larger intended outcome: Make restart and recovery cheaper across the workspace and planning front door.
- This slice completes the larger intended outcome: no
- Continuation surface: `ROADMAP.md` candidate `Long-horizon doctrine refresh discipline`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `ROADMAP.md`
- Activation trigger: The recovery contract lands and the remaining long-horizon work shifts to doctrine maintenance and extension-boundary reality checks.

## Active Milestone

- Status: completed
- Scope: define the canonical recovery contract, expose it in workspace defaults, align key planning/workspace docs, and validate the shipped planning/workspace surfaces.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Add the canonical recovery contract doc, wire it into `agentic-workspace defaults`, and update the planning/workspace docs that currently imply the same flow indirectly.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/`
- `src/agentic_workspace/cli.py`
- `tests/test_workspace_cli.py`
- `packages/planning/`

## Invariants

- Keep recovery guidance compact and ordered.
- Prefer one canonical recovery path over scattered prose hints.
- Do not duplicate memory ownership or package-specific domain logic in the workspace layer.

## Contract Decisions To Freeze

- `docs/environment-recovery-contract.md` is the canonical ordered recovery path for workspace and planning surfaces.
- `agentic-workspace defaults --format json` must expose the same recovery contract in machine-readable form.
- Recovery guidance should stay front-door and cross-surface; package-specific troubleshooting still belongs in package-owned docs.

## Open Questions To Close

- No blocking open questions remain for this slice.

## Validation Commands

- `uv run pytest tests/test_workspace_cli.py`
- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap upgrade --target .`

## Completion Criteria

- One canonical doc defines the recovery path for workspace/planning surfaces.
- `agentic-workspace defaults --format json` exposes the same recovery contract in machine-readable form.
- Planning/workspace docs reference the same recovery path instead of carrying divergent hints.
- The planning payload and root install stay aligned.

## Execution Summary

- Outcome delivered: One canonical recovery contract was added, wired into workspace defaults, and referenced from the planning/workspace front-door docs.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py`; `uv run pytest packages/planning/tests/test_installer.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-planning-bootstrap upgrade --target .`; `uv run agentic-memory-bootstrap upgrade --target .`
- Follow-on routed to: `ROADMAP.md` candidate `Long-horizon doctrine refresh discipline`
- Resume from: promote `Long-horizon doctrine refresh discipline` after archiving this slice

## Drift Log

- 2026-04-10: Plan created from the roadmap candidate after the planning beta-readiness review left recovery guidance as the clearest remaining non-summary maturity gap.
