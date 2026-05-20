---
name: workspace-proof-selection
description: Select proof that matches the task, slice, lane, or epic before claiming completion. Use when validation evidence, skips, warnings, retries, crashes, or negative proof need to be interpreted separately from whether the requested intent is satisfied.
---

# Workspace Proof Selection

This is a package-managed workspace skill installed under `.agentic-workspace/skills/`.

Use it to choose and interpret proof before closeout. It is not a test-running checklist; it is the decision layer that says what evidence is meaningful for the claim being made.

## Workflow

1. Identify the claim level:
   - task
   - bounded slice
   - lane
   - epic
   - regression guard
2. Read the structured proof route before broad inspection:
   - `agentic-workspace implement --changed <paths> --format json` when changed paths are known
   - `agentic-workspace proof --changed <paths> --format json` for proof-only selection
   - `agentic-workspace summary --format json` when an active plan or lane determines the claim level
3. Select proof for both behavior and intent:
   - command success for changed behavior
   - targeted tests for the touched surface
   - contract/schema checks for structured outputs
   - lint/type checks when the slice changes static interfaces
   - manual inspection only when the expected result is documentation, prose, or routing metadata
4. Classify the proof result:
   - `passed`
   - `passed_with_warning`
   - `retried_then_passed`
   - `skipped`
   - `crashed`
   - `not_run`
   - `incomplete`
   - `negative_proof_found`
5. Decide whether completion is allowed separately from command status:
   - `completion_claim_allowed=true` only when the proof covers the actual claim level and requested intent
   - `completion_claim_allowed=false` when proof is missing, stale, too narrow, skipped without justification, or contradicts the intended outcome
6. Route gaps instead of hiding them:
   - run the missing focused proof
   - narrow the completion claim to a slice
   - update the active plan with the gap
   - open or link follow-up work when the gap belongs outside the slice

## Guardrails

- Red flag: Tests passed, so completion is claimable.
- Use instead: Record proof execution evidence, inspect `completion_options`, and reconcile intent/residue before claiming completion.
- Do not claim a lane or epic complete from proof that only covers a local slice.
- Do not treat passing self-authored tests as sufficient when the parent intent, negative invariant, or user-visible behavior is unverified.
- Do not ignore warnings, skipped tests, retries, crashes, or environment failures; classify them.
- Do not replace proof with a review artifact unless the requested surface is review-only.
- Do not run broad validation first when a structured proof selector names a narrower command.

## Behavior-Impact Evidence

Changes to this skill must name the behavior being steered and cite the command/output that proves the proof route, allowed action, or completion claim still behaves correctly.

## Typical outputs

- selected proof command or inspection route
- claim level covered by that proof
- proof result classification
- `completion_claim_allowed=<true|false>`
- unresolved proof gaps and their owner
