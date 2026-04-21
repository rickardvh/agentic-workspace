---
name: vague-prompt-domain-understanding
description: Handle recurring vague-prompt interpretation by checking the smallest routed memory and front-door contract surfaces first, without turning the domain note into a workflow dump.
---

# Vague Prompt Domain Understanding

Use this skill when the same vague prompt class keeps recurring and you need the compact repeatable workflow rather than the durable domain note alone.

## Checklist

1. Read the smallest relevant routed memory note first.
2. Re-check the front-door intent surfaces:
   - `.agentic-workspace/docs/compact-contract-profile.md`
   - `.agentic-workspace/docs/reporting-contract.md`
   - `.agentic-workspace/docs/ownership-authority-contract.md`
   - `.agentic-workspace/docs/proof-surfaces-contract.md`
   - `.agentic-workspace/docs/delegation-posture-contract.md`
3. Confirm whether the prompt is missing repo-specific understanding, proof-lane selection, or owner selection.
4. If the same repo fact keeps recurring, tighten the durable Memory or canonical-doc owner instead of re-solving it in chat.
5. If the guidance has become stable contract wording or repo-wide policy, promote it into canonical docs rather than leaving it here.

## Typical verification

- `agentic-workspace defaults --section clarification --format json`
- `agentic-workspace defaults --section prompt_routing --format json`
- `agentic-workspace defaults --section relay --format json`
