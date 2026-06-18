# Agentic Planning

Agentic Planning is a checked-in planning-for-execution contract, distributed as the Planning module of Agentic Workspace. Use the root `agentic-workspace` CLI for normal host-repo lifecycle, startup, reporting, and module orchestration. The `agentic-planning` CLI remains the module-level interface for package-local maintenance, advanced debugging, and explicit Planning-only lifecycle control.

## Why

Active agent work often needs more than a TODO line but less than a project-management system. Planning gives the repo a small checked-in place for current intent, bounded execution scope, validation expectations, and honest closeout so another session can resume without reconstructing the task from chat.

Use Planning when the current work itself is the fragile thing. Use Memory when the durable knowledge around the work is the fragile thing.

Planning is intentional overhead. It pays back when the next session, branch, or agent would otherwise have to reconstruct scope, proof expectations, blockers, or the difference between a completed slice and an unfinished larger intent.

In the temporary-contributor mental model, Planning is the part of the repo that makes current work bounded and resumable: what is being attempted now, what proves it, where it must stop, and what the next contributor needs if the session ends first.

## What It Does

Choose this package when you want active work in a repository to stay bounded, resumable, and finishable across fragmented sessions.

Use it for:

- keeping active queue and candidate-lane state in `.agentic-workspace/planning/state.toml`
- attaching bounded execution contracts to active work in `.agentic-workspace/planning/execplans/`, with optional machine-first `.plan.json` canonical sidecars plus derived `.md` views
- capturing analysis-derived future-work findings in `.agentic-workspace/planning/reviews/` before promotion
- helping agents restart from checked-in execution state instead of chat-only context

Do not use it for:

- durable technical knowledge that should outlive the active task
- subsystem documentation or runbooks
- a full project-management or ticketing system

If your main problem is shared repo memory rather than active work steering, start with `agentic-memory` instead.

Current maturity in this repo: beta.

## How It Works

Adoption shape:

- Works through the Workspace layer in repos that need checked-in execution steering without a separate memory layer.
- Works alongside Agentic Memory when active planning should be able to reference durable repo knowledge.
- Selective adoption remains valid: a repo can install with `--modules planning` without Memory, while Workspace still owns startup routing, lifecycle coordination, shared config, and combined reports.

Participation shape:

- Contributes active-work and closeout state to the open Workspace operating loop.
- Declares module-managed roots, summary resources, lifecycle tools, planning skills, schemas, and proof/continuation expectations through the module registry and Planning manifests.
- Contributes task posture only when active planning state, lane-shaped work, planning-owned paths, or completion claims require allowed/forbidden actions, review posture, proof boundaries, or closeout gates.
- Acts as a first-party example of module participation; it should not force every module into Planning-shaped active state or make Planning a general backlog system.

Collaboration shape:

- Works best when active work is split into feature-scoped execplans instead of broad shared status files.
- Keeps branch-local execution state in `.agentic-workspace/planning/state.toml` plus the active execplan, while durable technical guidance stays elsewhere.
- Expects completed plans to archive quickly so active surfaces stay small and merge-friendly.

The ordinary model is direct first, planned when useful:

- Keep small, obvious work as a direct task in `.agentic-workspace/planning/state.toml`.
- Promote to an execplan when the work needs milestone sequencing, explicit blockers, non-obvious validation, rollback detail, or cross-session handoff.
- Archive completed execplans promptly, with proof and any required continuation routed to a checked-in owner.

## Current Limitations

- Planning is not a durable knowledge base; route reusable subsystem knowledge to Memory or canonical docs.
- Planning is not a ticketing, sprint, or PM platform.
- External issue reconciliation is optional evidence, not the source of planning authority.
- Optional review/intake surfaces and bundled skills are richer workflow affordances, not required installed payload.

## Good Fits

- a repo where active work drifts between sessions and needs a checked-in active queue
- a repo that wants bounded execution contracts without introducing a full project-management system
- a repo using agents heavily enough that chat-only task continuity is too fragile
- a solo or team repo where future handoff cost is high enough to justify checked-in execution state

## Bad Fits

- a repo looking for durable subsystem documentation or knowledge capture rather than execution steering
- a repo expecting a full ticketing, sprint, or PM platform
- work that is small enough to finish in one coherent pass with obvious validation

