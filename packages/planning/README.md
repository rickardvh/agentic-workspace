# agentic-planning-bootstrap

Agentic Planning is a checked-in planning-for-execution contract, currently distributed as the `agentic-planning-bootstrap` package and CLI.

## At A Glance

Choose this package when you want active work in a repository to stay bounded, resumable, and finishable across fragmented sessions.

Use it for:

- keeping a small active queue in `TODO.md`
- storing inactive future candidates in `ROADMAP.md`
- attaching bounded execution contracts to active work in `docs/execplans/`
- capturing analysis-derived future-work findings in `docs/reviews/` before promotion
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
- Keeps branch-local execution state in TODO plus the active execplan, while durable technical guidance stays elsewhere.
- Expects completed plans to archive quickly so active surfaces stay small and merge-friendly.

Bundled skills:

- The package also ships `planning-autopilot` under `skills/` and installs it into `.agentic-workspace/planning/skills/` for bounded milestone execution from the checked-in planning surfaces.
- It also ships `planning-intake-upstream-task` for tracker-agnostic upstream issue or task intake into checked-in planning.

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
- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/README.md`
- `docs/execplans/TEMPLATE.md`
- `docs/execplans/archive/README.md`
- `docs/reviews/README.md`
- `docs/reviews/TEMPLATE.md`
- `docs/upstream-task-intake.md`
- `docs/environment-recovery-contract.md`
- `.agentic-workspace/planning/agent-manifest.json`

Treat helper scripts and generated mirrors as lower-stability support surfaces unless a stricter promise is stated later. That lower-stability set currently includes the render and check scripts under `scripts/` and `.agentic-workspace/planning/scripts/`, plus generated mirrors such as `tools/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, and `tools/AGENT_ROUTING.md`.

Generated mirrors inherit stability from their canonical source relationships, not from their exact rendered text. If the manifest contract stays stable, the generated wording may still evolve when the renderer improves.

## Direct Execution Or Execplan

`docs/capability-aware-execution.md` is the canonical contract for capability fit: when cheap direct execution is still safe, when medium reasoning is enough, when stronger planning should come first, when bounded autopilot is appropriate, when delegation may save cost, when silent shaping should replace noisy executor-prompting, and when the agent should stop and escalate.
It also defines the bounded-initiative rule: improve means locally, but do not silently widen the requested outcome, owned surface, or time horizon.
`docs/delegated-judgment-contract.md` is the front-door companion: what the human should specify, what the agent may decide locally, and what should become an explicit promotion or escalation decision.
`docs/intent-contract.md` defines the compact machine-readable active intent contract exposed through `agentic-planning-bootstrap summary --format json` as a view over the canonical `planning_record`.
`docs/resumable-execution-contract.md` defines the smaller machine-readable restart contract as a view over the same canonical `planning_record`.
`docs/environment-recovery-contract.md` defines both how task-local environment assumptions and recovery paths should be expressed without growing a second plan schema, and the ordered recovery path when lifecycle work, repo-state inspection, or validation restart becomes ambiguous.
`docs/execution-summary-contract.md` defines the compact completion summary that archived slices should leave behind.
`docs/planning-routing-contract.md` defines the hierarchy and routing rules between `ROADMAP.md`, `TODO.md`, execplans, and reviews.

For active planning, `agentic-planning-bootstrap summary --format json` is the primary compact inspection path and `planning_record` is the canonical machine-readable active state. `active_contract`, `resumable_contract`, `follow_through_contract`, and `hierarchy_contract` remain thinner views over that record.
For compact module-state reporting without opening raw planning files first, use `agentic-planning-bootstrap report --format json`. It stays derived from the same canonical planning state and does not create a second state store.
Use `hierarchy_contract` when you need the larger-picture restart answer cheaply: active chunk, parent lane, next likely chunk, continuation owner, and proof state.

Use a direct task in `TODO.md` when the work is small enough to finish in one coherent pass and does not need milestone sequencing, blocker tracking, or a wider validation story.

Treat the direct-task shape as compact by default:

- `ID`
- `Status`
- `Surface`
- `Why now`
- `Next action`
- `Done when`

Do not promote work into an execplan just because a more capable model or agent is available. Advanced agents already have session-local planning; checked-in planning should appear only when it reduces rediscovery, restart cost, or coordination risk more than it costs to write.

Promote the task into `docs/execplans/` when any of the following becomes true:

- the work now spans more than one milestone or session-sized checkpoint
- the next contributor would need explicit blocker or dependency handling
- validation scope has to be spelled out instead of staying obvious from the change
- rollback, migration, or ownership-reconciliation detail appears
- the TODO row starts carrying extra execution fields or long narrative text
- the implementing agent lacks enough context window, tools, or local planning support to hold the task safely in one pass

