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

- Latest intake tranche: GitHub issue `#134`.
- Earlier open planning issues still available for intake: `#40`, `#96` through `#100`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, and declarative contract-tooling tranches are complete; the next queue is led by canonical module reporting follow-through, followed by the two bounded dogfood findings from the setup-findings pass.

## Next Candidate Queue
- Highest priority when the setup-findings planning candidate should become real module follow-through: Canonical module reporting surfaces.
  Issues: `#40`
  Why later: the setup-findings dogfood pass surfaced one bounded planning candidate for the next module-reporting slice, and the declarative contract-tooling lane is now complete.
  Promotion signal: promote when shared report work again bottoms out on module-specific state questions that still require raw file reads or when the next reporting slice can stay bounded to one module-owned contract.
  Suggested first slice: tighten one per-module derived report contract rather than broad reporting expansion.
- Second priority when shared workspace CLI hotspot evidence repeats enough to justify bounded refactoring: Shared workspace CLI hotspot reduction.
  Issues: `#134`
  Why later: the setup-findings dogfood pass produced promotable repo-friction evidence for `src/agentic_workspace/cli.py`, but a single hotspot signal should become one bounded cleanup slice rather than a broad rewrite campaign.
  Promotion signal: promote after another ordinary-work pass confirms the same hotspot pressure or when one coherent concern can be extracted without changing the workspace/package boundary.
  Suggested first slice: remove one coherent shared concern from `src/agentic_workspace/cli.py` or tighten one helper boundary that lowers reread cost while keeping the root CLI thin.
- Third priority when Memory becomes the main restart or trust bottleneck again: Memory trust, usefulness, and cleanup ergonomics.
  Issues: `#96`, `#97`, `#98`, `#99`, `#100`
  Why later: this remains important, but the immediate pain is still workspace/planning-side moderation burden and coherence rather than Memory operations alone.
  Promotion signal: promote when Memory again becomes the main restart/trust bottleneck or when one bounded cleanup/usefulness slice can be proved independently of the workspace lane.
  Suggested first slice: start with usefulness audit plus cleanup ergonomics before broader evidence-backed note invalidation.
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
