# Roadmap

Last reviewed: 2026-04-14

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff
- No active handoff right now.
## GitHub Issue Intake

- Latest intake tranche: GitHub issues `#25` through `#34`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Highest Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Minimal resumable execution contract` | GitHub issue `#34`; compact intent-contract follow-through | The compact intent contract now preserves the requested end state cheaply, but restart still benefits from one smaller active slice that also carries current next action and proof in the minimum checked-in form. This is the clearest next token-efficiency and continuity win. | Ordinary work still needs more than one compact checked-in slice to recover current intent, current next action, proof, and escalation boundaries safely after a restart. |

## Second Priority Queue

- No remaining second-priority candidates right now.

## Third Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Cross-agent workflow robustness hardening` | Archived execplan `docs/execplans/archive/cross-agent-workflow-robustness-hardening-2026-04-13.md`; mixed-agent dogfooding feedback | The first machine-readable hardening slice landed, but the broader goal stays open until future mixed-agent passes show startup routing, package-managed paths, and same-pass planning cleanup are no longer missed in ordinary use. | Another mixed-agent pass still misses startup routing, package-managed paths, or same-pass planning cleanup after the current machine-readable hardening slice. |

## Ongoing Maintenance Expectations

- Keep front-door and default-path surfaces quiet; remove transitional wording, duplicated route descriptions, and fallback explanations once newer defaults prove stable.
- Preserve review and issue discipline by keeping both layers bounded, quiet, and cheaper than the confusion they prevent.
- Treat cheap-agent-safe residue capture as part of the mixed-agent proof work above rather than a separate backlog lane unless it produces a distinct repeated failure class.

## Sequencing Recommendation

1. Prefer proof, refinement, and trust-hardening over new capability invention.
2. The first proof tranche is now complete: bounded dogfooding, synergy proof, external-agent handoff trust, selective adoption, and first-party portability all have current evidence.
3. The next promotion after the compact intent-contract slice should come from the resumable-execution lane if the first slice proves its contract cheaply in ordinary repo work.
4. Execute one bounded roadmap candidate at a time with narrow validation and prompt archival.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
