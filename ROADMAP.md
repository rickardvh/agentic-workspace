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

- Latest open planning tranche: GitHub issue `#98`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, and Memory trust/usefulness/reporting tranches are complete; the remaining queue is the low-friction Memory routing/capture follow-on.

## Candidate Lanes
- Lane: Low-friction Memory routing and capture
  ID: memory-routing-capture-cheap-path
  Priority: first
  Issues: `#98`
  Outcome: make Memory the cheap habitual path in ordinary work by tightening routing and lowering capture/update friction without broad memory browsing.
  Why now: trust/usefulness/reporting is now in place, and live dogfooding shows the remaining gap is still missed routing and sparse cheap capture proof rather than note trust or cleanup visibility.
  Promotion signal: promote when the next bounded slice is ready or when ordinary-work dogfooding still shows Memory being bypassed because route selection or note capture is not the cheapest path.
  Suggested first slice: tighten one or two common missed-note work shapes, add cheap fixture/feedback proof for them, and expose one lower-friction capture/update affordance that does not compete with Planning.
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
