---
name: workspace-work-shape
description: Decide work shape from AW facts, hard blockers, proof needs, and user intent before implementation.
---

# Workspace Work Shape

Use this skill before implementation when task size, proof cost, handoff needs, or the user's intended outcome are unclear.

AW reports facts about AW-owned state; it does not own the final semantic judgment for soft cases. When `implement --changed`
returns `work_shape_guidance.agent_decision_required=true`, use those facts to decide whether the work is `direct`, `bounded`,
`lane`, or `epic`. Treat hard blockers from AW as authoritative, but do not outsource ordinary intent interpretation to
keyword matches.

## Route

1. Run `agentic-workspace start --target . --task "<task>" --format json`.
2. If changed paths are known, run `agentic-workspace implement --target . --changed <paths> --format json`.
3. Run `agentic-workspace preflight --target . --format json` only for takeover, recovery, or uncertain state.
4. Read `planning_safety_gate.work_shape_guidance` when present:
   - `hard_blockers` are AW-owned stop signs.
   - `scope_factors` are observable changed-path, issue, active-state, and proof facts.
   - `direct_work_is_reasonable_when` and `planning_may_help_when` are guidelines, not package decisions.
   - `agent_decision_required=true` means you must choose and own the work shape.
   - `stop_conditions` name when to pause or promote Planning.
5. For vague outcome prompts, resolve the intended outcome before naming a solution:
   - What user-visible failure or cost should be reduced?
   - What would count as satisfaction?
   - Which repo-visible surface should preserve that intent for the next pass?
6. Decide whether the request is `direct`, `bounded`, `lane`, or `epic`; AW guidance can inform that decision but does not own it.
7. For `direct` work, keep workspace overhead minimal and prove with the obvious narrow command.
8. For `bounded` work, use compact planning or proof output when continuation, risk, or non-obvious validation matters.
9. For `lane` or `epic` work, stop before coding and create or continue checked-in Planning state.

## Common Soft Cases

- A PR review-comment fix with known, narrow changed paths can usually stay `direct` if `hard_blockers=[]`; name the proof and stop if the touched surface widens.
- A single-issue follow-through can usually stay `direct` or `bounded` when changed paths are known and AW reports no hard blocker; do not infer the full issue is complete from a narrow repair.
- A Memory routing-feedback update may be ancillary when it records dogfooding pressure from the same bounded task; it becomes central work if the task is to redesign Memory routing.
- A docs-only or CI-only repair can stay `direct` when proof is obvious; promote Planning when the fix changes policy, contracts, or cross-module behavior.
- If AW reports planning-plus-implementation, generated/source coupling, parent-decomposition debt, active delegation requirements, or scope growth, treat that as a hard blocker until resolved.

## Output

Report the inferred intended outcome, the shape, why that shape fits, the AW facts or blockers that shaped the call, the first repo-visible surface to inspect or update, the satisfaction evidence, the required next command, and whether Planning state is optional, recommended, or required.
