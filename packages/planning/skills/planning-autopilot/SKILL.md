---
name: planning-autopilot
description: Execute bounded planning slices from the checked-in planning surfaces until the active objective reaches an authorized terminal outcome.
---

# Planning Autopilot

Planning Autopilot is a bounded execution skill for the planning contract. It executes the current active planning slice, validates the result, updates task state, and re-reads planning state before deciding whether the same explicit objective has another safe continuation slice.

## Operating Rules

1. Read `AGENTS.md`, `.agentic-workspace/planning/state.toml`, and the active execplan before making changes.
2. Treat the checked-in planning surfaces as the execution contract. Do not invent new scope from chat context alone.
3. Execute one bounded slice at a time, then re-read the active planning surfaces before continuing.
4. Run the narrowest validation that proves the milestone.
5. Update `.agentic-workspace/planning/state.toml` and the active execplan when the milestone completes or blocks.
6. Capture improvement signals that matter to future execution, but do not expand scope just because an adjacent issue is visible.
7. Stop only on an authorized terminal outcome: completed objective, qualified external blocker with no safe continuation, or user pause. Ambiguity, plan drift, and code drift must route to reconciliation or to a typed BLOCKED outcome that proves no safe continuation remains.

## Suitability Check

Use autopilot only when the active work is clearly bounded, the touched paths are narrow, and the validation story is obvious enough to prove the change.

Stop and report instead of editing when:

- no active milestone is clear
- multiple competing threads are active
- the milestone is too vague to execute safely
- validation scope is unknown
- the plan and code materially diverge and reconciliation cannot produce a safe next slice
- broader redesign is needed before implementation can continue

## Execution Loop

1. Read the repo operating contract and planning surfaces.
2. Identify the current active milestone.
3. Confirm the work is suitable for autopilot.
4. Implement the milestone without broadening scope.
5. Run the narrowest proving validation.
6. Update planning state and record any blocker or improvement signal.
7. If the same explicit objective still has safe continuation state, repeat from step 2; otherwise stop with a structured summary.

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
- It must not become a general project manager.
- It must not use improvement signals to justify unconstrained cleanup.
- It must not treat one milestone completion as permission to yield while the same explicit objective remains safely continuable.
- It must preserve the boundary between planning state, durable memory, and long-horizon roadmap work.