Bundled skills:

- The package ships planning skills under `skills/`, but new default installs do not copy them into target repositories.
- Use `agentic-planning list-files --format json` to discover bundled skills and optional payload surfaces when a repo chooses to enable richer planning workflows.
- Pass `--include-optional` to `install`, `adopt`, or `upgrade` to copy optional review/intake surfaces, machine capability data, and bundled skills into a repo that intentionally wants the richer workflow.

## Quick Start

Default path: use `agentic-workspace init --modules planning`.
Treat the module selection as the user intent: "set up this repo for Agentic Planning" and let the workspace CLI choose the safe install vs adopt path from repo state.
Use the package CLI below only for package-local maintainer work, advanced debugging, or when you explicitly need module-level control.

Advanced module-only no-install path:

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt install --target ./repo

# Alternative when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt install --target ./repo
```

Prefer the root Workspace command for host repos. Use these module-only commands when you are maintaining Planning itself, debugging the module boundary, or performing a narrow package-level operation after Workspace has established repo context. Prefer `uvx` when `uv` is already available. Support `pipx` as the equivalent no-install path when it is the runner a repo already uses.

Use `prompt install` for a clean bootstrap. Use `adopt` when the repository already has planning-like docs and you want the package to merge conservatively around existing surfaces.
After workspace bootstrap, `docs/agentic-workspace-install.md` is the canonical external-agent install handoff and `.agentic-workspace/bootstrap-handoff.md` is the next-action brief when the repo still needs review.

## Advanced Package Path

Normal public lifecycle path:

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target ./repo --modules planning
```

If you want an agent to perform lifecycle work without a local CLI install, use the paired remote prompt commands below.

### Install Or Adopt

```bash
# Preferred when uvx is available: clean bootstrap
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt install --target ./repo

# Alternative when pipx is available instead: clean bootstrap
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt install --target ./repo

# Preferred when uvx is available: conservative adoption
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt adopt --target ./repo

# Alternative when pipx is available instead: conservative adoption
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt adopt --target ./repo
```

### Upgrade

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt upgrade --target ./repo

# Alternative when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt upgrade --target ./repo
```

### Uninstall

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt uninstall --target ./repo

# Alternative when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning prompt uninstall --target ./repo
```

## Deep Contract Details

### Stability Contract

The installed planning payload is not one flat compatibility promise.

Treat these files as the current planning compatibility contract surfaces that should not change shape casually:

- `AGENTS.md`
- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/decompositions/README.md`
- `.agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json`
- `.agentic-workspace/planning/execplans/README.md`
- `.agentic-workspace/planning/execplans/TEMPLATE.plan.json`
- `.agentic-workspace/planning/execplans/archive/README.md`
- `.agentic-workspace/docs/lifecycle-and-config-contract.md`
- `.agentic-workspace/docs/execution-flow-contract.md`
- `.agentic-workspace/docs/minimum-operating-model.md`
- `.agentic-workspace/docs/routing-contract.md`
- `.agentic-workspace/docs/system-intent-contract.md`
- `.agentic-workspace/docs/workspace-config-contract.md`
- `.agentic-workspace/planning/agent-manifest.json`

Treat optional package payload and generated mirrors as lower-stability support surfaces unless a stricter promise is stated later. That lower-stability set currently includes bundled skills, review/intake surfaces, and machine-readable capability data. Root-level generated adapter mirrors such as `tools/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, and `tools/AGENT_ROUTING.md` are target-repo generated surfaces, not planning bootstrap payload. Executable behavior belongs in the CLI/package source, so bootstrap payload files must remain declarative and non-executable.

Generated mirrors inherit stability from their canonical source relationships, not from their exact rendered text. If the manifest contract stays stable, the generated wording may still evolve when the renderer improves.

### Direct Execution Or Execplan

