# Config-Driven Execution Posture Follow-Through

## Goal

- Close roadmap lane `config-driven-execution-posture-follow-through` by making user-defined config posture authoritative as the default execution shape, while keeping deviations possible, visible, and justified instead of silent.

## Non-Goals

- Turn config into a scheduler.
- Add vendor-specific routing or target-specific hard policy.
- Require Memory just to restate what config already says.
- Force delegation for trivial or obviously direct work.

## Intent Continuity

- Larger intended outcome: the workspace should make configured mixed-agent posture visible enough at the moment of execution shaping that agents naturally follow it as the default when the task shape fits, and record deviations as exceptions rather than letting them disappear silently.
- This slice completes the larger intended outcome: yes
- Continuation surface: none
- Parent lane: config-driven-execution-posture-follow-through

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Iterative Follow-Through

- What this slice enabled: one combined execution-shaping answer now joins active planning state with effective local posture in the shared workspace report.
- Intentionally deferred: none
- Discovered implications: the shared workspace report is the right owner surface for this answer because it can combine config-backed posture with active planning without teaching planning to parse workspace-local policy.
- Proof achieved now: `agentic-workspace report --target ./repo --format json` now exposes `execution_shape` with an explicit default recommendation and deviation visibility rule.
- Validation still needed: none
- Next likely slice: none

## Delegated Judgment

- Requested outcome: promote the product gap behind issue `#179` into a bounded active lane with a clear owner surface and first implementation target.
- Hard constraints: keep the result advisory, config-driven, and agent-agnostic; treat user-defined config as the authoritative default posture; allow deviations only as local judgment rather than silent disregard; do not add scheduler logic; do not use Memory to compensate for a weak package surface unless the package contract proves insufficient.
- Agent may decide locally: the exact owner surface, whether the compact answer belongs in defaults, planning summary, handoff, or another existing contract, and the smallest implementation slice that would prove the change.
- Escalate when: the lane appears to require multiple competing owner surfaces, new persistent state, or vendor-specific routing logic.

## Active Milestone

- ID: execution-posture-contract-shaping
- Status: completed
- Scope: identify the compact execution-shaping answer, the owner surface that should carry it, how config-backed default posture should be expressed, and the first bounded implementation slice for `#179`.
- Ready: ready
- Blocked: none
- optional_deps: none

## Upcoming Milestones

- None.

## Immediate Next Action

- None; slice complete.

## Blockers

- None.

## Touched Paths

- TODO.md
- ROADMAP.md
- docs/default-path-contract.md
- .agentic-workspace/docs/reporting-contract.md
- src/agentic_workspace/cli.py
- src/agentic_workspace/contracts/report_contract.json
- src/agentic_workspace/workspace_output.py
- tests/test_workspace_cli.py

## Invariants

- Config remains posture, not scheduler control.
- The new answer must be decision-time guidance, not a second broad workflow script.
- The package surface should become strong enough that Memory is optional rather than required for this behavior.
- User-defined config should remain authoritative as the declared default posture even when local judgment may still justify a different choice in a specific case.

## Contract Decisions To Freeze

- The authoritative compact execution-shaping answer lives in `agentic-workspace report --target ./repo --format json` as `execution_shape`.
- The minimum answer shape combines effective posture, current task shape, one default recommendation, and an explicit deviation-visibility rule.
- The answer remains advisory and agent-agnostic.
- Deviations stay possible, but the report now makes clear that a broad-slice exception should be explained in checked-in planning residue rather than left implicit.

## Open Questions To Close

- None.

## Validation Commands

- uv run pytest tests/test_workspace_cli.py -q
- uv run python scripts/check/check_planning_surfaces.py
- uv run agentic-workspace report --target . --format json

## Required Tools

- uv
- gh

## Completion Criteria

- The active lane identifies one owner surface for the compact execution-shaping answer.
- The lane makes explicit that user-defined config is the authoritative default posture and that deviations must be visible rather than silent.
- The first bounded implementation slice is defined clearly enough to execute without relying on chat residue.
- Planning surfaces validate cleanly and the lane is ready for implementation.

## Execution Summary

- Outcome delivered: `agentic-workspace report --target ./repo --format json` now exposes a compact `execution_shape` answer that combines active planning state with effective config posture, and the report text surfaces the same default recommendation tersely for human inspection.
- Validation confirmed: `uv run pytest tests/test_workspace_cli.py -q`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run agentic-workspace report --target . --format json`.
- Follow-on routed to: lane retired from `TODO.md` and `ROADMAP.md`; GitHub issue `#179` closed.
- Resume from: the next roadmap lane, `memory-trust-habitual-pull`, when active queue capacity opens again.

## Drift Log

- 2026-04-18: Promoted issue `#179` immediately after direct dogfooding showed that configured delegation posture was still too easy to bypass at execution-shaping time.
- 2026-04-18: Completed by adding the combined `execution_shape` report surface, documenting it as the default current-slice owner, and retiring the lane.
