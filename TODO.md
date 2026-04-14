# TODO

Last pruned: 2026-04-10

## Purpose

Active queue for repository work.

## Now

- No active work right now.
## Action

- Promote the final remaining open GitHub issue after the lazy-discovery measurement tranche is archived.
## Done

- lazy-discovery-measurement-audit: Completed (added the first cheap lazy-discovery measurement framework, checked in one audit of the current defaults/proof/ownership selector path, and proved the existing compact-contract work with measured retrieval-size reduction instead of schema intuition)
- bootstrap-agents-preservation-hardening: Completed (fixed the workspace upgrade path so root `AGENTS.md` stays repo-owned outside the managed workspace fence, added focused regression coverage, and confirmed the live bootstrap/handoff surfaces still behave conservatively enough to close the remaining bootstrap hardening issue)
- structured-bootstrap-handoff-artifact: Completed (added `.agentic-workspace/bootstrap-handoff.json` as the compact structured sibling for bootstrap follow-through, used it to carry intent/proof/escalation boundaries in checked-in form, aligned the lifecycle docs and CLI tests, and dogfooded the new record against this repo's live bootstrap state)
- lazy-discovery-contract-profile-and-selectors: Completed (shipped the first compact queryable contract profile, added narrow selectors to the defaults/proof/ownership machine-readable surfaces, aligned the contract docs, and dogfooded the new retrieval path directly in this repo before archiving the tranche)
- cross-agent-workflow-robustness-hardening: Completed (tightened the machine-readable workflow-recovery and completion cues, kept the workspace default recovery rule selective-adoption-safe, and archived the slice while leaving broader mixed-agent follow-through in `ROADMAP.md`)
- portability-evidence-review: Completed (reviewed the current portability claims against fresh clean-room first-party install proof plus the extension-boundary docs, tightened the canonical doctrine to distinguish proven first-party portability from still-unproven broader ecosystem portability, and cleared the highest-priority queue)
- selective-adoption-proof-refresh: Completed (ran fresh clean-room `memory`, `planning`, and `full` installs through `agentic-workspace init`, fixed optional-memory append noise in blank repos, narrowed the planning startup checker so generic READMEs and starter TODO hygiene text no longer trigger false drift, and confirmed the remaining clean-room follow-up is expected starter customization rather than contract inconsistency)
- cross-agent-handoff-quality-audit: Completed (audited the external-agent and restart surfaces, found a real `llms.txt` drift against the current workspace contract, refreshed the root handoff file through the canonical workspace upgrade path, confirmed the handoff warning cleared, and routed the remaining AGENTS-preservation concern into bootstrap-hardening follow-through instead of keeping this broader lane open)
- strong-planner-cheap-implementer-proof-refresh: Completed (reassessed the archived mixed-agent proof set against the live mixed-agent contract surfaces, concluded the standalone lane is now satisfied, retired it from `ROADMAP.md`, and left the remaining continuity question under the narrower cross-agent handoff audit lane)
- repeated-ordinary-use-synergy-proof: Completed (used ordinary repo work to prove the combined install against a real stale-current-memory failure, tightened the shipped freshness and current-memory checks so explicit planning-state residue in `memory/current/*` is flagged, refreshed the root current-memory notes to a smaller current shape, and archived the slice)
- strong-planner-cheap-implementer-dogfood-pass: Completed (used `agentic-workspace config --format json` and `agentic-workspace defaults --format json` as the mixed-agent contract, ran a real generated-surface trust pass through the maintainer-surface validation lane, confirmed `make maintainer-surfaces` stayed the cheapest trustworthy proof path, and archived the result after closing the stale generated-surface trust backlog item)
- planning-beta-surface-alignment: Completed (rechecked current public maturity surfaces, found no remaining public `alpha` claim for planning outside archived historical review artifacts, and removed the stale roadmap candidate)
- validation-defaults-refinement: Completed (enriched `agentic-workspace defaults` with structured validation lanes that say what proof is enough, when broader checks are needed, and when to escalate, then aligned the front-door docs with the richer surface)
- mixed-agent-local-override-contract: Completed (shipped a narrow supported `agentic-workspace.local.toml` contract, added source-attributed mixed-agent posture reporting to `agentic-workspace config`, aligned the config docs, and gitignored the local-only surface)
- mixed-agent-config-boundaries-and-reporting: Completed (froze the mixed-agent contract boundary, shipped reporting-only mixed-agent output in `agentic-workspace defaults` and `agentic-workspace config`, aligned the front-door/config docs with the shipped surface, and archived the slice)
- extension-boundary-readiness-review: Completed (reviewed the extension-boundary gates against the current first-party contract, added a live readiness snapshot plus re-review triggers to the canonical boundary doc, recorded the bounded review artifact, and removed the roadmap candidate)
- environment-recovery-guidance-contract: Completed (shipped a canonical planning-side environment and recovery contract, wired it into the planning package payload and generated routing surfaces, refreshed the root install from the checked-in package contract, and removed the roadmap candidate)
- doctrine-refresh-discipline: Completed (made the capability map, ecosystem stance, and maturity docs state their role boundaries and refresh triggers explicitly, then removed the doctrine-refresh candidate from `ROADMAP.md` and archived the slice)
- repo-owned-config-and-update-policy: Completed (shipped repo-root `agentic-workspace.toml`, added `agentic-workspace config`, made `init` honor `workspace.default_preset`, kept normal updates behind the workspace wrapper while syncing module `UPGRADE-SOURCE.toml` metadata from repo-owned policy, documented the contract, and dogfooded it in this repo)
- archive-cleanup-follow-through: Completed (fixed `archive-plan --apply-cleanup` so it removes the plan's own active TODO pointer, restores the default Action hint when the queue empties, and archives the slice cleanly without manual TODO pre-cleanup)
- bounded-delegated-judgment-contract: Completed (defined bounded delegated judgment as a first-class capability, made intent sticky in capability-aware execution, and codified that agents may improve means locally but must not silently widen requested ends)
- bootstrap-intent-handoff-tranche: Completed (shipped explicit repo-state and inferred-policy reporting in the workspace bootstrap front door, added `llms.txt` as the canonical external-agent handoff surface plus `.agentic-workspace/bootstrap-handoff.md` as the finishing brief path, aligned the root/package docs around intent-first bootstrap, and covered the new contract with workspace CLI regression tests)
- front-door-defaults-tranche: Completed (compressed the front-door docs, added `agentic-workspace defaults` as the machine-readable default-route contract, captured bounded default-path and cheap-execution audits, and removed the clearest transitional startup/path-selection scaffolding)
- memory-planning-synergy: Completed (defined the first explicit combined-install contract so planning borrows durable context from memory, completed planning residue promotes cleanly, and repeated plan re-explanation becomes a missing-synergy signal for cheaper future execution)
- capability-aware-execution-followup: Completed (refined the planning capability-fit contract so it stays advisory, quiet, and tool-agnostic, and turns repeated stronger-capability outcomes into complexity-reduction signals for planning, reviews, and improvement-targeting)
- capability-aware-execution-contract: Completed (shipped the first planning capability-fit contract so agents can classify cheap direct execution, stronger planning first, delegation-friendly work, autopilot suitability, and stop-and-escalate cases in task-shape language)
- automatic-skill-selection-routing: Completed (added registry-backed activation hints and task-to-skill recommendation so `agentic-workspace skills --task ...` can suggest the right bundled or repo-owned skills without requiring the user to know skill ids)
- repo-package-skill-discovery-hardening: Completed (made bundled package skills explicitly registered on install/upgrade, gave repo-owned skills a separate registry path, and exposed `agentic-workspace skills` as the trustworthy workspace discovery surface before any raw fallback scan)
- installed-surface-ambiguity-cleanup: Completed (cleared the remaining package-context ambiguity by tightening the installed notes, adding a checked-in inspection skill, and hardening the memory doctor heuristics against package-context false positives)
- plugin-ready-capability-contract: Completed (made capabilities, dependency/conflict metadata, lifecycle hook expectations, and result-contract guarantees first-class in the workspace registry and enforced declared compatibility rules during module selection)
- orchestrator-module-contract-finalization: Completed (moved module ordering, preset membership, startup guidance, and root AGENTS cleanup rules into module-owned descriptors so the workspace CLI no longer depends on separate planning/memory globals for first-party extension)
- memory-context-note-shape-cleanup: Completed (moved repeatable package-context inspection into a runbook, tightened current and package-context notes, and reduced the remaining memory overlap/procedure signal)
- shared-tooling-extraction: Completed (codified the rule for managed-source reuse versus helper extraction versus broader shared-tooling extraction)
- extension-boundary-design: Completed (defined the current first-party-only extension boundary and the readiness gates for any future public external-module contract)
- composition-contract-hardening: Completed (moved maintainer-surface aggregation into one managed source and returned root/package wrappers to thin delegation)
- contract-integrity-review-mode: Completed (made the `contract-integrity` review mode explicit enough to use and locked its core failure classes with payload assertions)
- maintainer-surface-consistency-hardening: Completed (restored the missing source/payload/root-install guide and made the direct maintainer wrapper aggregate boundary drift when available)
- improvement-targeting-workflow: Completed (made symptom-to-remediation routing explicit across memory and review surfaces, including post-remediation note-shape guidance)
- workspace-first-lifecycle: Completed (made `agentic-workspace` the normal public lifecycle entrypoint, added the root prompt lane, and rewrote the chooser/package docs around workspace presets)
- review-portfolio: Completed (shipped the canonical review matrix/playbook, review template mode fields, and planning payload assertions)
- memory-contract-framing: Completed (clarified recurring-failures as anti-trap memory and tightened high-level memory framing around anti-rediscovery value, one-home ownership, and planning subordination)
- memory-overlap-audit-hardening: Completed (reduced the repeated installed-system overlap cluster and cleared current-note overlap pressure without suppressing the remaining package-context warning)
- migration-fixtures: Completed (legacy adopter, partial managed state, and stale generated residue coverage added across workspace and package layers)
- packaging-tests: Completed (wheel/sdist artifact validation for all 3 packages)
- lifecycle-matrix: Completed (install/adopt/upgrade/uninstall/idempotence for all 3 packages)
- lifecycle-matrix: Completed (root workspace, planning, and memory lifecycle tests passed; archived execplan)
