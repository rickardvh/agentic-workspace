---
name: planning-decompose
description: Decompose epic or lane shaped work into bounded schema-backed planning records before execplans.
---

# Planning Decompose

Use this skill when broad work is too large or vague for a single execplan.

## Primary Ownership

This skill owns parent/lane/slice structure before execplans. It decides how broad work becomes decomposition records and ready bounded slices; it does not decide semantic intent satisfaction or closeout permission.

Route intent satisfaction to `planning-intent-verification`, closeout mechanics to `planning-closeout-trust`, broad lifecycle sequencing to `planning-high-assurance-lifecycle`, and active-state projection to `planning-reporting`.

## Route

1. Run `agentic-workspace planning --target . --format json`.
2. Run `agentic-workspace summary --target . --format json`.
3. Classify whether the work is a lane or an epic before writing implementation files.
4. Create or update a schema-backed decomposition under `.agentic-workspace/planning/decompositions/` when the work has multiple lanes.
5. Promote only the next bounded ready lane into an execplan.

## Guardrails

- Do not use one execplan for unrelated lanes.
- Do not freehand epic Markdown as the durable authority.
- Do not create product source, dependency, database, or app scaffold files during prep-only decomposition.
