# Roadmap

Last reviewed: 2026-04-14

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff

- The active queue now owns the live open GitHub issue tranche `#73` through `#79`; roadmap candidates should stay inactive until that queue narrows or closes.

## GitHub Issue Intake

- Latest intake tranche: GitHub issues `#73` through `#79`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Long-Horizon Queue

| Priority | Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- | --- |
| 1 | `Canonical compact planning state and thin views for continuation safety` | GitHub issue `#78` | Smaller models are still being asked to recover too much structure from overloaded planning surfaces, and the current queue drift confirms the state model needs one compact canonical owner. | The active contract/reliability tranche closes and the next implementation pass is ready to rewrite planning state without reopening already-fixed smaller slices. |
| 2 | `Improve closure discipline for bounded smaller-model work` | GitHub issue `#79` | The repo now has compact active and resumable contract projections, but it still lacks a cheap, explicit closure discipline that catches dangling references and unfinished residue before smaller models stop. | Another bounded slice still leaves cleanup residue, or the compact planning-state tranche is ready to add a cheap completion check at the same time. |
| 3 | `Adapter patterns for agent-specific workflow artifacts` | GitHub issue `#73` | Native agent artifacts are a real ecosystem constraint, but the planning state should be compact and canonical before adding sync/adapter affordances around it. | Canonical compact planning state exists and the next follow-on can map runtime-native artifacts into repo-owned thin views without doubling sources of truth. |

## Ongoing Maintenance Expectations

- Keep front-door and default-path surfaces quiet; remove transitional wording, duplicated route descriptions, and fallback explanations once newer defaults prove stable.
- Preserve review and issue discipline by keeping both layers bounded, quiet, and cheaper than the confusion they prevent.
- Treat cheap-agent-safe residue capture as part of the mixed-agent proof work above rather than a separate backlog lane unless it produces a distinct repeated failure class.

## Sequencing Recommendation

1. Prefer proof, refinement, and trust-hardening over new capability invention.
2. Finish the live active issue queue first; do not reopen inactive candidates while `TODO.md` still owns the `#73`-`#79` tranche.
3. After the active queue narrows, treat issues `#78` and `#79` as the highest-priority pair because they define whether smaller models can continue and close work cleanly from compact checked-in state.
4. Treat issue `#73` as the next ecosystem follow-on only after the canonical planning-state contract is stable enough to adapt rather than duplicate.
5. Execute one bounded roadmap candidate at a time with narrow validation, dogfooding, and prompt archival.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
