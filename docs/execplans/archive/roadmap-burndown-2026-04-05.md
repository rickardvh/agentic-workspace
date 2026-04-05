# Roadmap Burndown

## Goal

- Implement or retire the remaining roadmap candidate epics so the repository returns to an empty active/candidate planning state.

## Non-Goals

- Redesign the planning contract beyond the concrete dogfooding improvements discovered while burning down the queue.
- Add speculative features that are not already represented in the checked-in planning surfaces.
- Turn roadmap cleanup into a generic backlog system.

## Active Milestone

- Status: completed
- Scope: burn down the remaining roadmap candidate queue, package the stable optional planning skill, and return the repo to an empty active-planning state.
- Ready: false
- Blocked: n/a
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and leave the active planning surfaces empty.

## Blockers

- None.

## Touched Paths

- `src/repo_planning_bootstrap/`
- `tests/`
- `README.md`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- New lifecycle commands must remain conservative and file-native.
- `adopt` stays safe for existing repositories.
- Planning surfaces should only be updated to reflect real implemented state.
- Dogfooding follow-ons should be captured compactly and retired as soon as they are implemented or ruled out.

## Validation Commands

- `uv run pytest`
- `uv run ruff check .`
- `uv run agentic-planning-bootstrap status --target .`
- `uv run agentic-planning-bootstrap doctor --target .`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The current roadmap candidate queue is either implemented or explicitly retired.
- `TODO.md` and active execplans are empty again after the work closes.
- Dogfooding follow-ons discovered during execution are either implemented in the same thread or consciously pruned from the planning surfaces.

## Drift Log

- 2026-04-05: Plan created to burn down the remaining roadmap candidate queue after the payload-hygiene thread closed.
- 2026-04-05: Added conservative `upgrade` and safe `uninstall` lifecycle commands, then tightened the lifecycle boundary so repo-owned files like `tools/agent-manifest.json` are preserved during upgrade dogfooding.
- 2026-04-05: Tightened `archive-plan --apply-cleanup` so removing the last TODO item restores a valid empty-state marker instead of leaving a blank `## Next` section behind.
- 2026-04-05: Added a second generated agent surface (`tools/AGENT_ROUTING.md`), updated the render/install/verify pipeline to keep generated docs in sync, and packaged a repo-specific `planning-surface-change` skill after the workflow proved stable in repeated dogfooding.