`.agentic-workspace/docs/execution-flow-contract.md` is the front-door companion for delegated judgment, active intent continuity, resumability, and execution summaries.
`.agentic-workspace/docs/system-intent-contract.md` defines how a bounded slice preserves the larger intended outcome and how closure decisions stay honest when the slice completes before the broader lane or issue does.
`.agentic-workspace/docs/execution-flow-contract.md` also defines the restart and execution-summary expectations carried by the canonical `planning_record`.
`.agentic-workspace/docs/lifecycle-and-config-contract.md` defines the ordered environment-recovery path when lifecycle work, repo-state inspection, or validation restart becomes ambiguous.
`.agentic-workspace/docs/execution-flow-contract.md` defines the compact completion summary that archived slices should leave behind.
`.agentic-workspace/docs/routing-contract.md` defines the hierarchy and routing rules between `.agentic-workspace/planning/state.toml`, execplans, and reviews.
Advanced capability fit, orchestration, standing-intent, reporting, and context-budget behavior is exposed by compact CLI report sections and optional skills rather than shipped target-repo prose docs.

For active planning, `agentic-planning summary --format json` is the default active-state router. Use `--select <field.path>` for exact fields and `--verbose` for audit or reconciliation work. In detailed output, `planning_record` is the canonical machine-readable active state. The `machine_first_planning` summary block reports whether active execplans are being read from canonical `.plan.json` sidecars or from Markdown compatibility fallback. `active_contract`, `resumable_contract`, `follow_through_contract`, `context_budget_contract`, `hierarchy_contract`, and `handoff_contract` remain thinner views over that record. `system_intent_alignment` records which higher-level intent materially shapes the slice, how it biases the slice shape, and what lane-level validation question remains. `context_budget_contract` now also carries the explicit pre-work retrieval prompt so ordinary work can ask what durable understanding should be recovered before execution and which area it concerns, while leaving Memory optional rather than required.
When an execplan has a sibling `.plan.json` file, that sidecar is the canonical execplan artifact and the `.md` file is treated as a derived human-readable view.
Planning mutations use optimistic revision guards rather than leases. Read surfaces expose `planning_revision.revision_id`, derived from `.agentic-workspace/planning/state.toml` and the active execplan identity/content hash. Active-plan-sensitive commands accept `--expect-planning-revision`; when supplied, the mutation stops if the observed revision has changed. This protects freshness without claiming session ownership. Command provenance still only proves a package writer recorded shared state, so agents must treat `active_plan_reliance` as the honest permission signal before continuing an active plan.
For delegated execution, `agentic-planning handoff --format json` is the compact worker handoff derived from that same active planning state. It carries intent interpretation, execution bounds, stop conditions, post-decomposition delegation routing, and explicit return-with residue fields for a bounded execution run plus finished-run review, including compact delegation outcome feedback and a `changed surfaces` answer for what actually changed. Its `handoff_contract.ready_worker_prompt` field is a ready-to-forward implementation prompt that points at the active plan and asks the worker to return with the existing execution, review, and delegation feedback contract.
For cheap delegated-work inspection, `intent_interpretation_contract`, `execution_run_contract`, `finished_run_review_contract`, `intent_validation_contract`, and `finished_work_inspection_contract` remain thin projections over the same active plan and surrounding planning state instead of becoming a second orchestration ledger. `execution_run_contract` keeps intended scope (`scope_touched`) separate from actual changed surfaces (`changed_surfaces`) so returned-run review does not depend on broad diff reconstruction.

`intent_validation_contract` keeps checked-in planning primary while allowing optional reconciliation against ignored `.agentic-workspace/local/cache/external-intent-evidence.json` or legacy `.agentic-workspace/planning/external-intent-evidence.json` when a repo also tracks work elsewhere. Its `external_work_reconciliation` field is the compact first answer for evidence freshness, current external work state, closeout reconciliation, and landed-open checks. Offline planning remains valid when external evidence is absent.
`finished_work_inspection_contract` keeps archived execplan residue primary while allowing provider-agnostic external evidence items with `reopens` refs to lower trust when source-owned work reopens an older closeout. Legacy `.agentic-workspace/planning/finished-work-evidence.json` remains a compatibility input, but stale copied title/status values should not override source-owned external evidence.
For compact module-state reporting without opening raw planning files first, use `agentic-planning report --format json`. It stays derived from the same canonical planning state and does not create a second state store.
Use `hierarchy_contract` when you need the larger-picture restart answer cheaply: active chunk, parent lane, next likely chunk, continuation owner, and proof state.

Use a direct task in `.agentic-workspace/planning/state.toml` when the work is small enough to finish in one coherent pass and does not need milestone sequencing, blocker tracking, or a wider validation story.

