---
name: planning-assurance-delegation
description: Apply assurance and delegation posture before handing off or implementing planned work.
---

# Planning Assurance Delegation

Use this skill when task risk or model fit affects whether work should stay direct, escalate, or be delegated.

## Route

1. Run `agentic-workspace config --target . --profile compact --format json`.
2. Run `agentic-workspace summary --target . --format json --profile compact`.
3. Classify risk, proof cost, ambiguity, and capability fit before implementation.
4. Record the chosen assurance/delegation posture in the active execplan when planned work continues.
5. Use `agentic-planning handoff --target . --format json` only after the plan is bounded enough for a worker.

## Outcomes

- stay direct when delegation would add overhead without quality or token benefit
- ask the human when ambiguity blocks safe classification
- escalate to a stronger planner when quality risk dominates
- delegate to a weaker or cheaper implementer only for bounded work with clear proof
