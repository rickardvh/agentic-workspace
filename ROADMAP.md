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

- Latest intake tranche: GitHub issues `#25` through `#27`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Highest Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Strong-planner / cheap-implementer dogfooding` | GitHub issue `#25`; `docs/delegated-judgment-contract.md`; `docs/agent-os-capabilities.md` | Current cost pressure makes mixed-agent proof the highest-value evidence track: a stronger planner writes or sharpens the contract, a cheaper model executes the bounded slice, and escalation happens only at explicit delegated-judgment boundaries. | Another real task is ready to be run end-to-end through a strong-planner / cheap-implementer handoff, or repeated local work shows the checked-in surfaces still leave too much ambiguity for weaker implementers. |
| `Repeated ordinary-use proof of Memory/Planning synergy` | GitHub issue `#25`; `docs/default-path-contract.md`; `docs/agent-os-capabilities.md` | The combined-install contract is strong on paper, but it still needs repeated ordinary-work proof that Memory shortens plans, restart uses the smallest useful bundle, residue promotes out of Planning cleanly, and combined installs reduce restart cost more than either module alone. | Another ordinary task completes with both modules installed, or repeated plan restatement and restart friction suggest the synergy claim is relying on doctrine more than fresh evidence. |
| `Selective-adoption proof refresh` | GitHub issue `#25`; `docs/design-principles.md`; `docs/ecosystem-roadmap.md`; `docs/extension-boundary.md` | Selective adoption is a core product requirement, but recent proof is still too tied to this monorepo's well-understood combined install rather than a fresh bounded check of memory-only, planning-only, and combined adoption quality. | Another adoption-related friction pass, lifecycle review, or maintainer question shows that selective-adoption confidence is starting to rely on doctrine more than recent evidence. |
| `Portability evidence review` | GitHub issue `#25`; `docs/design-principles.md`; `docs/agent-os-capabilities.md`; `docs/ecosystem-roadmap.md` | The doctrine emphasizes portability and cheaper restart outside this repo, but the strongest evidence is still dogfooding here. A bounded review should identify which current contracts are genuinely portable and which still rely too much on local familiarity. | Repeated adopter-facing questions appear, another repo tries the stack, or new features start leaning on assumptions that are only cheap inside this monorepo. |

## Second Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Cross-agent handoff quality audit` | GitHub issue `#25`; `llms.txt`; `.agentic-workspace/bootstrap-handoff.md`; `docs/default-path-contract.md` | The repo now needs repeated evidence that intent, active state, durable context, and success criteria survive cheap handoff between strong frontier agents, weaker local/open models, and human maintainers. | Another mixed-agent task completes with noticeable restart or handoff friction, or a dogfooding pass suggests the checked-in surfaces are still too expensive for weaker agents to reconstruct. |
| `Delegated-judgment practical follow-through` | GitHub issue `#25`; `docs/delegated-judgment-contract.md`; `docs/execplans/README.md` | Delegated judgment is now good on paper; the next work is proving it in repeated real workflows and tightening places where agents still silently widen ends, fail to escalate, or need too much user steering to stay bounded. | Another delegated task shows ambiguity around local latitude, escalation boundaries, or requested-end preservation. |
| `Repo-state classifier hardening` | GitHub issue `#27`; `llms.txt`; `.agentic-workspace/bootstrap-handoff.md` | Intent-first bootstrap and inferred-policy reporting are landed, but repo-state classification still needs proof across fresh, partial, ambiguous, customized, and conflicting repos. | Another bootstrap pass hits ambiguous repo state, or a new fixture/review shows classifier output is not yet conservative enough. |
| `External-agent handoff polish` | GitHub issue `#27`; `llms.txt`; `.agentic-workspace/bootstrap-handoff.md`; `README.md` | External-agent handoff surfaces are strong additions, but they still need proof that they are foolproof in use: no installed-CLI assumptions, no ambiguity about target repo versus this repo, and no drift between the README prompt, raw handoff file, and actual bootstrap behavior. | Another external-agent or cold-start pass shows ambiguity between docs, handoff files, and live bootstrap behavior. |

## Third Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Conservative automatic policy selection follow-through` | GitHub issue `#27`; `agentic-workspace.toml`; `llms.txt` | The workspace should keep reducing required user input, but only where inference is safe. The next refinement is proving when to install, adopt, emit review-required handoff, or preserve repo-owned surfaces aggressively. | Another bootstrap or adoption pass shows policy inference is either too eager or not explicit enough about review-required boundaries. |

## Ongoing Maintenance Expectations

- Keep front-door and default-path surfaces quiet; remove transitional wording, duplicated route descriptions, and fallback explanations once newer defaults prove stable.
- Preserve review and issue discipline by keeping both layers bounded, quiet, and cheaper than the confusion they prevent.
- Treat cheap-agent-safe residue capture as part of the mixed-agent proof work above rather than a separate backlog lane unless it produces a distinct repeated failure class.

## Sequencing Recommendation

1. Prefer proof, refinement, and trust-hardening over new capability invention.
2. Start with one real strong-planner / cheap-implementer dogfooding pass, then use the evidence to sharpen synergy, selective-adoption, and portability follow-through.
3. Treat bootstrap hardening and mixed-agent handoff quality as the second wave once the first proof tranche shows where ambiguity still leaks.
4. Execute one bounded roadmap candidate at a time with narrow validation and prompt archival.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
