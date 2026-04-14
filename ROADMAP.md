# Roadmap

Last reviewed: 2026-04-14

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff
- `Bounded post-install jumpstart phase for mature repos` is promoted to `docs/execplans/bounded-post-install-jumpstart-phase-2026-04-14.md`; the remaining mature-repo follow-on candidates stay queued below.
## GitHub Issue Intake

- Latest intake tranche: GitHub issues `#53` through `#58`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Highest Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Nearly automatic proof selection` | GitHub issue `#35`; compact intent/resumable contract follow-through | The active execution contract is now smaller, but a major remaining supervision cost is proof choice. The next highest-value refinement is making the narrowest sufficient proof lane and its escalation boundary cheaper to retrieve than human steering. | Ordinary work still requires human interpretation to decide what proof is enough, when broader proof is required, or when the narrow lane has stopped being meaningful. |

## Second Priority Queue

- `Cross-agent handoff as an ordinary-work mode` from GitHub issue `#36`

## Third Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Repeated-human-steering improvement signal` | GitHub issue `#37`; improvement-targeting workflow | Repeated human correction should become explicit product pressure, but that follow-through is lower urgency than shrinking the active execution contract and proof/handoff ambiguity first. | The same class of human steering still repeats after the intent, resumable-execution, proof, or handoff contracts improve. |
| `Cross-agent workflow robustness hardening` | Archived execplan `docs/execplans/archive/cross-agent-workflow-robustness-hardening-2026-04-13.md`; mixed-agent dogfooding feedback | The first machine-readable hardening slice landed, but the broader goal stays open until future mixed-agent passes show startup routing, package-managed paths, and same-pass planning cleanup are no longer missed in ordinary use. | Another mixed-agent pass still misses startup routing, package-managed paths, or same-pass planning cleanup after the current machine-readable hardening slice. |

## Fourth Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Mature-repo discovery reporting before seeding` | GitHub issue `#49`; jumpstart reporting prerequisite | Jumpstart needs a compact, auditable report that classifies durable Memory candidates, active Planning candidates, and unsafe ambiguity before any checked-in state is written. | The report shape can stay compact and machine-readable while identifying high-value candidates and no-action cases. |
| `Memory seeding from high-value mature-repo signals` | GitHub issue `#50`; jumpstart Memory slice | Mature repos often already contain durable anti-rediscovery knowledge that should seed Memory early, but only if the source material is high-confidence and compact enough to avoid noise. | High-confidence Memory seeds can be extracted as compact facts, invariants, runbooks, or stable conventions without bulk-importing prose. |
| `Planning seeding from current mature-repo reality` | GitHub issue `#51`; jumpstart Planning slice | Mature repos often already expose one useful active picture, and a bounded planning seed can make adoption feel immediately useful without migrating historic backlog state. | One current active slice, one or two roadmap candidates, or one bounded review artifact can be seeded without turning intake into backlog archaeology. |
| `Fast payoff mature-repo jumpstart mode` | GitHub issue `#52`; jumpstart ranking refinement | A bounded jumpstart phase also needs an explicit ranking policy so the highest-value low-risk seeds come first and the first visible gains stay small, clear, and reviewable. | Candidate ranking can be expressed with clear value and confidence signals, and skipped seeds stay explicit in reporting. |

## Fifth Priority Queue

| Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- |
| `Human-free benchmark harness for repo-operating evaluations` | GitHub issue `#54`; benchmark harness core | The fastest dogfooding payoff is a runnable evaluation loop that can score repo-operating behavior without requiring real humans in every run. | The repo can run a stable benchmark loop with explicit human, worker, and judge roles plus structured outputs. |
| `Structured judge rubric for agent-scored benchmarking` | GitHub issue `#55`; benchmark comparability | A harness is only useful if the judge produces comparable structured scores instead of free-form narrative. | The rubric can score action choice, scope discipline, proof, ownership, escalation, retrieval efficiency, and handoff continuity. |
| `Frozen fixture repos and scenario specs` | GitHub issue `#57`; benchmark reproducibility | Stable fixtures are needed to make dogfooding results comparable across branches, agents, and time. | The benchmark can run against frozen repo snapshots with compact scenario specs and narrow expected answers. |
| `Structured human-policy spec for benchmark human agents` | GitHub issue `#53`; benchmark role stability | The human-role agent needs bounded policy input or the benchmark will drift into ad hoc helpfulness. | The human-role policy can define outcome, constraints, approvals, prohibitions, and escalation responses in a structured way. |
| `Narrow operational-question benchmarks` | GitHub issue `#56`; benchmark alignment | The product’s value is repository operating cost, so the benchmark should ask narrow operational questions directly. | The benchmark family can score ownership, proof, escalation, bootstrap next action, and handoff continuity with clear answers. |
| `Token-cost and retrieval-efficiency metrics` | GitHub issue `#58`; efficiency proof | Efficiency claims should be measurable, but the metrics are most useful once the basic benchmark loop already exists. | The benchmark can record reading cost, selector use, broad dumps, and other retrieval-efficiency proxies in structured output. |

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
