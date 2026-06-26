---
name: workspace-intent-discovery
description: Run a bounded human intent-discovery dialogue before vague or high-stakes prompts become Planning or implementation work.
---

# Workspace Intent Discovery

Use this skill when a prompt is broad, vague, high-stakes, or outcome-shaped enough that silently choosing a first implementation slice could miss the user's real goal.

Use it for natural-language intent elicitation, not mechanical classification. The agent owns judgment about whether the prompt is clear enough to proceed.

## Trigger Conditions

- The requested task, initiative, repo/system outcome, completion boundary, anti-goals, or unresolved assumptions are unclear.
- Two plausible interpretations would produce materially different work, proof, or closure claims.
- Existing Planning, Memory, issue, config, or system-intent evidence is stale, contradictory, unavailable, or missing in a way that can change the next safe action.

## Protocol

1. Name two or three plausible interpretations, not just one inferred intent.
2. Ask one compact question that captures why the work matters, desired outcome, non-goals, and an acceptable first slice.
3. If the user does not answer and progress is still safe, proceed only with stated assumptions and visible uncertainty.
4. Carry the clarified result into the smallest existing surface: `task_intent`, `acceptance`, `durable_intent`, Memory, Planning, or an issue, including a `completion-boundary` when closure could otherwise be ambiguous.
5. Stop the dialogue after one bounded clarification unless the user's answer exposes a real safety, authority, or scope blocker.

## Output Shape

- `inferred_intent`
- `uncertainty`
- `candidate_interpretations`
- `likely_non_goals`
- `stakes_if_wrong`
- `proposed_first_slice`
- `question_to_user`
- `proceed_without_answer_when`
- `captured_intent_after_reply`
- `promotion_target`
- `intent_records`

Each `intent_records` entry should use the compact custody shape:

- `intent_ref`
- `level`: `task`, `initiative`, `repo`, `system`, `completion-boundary`, `anti-goal`, or `unresolved-assumption`
- `statement`
- `completion_boundary`
- `anti_goals`
- `unresolved_assumptions`
- `provenance`
- `freshness`

Prefer `intent_custody` when compact refs, boundaries, anti-goals, provenance, and freshness are enough. Promote to Planning, Memory, an issue, or `durable_intent` only when the intent must survive as owned durable state.

## Examples

Ask:
  "Make onboarding better." The outcome, audience, non-goals, and first slice are unclear enough that implementation or Planning would guess.

Acknowledge and proceed:
  "Implement #1234." The issue can carry detail; state the interpretation, first slice, and correction point before editing.

Do not interrupt:
  "Fix the typo in README.md." The target and proof are direct; clarification would add cost without preserving intent.
