# Roadmap

Last reviewed: 2026-04-09

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff
- No active handoff right now.
## GitHub Issue Intake

- Latest GitHub issue tranche is landed locally; keep detailed closure history in archived execplans and issue comments, not here.

## Next Candidate Queue

- `Archive cleanup follow-through for active execplan pointers` - promote when normal archive flow still requires manual TODO pre-cleanup for an active item that points at the plan being archived
  - Why: dogfooding still shows `archive-plan --apply-cleanup` failing closed when the standard active TODO pointer exists
  - First slice: make archive cleanup remove or rewrite the normal active TODO pointer before blocking on the same reference, while preserving explicit fail-closed behavior for unrelated residue

## Sequencing Recommendation

1. Execute one bounded roadmap candidate at a time with narrow validation and prompt archival.
2. Preserve review and issue discipline by keeping it quiet, bounded, and cheaper than the confusion it prevents.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
