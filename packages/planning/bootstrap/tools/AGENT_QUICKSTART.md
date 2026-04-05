<!-- GENERATED FILE: do not edit manually. -->

# Agent Quickstart

> GENERATED FILE. Do not edit manually. Update `.agentic-workspace/planning/agent-manifest.json` and rerender with `python scripts/render_agent_docs.py`.

Fast path for autonomous agents working on this repo.

## First reads

- `AGENTS.md`
- `TODO.md`
- `docs/execplans/README.md`
- `.agentic-workspace/planning/agent-manifest.json`

## Conditional reads

- Read the active feature plan in `docs/execplans/` when the task belongs to one.
- Read `ROADMAP.md` only when promoting work, reprioritising, or reviewing candidate epics.
- Before editing files in a subtree, read the nearest relevant descendant `AGENTS.md` for that subtree only.
- Read `memory/index.md` and `.agentic-workspace/memory/WORKFLOW.md` only when memory is installed and the plan or manifest does not already route the task, or when changing workflow, planning, or memory itself.
- Do not bulk-read all planning surfaces for ordinary execution work; start from `TODO.md` and then the one relevant active plan.
- Read only the repo docs explicitly referenced by that route.

## Small-task mode

- For very local changes, skip plans unless this manifest, the active plan, or the nearest descendant `AGENTS.md` says they are needed.

## When to create a plan

- Create or update a plan when work spans multiple milestones, will be handed across threads or models, or carries enough ambiguity that implementation should not start from chat context alone.

## Source of truth

- Active queue and lightweight direct tasks: `TODO.md`
- Active feature plans: `docs/execplans/`
- Archived plans: `docs/execplans/archive/`
- Long-horizon planning: `ROADMAP.md`
- Machine-readable routing: `.agentic-workspace/planning/agent-manifest.json`

## Validation flow

- Run the narrowest validation that proves the change.
- Use `.agentic-workspace/planning/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, `tools/AGENT_ROUTING.md`, and the nearest subsystem `AGENTS.md` for task-specific commands.
- Escalate to broader checks only when the change crosses subsystem boundaries or invalidates the narrower proof.

## Completion reminders

- Do not leave completed task detail in `TODO.md` once it no longer changes execution.

## Generated surfaces

- `tools/agent-manifest.json` is a generated mirror of `.agentic-workspace/planning/agent-manifest.json`.
- `tools/AGENT_QUICKSTART.md` is generated from `.agentic-workspace/planning/agent-manifest.json` by `python scripts/render_agent_docs.py`.
- `tools/AGENT_ROUTING.md` is generated from `.agentic-workspace/planning/agent-manifest.json` by `python scripts/render_agent_docs.py`.

## Common task classes

- `planning_surface_change`
  Use when: Editing planning-for-execution surfaces, plan templates, or planning-surface checks.
  Prefer this route when: the change affects TODO, ROADMAP, execplans, or the planning bootstrap itself.
  Touches: `AGENTS.md`, `TODO.md`, `ROADMAP.md`, `docs/execplans/`, `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`, `.agentic-workspace/planning/scripts/render_agent_docs.py`, `.agentic-workspace/planning/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, `tools/AGENT_ROUTING.md`
  Validate: `make planning-surfaces`; `make render-agent-docs`

## Skills

- Repo development skills: `tools/skills`
- Shared memory workflow skills: `.agentic-workspace/memory/skills`
- Repo-specific memory skills: `memory/skills`

## Core invariants

- TODO.md owns active queue state and lightweight direct tasks.
- Active execplans own milestone sequencing, blockers, validation scope, and completion detail for planned work.
- ROADMAP.md owns inactive long-horizon candidate epics and promotion signals.
- Checked-in memory, when installed, owns durable routed knowledge rather than active planning state.
- Planning should remain useful without memory being installed.
- Do not bulk-read all planning surfaces for ordinary execution work.
