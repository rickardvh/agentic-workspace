---
name: planning-assurance-delegation
description: Narrow pre-decision assessment reference for risk, proof cost, ambiguity, and capability fit.
---

# Planning Assurance Delegation

Use this skill before a canonical assignment decision exists and only when risk
or capability fit needs assessment. It is not an orchestration procedure and
must not override an existing assignment, action gate, target, or run state.

## Route

1. Run `agentic-workspace config --target . --format json`; use `--select <field[,field...]>` when exact detail is needed.
2. Run `agentic-workspace summary --target . --format json`.
3. Classify risk, proof cost, ambiguity, and capability fit before implementation.
4. Supply the assessment to the canonical Planning decision operation; do not
   retain a parallel target-selection record in skill prose.
5. After a delegated assignment exists, route to
   `planning-orchestrator-workflow`, not this skill.

## Outcomes

- recommend direct work, escalation, or delegation only before the canonical
  action gate is decided
- ask the human when ambiguity blocks safe classification
- escalate to a stronger planner when quality risk dominates
- delegate to a weaker or cheaper implementer only for bounded work with clear proof

## Boundary

This skill stays quiet for direct current-target-selected work and for every
binding assignment. The action gate, not this assessment, enforces the result.
