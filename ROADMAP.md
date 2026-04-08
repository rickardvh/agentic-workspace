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

- Landed: Issue #2, tracker-agnostic upstream task ingestion into checked-in planning. The intake contract now lives in `docs/upstream-task-intake.md` and archived planning history.
- Remaining: Issue #7, make the workspace orchestrator the sole normal public lifecycle entrypoint through a generic module contract. This is a real roadmap candidate and the clearest new architecture-level intake item.
- Remaining: Issue #6, define a canonical review portfolio for finding high-value follow-up work. The repo already has a shipped review lane and promotion threshold, so the remaining question is whether the issue still implies a broader review-matrix contract beyond the current first slice.
- Landed locally: Issue #5, tighten `memory/current/` so it cannot be mistaken for active planning authority. The weak-authority current-note contract and the remaining high-level framing tail are now implemented in shipped memory surfaces and archived planning history.
- Landed locally: Issue #3 and Issue #4, clarify `recurring-failures` as anti-trap memory rather than bug tracking. The duplicate recurring-failures wording signal has now landed as one bounded memory-contract slice.

## Next Candidate Queue

- Workspace-first module lifecycle contract: make `agentic-workspace` the sole normal public lifecycle entrypoint through a generic module capability and reporting contract, while keeping module lifecycle implementation package-local. Source: GitHub issue `#7`. Promote when lifecycle/platform work resumes or before another first-party or third-party module is added.
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
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
