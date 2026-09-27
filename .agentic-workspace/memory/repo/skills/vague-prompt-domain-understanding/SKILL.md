---
name: vague-prompt-domain-understanding
description: Handle recurring vague-prompt interpretation by checking the smallest routed memory and front-door contract surfaces first, without turning the domain note into a workflow dump.
---

# Vague Prompt Domain Understanding

Use this skill when the same vague prompt class keeps recurring and you need the compact repeatable workflow rather than the durable domain note alone.

## Checklist

1. Read the smallest relevant routed memory note first.
2. Read only the contract that can resolve the missing fact; these are alternatives,
   not a required reading sequence:
   - `.agentic-workspace/docs/compact-contract-profile.md`
   - `.agentic-workspace/docs/reporting-contract.md`
   - `.agentic-workspace/docs/ownership-authority-contract.md`
   - `.agentic-workspace/docs/proof-surfaces-contract.md`
   - `.agentic-workspace/docs/delegation-posture-contract.md`
3. Identify whether the missing fact is repository context, the evidence needed for
   a claim, or the component responsible for the requested action.
4. If the same repo fact keeps recurring, tighten the durable Memory or canonical-doc owner instead of re-solving it in chat.
5. For a correction that belongs in canonical docs or repository policy, use the
   [correction procedure](../../../../skills/workspace-instruction-correction/SKILL.md)
   and verify its supported publication result. This checklist grants no promotion.

## Current intent routing

Use `.agentic-workspace/skills/workspace-startup/SKILL.md` and its routed
`workspace-intent-discovery` skill to clarify missing intent. Resolve current
owner requests through the configured native invocation; this local procedure
adds no command aliases or verification authority.
