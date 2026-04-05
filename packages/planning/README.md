# agentic-planning-bootstrap

*A checked-in planning system for execution in agent-driven development*

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

## Core Idea

Development is organised across three horizons:

| Horizon | Surface | Role |
| ------ | ------- | ---- |
| Direction | `ROADMAP.md` | What might matter next |
| Activation | `TODO.md` | What matters now |
| Execution | `docs/execplans/` | How the active work is completed |

Each layer has a single responsibility and should not duplicate the others.

## What This System Does

### 1. Preserves long-horizon direction

Candidate epics and strategic intent stay visible without being forced into active execution.

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

### 7. Keeps active surfaces clean

Completed work should leave active surfaces rather than accumulate there.

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

## What the Package Installs

The package installs the checked-in planning contract and its supporting surfaces:

- `AGENTS.md`
- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/README.md`
- `docs/execplans/TEMPLATE.md`
- `docs/execplans/archive/README.md`
- `.agentic-planning/UPGRADE-SOURCE.toml`
- `tools/agent-manifest.json`
- `tools/AGENT_QUICKSTART.md`
- `tools/AGENT_ROUTING.md`
- `scripts/render_agent_docs.py`
- `scripts/check/check_planning_surfaces.py`

It packages:

- the planning contract
- the checker
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
- `make plan-check`
- `make plan-check-json`
- `make plan-check-strict`
- `make plan-summary`

`archive-plan --apply-cleanup` is intentionally narrow. It may remove completed TODO items that still point at the archived plan and compress stale `ROADMAP.md` Active Handoff residue tied to that same thread, but it does not invent hidden state or perform broad automatic rewrites.

`upgrade` is intentionally conservative: it refreshes package-managed helper surfaces and re-renders quickstart output, but leaves repo-owned planning surfaces like `AGENTS.md`, `TODO.md`, `ROADMAP.md`, and `tools/agent-manifest.json` unchanged when they already exist.

`uninstall` is intentionally safe: it removes managed files only when they still match package content and leaves locally modified files in place for manual review.

`.agentic-planning/UPGRADE-SOURCE.toml` records the intended bootstrap source for install and upgrade workflows. `doctor` reports that source and warns when the recorded source age crosses the configured threshold so upgrades remain intentional rather than silently drifting.

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
uv sync --group dev
uv run pytest
make render-agent-docs
make plan-check

# Or from the monorepo root
make check-planning
```
