---
name: planning-closeout-trust
description: Close out planned work with proof, intent satisfaction, trust, and residue distillation.
---

# Planning Closeout Trust

Use this skill after implementation of planned work, before closing the issue or archiving the plan.

## Route

1. Run the validation selected by the active plan or `agentic-workspace proof --target . --changed <paths> --format json`.
2. Decide whether original intent is fully satisfied, partially satisfied, or blocked.
3. Distill what should survive: future work to Planning, durable knowledge to Memory, stable guidance to docs, enforceable behavior to tests/contracts/config, and tracker follow-up to issues.
4. Use `agentic-workspace planning archive-plan --plan <plan> --target . --prepare-closeout --apply-cleanup --format json` when the plan is done.
5. Run `agentic-workspace summary --target . --format json` after archive cleanup.

## Guardrails

- Do not keep completed execplans as the knowledge base.
- Do not close external issues when intent is only partially satisfied.
- Treat missing proof, skipped startup, or absent closeout evidence as lower trust.
