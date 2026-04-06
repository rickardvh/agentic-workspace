# Roadmap

Last reviewed: 2026-04-06

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.

## Active Handoff

- The roadmap now only tracks bounded future candidates and promotion triggers.
- Stable policy, lifecycle, and ownership guidance live in canonical docs and active execplans.
- Promote work only when it is short enough for a focused execplan and narrow validation lane.

## Next Candidate Queue

- Composition contract hardening: define how modules interact, compose presets, and share lifecycle reporting without blurring ownership. Promote when future composition work needs a stable contract.
- Extension boundary design: define the public plugin or external-module contract only after first-party module assumptions have stabilized. Promote when external use becomes a product need.
- Shared tooling extraction: evaluate a common checker core when duplicated maintenance drag remains a real cost after the lifecycle and adoption phases settle. Promote when duplicated checker and renderer maintenance remains a higher cost than unresolved product-contract ambiguity.

## Sequencing Recommendation

1. Make the workspace lifecycle the default entrypoint.
2. Formalize the internal module contract.
3. Harden ownership boundaries as enforceable platform rules.
4. Stabilize memory and planning as boring first-party modules.
5. Add registry and capability-driven orchestration.
6. Make composition first-class.
7. Add new first-party modules only through the module contract.
8. Design the plugin boundary.
9. Prove the platform externally.
10. Publish the ecosystem as a stable modular platform.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
