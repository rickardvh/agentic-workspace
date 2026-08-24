---
name: planning-high-assurance-lifecycle
description: Route broad or high-assurance work across its canonical planning, assignment, proof, intent, and closeout owners.
---

# Planning High-Assurance Lifecycle

Use this umbrella route when work is broad, multi-lane, high-assurance,
cross-boundary, or likely to grow beyond an initially bounded slice. When
enabled-AW startup routes here, establish Planning custody before
implementation.

## Primary Ownership

This skill is the routing wrapper and owns lifecycle sequencing only. It does
not own decomposition semantics, assignment selection, dispatch,
returned-result admission, integration, proof interpretation, intent
satisfaction, or closeout mechanics.

## Route

1. Start from the compact current decision and active Planning summary.
2. Route intent and parent/lane/slice shaping to `planning-decompose`; tighten a
   newly created bounded execplan through `planning-new-plan-tighten`.
3. When the canonical assignment owner names unresolved assurance input, route
   that pre-decision assessment to `planning-assurance-delegation` and return
   its evidence to the assignment owner.
4. Follow the resulting structured assignment state:
   - selected-current-target work continues through the ordinary direct-work
     owner without loading `planning-orchestrator-workflow`;
   - a binding non-local assignment for an assigned orchestrator routes to
     `planning-orchestrator-workflow`;
   - missing, stale, tied, or unsafe assignment state returns to the exact
     shaping, probe, repair, override, or human-decision action named by the
     current decision.
5. Route manual transport to `planning-manual-delegation` and delegated returns
   to `planning-returned-result`; do not duplicate their procedures here.
6. Route validation to AW-owned proof, semantic satisfaction to
   `planning-intent-verification`, and closeout mechanics and residue
   distillation to `planning-closeout-trust`.

## Stop Conditions

Stop at the owning phase instead of coding when intent, decomposition,
assignment identity/revision, work bounds, or proof requirements are missing or
stale. Never use this umbrella route to bypass a binding assignment or to infer
completion from a narrower phase result.

## Output Contract

Report the active planning owner, current phase owner, assignment/action
identity when present, bounded result or blocker, AW proof status, semantic
intent status, closeout status, and routed continuation residue.
