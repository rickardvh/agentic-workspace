---
name: workspace-intent-discovery
description: Clarify ambiguous human intent and classify direct, bounded, lane, or epic work after the main AW operating skill routes to intent/shape judgment.
---

# Workspace Intent And Shape

Use this subskill after `workspace-startup` or compact routing when a prompt is broad, vague, high-stakes, or outcome-shaped enough that silently choosing a first implementation slice could miss the user's real goal.
This subskill owns the merged intent/work-shape decision. `workspace-work-shape` is reference support, not a competing peer skill.

## Selected executable preparation

Use `python .agentic-workspace/skills/workspace-intent-discovery/prepare.py
--native-cli <current-executable> --target . --task "<task>" --procedure intent
--judgment clear|ambiguous|required-decision` after making the semantic judgment.
Pass repeated `--changed` paths when known. The helper calls native `start` afresh;
it never reads or merges configuration files. Python and the current native CLI
are prerequisites. If either is unavailable, report preparation as unexecuted and
use the startup skill's conservative source-reading procedure.

The prepared posture consumes effective `clarification.mode`: clear work stays
direct; an independently required decision always remains with its owner;
`ask-first` awaits the bounded human answer; `suggest` surfaces the question and
assumptions while safe independent progress continues; `auto-continue` states the
smallest safe interpretation and correction point. Choose the actual question,
safe scope and remaining uncertainty yourself. No posture grants effects.

Use `--expected-revision` only to check carried preparation against fresh owners.
Changed relevant preferences, procedure bytes, task judgment or restrictions make
it stale. The helper stores no session and never answers an owner request.

## Protocol

1. Distinguish a clear task, meaningful ambiguity and a required owner decision.
2. Prepare the selected posture above; follow it for one bounded clarification.
3. Classify work as `direct`, `bounded`, `lane`, or `epic` using continuity value.
4. Carry useful clarified intent to its existing issue or current owner. Create
   Planning only through its exact native operation when durable continuity helps.
5. Preserve uncertainty and hard owner restrictions under every mode.

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
