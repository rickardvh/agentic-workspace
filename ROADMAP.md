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

- Latest intake tranche: GitHub issue `#127`.
- Earlier open planning issues still available for intake: `#40`, `#92` through `#100`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, and optimization-bias tranches are complete; the next queue is led by setup/jumpstart findings promotion.

## Next Candidate Queue
- Highest priority when setup/jumpstart findings need a durable promotion path: Agent-produced setup and jumpstart findings promotion.
  Issues: `#127`
  Why later: important for keeping the product lightweight and analysis-friendly, but it benefits from first deciding how repo-friction evidence and planning residue should be represented.
  Promotion signal: promote after the first repo-friction evidence shape exists or when a jumpstart/setup pass produces findings that are clearly useful but currently have no durable promotion contract.
  Suggested first slice: define one bounded promotion contract for setup/jumpstart findings worth preserving into planning, memory, or workspace evidence.
- Second priority when the near-term contract shapes stabilize enough to extract them safely: Declarative contract inventory and schemas.
  Issues: `#92`, `#93`, `#94`, `#95`
  Why later: still valuable, but less urgent than the current product-shaping friction lane and should follow once the near-term contract shapes settle.
  Promotion signal: promote when the near-term contract shapes have stabilized enough that extracting schemas or manifests would reduce drift instead of freezing churn.
  Suggested first slice: inventory Python-owned contract answers, then choose one small shared schema/manifests slice instead of broad extraction.
- Third priority when Memory becomes the main restart or trust bottleneck again: Memory trust, usefulness, and cleanup ergonomics.
  Issues: `#96`, `#97`, `#98`, `#99`, `#100`
  Why later: this remains important, but the immediate pain is still workspace/planning-side moderation burden and coherence rather than Memory operations alone.
  Promotion signal: promote when Memory again becomes the main restart/trust bottleneck or when one bounded cleanup/usefulness slice can be proved independently of the workspace lane.
  Suggested first slice: start with usefulness audit plus cleanup ergonomics before broader evidence-backed note invalidation.
- Fourth priority when shared reporting still bottoms out on raw module reads: Canonical module reporting surfaces.
  Issues: `#40`
  Why later: partially addressed by the newer shared report work, but still open as a follow-on once the higher-priority planning/workspace lanes stabilize.
  Promotion signal: promote when shared report work again bottoms out on module-specific state questions that still require raw file reads.
  Suggested first slice: tighten one per-module derived report contract rather than broad reporting expansion.
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