Direct execution is an explicit success mode for small local work. The goal is not to force every change through planning; the goal is to promote only when the cheap path stops being safe.

When delegation is useful, keep it capability-aware and optional. If available, a stronger model may draft a compact execplan or handoff for a smaller implementation model, but only when that is likely to save tokens overall without lowering quality. Do not assume subagents or multi-model workflows exist; the contract should still work for a single agent operating alone.
Use the capability-aware execution contract to describe that recommendation in task-shape terms instead of vendor-specific model names, and prefer silent task shaping over repeated instructions to switch executors manually.

If stronger capability keeps seeming necessary for the same class of work, treat that as a product signal for cheaper future execution. The next step is often better decomposition, clearer validation, or tighter guidance rather than accepting stronger execution as the permanent answer.

When a repo also installs Agentic Memory, Planning should borrow durable context from routed memory notes instead of re-explaining the same subsystem background inside each execplan. Completed planning residue should promote durable lessons into memory or canonical docs when they remain expensive to rediscover.

When a direct task completes, remove it from `TODO.md` promptly. If the task changed durable repo knowledge or left important follow-up work, record that residue in memory, canonical docs, `ROADMAP.md`, or a newly promoted execplan rather than leaving chat-only context behind.
If the completed slice came from `TODO.md` or `ROADMAP.md`, clear the matched queue residue in the same pass instead of leaving stale completed entries behind.
When a bounded slice completes only part of a larger intended outcome, do not close it with required continuation only in prose.
Execplans now treat four fields as first-class:

- `Intent Continuity`: whether the larger intended outcome is actually complete and what checked-in surface now owns it if not
- `Required Continuation`: whether follow-on is mandatory for that larger outcome, plus the owner surface and activation trigger
- `Iterative Follow-Through`: what the slice enabled, what it intentionally deferred, what new implications were discovered, and what proof or validation still carries forward
- `Execution Summary`: what the slice delivered, how validation was confirmed, where follow-on was routed, and how later work should resume
When an execplan is carrying broad direction across sessions, it should also record a compact `Delegated Judgment` section:

- `Requested outcome`
- `Hard constraints`
- `Agent may decide locally`
- `Escalate when`

If required follow-on remains, archive should happen only after those fields point at a checked-in next owner.
Completed plans should also leave an explicit execution summary before archive so later contributors do not have to reconstruct the outcome from drift prose or chat.
If the slice stopped intentionally rather than finishing the broader goal, keep `Iterative Follow-Through` current so the next bounded slice inherits the right residue without rereading the full plan.
Optional nice-to-have follow-up can still stay out of the archive gate.

## Direct-Task Recovery Cases

Keep the task direct only while the TODO row stays self-sufficient.

Promote into an execplan when any of these cases appears:

- interrupted work now needs an explicit restart or resume path
- a handoff between sessions, contributors, or models would require more than one TODO row
- partial failure or retry handling needs to be spelled out
- concurrent branch work creates merge, ownership, or sequencing risk
- stale residue would otherwise be left in `TODO.md` because the task can no longer close in one pass
- a compact checked-in plan would let a smaller or less capable agent implement safely without re-deriving the whole task

The practical test is simple: if safe continuation depends on more than `Why now`, `Next action`, and `Done when`, the work is no longer a direct task.
Use `docs/environment-recovery-contract.md` to keep that recovery guidance compact and in existing planning fields instead of inventing ad hoc restart prose.

Good fits:

- a repo where active work drifts between sessions and needs a checked-in active queue
- a repo that wants bounded execution contracts without introducing a full project-management system
- a repo using agents heavily enough that chat-only task continuity is too fragile

Bad fits:

- a repo looking for durable subsystem documentation or knowledge capture rather than execution steering
- a repo expecting a full ticketing, sprint, or PM platform

## Example Scenarios

- Before: each session restarts by rediscovering what mattered last time.
  After: `TODO.md` and one active execplan hold the live execution contract.
- Before: follow-on work derails the current thread because there is no compact place to capture it safely.
  After: future work goes to `ROADMAP.md` while the current thread stays bounded.

## Overview

`agentic-planning-bootstrap` is a file-based planning system for execution designed for repositories where development is performed by AI agents, humans working in short fragmented sessions, or both.

Its purpose is simple:

> Preserve direction, constrain active work, and ensure progress happens in coherent, completed threads.

Unlike traditional task trackers, this package is not primarily about managing tasks.
It is about keeping execution aligned over time.

This repo is both the self-hosted reference install for that contract and the packaging source for the reusable bootstrap payload.

## The Problem It Solves

In agent-driven or session-based development, work tends to degrade over time:

- long-term goals get forgotten
- agents drift into low-value side work
- partially completed features accumulate
- context must be re-derived every session
- follow-on work derails current execution

