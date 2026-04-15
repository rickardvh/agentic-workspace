# Roadmap

Last reviewed: 2026-04-15

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff
- No active handoff right now.
## GitHub Issue Intake

- Latest intake tranche: GitHub issues `#92` through `#95`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.
- The broader multi-runtime and lifecycle-extraction ideas in `contract-tooling-roadmap.md` are not yet promoted beyond this first bounded tranche.

## Next Candidate Queue
- `#92` Declarative contract boundary and Python-owned behavior inventory; promote when the first contract-tooling tranche is selected and the repo is ready to classify current proof/report/selector/lifecycle behavior before extracting any schemas.
- `#93` Shared schemas for proof, report, and selector contracts; promote after `#92` lands and the boundary note shows a stable declarative subset ready for versioned schemas.
- `#94` Manifest-backed extraction for proof, report, and selector metadata; promote when `#92` and `#93` have made the contract stable enough that Python can consume checked-in metadata without changing user-visible behavior.
- `#95` Schema and manifest validation for contract-backed surfaces; promote when shared schemas or manifests exist and drift checks can fail fast without widening adopter/runtime requirements.
## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Prefer measured friction, repeated failure, repeated dogfooding pain, or explicit maintainer override over concept opportunity when deciding whether new work belongs in planning at all.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
