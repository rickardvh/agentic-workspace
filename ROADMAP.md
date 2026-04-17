# Roadmap

Last reviewed: 2026-04-17

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff
- No active handoff right now.
## GitHub Issue Intake

- Latest open planning tranche: GitHub issues `#96` through `#100`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, and native candidate-lane tranches are complete; the remaining queue is the Memory trust/usefulness lane.

## Candidate Lanes
- Lane: Memory trust, usefulness, and cleanup ergonomics
  ID: memory-trust-usefulness-cleanup
  Priority: first
  Issues: `#96`, `#97`, `#98`, `#99`, `#100`
  Outcome: make Memory cheaper to trust, inspect, clean up, and prove useful in ordinary restart-heavy work.
  Why now: the planning-system gap around grouped deferred work is now closed, so Memory is the main remaining restart and trust bottleneck in the roadmap.
  Promotion signal: promote when the next bounded slice is ready or when another ordinary-work pass shows Memory as the primary remaining trust or rediscovery bottleneck.
  Suggested first slice: start with evidence-backed note trust states and cleanup/usefulness reporting on top of the new memory module report rather than widening immediately into automatic invalidation.
## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For new contract surfaces, require the promotion note to name the older path it replaces, merges, or materially simplifies.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Prefer measured friction, repeated failure, repeated dogfooding pain, or explicit maintainer override over concept opportunity when deciding whether new work belongs in planning at all.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
