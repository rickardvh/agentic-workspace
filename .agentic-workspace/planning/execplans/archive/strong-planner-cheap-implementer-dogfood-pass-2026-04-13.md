# Strong-Planner Cheap-Implementer Dogfood Pass

## Goal

- Prove the new mixed-agent reporting and validation-default surfaces against one real bounded repo task instead of only describing the workflow in doctrine.
- Capture whether a stronger planner can shape a compact checked-in contract that a cheaper implementer could follow with minimal rereading and explicit escalation boundaries.

## Non-Goals

- Build runtime model switching or automatic delegation.
- Claim broad mixed-agent proof from a single pass.
- Open a large proof program or multiple concurrent dogfood slices.
- Turn this into a generic review artifact without a concrete task outcome.

## Intent Continuity

- Larger intended outcome: demonstrate that Agentic Workspace can materially reduce token cost and restart burden by carrying enough checked-in context for strong-planner / cheap-implementer collaboration on real work.
- This slice completes the larger intended outcome: no
- Continuation surface: `TODO.md`

## Required Continuation

- Required follow-on for the larger intended outcome: yes
- Owner surface: `TODO.md`
- Activation trigger: another real mixed-agent proof slice is ready or repeated ordinary work exposes restart or handoff ambiguity that still needs tightening.

## Delegated Judgment

- Requested outcome: use the new mixed-agent surfaces on one real task, finish that task, and record whether the handoff state was sufficient or still too ambiguous.
- Hard constraints: keep the task bounded; use the shipped reporting/default surfaces directly; prefer a real repo task over a fake toy example; capture the proof result in checked-in planning or review state rather than chat residue.
- Agent may decide locally: which bounded task best fits the proof pass, the exact local mixed-agent posture used for this clone, and the smallest durable residue needed after completion.
- Escalate when: the chosen task would require broad architectural scope, the proof pass cannot stay bounded to one coherent milestone, or the current mixed-agent surfaces are clearly too weak to support even a small real handoff without reopening product shape first.

## Active Milestone

- ID: strong-planner-cheap-implementer-dogfood-pass
- Status: completed
- Scope: configure the local mixed-agent posture for this clone, query the new reporting/default surfaces, complete one bounded real task through that contract, and record the result.
- Ready: completed
- Blocked: none
- optional_deps: GitHub issue `#25`

## Immediate Next Action

- Promote the next proof-oriented roadmap item when another ordinary task can be run end-to-end through the same mixed-agent contract.

## Blockers

- None.

## Touched Paths

- `TODO.md`
- `ROADMAP.md`
- `.agentic-workspace/planning/execplans/archive/strong-planner-cheap-implementer-dogfood-pass-2026-04-13.md`
- `.agentic-workspace/config.local.toml` (local-only, untracked)

## Invariants

- The proof task must be real and bounded.
- Checked-in surfaces should carry the handoff.
- Local override remains local-only and untracked.
- Success means cheaper restart and less rereading.
- Any failure signal should survive this session in checked-in form.

## Contract Decisions To Freeze

- The first dogfood pass should use the shipped `agentic-workspace defaults` and `agentic-workspace config` outputs as the planner-facing contract rather than inventing a new proof scaffold.
- The local override for this proof pass should express capability/cost posture only.
- The proof result should record both what worked and what still leaked ambiguity if the handoff remained too expensive.

## Open Questions Closed

- Chosen bounded task: generated-surface trust follow-through, because it had a narrow maintainer-surface proving lane and directly tested whether generated startup surfaces were still the cheapest trustworthy path.
- Planner-side contract sufficiency: sufficient for this slice. The mixed-agent report established the local posture and the validation-default lane pointed directly to `make maintainer-surfaces` as enough proof.
- Implementer-side rereading requirement: low. No extra repo-specific orchestration or broad rereads were needed beyond the active plan and the relevant trust doc.

## Validation Commands

- `uv run agentic-workspace config --target . --format json`
- `uv run agentic-workspace defaults --format json`
- `make maintainer-surfaces`

## Completion Criteria

- One real bounded task is completed through an explicit mixed-agent proof pass.
- The plan records whether the current surfaces were sufficient for a cheap handoff.
- Any discovered product gap is routed into checked-in follow-up rather than left in chat-only commentary.

## Execution Summary

- Outcome delivered: yes. The first mixed-agent proof pass completed on a real generated-surface trust task.
- Validation confirmed: yes. `make maintainer-surfaces` reported no planning, source/payload/root-install, payload, or maintainer-surface drift warnings.
- Follow-on routed to: `TODO.md`.
- Resume from: promote the next real mixed-agent proof slice, most likely repeated synergy proof, selective-adoption proof refresh, or cross-agent handoff audit.

## Proof Outcome

- What worked:
- `agentic-workspace config --format json` was enough to establish the local posture for this clone without adding repo-owned runtime scheduling.
- `agentic-workspace defaults --format json` was enough to choose the narrow validation lane directly instead of inferring it from prose.
- The bounded task completed through a cheap proving lane with no mismatch to fix, which is still meaningful evidence that the generated surfaces remain trustworthy and fresh.

- What still leaked:
- This pass proved one narrow trust question, not repeated cross-agent execution. It does not yet show that a weaker external implementer can carry a nontrivial code change with equally little rereading.

- Resulting backlog change:
- `Generated-surface trust follow-through` no longer needs its own roadmap lane or open issue because the maintainer-surface proof pass found no remaining trust mismatch.

## Drift Log

- 2026-04-13: Promoted from the highest-priority roadmap queue after the mixed-agent reporting, local-override, and validation-default slices landed and the next need was real dogfooding proof.
- 2026-04-13: Completed on a generated-surface trust pass; archived after the maintainer-surface lane showed no remaining trust drift and the separate generated-surface backlog item was retired.
