---
name: planning-review-pass
description: Run one bounded review pass, capture evidence-backed findings in docs/reviews, and stop short of activating future work automatically.
---

# Planning Review Pass

Planning Review Pass is a deliberate analysis skill for future-work discovery.
It exists to capture compact, evidence-backed findings without turning review output into immediate queue churn.

## Operating Rules

1. Read `AGENTS.md`, `TODO.md`, and any explicitly referenced review scope before starting.
2. Treat the task as analysis, not implementation, unless the prompt explicitly asks for fixes too.
3. Keep the review bounded to one subsystem, one question, or one risk area.
4. Write findings into `docs/reviews/` using the local template.
5. Label each finding with confidence, source class, promotion target, and promotion trigger.
6. Keep friction-confirmed findings distinct from pure analysis findings.
7. Do not add findings directly to `TODO.md` or create an execplan unless the prompt explicitly asks for promotion.

## Suitable Inputs

Use this skill when the user wants:

- a review pass over one repo area
- analysis of future risks or opportunities
- compact capture of findings for later prioritisation
- a structured artifact rather than chat-only review residue

Do not use it for:

- active implementation work
- broad repo-wide audits with no bounded scope
- static-analysis dump capture without triage
- durable memory capture

## Execution Loop

1. Define the bounded review question and scope.
2. Inspect the minimum code and docs needed.
3. Record only evidence-backed findings.
4. Classify each finding by source and confidence.
5. Recommend promote, defer, or dismiss outcomes.
6. Stop after the review artifact is updated.

## Output Contract

End each run with:

- review scope
- artifact path
- findings captured
- source-class split
- promotion candidates, if any
- explicit note that no activation occurred unless promotion was requested
