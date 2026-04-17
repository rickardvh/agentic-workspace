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
- Earlier open planning issues still available for intake: `#96` through `#100`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, declarative contract-tooling, and canonical module-reporting tranches are complete; the remaining queue is the bounded workspace CLI hotspot slice followed by the memory trust/usefulness lane.

## Next Candidate Queue
- Highest priority when shared workspace CLI hotspot evidence repeats enough to justify bounded refactoring: Shared workspace CLI hotspot reduction.
  Issues: `#134`
  Why now: the reporting tranche is complete, so the next queue should spend one bounded slice reducing the shared workspace CLI reread hotspot that setup/report dogfooding already preserved as explicit friction evidence.
  Promotion signal: promote after another ordinary-work pass confirms the same hotspot pressure or when one coherent concern can be extracted without changing the workspace/package boundary.
  Suggested first slice: remove one coherent shared concern from `src/agentic_workspace/cli.py` or tighten one helper boundary that lowers reread cost while keeping the root CLI thin.
- Second priority when Memory becomes the main restart or trust bottleneck again: Memory trust, usefulness, and cleanup ergonomics.
  Issues: `#96`, `#97`, `#98`, `#99`, `#100`
  Why later: the new compact memory report now exposes real trust/usefulness follow-through, but the bounded workspace CLI hotspot still sits in front of it as the smaller next slice.
  Promotion signal: promote when the CLI hotspot slice lands or when another ordinary-work pass shows Memory as the primary remaining trust or rediscovery bottleneck.
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
