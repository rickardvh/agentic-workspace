# agentic-planning-bootstrap

Agentic Planning is a checked-in planning-for-execution contract, currently distributed as the `agentic-planning-bootstrap` package and CLI.

## At A Glance

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

If your main problem is shared repo memory rather than active work steering, start with `agentic-memory-bootstrap` instead.

Current maturity in this repo: beta.

Adoption shape:

- Works well alone in repos that need checked-in execution steering without a separate memory layer.
- Works alongside Agentic Memory when active planning should be able to reference durable repo knowledge.
- Does not require the full stack or the workspace layer.
- Selective adoption must remain valid: planning should still make sense in repos that do not install memory.

Collaboration shape:

- Works best when active work is split into feature-scoped execplans instead of broad shared status files.
- Keeps branch-local execution state in `.agentic-workspace/planning/state.toml` plus the active execplan, while durable technical guidance stays elsewhere.
- Expects completed plans to archive quickly so active surfaces stay small and merge-friendly.

Bundled skills:

- The package ships planning skills under `skills/`, but new default installs do not copy them into target repositories.
- Use `agentic-planning-bootstrap list-files --format json` to discover bundled skills and optional payload surfaces when a repo chooses to enable richer planning workflows.
- Pass `--include-optional` to `install`, `adopt`, or `upgrade` to copy those optional docs and bundled skills into a repo that intentionally wants the richer workflow.

## Quick Start

Default path: use `agentic-workspace init --preset planning`.
Treat the preset as the user intent: "set up this repo for Agentic Planning" and let the workspace CLI choose the safe install vs adopt path from repo state.
Use the package CLI below only for package-local maintainer work, advanced debugging, or when you explicitly need module-level control.

Fastest no-install path:

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target ./repo

# Alternative when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target ./repo
```

Prefer `uvx` when `uv` is already available. Support `pipx` as the equivalent no-install path when it is the runner a repo already uses.

Use `prompt install` for a clean bootstrap. Use `adopt` when the repository already has planning-like docs and you want the package to merge conservatively around existing surfaces.
After workspace bootstrap, `llms.txt` is the canonical external-agent handoff surface and `.agentic-workspace/bootstrap-handoff.md` is the next-action brief when the repo still needs review.

## Advanced Package Path

Normal public lifecycle path:

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target ./repo --preset planning
```

If you want an agent to perform lifecycle work without a local CLI install, use the paired remote prompt commands below.

### Install Or Adopt

```bash
# Preferred when uvx is available: clean bootstrap
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target ./repo

# Alternative when pipx is available instead: clean bootstrap
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target ./repo

# Preferred when uvx is available: conservative adoption
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt adopt --target ./repo

# Alternative when pipx is available instead: conservative adoption
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt adopt --target ./repo
```

### Upgrade

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt upgrade --target ./repo

# Alternative when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt upgrade --target ./repo
```

### Uninstall

```bash
# Preferred when uvx is available
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt uninstall --target ./repo

# Alternative when pipx is available instead
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt uninstall --target ./repo
```

## Good Fits / Bad Fits

## Stability Contract

The installed planning payload is not one flat compatibility promise.

Treat these files as the current planning compatibility contract surfaces that should not change shape casually:

- `AGENTS.md`
- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/README.md`
- `.agentic-workspace/planning/execplans/TEMPLATE.md`
- `.agentic-workspace/planning/execplans/archive/README.md`
- `.agentic-workspace/docs/lifecycle-and-config-contract.md`
- `.agentic-workspace/docs/execution-flow-contract.md`
- `.agentic-workspace/docs/minimum-operating-model.md`
- `.agentic-workspace/docs/routing-contract.md`
- `.agentic-workspace/docs/system-intent-contract.md`
- `.agentic-workspace/docs/workspace-config-contract.md`
- `.agentic-workspace/planning/agent-manifest.json`

