# Orchestrator Workflow Evidence

## Goal

- Capture what the lane-scale planner-to-worker trial actually cost and saved so the repo can draft a cheaper reusable workflow for this mode.

## Scope

- `docs/execplans/planning-surface-clarity-lane-2026-04-17.md`
- `docs/reviews/planning-recovery-ambiguity-audit-2026-04-17.md`
- worker task for issue `#162`
- worker task for issue `#164`
- local orchestration, validation, cleanup, and closure work done around those slices

## Summary

- Result: lane-scale orchestration was worthwhile here.
- Why: the strong planner paid the shaping cost once, then the same smaller worker completed two bounded slices cleanly from checked-in planning.
- Limit: the remaining overhead is no longer mostly slice planning; it is closure, reread duplication, and the lack of a dedicated delegated handoff artifact.

## Evidence

### Savings observed

- The execplan was useful anyway.
  The lane needed checked-in planning regardless of delegation, so the plan was not delegation-only overhead.
- Reusing the same worker reduced handoff setup on the second slice.
  The second delegated task reused the same worker, the same lane contract, and the same minimal reference pattern instead of paying full setup again.
- The worker stayed bounded with a small owned write set.
  The audit touched only a review artifact; the implementation touched only the targeted docs and bootstrap mirror.
- The compact planning summary carried the active contract cheaply.
  `agentic-planning-bootstrap summary --format json` was enough to re-establish active state, next action, proof expectations, and lane ownership without rereading broad planning prose.

### Overhead observed

- The worker handoff was still authored manually.
  The orchestrator still had to restate the bounded task, owned write scope, constraints, and validation lane instead of deriving them directly from checked-in planning.
- Closure work stayed mostly orchestrator-owned.
  The worker implemented and validated the slice, but archive, roadmap cleanup, issue routing, and final integration still lived with the orchestrator.
- Duplicated reading still existed.
  Both orchestrator and worker read some of the same contract docs because the lane had no dedicated delegated handoff artifact beyond the execplan plus prompt.

## Practical Conclusions

- One-off delegated slices are only modestly cheaper.
- Lane-scale delegated execution becomes meaningfully better when:
  - the lane is shaped once by a stronger planner
  - the same worker is reused across multiple bounded slices
  - the worker contract stays stable
  - checked-in planning carries the handoff backbone
- The next optimization target is not more planning hierarchy.
  It is making the planner-to-worker handoff cheaper and pushing safe closure work down when the contract is explicit enough.

## Recommended Workflow Shape

- Strong planner shapes the lane, execplan, and slice boundaries once.
- Worker handoff should be derived from checked-in planning state, not written ad hoc.
- Worker should own implementation, narrow validation, and cleanup or commit when the contract stays within a bounded write scope.
- Orchestrator should retain lane shaping, roadmap or issue decisions, and escalation-only work.
- Delegated handoff should carry explicit minimal refs so the worker does not need broad rereads.

## Promotion Target

- Promote the workflow follow-through as GitHub issue `#171`.

## Validation / Inspection Commands

- `uv run python scripts/check/check_planning_surfaces.py`
- `uv run pytest packages/planning/tests/test_check_planning_surfaces.py -q`
- `uv run agentic-planning-bootstrap summary --format json`

## Drift Log

- 2026-04-17: Recorded evidence from the `planning-surface-clarity-lane` orchestrator-to-worker trial.
