---
name: planning-decompose
description: Decompose epic or lane shaped work into bounded schema-backed planning records before execplans.
---

# Planning Decompose

Use this skill when broad work is too large or vague for a single execplan.

## Route

1. Run `agentic-workspace planning --target . --format json`.
2. Run `agentic-workspace summary --target . --format json --profile compact`.
3. Classify whether the work is a lane or an epic before writing implementation files.
4. Create or update a schema-backed decomposition under `.agentic-workspace/planning/decompositions/` when the work has multiple lanes.
5. Promote only the next bounded ready lane into an execplan.

## Guardrails

- Do not use one execplan for unrelated lanes.
- Do not freehand epic Markdown as the durable authority.
- Do not create product source, dependency, database, or app scaffold files during prep-only decomposition.
