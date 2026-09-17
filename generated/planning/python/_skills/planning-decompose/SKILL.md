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

1. Resolve `agentic-workspace start --target . --task "<task>" --format json`.
2. Inspect its current Planning detail and exact owner requests.
3. Classify whether the work is a lane or an epic before writing implementation files.
4. Use current owner-returned requests and actions to create or update a bounded decomposition when the work has multiple lanes.
5. Select only the next bounded ready slice through its current owner; do not hand-edit managed records.

## Guardrails

- Do not use one execplan for unrelated lanes.
- Do not freehand epic Markdown as the durable authority.
- Do not create product source, dependency, database, or app scaffold files during prep-only decomposition.
