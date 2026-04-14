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

- Latest intake tranche: GitHub issues `#25` through `#32`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Highest Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Compact queryable contract profile for lazy discovery` | GitHub issue `#29`; `docs/design-principles.md`; `src/agentic_workspace/cli.py` | The next direct efficiency gain is not more structured output in general but making contract discovery truly lazy: one proof answer, one ownership answer, one escalation answer, one next-action answer. That is now the clearest product-level way to reduce rereading and help weaker or cheaper agents act safely with less context. | Another ordinary task or mixed-agent handoff still requires loading broad defaults, proof, ownership, or handoff output just to answer one bounded operating question. |
| `Narrow query selectors for machine-readable surfaces` | GitHub issue `#30`; `agentic-workspace defaults --format json`; `agentic-workspace proof --format json`; `agentic-workspace ownership --format json` | The current machine-readable front door is much stronger, but agents still often have to load broad objects and filter them mentally. Narrow selectors are the most concrete next slice for turning the lazy-discovery goal into cheaper routine retrieval. | Another proof, ownership, startup, or handoff query still needs a whole-surface dump instead of one narrow structured answer. |

## Second Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Delegated-judgment practical follow-through` | GitHub issue `#25`; `docs/delegated-judgment-contract.md`; `docs/execplans/README.md` | Delegated judgment is now good on paper; the next work is proving it in repeated real workflows and tightening places where agents still silently widen ends, fail to escalate, or need too much user steering to stay bounded. | Another delegated task shows ambiguity around local latitude, escalation boundaries, or requested-end preservation. |
| `External-agent handoff polish` | GitHub issue `#27`; `llms.txt`; `.agentic-workspace/bootstrap-handoff.md`; `README.md` | External-agent handoff surfaces are strong additions, but they still need proof that they are foolproof in use: no installed-CLI assumptions, no ambiguity about target repo versus this repo, and no drift between the README prompt, raw handoff file, and actual bootstrap behavior. | Another external-agent or cold-start pass shows ambiguity between docs, handoff files, and live bootstrap behavior. |
| `Compact structured handoff artifacts` | GitHub issue `#31`; `llms.txt`; `.agentic-workspace/bootstrap-handoff.md`; `docs/workspace-config-contract.md` | The repo now has useful prose handoff surfaces, but strong-planner and cheap-implementer collaboration still pays too much narration cost. A compact structured sibling artifact is the next likely way to preserve intent, proof, and escalation boundaries more cheaply across agents and sessions. | Another mixed-agent handoff needs broad prose rereading to recover scope, proof, escalation triggers, or hard boundaries. |

## Third Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Token-cost and lazy-discovery measurements` | GitHub issue `#32`; `docs/design-principles.md`; future compact-contract proof work | Compactness work should be justified by less reading, not only cleaner structure. A small measurement framework will become more valuable once the next lazy-discovery slice is concrete enough to audit. | A compact-contract or narrow-selector slice lands and needs repeatable evidence that it reduced discovery and restart cost rather than just improving schema neatness. |
| `Configurable canonical agent-instructions filename` | GitHub issue `#28`; `AGENTS.md`; `agentic-workspace.toml`; bootstrap/adopt lifecycle docs | Cross-agent compatibility should not depend forever on a hard-coded `AGENTS.md` assumption, but the repo already has one-home startup discipline and the immediate pressure is still cheaper retrieval and handoff. This is worth keeping visible without pulling it ahead of current efficiency and trust work. | Another adoption or bootstrap pass shows avoidable friction because an existing repo already uses a different canonical startup filename and safe preservation is not possible. |
| `Cross-agent workflow robustness hardening` | Archived execplan `docs/execplans/archive/cross-agent-workflow-robustness-hardening-2026-04-13.md`; mixed-agent dogfooding feedback | The first machine-readable hardening slice landed, but the broader goal stays open until future mixed-agent passes show startup routing, package-managed paths, and same-pass planning cleanup are no longer missed in ordinary use. | Another mixed-agent pass still misses startup routing, package-managed paths, or same-pass planning cleanup after the current machine-readable hardening slice. |
| `Conservative automatic policy selection follow-through` | GitHub issue `#27`; `agentic-workspace.toml`; `llms.txt` | The workspace should keep reducing required user input, but only where inference is safe. The next refinement is proving when to install, adopt, emit review-required handoff, or preserve repo-owned surfaces aggressively. | Another bootstrap or adoption pass shows policy inference is either too eager or not explicit enough about review-required boundaries. |

## Ongoing Maintenance Expectations

- Keep front-door and default-path surfaces quiet; remove transitional wording, duplicated route descriptions, and fallback explanations once newer defaults prove stable.
- Preserve review and issue discipline by keeping both layers bounded, quiet, and cheaper than the confusion they prevent.
- Treat cheap-agent-safe residue capture as part of the mixed-agent proof work above rather than a separate backlog lane unless it produces a distinct repeated failure class.

## Sequencing Recommendation

1. Prefer proof, refinement, and trust-hardening over new capability invention.
2. The first proof tranche is now complete: bounded dogfooding, synergy proof, external-agent handoff trust, selective adoption, and first-party portability all have current evidence.
3. Next promotions should come first from the highest-priority lazy-discovery and narrow-retrieval lanes, then from delegated-judgment and external-handoff trust follow-through.
4. Execute one bounded roadmap candidate at a time with narrow validation and prompt archival.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
