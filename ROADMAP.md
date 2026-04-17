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

- Latest open planning tranche: GitHub issues `#137`-`#159`, grouped below into ordered inactive candidate lanes.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, standing-intent, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, and Memory trust/usefulness/routing/capture tranches are complete.

## Candidate Lanes

- Lane: Workspace optimization bias and setup findings
  ID: workspace-optimization-bias-findings
  Priority: first
  Issues: #148, #149, #151, #152, #153, #154, #155, #156
  Outcome: integrate optimization bias and setup or jumpstart findings into normal repo operation without adding a second analysis framework.
  Why later: wait until planning routing and standing-intent surfaces are settled so the reporting path has a stable target.
  Promotion signal: promote when repeated dogfooding shows the bias and findings path is still hidden, noisy, or too hard to recover.
  Suggested first slice: surface the effective optimization bias in the compact normal recovery path.

- Lane: Memory trust and habitual pull
  ID: memory-trust-habitual-pull
  Priority: second
  Issues: #146, #150, #157, #158, #159
  Outcome: prove Memory is a cheap habitual path for ordinary work and clarify its boundary with other standing guidance.
  Why later: wait until the planning and standing-intent paths stop changing so memory can converge against a stable contract.
  Promotion signal: promote when the repo can show a clear remaining bypass reason or a bounded final follow-through slice.
  Suggested first slice: audit ordinary-work cases to separate real consultation from hypothetical usefulness.

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