Treat the direct-task shape as compact by default:

- `ID`
- `Status`
- `Surface`
- `Why now`
- `Next action`
- `Done when`

Do not promote work into an execplan just because a more capable model or agent is available. Advanced agents already have session-local planning; checked-in planning should appear only when it reduces rediscovery, restart cost, or coordination risk more than it costs to write.

Promote the task into `.agentic-workspace/planning/execplans/` when any of the following becomes true:

- the work now spans more than one milestone or session-sized checkpoint
- the next contributor would need explicit blocker or dependency handling
- validation scope has to be spelled out instead of staying obvious from the change
- rollback, migration, or ownership-reconciliation detail appears
- the TODO row starts carrying extra execution fields or long narrative text
- the implementing agent lacks enough context window, tools, or local planning support to hold the task safely in one pass

Direct execution is an explicit success mode for small local work. The goal is not to force every change through planning; the goal is to promote only when the cheap path stops being safe.

When delegation is useful, keep it capability-aware and optional. If available, a stronger model may draft a compact execplan or handoff for a smaller implementation model, or use a read-only explorer for one bounded inspection question, but only when that is likely to save tokens overall without lowering quality. Do not assume subagents or multi-model workflows exist; the contract should still work for a single agent operating alone.
Use the capability-aware execution contract to describe that recommendation in task-shape terms instead of vendor-specific model names, and prefer silent task shaping over repeated instructions to switch executors manually.
Use the orchestrator workflow contract plus `agentic-planning handoff --format json` when the goal is to reuse the same checked-in handoff across internal delegation, local CLI/API execution, or another vendor executor.

If stronger capability keeps seeming necessary for the same class of work, treat that as a product signal for cheaper future execution. The next step is often better decomposition, clearer validation, or tighter guidance rather than accepting stronger execution as the permanent answer.

When a repo also installs Agentic Memory, Planning may borrow durable context from routed memory notes instead of re-explaining the same subsystem background inside each execplan. That cooperation must stay optional: planning still owns active steering, docs still own canonical contracts, and Memory remains an additive durable-context source rather than a planning dependency. Completed planning residue should promote durable lessons into memory or canonical docs when they remain expensive to rediscover.

When a direct task completes, remove it from `.agentic-workspace/planning/state.toml` promptly. If the task changed durable repo knowledge or left important follow-up work, record that residue in memory, canonical docs, the roadmap state in `.agentic-workspace/planning/state.toml`, or a newly promoted execplan rather than leaving chat-only context behind.
If the completed slice came from the active queue or roadmap state, clear the matched queue residue in the same pass instead of leaving stale completed entries behind.
When a bounded slice completes only part of a larger intended outcome, do not close it with required continuation only in prose.
Execplans now treat four fields as first-class:

- `Intent Continuity`: whether the larger intended outcome is actually complete and what checked-in surface now owns it if not
- `Required Continuation`: whether follow-on is mandatory for that larger outcome, plus the owner surface and activation trigger
- `Iterative Follow-Through`: what the slice enabled, what it intentionally deferred, what new implications were discovered, and what proof or validation still carries forward
- `Execution Summary`: what the slice delivered, how validation was confirmed, where follow-on was routed, what posterity should survive and where it belongs, and how later work should resume
Execplans also leave an explicit `Closure Check`: whether the bounded slice is complete, whether the larger intended outcome is actually closed, which archive path is honest, what evidence carries forward, and what should trigger reopening.
When an execplan is carrying broad direction across sessions, it should also record a compact `Delegated Judgment` section:

- `Requested outcome`
- `Hard constraints`
- `Agent may decide locally`
- `Escalate when`

If required follow-on remains, archive should happen only after those fields point at a checked-in next owner.
Completed plans should also leave an explicit execution summary before archive so later contributors do not have to reconstruct the outcome from drift prose or chat.
Completed plans should also leave an explicit closure check before archive so later contributors can tell the difference between slice completion and larger-intent closure without reopening issue prose.
If the slice stopped intentionally rather than finishing the broader goal, keep `Iterative Follow-Through` current so the next bounded slice inherits the right residue without rereading the full plan.
Optional nice-to-have follow-up can still stay out of the archive gate.

