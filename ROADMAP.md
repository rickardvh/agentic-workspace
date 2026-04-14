# Roadmap

Last reviewed: 2026-04-14

## Purpose

Inactive long-horizon candidate work.

## Scope

This file is a concise sequencing queue, not the canonical home for product doctrine or long-form maturity framing.

Keep long-horizon narrative in `docs/ecosystem-roadmap.md` and design constraints in `docs/design-principles.md`.
Keep the broader long-horizon capability map in `docs/agent-os-capabilities.md`.

## Active Handoff

- The bounded post-install setup phase is complete; the next mature-repo follow-on work now comes from the combined upgrade-quality and setup-quality issue tranches below.

## GitHub Issue Intake

- Latest intake tranche: GitHub issues `#65` through `#77`.
- Keep issue bodies as compact intake sources only; execute from checked-in planning after promotion.
- Keep detailed closure history in archived execplans and issue comments, not here.

## Long-Horizon Queue

| Priority | Candidate | Source | Why now | Promote when |
| --- | --- | --- | --- | --- |
| 1 | `Canonical compact planning state and thin views for continuation safety` | GitHub issue `#78` | Smaller models are more likely to lose continuity when active queue, completion history, and long-horizon candidate notes are mixed together. The planning layer needs a compact canonical record and thinner rendered views so weaker agents can continue cleanly without reconstructing structure from prose. | The planning-state drift is visible in another dogfood pass, or the stronger-model implementation slice is ready to define the canonical compact record and thin views. |
| 2 | `Renderer wrapper upgrade compatibility hardening` | GitHub issue `#66` | The canonical workspace upgrade path now works on mature repos, but it can still break a preserved repo-local `scripts/render_agent_docs.py` wrapper contract and force a manual compatibility repair after upgrade. | Another preserved repo hits the same post-upgrade renderer-wrapper gap, or the next workspace upgrade hardening pass is ready to close the highest-signal mature-repo compatibility issue first. |
| 3 | `Workspace config path semantics clarification` | GitHub issue `#65` | `agentic-workspace config` still reports `agentic-workspace.toml` as the authoritative config path even when the file does not exist, which weakens the default-path and trust-surface contract in both migration and upgrade evidence. | Another adopter or upgrade report still finds the missing-file ambiguity, or the next defaults/config tranche is ready to sharpen front-door config trust. |
| 4 | `Setup public workflow clarification` | GitHub issue `#69` | Setup is now a documented public contract concept, but the public `agentic-workspace setup` command still needs the last pass of front-door clarification, which leaves the concept and the product surface out of sync. | Another adopter looks for the public setup entrypoint, or the next front-door workflow refinement pass is ready to resolve the concept-versus-command mismatch directly. |
| 5 | `Mature-repo setup no-op detection` | GitHub issue `#72` | On a mature already-customized repo, setup currently adds little useful signal but does not clearly say that no new seed surfaces are needed, which weakens the quiet-by-default goal. | Another mature repo shows the same low-value setup result set, or the next setup/product-shape tranche is ready to improve graceful no-op behavior before adding more guidance surfaces. |
| 6 | `Execplan upgrade-guidance ergonomics` | GitHub issue `#67` | A successful canonical upgrade can still look attention-needing until preserved repo-owned execplans are manually brought to the newer planning contract shape, leaving avoidable guesswork in otherwise healthy upgrades. | Another preserved repo needs manual execplan contract reconciliation after upgrade, or the next planning contract change is large enough that upgrade hints should land before more schema growth. |
| 7 | `Setup bounded-proof separation` | GitHub issue `#70` | `report` is the closest thing to useful setup behavior today, while `proof` is still too backlog-heavy for bounded mature-repo orientation, so the setup lane is not yet clearly separated from the full proof backlog. | Another setup evaluation shows `proof` drowning bounded orientation in full backlog output, or the next setup pass is ready to sharpen the compact orientation lane. |
| 8 | `Setup skill recommendation quality` | GitHub issue `#71` | `skills --task "setup"` currently degrades into a broad skill dump with empty recommendations, which is anti-signal in exactly the quick-orientation lane where precision matters most. | Another repo shows the same empty-recommendation broad dump, or the next skill-routing refinement pass is ready to give setup a real recommendation contract. |
| 9 | `Memory doctor mature-corpus signal tuning` | GitHub issue `#68` | The remaining upgrade friction is now mostly low-signal advisory pressure from memory doctor on established customized corpora rather than lifecycle failure, so signal quality is the next mature-repo trust problem after the upgrade-path and setup-shape gaps above. | Repeated mature-repo evidence still shows overlap and current-note warnings dominating doctor output, or the higher-priority upgrade-contract and setup-shape issues above are closed and signal quality becomes the next trust bottleneck. |
| 10 | `Model Permissions in Delegation Posture Contract` | GitHub issue `#76` | Provides immediate, concrete safety guarantees for autonomous agents. Very quick to implement by extending `MixedAgentLocalOverride`. | The current active queue completes or an explicit safety-bounding need arises. |
| 11 | `Strict CLI Non-Interactivity and Windows Support` | GitHub issue `#75` | Crucial for robust CI and autonomous agent execution (especially on Windows), by adding `--non-interactive` argument propagation to prevent hanging prompts. | Autonomous agents consistently hang during lifecycle updates, or formatting/workflow cleanup tranche is selected. |
| 12 | `Structured Data Schemas for State Retrieval` | GitHub issue `#74` | Reduces agent parsing errors and hallucinations by exposing machine-friendly state. | Markdown prose continues to cause heavy extraction faults. |
| 13 | `Explicit Tool Verification State for Execplans` | GitHub issue `#77` | Complements schemas by warning agents if they lack required tools before attempting execution. | Capability-aware execution is expanded. |
| 14 | `Adapter Patterns for Agent-Specific Workflow Artifacts` | GitHub issue `#73` | Eliminates friction of maintaining two sets of plans for agents with native workflow artifacts. | Ecosystem integration lane is opened. |

