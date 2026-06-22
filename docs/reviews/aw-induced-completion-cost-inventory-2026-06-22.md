# AW-Induced Completion Cost Inventory

Date: 2026-06-22

Scope: dogfooding issues #1680, #1684, #1686, and #1687.

## Landed Reductions

| Issue | Cost type | Owner surface | Before | After |
| --- | --- | --- | --- | --- |
| #1684 | repair churn, planning residue | Planning closeout | `planning closeout` could mutate proof and closeout fields before archive validation discovered an existing continuation conflict. | Closeout preflights structured continuation state before mutation and exits with a next safe action when archive-and-close is incompatible. |
| #1686 | stale proof, validation time | Workspace proof selection | Host subsystem proof could require an executable inventory sweep for a retired/deleted test path. | Proof selection downgrades commands with absent path-like arguments to unavailable proof and keeps them out of required commands. |
| #1687 | planning residue, intent repair | Planning promotion | External-intent candidates with generic outcome/reason text promoted into generic execplan intent. | Promotion preserves specific source outcomes and replaces known generic scaffold fallbacks with structured issue ref/title intent. |

## Closure Boundary

This closes the small dogfooding lane by removing three concrete sources of AW-induced completion cost while preserving safety gates:

- proof remains required, but stale deleted-test sweeps are not treated as runnable required proof;
- Planning closeout still blocks dishonest full closure, but does so before mutating records;
- promoted plans still require agent review, but issue-specific intent is carried into the canonical record when available.

Remaining broader completion-cost work should stay in external-agent evaluation and ordinary-loop noise issues rather than being claimed by this lane.