### Direct-Task Recovery Cases

Keep the task direct only while the TODO row stays self-sufficient.

Promote into an execplan when any of these cases appears:

- interrupted work now needs an explicit restart or resume path
- a handoff between sessions, contributors, or models would require more than one TODO row
- partial failure or retry handling needs to be spelled out
- concurrent branch work creates merge, ownership, or sequencing risk
- stale residue would otherwise be left in `.agentic-workspace/planning/state.toml` because the task can no longer close in one pass
- a compact checked-in plan would let a smaller or less capable agent implement safely without re-deriving the whole task

The practical test is simple: if safe continuation depends on more than `Why now`, `Next action`, and `Done when`, the work is no longer a direct task.
Use `.agentic-workspace/docs/lifecycle-and-config-contract.md` to keep that recovery guidance compact and in existing planning fields instead of inventing ad hoc restart prose.

## Example Scenarios

- Before: each session restarts by rediscovering what mattered last time.
  After: `.agentic-workspace/planning/state.toml` and one active execplan hold the live execution contract.
- Before: follow-on work derails the current thread because there is no compact place to capture it safely.
  After: future work stays in the roadmap section of `.agentic-workspace/planning/state.toml` while the current thread stays bounded.

## Detailed Contracts

Keep this README as the package entrypoint. Use the installed contracts for deep operating rules:

- `.agentic-workspace/docs/execution-flow-contract.md`: active state, execplans, handoff, restart, and closeout.
- `.agentic-workspace/docs/routing-contract.md`: hierarchy between state, execplans, and reviews.

Optional packaged affordances remain discoverable through `agentic-planning list-files --format json` when a repo needs review promotion, upstream-task intake, machine-readable capability data, or bundled planning skills.
Use `--include-optional` with `install`, `adopt`, or `upgrade` only when the repo intentionally wants those richer workflow surfaces copied into its checkout.
Package maintainers can use `extraction-candidates.json` to review which planning-adjacent capabilities should stay internal, remain optional extensions, or wait for future extraction evidence.

Planning is deliberately not a task tracker, backlog manager, knowledge base, documentation system, database-backed planner, or runtime orchestration tool.
It should preserve active execution state and route durable knowledge to memory or canonical docs.
Required continuation for an unfinished larger intended outcome must be routed into a checked-in owner before the current slice closes; it should not survive only as drift-log prose or chat residue.

## What the Package Installs

The default install writes only the core daily-operation payload.

The package ships these payload files:

- `AGENTS.template.md`
- `.agentic-workspace/docs/execution-flow-contract.md`
- `.agentic-workspace/docs/lifecycle-and-config-contract.md`
- `.agentic-workspace/docs/minimum-operating-model.md`
- `.agentic-workspace/docs/routing-contract.md`
- `.agentic-workspace/docs/system-intent-contract.md`
- `.agentic-workspace/docs/workspace-config-contract.md`
- `.agentic-workspace/planning/UPGRADE-SOURCE.toml`
- `.agentic-workspace/planning/agent-manifest.json`
- `.agentic-workspace/planning/decompositions/README.md`
- `.agentic-workspace/planning/decompositions/TEMPLATE.decomposition.json`
- `.agentic-workspace/planning/execplans/README.md`
- `.agentic-workspace/planning/execplans/TEMPLATE.plan.json`
- `.agentic-workspace/planning/execplans/archive/README.md`
- `.agentic-workspace/planning/lanes/README.md`
- `.agentic-workspace/planning/lanes/TEMPLATE.lane.json`
- `.agentic-workspace/planning/schemas/planning-decomposition.schema.json`
- `.agentic-workspace/planning/schemas/planning-execplan.schema.json`
- `.agentic-workspace/planning/schemas/planning-external-intent-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-finished-work-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-closeout-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-lane.schema.json`
- `.agentic-workspace/planning/schemas/planning-review.schema.json`

The package also ships optional payload files that are not copied by default. Use `--include-optional` with `install`, `adopt`, or `upgrade` to copy them on purpose:

- `.agentic-workspace/docs/capability-contract.json`
- `.agentic-workspace/planning/pre-ingestion-refinement.md`
- `.agentic-workspace/planning/reviews/README.md`
- `.agentic-workspace/planning/reviews/TEMPLATE.review.json`
- `.agentic-workspace/planning/upstream-task-intake.md`
- bundled skills under `skills/`