## Ongoing Maintenance Expectations

- Keep front-door and default-path surfaces quiet; remove transitional wording, duplicated route descriptions, and fallback explanations once newer defaults prove stable.
- Preserve review and issue discipline by keeping both layers bounded, quiet, and cheaper than the confusion they prevent.
- Treat cheap-agent-safe residue capture as part of the mixed-agent proof work above rather than a separate backlog lane unless it produces a distinct repeated failure class.

## Sequencing Recommendation

1. Prefer proof, refinement, and trust-hardening over new capability invention.
2. The next mature-repo tranche should come from the upgrade-quality queue first, then the setup product-shape queue, before broader doctor signal tuning.
3. Treat issue `#66` and issue `#65` as the highest-priority pair because they affect whether the canonical upgrade path and config trust surface stay trustworthy on preserved custom repos.
4. Treat issue `#69` and issue `#72` as the next pair because they decide whether setup is a real quiet workflow or just a partially productized concept.
5. Execute one bounded roadmap candidate at a time with narrow validation and prompt archival.

## Reopen Conditions

- Reopen roadmap planning when the active queue completes or a new bounded candidate is ready to promote.

## Promotion Rules

- Promote candidate items only when dependencies are clear and the scope fits a short execplan.
- For review-derived candidates, prefer promotion only after the same product-level deficiency appears in at least two independent captures, or one review artifact plus one repeated maintenance or dogfooding pass, unless explicit maintainer direction justifies immediate activation.
- Keep detailed execution in `docs/execplans/` once promoted.
- Prefer collaboration-safe installed-contract work over new top-level concepts when dogfooding shows concurrent-edit ambiguity or merge pressure.
- Prefer friction-confirmed or repeated review findings over one-off static-analysis neatness.
