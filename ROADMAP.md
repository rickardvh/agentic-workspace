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

- Latest intake tranche: GitHub issues `#80` through `#88`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Next Candidate Queue
- Priority 1: `Finish the planning state transition by making compact planning state unmistakably primary and prose views unmistakably secondary` from GitHub issue `#86`; promote next and keep `#85` bundled with it because both are about making compact planning state and reporting-first inspection operationally primary.
- Priority 2: `Make reporting and summary surfaces the default inspection path everywhere and demote raw file reads to fallback status` from GitHub issue `#85`; promote with `#86` as one bounded hierarchy-and-routing tranche instead of splitting the same source-of-truth change across two plans.
- Priority 3: `Add a compact operating map so the growing contract surface stays queryable without growing concept overhead` from GitHub issue `#84`; promote after the planning-state and reporting-first hierarchy is stable enough to compress cleanly.
- Priority 4: `Add a compact maintenance rule that new work must come from measured friction or repeated failure, not concept opportunity alone` from GitHub issue `#88`; promote once the next intake or promotion pass can apply the rule immediately.
- Priority 5: `Expand lazy-discovery and curation-cost measurement across real workflows so current compact surfaces are justified by measured savings` from GitHub issue `#87`; promote after the hierarchy/reporting tranche and maintenance guardrail settle so the measurements target the intended steady-state path.
## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
