---
name: planning-new-plan-tighten
description: Create or tighten a schema-backed execplan scaffold before coding.
---

# Planning New Plan Tighten

Use this skill when checked-in Planning is required and the current plan is missing concrete execution detail.

If the current request is prep-only handoff, the goal is cheaper durable state, not an implementation-ready contract.

## Route

1. Prefer `agentic-workspace planning new-plan --id <id> --title <title> --target . --activate --format json` for new active work.
2. If a planning item already exists, use `agentic-workspace planning promote-to-plan --item-id <item-id> --target . --format json`.
3. For prep-only handoff, use `agentic-workspace planning new-plan --id <id> --title <title> --target . --activate --prep-only --format json`, then run `agentic-workspace summary --target . --format json` and stop unless summary reports a blocking Planning problem.
4. For implementation work, tighten the scaffold before implementation: goal, non-goals, touched paths, execution bounds, validation commands, completion criteria, assurance/delegation posture, and stop conditions.
5. Run `agentic-workspace summary --target . --format json` before editing product files.

## Guardrails

- A scaffold is not an implementation contract until the vague fields are replaced.
- A prep-only scaffold is different: it is enough when summary verifies active Planning state. Do not manually polish or revalidate generated JSON during prep-only handoff.
- Do not copy templates into unchecked custom shapes.
- Do not leave `state.toml` pointing at a plan that summary reports as unhealthy.
- Do not use ad hoc shell snippets to validate generated JSON when summary or package checks can validate the surface.
