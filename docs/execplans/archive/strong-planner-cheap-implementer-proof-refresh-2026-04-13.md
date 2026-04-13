# Strong-Planner Cheap-Implementer Proof Refresh

## Goal

- Reassess the strong-planner / cheap-implementer evidence after the first mixed-agent dogfood pass and the ordinary-use synergy proof.
- Decide whether the separate backlog lane is now satisfied, or whether a narrower unresolved remainder still needs to stay active.

## Non-Goals

- Build runtime model switching or agent routing.
- Reopen the mixed-agent contract boundary that already landed.
- Treat cross-agent continuity or selective adoption as part of this slice.

## Intent Continuity

- Larger intended outcome: the repo should have enough checked-in evidence that a stronger planner can shape a bounded contract and a cheaper implementer can execute it with minimal rereading and explicit escalation boundaries.
- This slice completes the larger intended outcome: yes
- Continuation surface: none

## Required Continuation

- Required follow-on for the larger intended outcome: no
- Owner surface: none
- Activation trigger: none

## Delegated Judgment

- Requested outcome: review the current checked-in proof set, verify whether it now establishes the intended strong-planner / cheap-implementer behavior strongly enough, and leave only the smallest justified follow-on.
- Hard constraints: use checked-in evidence, not chat memory; keep the slice bounded to proof evaluation plus any narrow roadmap/issue cleanup it justifies.
- Agent may decide locally: the exact proof threshold for retiring the lane, whether a review artifact is needed, and how much of the issue scope remains after the refresh.
- Escalate when: the evidence is too mixed to judge without running another real task first.

## Active Milestone

- Status: completed
- Scope: reassess the current proof set and either retire the roadmap lane or leave a smaller explicitly defined remainder.
- Ready: completed
- Blocked: none
- optional_deps: GitHub issue `#25`

## Immediate Next Action

- Promote `Cross-agent handoff quality audit` from the highest-priority queue.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/archive/strong-planner-cheap-implementer-proof-refresh-2026-04-13.md`

## Invariants

- Checked-in surfaces, not runtime scheduling, remain the product boundary.
- Any remaining follow-on should stay narrower than the original broad backlog wording.
- This slice should reduce queue ambiguity, not create another shadow proof program.

## Open Questions Closed

- Proof-threshold question: yes. The archived generated-surface trust pass and the archived ordinary-use synergy proof together now show that checked-in surfaces can shape bounded work, select the narrow validation lane, and carry the implementer without broad rereading.
- Remainder question: the unresolved remainder is now the narrower cross-agent continuity problem, which is already covered by `Cross-agent handoff quality audit` rather than this broader standalone lane.

## Validation Commands

- `uv run agentic-workspace config --target . --format json`
- `uv run agentic-workspace defaults --format json`
- `uv run python scripts/check/check_planning_surfaces.py`

## Completion Criteria

- The strong-planner / cheap-implementer roadmap lane is either retired or narrowed with a clearer remainder.
- The issue tracker comment trail reflects the updated proof state.
- The slice archives with a compact statement of what the repo has now proved.

## Execution Summary

- Outcome delivered: yes. The standalone roadmap lane was retired.
- Validation confirmed: yes. The live mixed-agent contract surfaces still match the archived proof assumptions, and planning-surface validation passed.
- Follow-on routed to: none.
- Resume from: promote the cross-agent handoff audit.

## Proof Outcome

- What is now proved:
- `agentic-workspace config --format json` and `agentic-workspace defaults --format json` are sufficient planner-facing contract surfaces for bounded mixed-agent work in this repo.
- One bounded generated-surface trust task and one ordinary package-fix task both completed through those checked-in surfaces with low rereading and narrow validation.
- The current product gap is no longer basic bounded strong-planner / cheap-implementer viability.

- What is not covered here:
- This slice does not establish cheap continuity across different agents or contributors; that remains a separate handoff-quality problem.

## Drift Log

- 2026-04-13: Promoted after the ordinary-use synergy proof landed and the next need was to reassess whether the separate strong-planner / cheap-implementer backlog lane still represented a real unresolved gap.
- 2026-04-13: Completed after the archived proof set showed the standalone lane was satisfied and its remaining ambiguity belonged under cross-agent handoff quality instead.
