# Maintenance Rule For Measured Friction

## Goal

- Close GitHub issue `#88` by adding one compact rule that new planning work should come from measured friction, repeated failure, repeated dogfooding pain, or an explicit maintainer override rather than concept opportunity alone.

## Non-Goals

- Do not turn planning into a heavy approval workflow.
- Do not block strategic maintainer overrides.
- Do not widen this slice into the measurement tranche from `#87`.

## Intent Continuity

- Larger intended outcome: close the remaining GitHub planning-refinement queue and empty the roadmap while keeping backlog quality higher than concept churn.
- This slice completes the larger intended outcome: no
- Continuation surface: ROADMAP.md

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: ROADMAP.md
- Activation trigger: when the maintenance rule lands and the lazy-discovery measurement tranche for `#87` is ready to use that rule

## Delegated Judgment

- Requested outcome: add one explicit maintenance rule to the relevant planning/design/review surfaces and apply it immediately to the remaining queue so speculative work stops entering planning without a real trigger.
- Hard constraints: keep the rule short and operational, preserve maintainer override as an explicit escape hatch, and avoid turning the rule into abstract anti-innovation doctrine.
- Agent may decide locally: the exact wording, which surfaces need the rule most, and which immediate planning pass best demonstrates that the rule is now active.
- Escalate when: the smallest safe implementation would require a new process layer, a heavier approval gate, or a broader redesign of planning promotion beyond the stated rule.

## Active Milestone

- Status: completed
- Scope: added the maintenance rule to design, review, and upstream-intake surfaces, then applied it to the remaining queue so the repo ends with only the measurement tranche as follow-on work.
- Ready: complete
- Blocked: none
- optional_deps: none

## Immediate Next Action

- Promote the measurement tranche from `ROADMAP.md`.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/design-principles.md
- .agentic-workspace/planning/reviews/README.md
- .agentic-workspace/planning/skills/planning-promote-review-findings/SKILL.md
- .agentic-workspace/planning/upstream-task-intake.md

## Invariants

- New planning work still may enter through explicit maintainer override when strategically necessary.
- The rule stays cheap and operational rather than becoming a review bureaucracy.
- Measured friction, repeated failure, repeated dogfooding pain, or explicit maintainer override are the only acceptable default triggers.

## Contract Decisions To Freeze

- The maintenance rule belongs in existing planning/design/review surfaces rather than a new policy file.
- The rule should govern review promotion and upstream intake directly, not just long-form design doctrine.
- The remaining queue should be pruned under the new rule immediately instead of waiting for a later housekeeping pass.

## Open Questions To Close

- Which wording best distinguishes measured friction from generic opportunity without implying that all new capability work is banned?
- What is the smallest immediate application of the rule to the remaining queue?

## Validation Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run agentic-planning-bootstrap summary --format json`

## Completion Criteria

- GitHub issue `#88` is closed.
- The maintenance rule is explicit in the relevant design/review/intake surfaces.
- The remaining queue has been filtered or reaffirmed under the new rule immediately.
- The repo is ready to promote only the measurement tranche from `#87`.

## Execution Summary

- Outcome delivered: the design principles, review-promotion contract, review-promotion skill, upstream-intake contract, and roadmap promotion rules now all require measured friction, repeated failure, repeated dogfooding pain, or explicit maintainer override before new work should enter planning by default.
- Validation confirmed: `uv run python scripts/check/check_planning_surfaces.py`, `uv run agentic-planning-bootstrap summary --format json`
- Follow-on routed to: ROADMAP.md
- Resume from: promote the lazy-discovery measurement tranche for `#87`, then empty the roadmap when that evidence pass is archived

## Drift Log

- 2026-04-15: Promoted GitHub issue `#88` after the compact operating map landed so the repo could apply the rule immediately to the remaining queue instead of adding another speculative candidate.
- 2026-04-15: Closed `#88` after encoding the rule in design, review, and intake surfaces and using it immediately to leave only the measurement tranche in `ROADMAP.md`.
