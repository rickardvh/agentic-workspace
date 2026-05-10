---
name: workspace-work-shape
description: Classify work shape and route direct, bounded, lane, or epic work before implementation.
---

# Workspace Work Shape

Use this skill before implementation when task size, proof cost, handoff needs, or the user's intended outcome are unclear.

## Route

1. Run `agentic-workspace start --target . --task "<task>" --format json`.
2. If changed paths are known, run `agentic-workspace implement --target . --changed <paths> --format json`.
3. Run `agentic-workspace preflight --target . --format json` only for takeover, recovery, or uncertain state.
4. For vague outcome prompts, resolve the intended outcome before naming a solution:
   - What user-visible failure or cost should be reduced?
   - What would count as satisfaction?
   - Which repo-visible surface should preserve that intent for the next pass?
5. Classify the request as `direct`, `bounded`, `lane`, or `epic`.
6. For non-direct, vague-outcome, bounded, lane, or epic work, use the stated-assumption middle path before editing: state the inferred intent, the concrete first slice, non-goals/deferred scope, and that you will proceed unless corrected.
7. For `direct` work, keep workspace overhead minimal and prove with the obvious narrow command.
8. For `bounded` work, use compact planning or proof output when continuation, risk, or non-obvious validation matters.
9. For `lane` or `epic` work, stop before coding and create or continue checked-in Planning state.

## Token Budget

- A useful plan reduces future reading. Keep it to intent, slice, stop condition, proof, and next action.
- Ask for clarification only when the answer changes the safe next step; otherwise state a bounded assumption.
- Preserve compact continuation state only when work is unfinished or handoff/restart would otherwise force rediscovery.
- In final reports, summarize changed, intent served, verified, and unresolved; do not narrate obvious diffs or dump raw logs.

## Output

Report the inferred intended outcome, the shape, why that shape fits, the first repo-visible surface to inspect or update, the satisfaction evidence, the required next command, whether Planning state is optional/recommended/required, and any correction point from `intent_acknowledgement`.
