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

- Latest intake tranche: GitHub issue `#135`.
- Earlier open planning issues still available for intake: `#96` through `#100`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, declarative contract-tooling, canonical module-reporting, and bounded workspace CLI hotspot tranches are complete; the remaining queue is the native candidate-lane planning gap followed by the memory trust/usefulness lane.

## Next Candidate Queue
- Highest priority when the ad hoc roadmap queue shape itself becomes the next planning friction: Native candidate-lane queue for deferred grouped work.
  Issues: `#135`
  Why now: the roadmap just carried another grouped deferred lane through ad hoc queue structure, which confirms the planning-system gap and makes this the smallest next slice with immediate dogfooding value.
  Promotion signal: promote when one thin native shape can capture grouped deferred lanes without turning planning into a backlog system.
  Suggested first slice: inventory what the current roadmap queue is expressing beyond existing planning shapes, define the minimum candidate-lane fields, and translate the remaining memory lane into that native form.
- Second priority when Memory becomes the main restart or trust bottleneck again: Memory trust, usefulness, and cleanup ergonomics.
  Issues: `#96`, `#97`, `#98`, `#99`, `#100`
  Why later: the new compact memory report now exposes real trust/usefulness follow-through, but the planning-system gap around grouped deferred work has become the smaller next slice with immediate repo-native payoff.
  Promotion signal: promote when the native candidate-lane slice lands or when another ordinary-work pass shows Memory as the primary remaining trust or rediscovery bottleneck.
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
