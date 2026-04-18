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

- Latest open planning tranche: GitHub issues `#146`-`#178`, grouped below into ordered inactive candidate lanes.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The simplification, improvement-latitude, iterative follow-through, optimization-bias, setup-findings, standing-intent, planning-surface-clarity, planner-worker orchestrator workflow, declarative contract-tooling, canonical module-reporting, bounded workspace CLI hotspot, native candidate-lane, workspace-self-adaptation/friction-order, and Memory trust/usefulness/routing/capture tranches are complete.

## Candidate Lanes

- Lane: Validation friction as repo-friction evidence
  ID: validation-friction-repo-friction
  Priority: first
  Issues: #175
  Outcome: treat hard-to-validate work as explicit repo-friction evidence when proof lanes, tranche boundaries, or safe validation scope are still unclear after the compact proof path.
  Why later: wait until repeated dogfooding shows that validation choice remains the dominant friction class after the workspace-self-adaptation lane has settled.
  Promotion signal: promote when repeated dogfooding shows that the hardest part of a task is still choosing the narrowest safe proof lane or validation boundary rather than implementing the change itself.
  Suggested first slice: define validation-friction operationally, distinguish it from ordinary test work, and decide how it should appear in the existing repo-friction report path.

- Lane: Memory trust and habitual pull
  ID: memory-trust-habitual-pull
  Priority: third
  Issues: #146, #150, #157, #158, #159
  Outcome: prove Memory is a cheap habitual path for ordinary work and clarify its boundary with other standing guidance.
  Why later: wait until the planning recovery path stops shifting so Memory can converge against a stable operating contract.
  Promotion signal: promote when the repo can show a clear remaining bypass reason or a bounded final follow-through slice.
  Suggested first slice: audit ordinary-work cases to separate real consultation from hypothetical usefulness.

- Lane: Portable declarative contracts beyond Python CLI
  ID: portable-declarative-contracts-beyond-python-cli
  Priority: fourth
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