This package helps prevent that by installing a structured execution layer that lives in the repo itself.

For many users the simplest mental model is: planning owns what matters now, what comes next, and what counts as done.

## Core Idea

Development is organised across three horizons:

| Horizon | Surface | Role |
| ------ | ------- | ---- |
| Direction | `ROADMAP.md` | What might matter next through compact candidate lanes |
| Activation | `TODO.md` | What matters now |
| Execution | `docs/execplans/` | How the active work is completed |

Each layer has a single responsibility and should not duplicate the others.

## What This System Does

### 1. Preserves long-horizon direction

Candidate lanes and strategic intent stay visible without being forced into active execution.

### 2. Constrains active work

Only a small number of items should be active at any given time, which reduces overload and drift.

### 3. Enforces execution contracts

Every meaningful piece of active work can be backed by a structured execution contract that defines:

- scope
- next action
- blockers
- validation
- completion criteria

### 4. Enables cheap resumption

In the normal startup path, agents should be able to restart work by reading:

`AGENTS.md -> TODO.md -> one execplan -> begin execution`

No large context load should be required.

### 5. Prevents partial work accumulation

The system biases strongly toward finishing and integrating work rather than starting new work.

### 6. Captures follow-on work safely

New ideas and follow-ups are routed into:

- the roadmap, for future work
- the active plan, if immediately relevant

without breaking execution focus.
Required continuation for an unfinished larger intended outcome must be routed into a checked-in owner before the current slice closes; it should not survive only as drift-log prose or chat residue.

### 7. Keeps active surfaces clean

Completed work should leave active surfaces rather than accumulate there.
`TODO.md` should stay a live activation surface, not a running list of what was finished in the current pass.

## Key Properties

### Multi-horizon structure

Clear separation between:

- direction
- activation
- execution

### Anti-drift by design

The checked-in surfaces preserve intent across fragmented sessions.

### Single-thread bias

The contract encourages finishing work before expanding scope.

### Context compression

Agents can operate with minimal working context.

### Archive-over-accumulation

Active files stay small and current.

### File-native and inspectable

- plain Markdown and JSON
- version-controlled
- no runtime dependencies in the adopting repo
- no hidden state

## Ownership Boundary

Put information in planning when it changes what is active now, what comes next, or what counts as done for live work.

Planning owns:

- roadmap state
- active queue state
- execplan structure
- bounded review-artifact structure for future-work discovery
- milestone sequencing
- blockers and completion criteria for live work
- planning-surface lifecycle helpers

Planning does not own:

- durable subsystem memory
- recurring technical lessons that outlive the active task
- routing of durable note bundles
- broad knowledge-base content
- canonical architecture documentation

## Review-Driven Future Work Discovery

Planning includes a bounded review lane for deliberate future-work discovery:

- `docs/reviews/` captures review artifacts
- `ROADMAP.md` receives promoted future candidates
- `TODO.md` plus `docs/execplans/` receive only the findings that are explicitly activated

The review lane exists so analysis-derived findings do not masquerade as friction-confirmed work.
Its rules are:

- capture and promotion are separate steps
- each finding carries evidence, confidence, source class, and promotion guidance
- friction-confirmed findings remain higher trust than pure analysis findings
- weak or speculative findings should be dismissed instead of promoted

The shipped review contract now includes a canonical review portfolio with named bounded modes such as `contract-integrity`, `planning-surface`, `current-context`, `memory-boundary`, `maintainer-workflow`, `source-payload-install`, and `generated-surface-trust`, plus occasional audit modes for `validation-lane`, `context-cost`, and `review-promotion`.
Each mode defines what to inspect first, the typical finding class, the likely promotion target, and a default output cap so reviews do not turn into open-ended critique.
The review lane also now defines an explicit improvement-targeting workflow so symptom-like memory or review signals choose one remediation target, route into the right surface, and then shrink, stub, or disappear after remediation instead of lingering as workaround residue.

Use review artifacts when a task is a bounded review pass rather than implementation.
Do not use them as a substitute for durable docs, memory notes, or active execplans.

## Upstream Task Intake

Planning also includes a tracker-agnostic intake contract for work that starts in an external tracker but should execute from checked-in planning.

- `docs/upstream-task-intake.md` owns the intake rules
- `ROADMAP.md` owns inactive accepted upstream candidates
- `TODO.md` owns only the active queue
- `docs/execplans/` own detailed intake metadata for active promoted work

The contract is intentionally neutral across GitHub Issues, Linear, Jira, Notion, and other upstream systems.
The external tracker may supply the signal, but once the work is promoted, checked-in planning remains the execution authority.

## What This Is Not

`agentic-planning-bootstrap` is deliberately not primarily:

