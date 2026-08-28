---
name: planning-promote-review-findings
description: Promote selected findings from .agentic-workspace/planning/reviews into roadmap or active planning only when the trigger and target are explicit.
---

# Planning Promote Review Findings

Planning Promote Review Findings turns selected review findings into planned work candidates without blurring the boundary between review capture and planning activation.

## Operating Rules

1. Read the relevant review artifact and canonical Planning summary before editing.
2. Promote only findings with explicit evidence, confidence, and a concrete promotion trigger.
3. Prefer a bounded lane or decomposition owner for plausible future work that needs checked-in planning custody.
4. Create and locally select an execplan only when urgency, repeated friction, or explicit maintainer direction justifies activation.
5. Preserve the original source classification when summarising the promoted item.
6. Do not promote every finding from a review artifact.
7. If the real value is durable guidance rather than future work, promote to canonical docs or memory instead of planning.
8. By default, do not promote a new planning item unless there is measured friction, repeated failure, repeated dogfooding pain, or an explicit maintainer override.

## Promotion Checklist

- Is the finding still current?
- Is the source class clear?
- Is the suggested action concrete enough to be useful?
- Is there an explicit trigger for activation?
- Does the target surface match the time horizon?
- Is there measured friction, repeated failure, repeated dogfooding pain, or explicit maintainer override for why this should exist now?

If any answer is no, defer or dismiss instead of promoting.

## Output Contract

End each run with:

- review artifact used
- findings promoted
- target surfaces updated
- findings deferred or dismissed
- rationale for any execplan activation
