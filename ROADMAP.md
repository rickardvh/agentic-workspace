# Roadmap

Last reviewed: 2026-04-13

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

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Planning beta surface alignment` | `docs/maturity-model.md`, `README.md`, `packages/planning/README.md` | The planning contract is now documented as `beta` in the maturity model, but at least one front-door surface still presents planning as `alpha`, which weakens the one-home-per-concern and trustworthy-surface goals. | Another public-facing surface disagrees on planning maturity or contract status, or the next maintainer/docs pass touches planning front-door messaging anyway. |
| `Selective-adoption proof refresh` | `docs/design-principles.md`, `docs/ecosystem-roadmap.md`, `docs/extension-boundary.md` | Selective adoption is a core product requirement, but most current proof still comes from this monorepo's well-understood Memory + Planning pair rather than a fresh bounded check of memory-only, planning-only, and combined adoption quality. | Another adoption-related friction pass, lifecycle review, or maintainer question shows that selective-adoption confidence is starting to rely on doctrine more than recent evidence. |
| `Portability evidence review` | `docs/design-principles.md`, `docs/agent-os-capabilities.md`, `docs/ecosystem-roadmap.md` | The doctrine emphasizes portability and cheaper restart outside this repo, but the strongest evidence is still dogfooding here. A bounded review should identify which current contracts are genuinely portable and which still depend too much on monorepo familiarity. | Repeated adopter-facing questions appear, another repo tries the stack, or new features start leaning on assumptions that are only cheap inside this monorepo. |
| `Generated-surface trust follow-through` | `docs/design-principles.md`, `docs/agent-os-capabilities.md`, `docs/generated-surface-trust.md` | Generated routing and maintainer surfaces are now central to cheap startup, so any remaining drift between canonical docs, generated mirrors, and front-door messaging is directly on the path to the long-term trustworthiness goal. | Another docs/generated-surface mismatch appears, or a maintainer pass finds that generated surfaces are no longer the cheapest trustworthy startup path. |

## Sequencing Recommendation

1. Prefer evidence-generating candidates before new capability invention: close consistency drift, refresh selective-adoption proof, and test portability claims before opening larger ecosystem scope.
2. Execute one bounded roadmap candidate at a time with narrow validation and prompt archival.
3. Preserve review and issue discipline by keeping it quiet, bounded, and cheaper than the confusion it prevents.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