- a task tracker
- a backlog manager
- a project management system
- a knowledge base
- a documentation system
- a database-backed planner
- a runtime orchestration tool

It is not meant to become a Jira replacement, even though a repo may use it for lightweight planning and tracking.

## Anti-Blur Rules

- Planning must not become a knowledge base.
- Planning should not absorb durable technical residue that belongs in memory or canonical docs.
- Planning should stay useful on its own; it must not require a memory install to make sense.
- The package should preserve clear horizons rather than growing a shadow routing or orchestration layer inside planning surfaces.

## What the Package Installs

The package installs the checked-in planning contract and its supporting surfaces:

- `AGENTS.md`
- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/README.md`
- `docs/execplans/TEMPLATE.md`
- `docs/execplans/archive/README.md`
- `docs/upstream-task-intake.md`
- `docs/environment-recovery-contract.md`
- `.agentic-workspace/planning/UPGRADE-SOURCE.toml`
- `.agentic-workspace/planning/agent-manifest.json`
- `.agentic-workspace/planning/scripts/render_agent_docs.py`
- `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
- `.agentic-workspace/planning/scripts/check/check_maintainer_surfaces.py`
- `tools/agent-manifest.json`
- `tools/AGENT_QUICKSTART.md`
- `tools/AGENT_ROUTING.md`
- `scripts/render_agent_docs.py`
- `scripts/check/check_planning_surfaces.py`
- `scripts/check/check_maintainer_surfaces.py`

It packages:

- the planning contract
- the module-managed planning manifest and helper scripts
- generated mirrors and thin root wrappers for repo ergonomics
- review-artifact contract surfaces under `docs/reviews/`
- upstream-task intake contract surfaces under `docs/upstream-task-intake.md`
- environment and recovery contract surfaces under `docs/environment-recovery-contract.md`
- file-native helper commands for promotion, archiving, and summary
- starter surfaces
- startup docs and manifest wiring

It does not package repo-specific active execution content.

In this monorepo checkout, the active operational planning install lives at the repository root. This package directory keeps the reusable package source, bootstrap payload, tests, and fixtures; the planning surfaces listed above describe the target-repository structure that `install` or `adopt` writes.

## Repository Structure

```text
TODO.md                    # activation surface
ROADMAP.md                 # long-horizon direction
docs/execplans/            # execution contracts
docs/execplans/archive/    # completed plans
scripts/check/             # validation tooling
```

## Execution Model

### 1. Start from the startup surface

Read `AGENTS.md`, then `TODO.md`, and select one active item.

### 2. Load the execution contract

If the item references an execplan, read that plan.

### 3. Execute in small steps

Follow:

- immediate next action
- validation commands
- invariants

### 4. Keep scope tight

Do not expand beyond:

- touched paths
- defined scope

### 5. Capture follow-on work

- future work goes to the roadmap
- immediate execution follow-through goes into the active plan

### 6. Complete and archive

Once done:

- remove the item from `TODO.md`
- mark the active milestone completed
- archive the execplan when it no longer affects future execution

## Design Principles

### One surface per concern

- `TODO.md` -> activation only
- `docs/execplans/` -> execution only
- `ROADMAP.md` -> direction only

### No duplication of intent

Each idea should have one primary home.
If a slice leaves required continuation behind, that continuation should also have one explicit checked-in owner and trigger.

### Plans are contracts, not notebooks

Execplans should remain:

- bounded
- concise
- actionable

### Archive aggressively

Completed work should leave active surfaces quickly.

### Minimal startup context

Agents should not need to read the entire system to begin work.

### Preserve the proven contract

The package should stabilise and document the repo-native contract already proved in practice, not replace it with unnecessary schema invention.

## Relationship to Memory Systems

This system is designed to work alongside a memory layer such as `agentic-memory`, but does not depend on it.

- planning -> active work, sequencing, intent
- memory -> durable technical knowledge

Interaction points:

- execplans may reference memory notes
- durable insights may be promoted to memory
- memory may use planning context such as touched paths for routing

But planning remains the owner of execution state.

Planning should remain useful in a repo with no memory installed at all, and memory should remain useful in a repo that uses a different planning system.

## When to Use This

This system is most useful when:

- working with AI agents across many sessions
- development is iterative and exploratory
- long-term direction matters
- work tends to fragment or stall
- you want tight control over active scope

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

`archive-plan --apply-cleanup` is intentionally narrow. It may remove completed TODO items that still point at the archived plan and compress stale `ROADMAP.md` Active Handoff residue tied to that same thread, but it does not invent hidden state or perform broad automatic rewrites.

`upgrade` is intentionally conservative: it refreshes package-managed helper surfaces and re-renders generated planning docs, but leaves repo-owned planning surfaces like `AGENTS.md`, `TODO.md`, and `ROADMAP.md` unchanged when they already exist.
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
