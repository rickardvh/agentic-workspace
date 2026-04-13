# TODO

Last pruned: 2026-04-10

## Purpose

Active queue for repository work.

## Now

- No active work right now.
## Action

- Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation.
## Done

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