Treat optional package payload and generated mirrors as lower-stability support surfaces unless a stricter promise is stated later. That lower-stability set currently includes bundled skills, review/intake docs, and advanced reporting/orchestration/capability docs. Root-level generated adapter mirrors such as `tools/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, and `tools/AGENT_ROUTING.md` are target-repo generated surfaces, not planning bootstrap payload.

Generated mirrors inherit stability from their canonical source relationships, not from their exact rendered text. If the manifest contract stays stable, the generated wording may still evolve when the renderer improves.

## Direct Execution Or Execplan

`.agentic-workspace/docs/capability-aware-execution.md` is the canonical contract for capability fit: when cheap direct execution is still safe, when medium reasoning is enough, when stronger planning should come first, when bounded autopilot is appropriate, when delegation may save cost, when silent shaping should replace noisy executor-prompting, and when the agent should stop and escalate.
It also defines the bounded-initiative rule: improve means locally, but do not silently widen the requested outcome, owned surface, or time horizon.
`.agentic-workspace/docs/execution-flow-contract.md` is the front-door companion for delegated judgment, active intent continuity, resumability, and execution summaries.
`.agentic-workspace/docs/orchestrator-workflow-contract.md` defines the delegated planner-to-worker workflow and `agentic-planning-bootstrap handoff --format json` surface for agent-agnostic bounded handoff.
`.agentic-workspace/docs/standing-intent-contract.md` defines the standing-intent classification and promotion contract used by the workspace report to route durable repo-wide guidance into the right owner surface.
`.agentic-workspace/docs/system-intent-contract.md` defines how a bounded slice preserves the larger intended outcome and how closure decisions stay honest when the slice completes before the broader lane or issue does.
`.agentic-workspace/docs/execution-flow-contract.md` also defines the restart and execution-summary expectations carried by the canonical `planning_record`.
`.agentic-workspace/docs/lifecycle-and-config-contract.md` defines the ordered environment-recovery path when lifecycle work, repo-state inspection, or validation restart becomes ambiguous.
`.agentic-workspace/docs/execution-flow-contract.md` defines the compact completion summary that archived slices should leave behind.
`.agentic-workspace/docs/context-budget-contract.md` defines the live-working-set versus recoverable-later distinction, the minimum residue that must be externalized before a context shift, the compact pre-work retrieval prompt, the tiny resumability-note form, and the main context-switch triggers.
`.agentic-workspace/docs/routing-contract.md` defines the hierarchy and routing rules between `.agentic-workspace/planning/state.toml`, execplans, and reviews.

For active planning, `agentic-planning-bootstrap summary --format json` is the primary compact inspection path and `planning_record` is the canonical machine-readable active state. The `machine_first_planning` summary block reports whether active execplans are being read from canonical `.plan.json` sidecars or from Markdown compatibility fallback. `active_contract`, `resumable_contract`, `follow_through_contract`, `context_budget_contract`, `hierarchy_contract`, and `handoff_contract` remain thinner views over that record. `system_intent_alignment` records which higher-level intent materially shapes the slice, how it biases the slice shape, and what lane-level validation question remains. `context_budget_contract` now also carries the explicit pre-work retrieval prompt so ordinary work can ask what durable understanding should be recovered before execution and which area it concerns, while leaving Memory optional rather than required.
When an execplan has a sibling `.plan.json` file, that sidecar is the canonical execplan artifact and the `.md` file is treated as a derived human-readable view.
For delegated execution, `agentic-planning-bootstrap handoff --format json` is the compact worker handoff derived from that same active planning state. It now carries intent interpretation, execution bounds, stop conditions, and explicit return-with residue fields for a bounded execution run plus finished-run review, including a compact `changed surfaces` answer for what actually changed.
For cheap delegated-work inspection, `intent_interpretation_contract`, `execution_run_contract`, `finished_run_review_contract`, `intent_validation_contract`, and `finished_work_inspection_contract` remain thin projections over the same active plan and surrounding planning state instead of becoming a second orchestration ledger. `execution_run_contract` keeps intended scope (`scope_touched`) separate from actual changed surfaces (`changed_surfaces`) so returned-run review does not depend on broad diff reconstruction.

`intent_validation_contract` keeps checked-in planning primary while allowing optional reconciliation against ignored `.agentic-workspace/local/cache/external-intent-evidence.json` or legacy `.agentic-workspace/planning/external-intent-evidence.json` when a repo also tracks work elsewhere. Its `external_work_reconciliation` field is the compact first answer for evidence freshness, current external work state, closeout reconciliation, and landed-open checks. Offline planning remains valid when external evidence is absent.
`finished_work_inspection_contract` keeps archived execplan residue primary while allowing provider-agnostic external evidence items with `reopens` refs to lower trust when source-owned work reopens an older closeout. Legacy `.agentic-workspace/planning/finished-work-evidence.json` remains a compatibility input, but stale copied title/status values should not override source-owned external evidence.
For compact module-state reporting without opening raw planning files first, use `agentic-planning-bootstrap report --format json`. It stays derived from the same canonical planning state and does not create a second state store.
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

When delegation is useful, keep it capability-aware and optional. If available, a stronger model may draft a compact execplan or handoff for a smaller implementation model, but only when that is likely to save tokens overall without lowering quality. Do not assume subagents or multi-model workflows exist; the contract should still work for a single agent operating alone.
Use the capability-aware execution contract to describe that recommendation in task-shape terms instead of vendor-specific model names, and prefer silent task shaping over repeated instructions to switch executors manually.
Use the orchestrator workflow contract plus `agentic-planning-bootstrap handoff --format json` when the goal is to reuse the same checked-in handoff across internal delegation, local CLI/API execution, or another vendor executor.

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

## Direct-Task Recovery Cases

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

Good fits:

- a repo where active work drifts between sessions and needs a checked-in active queue
- a repo that wants bounded execution contracts without introducing a full project-management system
- a repo using agents heavily enough that chat-only task continuity is too fragile

Bad fits:

- a repo looking for durable subsystem documentation or knowledge capture rather than execution steering
- a repo expecting a full ticketing, sprint, or PM platform

## Example Scenarios

- Before: each session restarts by rediscovering what mattered last time.
  After: `.agentic-workspace/planning/state.toml` and one active execplan hold the live execution contract.
- Before: follow-on work derails the current thread because there is no compact place to capture it safely.
  After: future work stays in the roadmap section of `.agentic-workspace/planning/state.toml` while the current thread stays bounded.

## Detailed Contracts

Keep this README as the package entrypoint. Use the installed contracts for deep operating rules:

- `.agentic-workspace/docs/execution-flow-contract.md`: active state, execplans, handoff, restart, and closeout.
- `.agentic-workspace/docs/routing-contract.md`: hierarchy between state, execplans, and reviews.

Optional packaged contracts remain discoverable through `agentic-planning-bootstrap list-files --format json` when a repo needs capability-aware execution, review promotion, upstream-task intake, richer reporting, or orchestration workflows.
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
- `.agentic-workspace/planning/execplans/README.md`
- `.agentic-workspace/planning/execplans/TEMPLATE.plan.json`
- `.agentic-workspace/planning/execplans/archive/README.md`
- `.agentic-workspace/planning/schemas/planning-execplan.schema.json`
- `.agentic-workspace/planning/schemas/planning-external-intent-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-finished-work-evidence.schema.json`
- `.agentic-workspace/planning/schemas/planning-review.schema.json`

The package also ships optional payload files that are not copied by default. Use `--include-optional` with `install`, `adopt`, or `upgrade` to copy them on purpose:

- `.agentic-workspace/docs/candidate-lanes-contract.md`
- `.agentic-workspace/docs/capability-aware-execution.md`
- `.agentic-workspace/docs/capability-contract.json`
- `.agentic-workspace/docs/context-budget-contract.md`
- `.agentic-workspace/docs/external-intent-evidence-contract.md`
- `.agentic-workspace/docs/extraction-and-discovery-contract.md`
- `.agentic-workspace/docs/finished-work-inspection-contract.md`
- `.agentic-workspace/docs/installer-behavior.md`
- `.agentic-workspace/docs/knowledge-promotion-workflow.md`
- `.agentic-workspace/docs/orchestrator-workflow-contract.md`
- `.agentic-workspace/docs/reporting-contract.md`
- `.agentic-workspace/docs/signal-hygiene-contract.md`
- `.agentic-workspace/docs/standing-intent-contract.md`
- `.agentic-workspace/planning/pre-ingestion-refinement.md`
- `.agentic-workspace/planning/reviews/README.md`
- `.agentic-workspace/planning/reviews/TEMPLATE.review.json`
- `.agentic-workspace/planning/upstream-task-intake.md`
- bundled skills under `skills/`

It packages:

- the planning contract
- the module-managed planning manifest and helper scripts
- optional review-artifact contract surfaces under `.agentic-workspace/planning/reviews/`
- optional upstream-task intake contract surfaces under `.agentic-workspace/planning/upstream-task-intake.md`
- environment and recovery contract surfaces under `.agentic-workspace/docs/lifecycle-and-config-contract.md`
- file-native helper commands for promotion, archiving, and summary
- starter surfaces
- startup docs and manifest wiring

It does not package repo-specific active execution content.

In this monorepo checkout, the active operational planning install lives at the repository root. This package directory keeps the reusable package source, bootstrap payload, tests, and fixtures; the default planning surfaces listed above describe the target-repository structure that `install` or `adopt` writes.

## Installed Operating Shape

The installed planning state lives under `.agentic-workspace/planning/`.
The root `AGENTS.md` adapter points agents to compact startup commands, and the package payload supplies reusable contracts and templates.

This package can work alongside Agentic Memory, but does not require it: planning owns active execution state, while memory owns durable technical knowledge.

## Commands

- `agentic-planning-bootstrap install --target <repo>`
- `agentic-planning-bootstrap adopt --target <repo>`
- `agentic-planning-bootstrap upgrade --target <repo>`
- `agentic-planning-bootstrap uninstall --target <repo>`
- `agentic-planning-bootstrap doctor --target <repo>`
- `agentic-planning-bootstrap status --target <repo>`
- `agentic-planning-bootstrap summary --target <repo> --format json`
- `agentic-planning-bootstrap promote-to-plan <todo-id> --target <repo>`
- `agentic-planning-bootstrap archive-plan <plan> --target <repo>`
- `agentic-planning-bootstrap archive-plan <plan> --target <repo> --apply-cleanup`
- `agentic-planning-bootstrap list-files`
- `agentic-planning-bootstrap verify-payload`
- `agentic-planning-bootstrap prompt install --target <repo>`
- `python scripts/check/check_maintainer_surfaces.py`
- `make maintainer-surfaces`
- `make planning-surfaces`
- `make planning-surfaces-strict`
- `make render-agent-docs`

`archive-plan --apply-cleanup` is intentionally narrow. It may remove completed active-queue items that still point at the archived plan and compress stale roadmap residue tied to that same thread, but it does not invent hidden state or perform broad automatic rewrites. Archive output is compact inactive-plan residue rather than a full forever-growing copy of the active execplan.

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
