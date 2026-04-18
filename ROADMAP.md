# Roadmap

Last reviewed: 2026-04-18

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff

- No active handoff right now.

## GitHub Issue Intake

- Latest open planning tranche: GitHub issues `#161`-`#170`, grouped below into ordered inactive candidate lanes.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, standing-intent, planning-surface-clarity, planner-worker orchestrator workflow, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, workspace-self-adaptation/friction-order, repo-directed improvement evidence-threshold, validation-friction repo-friction, config-driven execution posture, config-driven autonomy and agnostic improvements, Memory trust/usefulness/routing/capture, and Memory trust/habitual-pull tranches are complete.

## Candidate Lanes

- Lane: Portable declarative contracts beyond Python CLI
  ID: portable-declarative-contracts-beyond-python-cli
  Priority: first
  Issues: #161, #166, #167, #168, #169, #170
  Outcome: move stable lifecycle and runtime truth toward declarative portable contract sources so Python remains a strong reference implementation rather than the only credible operational embodiment.
  Why later: wait until the current planning/reporting lanes settle so the next declarative extraction tranche targets stable truths rather than moving boundaries.
  Promotion signal: promote when the repo can name one stable next extraction target or a clear portable architecture/tool-selection rule without inventing a bespoke workflow language.
  Suggested first slice: inventory which truths still live mainly in Python, define the declarative/procedural/generated-layer boundary, and pick the next bounded extraction target only where stability is proven.

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
