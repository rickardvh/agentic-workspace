# Config-Driven Execution Posture Follow-Through

## Goal

- Close roadmap lane `config-driven-execution-posture-follow-through` by making the effective config-driven delegation posture more decisive at execution-shaping time so broad work stops bypassing the already-configured strong-planner / cheap-executor posture casually.

## Non-Goals

- Turn config into a scheduler.
- Add vendor-specific routing or target-specific hard policy.
- Require Memory just to restate what config already says.
- Force delegation for trivial or obviously direct work.

## Intent Continuity

- Larger intended outcome: the workspace should make configured mixed-agent posture visible enough at the moment of execution shaping that agents naturally follow it when the task shape fits, instead of repeatedly defaulting to direct execution.
- This slice completes the larger intended outcome: no
- Continuation surface: `TODO.md`
- Parent lane: config-driven-execution-posture-follow-through

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `TODO.md`
- Activation trigger: after the contract for default execution-shaping guidance is frozen and ready for implementation

## Iterative Follow-Through

- What this slice should enable: a bounded implementation pass can add the right decision-time surface without re-litigating whether the gap is product-side or Memory-side.
- Intentionally deferred: the implementation itself, any new runtime heuristics, and any Memory follow-on unless the contract still proves insufficient.
- Discovered implications: this lane should first answer where the recommendation belongs and what it should say, because the recent misses indicate a surfacing problem more than a missing capability.
- Proof still needed: checked-in planning should name the owner surface, the compact answer shape, and the boundary against scheduler behavior.
- Validation still needed: planning-surface checks after promotion; implementation validation will belong to the next slice.
- Next likely slice: implement the chosen compact execution-shaping answer in the existing recovery/planning contract and dogfood it on a real lane.

## Delegated Judgment

- Requested outcome: promote the product gap behind issue `#179` into a bounded active lane with a clear owner surface and first implementation target.
- Hard constraints: keep the result advisory, config-driven, and agent-agnostic; do not add scheduler logic; do not use Memory to compensate for a weak package surface unless the package contract proves insufficient.
- Agent may decide locally: the exact owner surface, whether the compact answer belongs in defaults, planning summary, handoff, or another existing contract, and the smallest implementation slice that would prove the change.
- Escalate when: the lane appears to require multiple competing owner surfaces, new persistent state, or vendor-specific routing logic.

## Active Milestone

- ID: execution-posture-contract-shaping
- Status: in-progress
- Scope: identify the compact execution-shaping answer, the owner surface that should carry it, and the first bounded implementation slice for `#179`.
- Ready: ready
- Blocked: none
- optional_deps: none

## Upcoming Milestones

- None.

## Immediate Next Action

- Inspect the existing delegation-posture, default-path, and planning-summary/handoff surfaces, then freeze where the default execution-shaping recommendation should live and what it should contain.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/execplans/config-driven-execution-posture-follow-through-2026-04-18.md

## Invariants

- Config remains posture, not scheduler control.
- The new answer must be decision-time guidance, not a second broad workflow script.
- The package surface should become strong enough that Memory is optional rather than required for this behavior.

## Contract Decisions To Freeze

- Which existing owner surface should carry the default execution-shaping answer.
- What the minimum answer shape is.
- How the answer stays advisory and agent-agnostic.

## Open Questions To Close

- Should the recommended execution shape live in `agentic-workspace defaults --section delegation_posture`, planning summary, handoff, or another existing compact surface?
- What task-shape threshold should trigger the answer to matter?
- What is the smallest implementation slice that will prove the recommendation becomes harder to bypass in ordinary work?

## Validation Commands

- uv run python scripts/check/check_planning_surfaces.py

## Required Tools

- uv
- gh

## Completion Criteria

- The active lane identifies one owner surface for the compact execution-shaping answer.
- The first bounded implementation slice is defined clearly enough to execute without relying on chat residue.
- Planning surfaces validate cleanly and the lane is ready for implementation.

## Execution Summary

- Outcome delivered: pending.
- Validation confirmed: pending.
- Follow-on routed to: pending.
- Resume from: the active milestone in this execplan.

## Drift Log

- 2026-04-18: Promoted issue `#179` immediately after direct dogfooding showed that configured delegation posture was still too easy to bypass at execution-shaping time.
