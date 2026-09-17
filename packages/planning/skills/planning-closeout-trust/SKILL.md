---
name: planning-closeout-trust
description: Close out planned work with proof, intent satisfaction, trust, and residue distillation.
---

# Planning Closeout Trust

Use this skill after implementation of planned work, before closing the issue or archiving the plan.

## Primary Ownership

This skill owns closeout procedure: proof-to-claim reconciliation, archive/close decisions, residue distillation, and final trust posture. It invokes `planning-intent-verification` for semantic intent satisfaction instead of redefining that judgment.

Route broad/high-risk workflow setup to `planning-high-assurance-lifecycle`, decomposition questions to `planning-decompose`, and read-only active-state summaries to `planning-reporting`.

## Route

1. Resolve current Verification requirements through `agentic-workspace start --target . --task "<task>" --changed <path> --format json`, or use the workspace proof-selection skill to prepare and execute an admitted check through `proof-procedure`.
2. Consult `planning-intent-verification` and the current owner evidence to decide whether original intent is fully satisfied, partially satisfied, or blocked.
3. Distill what should survive: future work to Planning, durable knowledge to Memory, stable guidance to docs, enforceable behavior to tests/contracts/config, and tracker follow-up to issues.
4. Use exact current Planning requests and actions to reconcile completion, required continuation and archival when admitted.
5. Inspect the effect outcome and current continuation after the transition. A successful write does not replace source reconciliation or independent review.

## Guardrails

- Red flag: Archive or close is safe because validation passed.
- Use instead: Inspect current Planning and Verification detail, then archive only when proof, intent satisfaction, residue and continuation owner are reconciled.
- Do not keep completed execplans as the knowledge base.
- Do not close external issues when intent is only partially satisfied.
- Treat missing proof, skipped startup, or absent closeout evidence as lower trust.

## Behavior-Impact Evidence

Changes to this skill must preserve the separation between validation, intent satisfaction, issue closure, residue routing and archive mechanics. Use current owner outcomes and focused native closeout tests as evidence.
