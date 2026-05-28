---
name: planning-autopilot
description: Execute one bounded planning milestone from the checked-in planning surfaces, validate it narrowly, and keep plan state current.
---

# Planning Autopilot

Planning Autopilot is a bounded execution skill for the planning contract. It executes the current active milestone, validates the result, updates task state, and stops cleanly when the work is done or blocked.

## Operating Rules

1. Read `AGENTS.md`, `.agentic-workspace/planning/state.toml`, and the active execplan before making changes.
2. Treat the checked-in planning surfaces as the execution contract. Do not invent new scope from chat context alone.
3. Execute only one active milestone at a time unless the prompt explicitly says otherwise.
4. Run the narrowest validation that proves the milestone.
5. Update `.agentic-workspace/planning/state.toml` and the active execplan when the milestone completes or blocks.
6. Capture improvement signals that matter to future execution, but do not expand scope just because an adjacent issue is visible.
7. Stop on blockers, ambiguity, or plan/code drift instead of trying to power through.

## Suitability Check

Use autopilot only when the active work is clearly bounded, the touched paths are narrow, and the validation story is obvious enough to prove the change.

Stop and report instead of editing when:

- no active milestone is clear
- multiple competing threads are active
- the milestone is too vague to execute safely
- validation scope is unknown
- the plan and code materially diverge
- broader redesign is needed before implementation can continue

## Execution Loop

1. Read the repo operating contract and planning surfaces.
2. Identify the current active milestone.
3. Confirm the work is suitable for autopilot.
4. Implement the milestone without broadening scope.
5. Run the narrowest proving validation.
6. Update planning state and record any blocker or improvement signal.
7. Stop with a structured summary.

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
- It must preserve the boundary between planning state, durable memory, and long-horizon roadmap work.
