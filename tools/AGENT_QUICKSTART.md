<!-- GENERATED FILE: do not edit manually. -->

# Agent Quickstart

> GENERATED FILE. Do not edit manually. Update `.agentic-workspace/planning/agent-manifest.json` and rerender with `python scripts/render_agent_docs.py`.

Fast path for autonomous agents working on this repo.

## First reads

- `AGENTS.md`
- `TODO.md`

## First queries

- Use `agentic-workspace report --startup --format json` for immediate high-signal orientation (Active Goal, Next Action, Constraints).
- Use `agentic-workspace defaults --section startup --format json` when startup or first-contact routing is the question.
- Use `agentic-workspace config --target ./repo --format json` to find the configured startup entrypoint and effective repo posture.
- Use `agentic-workspace summary --format json` when the question is active planning recovery rather than startup order.
- Use `agentic-workspace report --target ./repo --format json` when the question is combined workspace state.

## Surface roles

- `AGENTS.md` is the canonical ordinary repo startup entrypoint.
- `TODO.md` is the canonical active queue after startup.
- `docs/routing-contract.md` is the authoritative routing home.
- `llms.txt` is the agent entrypoint router.
- `tools/AGENT_QUICKSTART.md` and `tools/AGENT_ROUTING.md` are generated helpers, not doctrine owners.
- `.agentic-workspace/planning/agent-manifest.json` is the canonical source for the generated helper docs.

## Conditional reads

- Read the active feature plan in `docs/execplans/` when the task belongs to one.
- Read `ROADMAP.md` only when promoting work, reprioritising, or reviewing candidate epics.
- Read `docs/routing-contract.md` when execution hits an edge case, ambiguity, or requires deep context.
- Do not bulk-read all planning surfaces for ordinary execution work; start from `TODO.md` and then the one relevant active plan.
- Read only the repo docs explicitly referenced by that route.
- When the question is active planning recovery rather than startup order, prefer `agentic-workspace summary --format json`. For configuration and routing, prefer `agentic-workspace defaults --section startup --format json` and `agentic-workspace config --target ./repo --format json` before broader prose.

## Small-task mode

- For very local changes, skip plans unless this manifest, the active plan, or the nearest descendant `AGENTS.md` says they are needed.
- Keep direct tasks in `TODO.md` only when one coherent pass can finish them and the row can stay compact: `ID`, `Status`, `Surface`, `Why now`, `Next action`, and `Done when`.
- Use `docs/capability-aware-execution.md` when deciding whether the cheap direct path is still safe or whether medium reasoning is a better fit; prefer silent task shaping over repeated executor-selection prompts.
- Do not create a checked-in plan just because a stronger model could write one; escalate only when the artifact should save more rediscovery, restart cost, or coordination risk than it costs to produce.

## When to create a plan

- Create or update a plan when work spans multiple milestones, will be handed across threads or models, or carries enough ambiguity that implementation should not start from chat context alone.
- Promote a direct task once it picks up blocker handling, validation scope, rollback or migration detail, ownership reconciliation, enough context pressure that a smaller or less capable agent would need checked-in state, or enough narrative that the TODO row stops being self-sufficient.
- If the task is no longer a good fit for the current execution capability, use `docs/capability-aware-execution.md` to decide whether stronger planning, delegation, explicit escalation, or quieter task shaping is the right next step.
- If multi-agent or multi-model delegation is available, a more capable agent may write the compact plan first and hand implementation to a smaller one only when that is likely to save tokens without sacrificing quality.
- Use `docs/execution-flow-contract.md` for orchestrator-worker handoff rules.

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
- If the completed slice came from `TODO.md` or `ROADMAP.md`, clear the matched queue residue in the same pass.
- When direct execution changes durable knowledge or leaves meaningful follow-up, record only that minimal residue in memory, canonical docs, `ROADMAP.md`, or a promoted execplan.

## Generated surfaces

- `tools/agent-manifest.json` is a generated mirror of `.agentic-workspace/planning/agent-manifest.json`.
- `tools/AGENT_QUICKSTART.md` is generated from `.agentic-workspace/planning/agent-manifest.json` by `python scripts/render_agent_docs.py`.
- `tools/AGENT_ROUTING.md` is generated from `.agentic-workspace/planning/agent-manifest.json` by `python scripts/render_agent_docs.py`.

## Common task classes

- `review_workflow`
  Use when: Handling a bounded review, audit, or review-shaped request that should capture findings without activating work automatically.
  Prefer this route when: the request asks for a review, audit, or compact finding capture over one repo area or change.
  Touches: `docs/reviews/`, `docs/extraction-and-discovery-contract.md`, `.agentic-workspace/planning/skills/planning-review-pass/SKILL.md`, `.agentic-workspace/planning/skills/REGISTRY.json`
  Validate: `uv run agentic-workspace skills --target ./repo --task "<task>" --format json`; `make maintainer-surfaces`
- `planning_surface_change`
  Use when: Editing planning-for-execution surfaces, plan templates, or planning-surface checks.
  Prefer this route when: the change affects TODO, ROADMAP, execplans, or the planning bootstrap itself.
  Touches: `AGENTS.md`, `TODO.md`, `ROADMAP.md`, `docs/upstream-task-intake.md`, `docs/lifecycle-and-config-contract.md`, `docs/routing-contract.md`, `docs/execution-flow-contract.md`, `docs/execplans/`, `scripts/check/check_maintainer_surfaces.py`, `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`, `.agentic-workspace/planning/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, `tools/AGENT_ROUTING.md`
  Validate: `make maintainer-surfaces`; `make render-agent-docs`

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
- Direct execution is a valid success mode for small local work.
- Do not bulk-read all planning surfaces for ordinary execution work.
