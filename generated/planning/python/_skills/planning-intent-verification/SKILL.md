---
name: planning-intent-verification
description: Verify original, interpreted, parent, and negative intent before decomposition, validation, or completion claims.
---

# Planning Intent Verification

Use this skill when work may satisfy a narrower proxy than the requested outcome, when a task references parent/lane/epic intent, when negative invariants or non-goals matter, or before claiming completion for planned work.

## Primary Ownership

This skill owns semantic intent satisfaction. It decides whether original, interpreted, parent/larger intent, non-goals, and negative invariants are satisfied, partially satisfied, deferred with owner, rejected, or still blocked.

Route closeout mechanics to `planning-closeout-trust`, broad-work sequencing to `planning-high-assurance-lifecycle`, decomposition structure to `planning-decompose`, and compact state projection to `planning-reporting`.

## Route

1. Inspect the cheapest structured surface first: `agentic-workspace start --target . --task "<task>" --format json`, `agentic-workspace summary --target . --format json`, or `agentic-workspace report --target ./repo --section closeout_trust --format json`.
2. Extract original intent, interpreted local intent, parent or larger intent, non-goals, negative invariants, escalation triggers, and continuation owner from the user request, issue body/comments, active planning record, and relevant repo docs.
3. Compare the intended outcome to the proposed or delivered slice. Classify it as satisfied, partially satisfied, unsatisfied, deferred-with-owner, or escalation-required.
4. Keep proof separate from intent. Passing validation proves behavior, not task/lane/epic satisfaction by itself.
5. Before closeout, require explicit evidence for parent/larger intent satisfaction and for each negative invariant being satisfied, deferred, or rejected.
6. If CLI output exposes `next_safe_action`, preserve its forbidden actions, `completion_claim_allowed`, proof boundary, module slot, and fallback behavior.

## Completion Claims

Completion is not allowed when any of these are true:

- the delivered slice proves only a narrower proxy;
- parent/larger intent is open, stale, or unreconciled;
- negative invariants are present but not satisfied, deferred, or rejected;
- external issue evidence is missing or older than the local closeout claim;
- a continuation owner is required but not recorded;
- the next-safe-action packet forbids completion.

## Fallback

If the CLI is unavailable, read only the active planning record or issue text needed to answer the same fields. Do not mutate managed planning state by hand unless the package lifecycle command is unavailable and the user explicitly asked for recovery.
