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

1. Run the validation selected by the active plan or `agentic-workspace proof --target . --changed <paths> --format json`.
2. Consult `planning-intent-verification` or `report --section closeout_trust` to decide whether original intent is fully satisfied, partially satisfied, or blocked.
3. Distill what should survive: future work to Planning, durable knowledge to Memory, stable guidance to docs, enforceable behavior to tests/contracts/config, and tracker follow-up to issues.
4. Use `agentic-workspace planning archive-plan --plan <plan> --target . --prepare-closeout --apply-cleanup --format json` when the plan is done.
5. Run `agentic-workspace summary --target . --format json` after archive cleanup.

## Guardrails

- Red flag: Archive or close is safe because validation passed.
- Use instead: Run `agentic-workspace report --target . --section closeout_trust --format json`, then archive only when proof, intent satisfaction, residue, and continuation owner are reconciled.
- Do not keep completed execplans as the knowledge base.
- Do not close external issues when intent is only partially satisfied.
- Treat missing proof, skipped startup, or absent closeout evidence as lower trust.

## Behavior-Impact Evidence

Changes to this skill must preserve the separation between validation, intent satisfaction, issue closure, residue routing, and archive mechanics. Use closeout-trust report output or focused closeout tests as evidence.
