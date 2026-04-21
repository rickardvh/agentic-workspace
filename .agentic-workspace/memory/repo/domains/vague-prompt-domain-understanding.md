# Vague Prompt Domain Understanding

## Status

Stable

## Canonicality

agent_only

## Scope

Repo-native prompt interpretation and the durable domain knowledge needed to resolve vague prompts without repeated broad rereads.

## Applies to

This understanding currently matters for `src/agentic_workspace/cli.py` and the front-door workspace contracts under `.agentic-workspace/docs/`: `compact-contract-profile.md`, `reporting-contract.md`, `ownership-authority-contract.md`, `proof-surfaces-contract.md`, and `delegation-posture-contract.md`.

## Load when

- The same vague prompt class keeps arriving.
- Clarification keeps asking for the same repo facts.
- Proof-lane or owner inference depends on repo-specific context.

## Review when

- The intent, clarification, prompt-routing, or relay surfaces change.
- Routed Memory is absent or does not change the interpretation choice.
- The repo learns a new recurring prompt class.

## Failure signals

- Repeated prompt-polishing.
- Repeated proof-lane uncertainty.
- Repeated owner-inference uncertainty.
- Broad rereads are needed even after clarification surfaces exist.

## Rule or lesson

- Borrow from routed Memory before freezing the compact contract for a vague prompt.
- If the same prompt class keeps recurring, capture the missing repo knowledge in Memory or canonical docs instead of re-solving it every time.
- Memory should store durable domain understanding, not only task context.
- If the content becomes stable policy or front-door contract wording, promote it into canonical docs.
- Keep reusable maintenance choreography in a companion skill instead of turning this note into a workflow dump.

## How to recognise it

- The same vague prompt class keeps arriving.
- Clarification asks for the same repo facts repeatedly.
- A cheap implementer would otherwise need broad rereads.

## Companion procedure

Use the companion skill at `.agentic-workspace/memory/repo/skills/vague-prompt-domain-understanding/SKILL.md` when the task is the repeatable workflow for handling this prompt class.
Keep this note focused on the recurring domain fact: vague prompts get cheaper when routed Memory supplies repo-specific understanding before proof-lane or owner selection.

## Verify

The clarification, prompt-routing, and relay selectors should still agree on the cheap-first vague-prompt path.

## Verified against

Verified against `.agentic-workspace/docs/compact-contract-profile.md`, `.agentic-workspace/docs/reporting-contract.md`, `.agentic-workspace/docs/ownership-authority-contract.md`, `.agentic-workspace/docs/proof-surfaces-contract.md`, `.agentic-workspace/docs/delegation-posture-contract.md`, and `src/agentic_workspace/cli.py`.

## Last confirmed

2026-04-16 during intent interpretation tranche
