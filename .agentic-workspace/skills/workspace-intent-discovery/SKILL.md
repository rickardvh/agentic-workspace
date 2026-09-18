---
name: workspace-intent-discovery
description: Clarify ambiguous human intent and classify direct, bounded, lane, or epic work after the main AW operating skill routes to intent/shape judgment.
---

# Workspace Intent And Shape

Use this subskill after `workspace-startup` or compact routing when a prompt is broad, vague, high-stakes, or outcome-shaped enough that silently choosing a first implementation slice could miss the user's real goal.
This subskill owns the merged intent/work-shape decision. `workspace-work-shape` is reference support, not a competing peer skill.

## Current owner preparation

Use the configured AW invocation with `start --target . --task "<task>"
--projection full --format json`, repeating `--changed` for known paths. Read
effective `configuration.clarification.mode` and the current owner's restrictions.
The agent or human judges whether work is clear, ambiguous, or requires an owner
decision. No language-specific helper or executable-launch parsing is needed.
If native execution is unavailable, follow the startup skill's conservative
source-reading procedure and keep effective runtime preferences unknown.

The prepared posture consumes effective `clarification.mode`: clear work stays
direct; an independently required decision always remains with its owner;
`ask-first` awaits the bounded human answer; `suggest` surfaces the question and
assumptions while safe independent progress continues; `auto-continue` states the
smallest safe interpretation and correction point. Choose the actual question,
safe scope and remaining uncertainty yourself. No posture grants effects.

Reobserve when relevant preferences, procedure, task judgment or restrictions
change. Use exact fresh owner requests for required decisions; this procedure
does not answer them or grant effects.

## Protocol

1. Apply the startup skill's evidence/sufficiency boundary before interpreting
   ambiguity. Read cheap named intent sources and their material subsequent
   discussion; discover a bounded source when none is identified. In a sparse
   repository, lack of AW material is not lack of accessible project evidence.
   Distinguish evidence not yet read from genuinely missing human judgment.
2. Compare intended requirements with observed behavior and proposals with
   accepted decisions. Preserve legitimate version/environment/local differences.
   For a genuine conflict, seek the smallest discriminating observation or bounded
   owner decision; code, documentation and the latest comment do not win by default.
   Then distinguish clear work, meaningful ambiguity and a required owner decision.
   Prepare the selected posture above only when needed; clarify the remaining
   domain question, not which filename or AW mechanism the human should choose.
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

Use only fields that help resolve meaningful uncertainty or carry intent. Clear
direct work needs no questionnaire, classification report or capture artifact.

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
  "Make onboarding better." Consult available product and task sources first;
  ask about the remaining outcome/audience choice if implementation would still guess.

Acknowledge and proceed:
  "Implement #1234." Read the issue, material later discussion and linked work
  needed to establish accepted intent; state the bounded interpretation before editing.

Do not interrupt:
  "Fix the typo in README.md." The target and proof are direct; clarification would add cost without preserving intent.
