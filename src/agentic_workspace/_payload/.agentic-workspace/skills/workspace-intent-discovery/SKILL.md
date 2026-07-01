---
name: workspace-intent-discovery
description: Clarify ambiguous human intent and classify direct, bounded, lane, or epic work after the main AW operating skill routes to intent/shape judgment.
---

# Workspace Intent And Shape

Use this subskill after `workspace-startup` or compact routing when a prompt is broad, vague, high-stakes, or outcome-shaped enough that silently choosing a first implementation slice could miss the user's real goal.
This subskill owns the merged intent/work-shape decision. `workspace-work-shape` is reference support, not a competing peer skill.

## Protocol

1. Name two or three plausible interpretations, not just one inferred intent.
2. Ask one compact question that captures why the work matters, desired outcome, non-goals, and an acceptable first slice.
3. If the user does not answer and progress is still safe, proceed only with stated assumptions and visible uncertainty.
4. Classify the work as `direct`, `bounded`, `lane`, or `epic`.
5. Carry the clarified result into the smallest existing surface: `task_intent`, `acceptance`, `durable_intent`, Memory, Planning, or an issue, including a `completion-boundary` when closure could otherwise be ambiguous.
6. Stop the dialogue after one bounded clarification unless the user's answer exposes a real safety, authority, or scope blocker.

## Shape Rules

- `direct`: target and proof are obvious; keep workspace overhead minimal.
- `bounded`: finite local implementation with non-obvious proof or continuation risk; use compact implement/proof output.
- `lane`: multi-slice work that needs checked-in Planning state before coding.
- `epic`: multiple lanes, unclear decomposition, or high assurance; stop before implementation and shape the durable plan first.

## Output Shape

- `inferred_intent`
- `uncertainty`
- `candidate_interpretations`
- `likely_non_goals`
- `stakes_if_wrong`
- `proposed_first_slice`
- `work_shape`
- `why_shape_fits`
- `satisfaction_evidence`
- `question_to_user`
- `proceed_without_answer_when`
- `captured_intent_after_reply`
- `promotion_target`

Prefer `intent_custody` when compact refs, boundaries, anti-goals, provenance, and freshness are enough. Use `unresolved-assumption` entries when uncertainty must remain visible through proof or closeout.

## Examples

Ask:
  "Make onboarding better." The outcome, audience, non-goals, and first slice are unclear enough that implementation or Planning would guess.

Acknowledge and proceed:
  "Implement #1234." The issue can carry detail; state the interpretation, first slice, and correction point before editing.

Do not interrupt:
  "Fix the typo in README.md." The target and proof are direct; clarification would add cost without preserving intent.
