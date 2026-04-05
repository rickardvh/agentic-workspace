# TODO

Last pruned: 2026-04-05

## Purpose

Active queue for repository work.

## Now

- [docs-ecosystem-hardening-2026-04-05](docs/execplans/docs-ecosystem-hardening-2026-04-05.md) - Documentation and liveness tranche for naming clarity, chooser guidance, canonical policy docs, and startup/routing consistency checks.

## Action

- Treat collaboration-safe installed-contract hardening as the preferred next promotion set after the current docs tranche, in this order: planning contract safety, memory contract safety, then cross-module collaboration rules.
- Promote the next roadmap candidate only when it is bounded enough for a short active execplan.
- Prefer documentation, liveness checks, and consistency hardening over introducing new top-level concepts.
- Favor merge-safe installed file shapes, weak-authority current surfaces, and collaboration-oriented checks over repo-local workaround guidance.
- Keep root planning surfaces compact; archive completed plans instead of letting TODO accumulate residue.

## Added In This Pass

- Completed and archived the workspace-orchestrator cleanup tranche after consolidating managed planning assets under `.agentic-workspace/planning/` and switching both package installers to the shared ownership ledger for module-root decisions.

- Captured uv workspace lessons: member cwd does not isolate workspace installs and shared group names (`dev`) merge at root sync.
- Queued follow-up work for dependency-group routing, package-scoped sync/check targets, and documentation of shared vs scoped environments.
- Captured installed-system overlap: `packages/memory/` contains an installed memory system and `packages/planning/` contains both installed memory and planning systems.
- Queued root-level adopt plus populate consolidation work to merge existing memory/planning content and define post-merge handling for package-local installed-system files.
- Implemented root adoption and population for planning/memory systems, imported package planning archives into root planning archive, and added root sync lane orchestration in Make and CI.
- Ran uninstall flows under package subdirectories and verified package checks; retained package-local system files needed by package-local test fixtures.
- Added fixture-lane hardening to active follow-up: document package-local systems as package test/dev fixtures, guard root orchestration against fixture paths, and add drift checks for unexpected fixture-surface growth.
- Added redirection queue: point package tests at root-owned planning/memory fixture homes where possible, and keep only minimal package-local payload-contract tests.
- Implemented root-fixture redirection and uninstall-safe checks: planning checker tests now load root checker first, memory installer tests use fixture templates instead of package-installed memory files, and root/package check targets fall back to root scripts.
- Executed uninstall flows (dry-run + apply) in both `packages/memory` and `packages/planning`; root `make check-all` now passes against the post-uninstall layout.
- Completed manual-review residue cleanup in both package roots and updated tests to avoid deleted package-local current-note dependencies; `make check-all` remains green.
- Captured new collaboration-safety follow-on work for installed contracts, centered on merge-friendly planning templates, weak-authority memory current-state surfaces, cross-module write-authority rules, and package-authoring checklists for git-heavy teams.
- Completed the planning collaboration-safety tranche: execplan templates now push merge-friendly compact shape, planning checks warn on completed plans left active and oversized active plan sets, and the planning package docs now describe collaboration-safe active-state handling more explicitly.
- Completed the memory collaboration-safety tranche: `memory/current/` notes now carry weak-authority manifest metadata, the freshness audit warns on current-note authority drift and durable-truth drift, and the shipped memory docs/templates now reinforce one-fact-one-home current-state handling.
- Completed the cross-module collaboration contract tranche: integration docs now spell out canonical-source precedence, branch-vs-trunk boundaries, generated-surface edit rules, and partial-adoption write authority across memory, planning, and the workspace layer.
- Completed the installed-contract design checklist tranche: package authors now have one canonical checklist for merge-safe file shape, canonical-source clarity, lifecycle markers, validation hooks, and partial-adoption review before shipping new installed surfaces.
