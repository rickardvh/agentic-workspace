# Repository Stewardship Rule

## Goal

- Add a durable stewardship rule that keeps the repository in a better state after task execution, with bounded cleanup, adjacent improvements, and explicit follow-up for broader work.

## Non-Goals

- Turn routine task completion into a large refactor mandate.
- Expand scope silently beyond the touched surfaces.
- Replace the existing design principles or maintainer playbook.

## Deliverables

- A short canonical stewardship rule that says tasks should leave the repository cleaner than they found it within scope.
- Integration into the design-principles and maintainer-facing guidance surfaces.
- A clear distinction between in-scope cleanup and follow-up improvements.
- A repeatable signal for recurring cleanup friction so it can become roadmap input instead of invisible toil.

## Canonical Inputs

- docs/design-principles.md
- AGENTS.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- docs/installed-contract-design-checklist.md
- docs/dogfooding-feedback.md

## Active Milestone

- Status: planned
- Scope: define the stewardship rule and place it in the repo’s durable guidance surfaces without turning it into a broad cleanup policy.
- Ready: not-started
- Blocked: none
- optional_deps: none

Keep one active milestone by default.

## Immediate Next Action

- Wait for the current active tranche to settle, then promote this rule alongside the maintainer guidance updates it needs.

## Blockers

- None.

## Invariants

- Cleanup stays bounded to the touched surfaces and should not expand scope silently.
- Broader improvements must be recorded as follow-up instead of absorbed without a trace.
- The stewardship rule must stay short enough to remain usable during task completion.

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Drift Log

- 2026-04-06: Parked from the planning-spec intake to keep the repo stewardship rule queued behind the active registry work.

## Touched Paths

- docs/design-principles.md
- AGENTS.md
- docs/contributor-playbook.md
- docs/maintainer-commands.md
- docs/dogfooding-feedback.md

Keep this as a scope guard, not a broad file inventory.

## Validation

- Check that the rule is short, actionable, and adjacent to existing stewardship guidance.
- Verify the repo still distinguishes task-local cleanup from follow-up planning.
- Confirm the guidance does not create a second maintenance doctrine.

## Completion Criteria

- Maintainers can tell what cleanup is expected at the end of a task.
- Broader improvements are captured as follow-up instead of being silently absorbed.
- Repeated cleanup burden becomes an explicit improvement signal.

## Follow-On Work Not Pulled In

- Automation for cleanup suggestions.
- Repo-wide residue sweeps.
- Scope-expanding maintenance checklists.
