# Review Portfolio

## Goal

- Define the first canonical review portfolio and playbook so agents run bounded named review modes with clear inputs, output caps, and promotion targets instead of generic open-ended critique.

## Non-Goals

- Build review automation or a new checker.
- Expand into a scoring system or review scheduler.
- Blur the boundary between review capture, roadmap promotion, and active execution.

## Active Milestone

- Status: completed
- Scope: add the canonical review matrix to the shipped review docs, thread the contract through the review template and planning package docs, and lock it with payload assertions.
- Ready: ready
- Blocked: none
- optional_deps: none

## Immediate Next Action

- None. Milestone completed and archived after the review matrix, template contract, package docs, payload assertions, and payload checker regression fix all landed.

## Blockers

- None.

## Touched Paths

- `.agentic-workspace/planning/reviews/`
- `packages/planning/`
- `TODO.md`
- `ROADMAP.md`

## Invariants

- Review artifacts remain bounded capture, not active execution plans.
- Review modes must stay small enough to run intentionally instead of becoming a generic “find improvements” pass.
- Promotion from review capture remains a separate explicit decision.

## Validation Commands

- `uv run pytest packages/planning/tests/test_installer.py`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The shipped review docs define a small canonical review portfolio with purpose, inputs, findings, likely promotion targets, and default output caps.
- The review template requires the mode, questions, and cap for each review artifact.
- The planning package docs and payload assertions reflect the same review-portfolio contract.

## Drift Log

- 2026-04-08: Promoted from GitHub issue `#6` after the repo had review capture and promotion thresholds but still lacked the canonical bounded review portfolio itself.
- 2026-04-08: Completed after shipping the canonical review matrix/playbook, threading mode and cap requirements into the template, and restoring the dropped docs-surface role audit in the planning payload checker.
