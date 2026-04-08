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

Prioritized from the latest GitHub issue set:

- P1: Issue #2, tracker-agnostic upstream task ingestion into checked-in planning. This is the clearest product-gap item because it defines how external tasks become repo-native execution without making GitHub Issues the authority.
- P2: Issue #5, tighten `memory/current/` so it cannot be mistaken for active planning authority. This is a contract-risk item that affects restart safety and should stay close behind the intake contract work.
- P3: Issue #6, define a canonical review portfolio for finding high-value follow-up work. This overlaps the existing review-driven roadmap items and should be folded into that tranche instead of drifting as an open-ended review idea.
- P4: Issue #3 and Issue #4, clarify `recurring-failures` as anti-trap memory rather than bug tracking. These are duplicates in substance and should be consolidated into one memory contract follow-up.

## Next Candidate Queue

- Legacy-adopter migration fixtures: add migration fixtures representing older standalone installs, partial conversions, and stale residue so the tools can detect, warn about, and upgrade legacy adopter repos without leaving them in an incomplete state. Promote before the next bootstrap release for outside adopters or when another migration failure appears. (friction-confirmed, high-confidence)
- Review-finding promotion threshold: define when repeated review findings or repeated dogfooding friction should graduate from review or memory capture into `ROADMAP.md`, `TODO.md`, or an execplan so agents do not oscillate between over-eager direct fixes and under-reacting to repeated product deficiencies. Promote when repeated repo-local product friction is captured more than once without a clear activation rule. (mixed, medium-confidence)
- Review-driven future-work discovery: formalize a deliberate planning lane for bounded review passes, review artifacts, explicit source/confidence labels, and promotion rules that keep analysis-derived findings lower-trust than friction-derived improvement signals until confirmed. Promote when agent-driven future-work discovery needs a canonical contract instead of ad hoc review notes.
- Contract-integrity review mode: add a canonical review mode for broken references, missing canonical surfaces, docs-code drift, promise-vs-enforcement gaps, and planning-surface coherence so agents can detect repo claims that future contributors would reasonably trust but the checked-in surfaces do not consistently uphold. Promote when the same class of contract drift appears again or current maintainer guidance remains misleading.
- Maintainer-surface consistency hardening: keep maintainer-facing docs, referenced canonical files, and actual check wiring aligned, including the source/payload/root-install boundary path and any generated-surface or lifecycle claims. Promote when docs reference missing canonical surfaces, command docs overclaim enforcement, or check aggregation drifts from the documented maintainer contract.
- Composition contract hardening: define how modules interact, compose presets, and share lifecycle reporting without blurring ownership. Promote when future composition work needs a stable contract.
- Extension boundary design: define the public plugin or external-module contract only after first-party module assumptions have stabilized. Promote when external use becomes a product need.
- Shared tooling extraction: evaluate a common checker core when duplicated maintenance drag remains a real cost after the lifecycle and adoption phases settle. Promote when duplicated checker and renderer maintenance remains a higher cost than unresolved product-contract ambiguity.

## Sequencing Recommendation

1. Make the workspace lifecycle the default entrypoint.
2. Formalize the internal module contract.
3. Harden ownership boundaries as enforceable platform rules.
4. Stabilize memory and planning as boring first-party modules.
5. Add review-driven future-work discovery and promotion rules.
6. Add registry and capability-driven orchestration.
7. Make composition first-class.
8. Add new first-party modules only through the module contract.
9. Design the plugin boundary.
10. Prove the platform externally.
11. Publish the ecosystem as a stable modular platform.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
