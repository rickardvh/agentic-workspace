# Roadmap

Last reviewed: 2026-04-08

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.

## Active Handoff

- The roadmap now only tracks bounded future candidates and promotion triggers.
- Stable policy, lifecycle, and ownership guidance live in canonical docs and active execplans.
- Promote work only when it is short enough for a focused execplan and narrow validation lane.

## GitHub Issue Intake

- Latest GitHub issue tranche is landed locally; keep detailed closure history in archived execplans and issue comments, not here.

## Next Candidate Queue

- Plugin-ready capability contract: define first-class capability declarations, lifecycle hook expectations, result schema guarantees, and dependency/conflict metadata so the current first-party boundary can later open without freezing private assumptions as a fake public API. Promote when extension-boundary work needs more than first-party-only wording or when a realistic external-module use case appears.
- Installed-surface ambiguity cleanup: keep tightening repo memory and installed surfaces until the wrong interpretation becomes unnatural, with current focus on the residual package-context overlap/procedure signal in `memory/domains/memory-package-context.md`. Promote when memory doctor still reports that same ambiguity class after another normal maintenance pass.

## Sequencing Recommendation

1. Execute one bounded roadmap candidate at a time with narrow validation and prompt archival.
2. Turn the internal module contract into a plugin-ready capability/dependency/result contract before treating external extension as supported.
3. Keep tightening installed-surface ambiguity, especially in memory, until the cheap path is also the correct path.
4. Preserve review and issue discipline by keeping it quiet, bounded, and cheaper than the confusion it prevents.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