It packages:

- the planning contract
- the module-managed planning manifest
- optional review-artifact contract surfaces under `.agentic-workspace/planning/reviews/`
- optional upstream-task intake contract surfaces under `.agentic-workspace/planning/upstream-task-intake.md`
- optional machine-readable capability data under `.agentic-workspace/docs/capability-contract.json`
- environment and recovery contract surfaces under `.agentic-workspace/docs/lifecycle-and-config-contract.md`
- file-native helper commands for promotion, archiving, and summary
- starter surfaces
- startup docs and manifest wiring

It does not package repo-specific active execution content.

In this monorepo checkout, the active operational planning install lives at the repository root. This package directory keeps the reusable package source, bootstrap payload, tests, and fixtures; the default planning surfaces listed above describe the target-repository structure that `install` or `adopt` writes.

## Installed Operating Shape

The installed planning state lives under `.agentic-workspace/planning/`, inside the shared Workspace operating layer.
The root `AGENTS.md` adapter points agents to compact Workspace startup commands, and the package payload supplies reusable contracts and templates consumed by the Workspace orchestrator.

This module can work alongside Agentic Memory, but does not require Memory: Planning owns active execution state, while Memory owns durable technical knowledge. Workspace remains the common orchestrator whether a repo installs Planning alone, Memory alone, both modules, or only routing surfaces.

## Commands

- `agentic-planning install --target <repo>`
- `agentic-planning adopt --target <repo>`
- `agentic-planning upgrade --target <repo>`
- `agentic-planning uninstall --target <repo>`
- `agentic-planning doctor --target <repo>`
- `agentic-planning status --target <repo>`
- `agentic-planning summary --target <repo> --format json`
- `agentic-planning promote-to-plan <todo-id> --target <repo>`
- `agentic-planning archive-plan <plan> --target <repo>`
- `agentic-planning archive-plan <plan> --target <repo> --apply-cleanup`
- `agentic-planning list-files`
- `agentic-planning verify-payload`
- `agentic-planning prompt install --target <repo>`
- `python scripts/check/check_maintainer_surfaces.py`
- `make maintainer-surfaces`
- `make planning-surfaces`
- `make planning-surfaces-strict`
- `make render-agent-docs`

`archive-plan` is the compatibility command name for plan closeout. The normal path distills closeout, routes future-relevant residue to its real owner, and removes the completed execplan from Planning. Use `--retain-archive` only for legacy audit/compatibility cases. `archive-plan --apply-cleanup` is intentionally narrow: it may remove completed active-queue items that still point at the closed plan and compress stale roadmap residue tied to that same thread, but it does not invent hidden state or perform broad automatic rewrites.

`upgrade` is intentionally conservative: it refreshes package-managed helper surfaces, re-renders generated planning docs, removes stale generated queue views from older installs, and leaves repo-owned surfaces like `AGENTS.md` unchanged when they already exist.
When older active execplans were written against a previous template, the upgrade path is to reconcile those plans to the current contract shape, not to expect `upgrade` to rewrite them automatically.

`uninstall` is intentionally safe: it removes managed files only when they still match package content and leaves locally modified files in place for manual review.

`.agentic-workspace/planning/UPGRADE-SOURCE.toml` records the intended bootstrap source for install and upgrade workflows. `doctor` reports that source and warns when the recorded source age crosses the configured threshold so upgrades remain intentional rather than silently drifting.

## Success Criteria

The system is working when:

- agents resume work without re-deriving intent
- active work stays small and focused
- features are completed and integrated
- long-term goals remain visible
- partial work is reduced significantly
- planning surfaces remain compact and current

## Philosophy

> Do less at once.  
> Keep direction visible.  
> Finish what you start.  
> Let structure carry context.

## Development

```bash
make sync-planning
cd packages/planning && make test

# For a tiny focused repro where xdist startup would dominate
cd packages/planning && uv run pytest tests/test_installer.py
make render-agent-docs
make maintainer-surfaces

# Or from the monorepo root
make check-planning
```

Package checks run against the shared root workspace environment; the package directory is not a separate operational planning install in this monorepo.
