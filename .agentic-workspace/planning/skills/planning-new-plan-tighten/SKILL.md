---
name: planning-new-plan-tighten
description: Create or tighten a schema-backed execplan scaffold before coding.
---

# Planning New Plan Tighten

Use this skill when checked-in Planning is required and the current plan is missing concrete execution detail.

## Route

1. Prefer `agentic-planning new-plan --id <id> --title <title> --target . --activate --format json` for new active work.
2. If a planning item already exists, use `agentic-planning promote-to-plan <item-id> --target . --format json`.
3. Tighten the scaffold before implementation: goal, non-goals, touched paths, execution bounds, validation commands, completion criteria, assurance/delegation posture, and stop conditions.
4. Run `agentic-workspace summary --target . --format json --profile compact` before editing product files.

## Guardrails

- A scaffold is not an implementation contract until the vague fields are replaced.
- Do not copy templates into unchecked custom shapes.
- Do not leave `state.toml` pointing at a plan that summary reports as unhealthy.
