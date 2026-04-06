# Repository Stewardship Rule

## Goal

- Add a durable stewardship rule that keeps the repository in a better state after task execution, with bounded cleanup, adjacent improvements, and explicit follow-up for broader work.

## Non-Goals

- Turn routine task completion into a large refactor mandate.
- Expand scope silently beyond the touched surfaces.
- Replace the existing design principles or maintainer playbook.

## Active Milestone

- Status: completed
- Scope: define the stewardship rule and place it in the repo’s durable guidance surfaces without turning it into a broad cleanup policy.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Archive this completed plan and move the init-lifecycle milestone into active execution.

## Blockers

- None.

## Touched Paths

- docs/design-principles.md
- AGENTS.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- docs/dogfooding-feedback.md

Keep this as a scope guard, not a broad file inventory.

## Invariants

- Cleanup stays bounded to the touched surfaces and should not expand scope silently.
- Broader improvements must be recorded as follow-up instead of absorbed without a trace.
- The stewardship rule must stay short enough to remain usable during task completion.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake to keep the repo stewardship rule queued behind the active registry work.
- 2026-04-06: Milestone complete: the repo now says to leave touched surfaces cleaner than you found them and routes repeated cleanup burden through a specific stewardship-friction signal.

## Completion Criteria

- Maintainers can tell what cleanup is expected at the end of a task.
- Broader improvements are captured as follow-up instead of being silently absorbed.
- Repeated cleanup burden becomes an explicit improvement signal.

## Follow-On Work Not Pulled In

- Automation for cleanup suggestions.
- Repo-wide residue sweeps.
- Scope-expanding maintenance checklists.