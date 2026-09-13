---
name: workspace-proof-selection
description: Select and interpret proof for a routed claim level. Use when validation evidence, skips, warnings, retries, crashes, or negative proof need proof-specific interpretation.
---

# Workspace Proof Selection

This is a package-managed workspace skill installed under `.agentic-workspace/skills/`.

Use it after the main AW operating skill or compact router points at proof selection. It is not a test-running checklist or a general completion policy; it decides what evidence is meaningful for the claim being made.

## Workflow

1. Identify the claim level:
   - task
   - bounded slice
   - lane
   - epic
   - regression guard
2. Resolve with the configured AW invocation:
   `start --target . --task "<task>" --changed <path> --format json`.
   Repeat `--changed` for each known path; omit it when no paths are known.
   Read `decision_packet` first, then the current Verification strategy and
   owner-returned requests. Preserve any selected Planning subject and blockers.
   Supply only bounded answers in the returned request through
   `start --input <request.json>` with the same context. Execute only the returned
   `primary_action` through `invoke --input <action.json>`, then use its current
   continuation or exact re-entry. Effect outcome and continuation availability
   are separate; continuation failure never authorizes retrying a committed effect.
   Source-read and other prerequisite requests may be combined in an array.
   An unavailable proof route remains an owner gap; retired commands are not a fallback.
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
5. Report proof adequacy separately from completion permission:
   - proof can support the claim level only when it covers the changed behavior and requested intent
   - proof is insufficient when it is missing, stale, too narrow, skipped without justification, or contradicts the intended outcome
   - completion permission still belongs to the routed closeout/claim boundary, not this subskill alone
6. Route gaps instead of hiding them:
   - run the missing focused proof
   - report the bounded proof without substituting it for the requested completion
   - update the active plan with the gap
   - open or link follow-up work when the gap belongs outside the slice

## Current native judgments

For instruction checks, select the current `verification.execution_requests`
command and consume its native receipt. Named and inline checks share the existing
Verification producer; a check pass does not satisfy source reconciliation.

For resulting-work consistency, use the exact
`verification.source_reconciliation.requests` material request and supply
`updated` or `reviewed-current` with a reason for each named source. Verification
requests an exact human confirmation unless a current explicit policy grant
already authorizes the acting agent for the exact source/work path set.

For semantic claim sufficiency, use `verification.claim_review.request` with the
current evidence refs and the bounded judgment/reason. Return its exact authorized
answer; inspect remaining claim blockers. Preserve the answer in ordinary caller
carriage only while current; a fresh consumer revalidates postimages, strategy,
evidence and policy. This is not independent-review admission or authority to
close unfinished Planning work. Missing required reviewer custody remains a gap.

## Guardrails

- Red flag: Tests passed, so completion is claimable.
- Use instead: Admit current proof through Verification, inspect `decision_packet.claim_boundary`, and reconcile remaining intent before claiming completion.
- A manually reported result is an interoperability observation, not authenticated native execution. A command receipt does not grant task judgment, independent review or completion.
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
