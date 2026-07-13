---
name: planning-autopilot
description: Execute bounded planning slices from the checked-in planning surfaces until the active objective reaches an authorized terminal outcome.
---

# Planning Autopilot

Planning Autopilot is a bounded execution skill for the planning contract. Its ordinary host entrypoint is `agentic-workspace autopilot --target <repo> --executor-command <agent-command> --format json`; do not run the slice loop directly outside that host boundary. The host entrypoint delegates each executor attempt through `autopilot.run` / `final-response admit`, admits model-authored final responses before output, and re-enters execution while the same explicit objective has safe continuation state.

## Operating Rules

1. Read `AGENTS.md`, `.agentic-workspace/planning/state.toml`, and the active execplan before making changes.
2. Treat the checked-in planning surfaces as the execution contract. Do not invent new scope from chat context alone.
3. Enter ordinary Autopilot through `autopilot.run`; if a host cannot supply an executor command, report that the host boundary is unavailable instead of running a direct skill-owned loop.
4. Execute one bounded slice per executor invocation, then let the host entrypoint admit the attempted final response and decide whether continuation is required.
5. Run the narrowest validation that proves the milestone.
6. Update `.agentic-workspace/planning/state.toml` and the active execplan when the milestone completes or blocks.
7. Capture improvement signals that matter to future execution, but do not expand scope just because an adjacent issue is visible.
8. Stop only on an authorized terminal outcome: completed objective, qualified external blocker with no safe continuation, or user pause. Ambiguity, plan drift, and code drift must route to reconciliation or to a typed BLOCKED outcome that proves no safe continuation remains.

## Suitability Check

Use autopilot only when the active work is clearly bounded, the touched paths are narrow, and the validation story is obvious enough to prove the change.

Reconcile before editing when:

- no active milestone is clear: select or create the smallest planning-owned next slice before implementation
- multiple competing threads are active: choose the current objective owner or record a typed BLOCKED state only when no safe selection exists
- the milestone is too vague to execute safely: tighten the milestone until it yields one safe slice or a typed blocker
- validation scope is unknown: derive the narrowest proof lane before implementation or block with evidence that no proof path is available
- the plan and code materially diverge: reconcile the plan/code boundary before continuing, or block only with evidence that reconciliation cannot produce a safe next slice
- broader redesign appears necessary: route to decomposition or high-assurance planning before implementation, or block only when no bounded continuation exists

## Host Entry

Launch the ordinary route with the package-owned host boundary:

```text
agentic-workspace autopilot --target <repo> --executor-command <agent-command> --format json
```

The executor command is the agent implementation slice. The host entrypoint is responsible for admitting its stdout as the attempted final response, running the selected continuation operation when CONTINUE remains, preserving continuation state, and re-invoking the executor until an authorized terminal outcome is reached.

## Executor Slice Contract

Inside each executor invocation:

1. Read the repo operating contract and planning surfaces.
2. Identify the current active milestone.
3. Confirm the work is suitable for autopilot.
4. Implement the milestone without broadening scope.
5. Run the narrowest proving validation.
6. Update planning state and record any blocker or improvement signal.
7. Emit only the attempted final response for the host entrypoint to admit; do not bypass admission with a direct user-facing final.

## Output Contract

End each run with:

- active task
- milestone executed
- files changed
- validation run
- outcome
- planning state updates performed
- blockers, if any
- improvement signals captured
- recommended next step

Outcome values:

- `completed`
- `blocked`
- `partial`
- `unsuitable`

## Boundaries

- This skill executes planning work; it does not replace planning itself.
- Its ordinary route is the `autopilot.run` host boundary, not a parallel direct loop owned only by skill prose.
- It must not become a general project manager.
- It must not use improvement signals to justify unconstrained cleanup.
- It must not treat one milestone completion as permission to yield while the same explicit objective remains safely continuable.
- It must preserve the boundary between planning state, durable memory, and long-horizon roadmap work.
