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

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Environment and recovery guidance contract` | `docs/agent-os-capabilities.md` | Recovery guidance still exists mostly as scattered module-local prose even though environment dead-ends are a recurring cost surface in real use. | The next long-horizon slice should reduce restart or recovery friction, or repeated environment/setup failures appear in dogfooding. |
| `Handoff and execution summary contract` | `docs/agent-os-capabilities.md` | The capability map still treats summaries as supporting infrastructure, but consistent cross-session outcome shape is now important enough to deserve an explicit bounded contract. | A completed slice leaves useful continuation state in chat or ad hoc prose instead of one durable checked-in summary shape. |
| `Planning beta-readiness review` | `docs/maturity-model.md` | Planning is still labeled `alpha`; the repo now needs an explicit review of what still keeps it there and which remaining gaps are real versus historical residue. | The next planning-facing tranche should stabilize contract wording or maturity claims, or another planning regression suggests the maturity label is stale. |
| `Long-horizon doctrine refresh discipline` | `docs/agent-os-capabilities.md`, `docs/ecosystem-roadmap.md`, `docs/maturity-model.md` | This consolidation pass exposed a real maintenance need: doctrine can drift as the system evolves unless there is an explicit review-and-refresh rule. | Another doctrine page starts carrying stale direction, conflicting goals, or implicit backlog residue. |
| `Extension-boundary readiness review` | `docs/extension-boundary.md` | The public extension boundary remains intentionally closed, but the readiness gates now need periodic reality checks so the doc does not become a static promise or a stale blocker. | New plugin/module pressure appears, or first-party module-contract changes materially move one of the readiness gates. |

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
