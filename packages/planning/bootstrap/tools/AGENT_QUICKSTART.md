<!-- GENERATED FILE: do not edit manually. -->

# Agent Quickstart

> GENERATED FILE. Do not edit manually. Update `.agentic-workspace/planning/agent-manifest.json` and rerender with `python scripts/render_agent_docs.py`.

Fast path for autonomous agents working on this repo.

## First reads

- `AGENTS.md`

## First queries

- Use `agentic-workspace summary --format json` first when active planning recovery or compact ownership state is the question.
- Use `agentic-workspace defaults --section startup --format json` when startup or first-contact routing is the question.
- Use `agentic-workspace config --target ./repo --format json` to find the configured startup entrypoint and effective repo posture.
- Use `agentic-workspace report --target ./repo --format json` when the question is combined workspace state.

## Surface roles

- `AGENTS.md` is the canonical ordinary repo startup entrypoint.
- `.agentic-workspace/planning/state.toml` is the package-owned active queue and candidate-lane state after the compact summary has shown raw detail is needed.
- `.agentic-workspace/docs/routing-contract.md` is the authoritative routing home.
- `llms.txt` is the agent entrypoint router.
- `tools/AGENT_QUICKSTART.md` and `tools/AGENT_ROUTING.md` are generated helpers, not doctrine owners.
- `.agentic-workspace/planning/agent-manifest.json` is the canonical source for the generated helper docs.

## Conditional reads

- Read `agentic-workspace summary --format json` first when planning recovery or ownership boundary review is the question.
- Read `.agentic-workspace/planning/state.toml` only when the compact summary shows active work that still needs raw queue detail.
- Read the active feature plan in `.agentic-workspace/planning/execplans/` when the task belongs to one.
- Read the roadmap data in `.agentic-workspace/planning/state.toml` only when promoting work, reprioritising, or reviewing candidate epics.
- Read `.agentic-workspace/docs/routing-contract.md` when execution hits an edge case, ambiguity, or requires deep context.
- Do not bulk-read all planning surfaces for ordinary execution work; start from `agentic-workspace summary --format json` and then the one relevant active plan.
- Read only the repo docs explicitly referenced by that route.
- When the question is active planning recovery rather than startup order, prefer `agentic-workspace summary --format json`. For configuration and routing, prefer `agentic-workspace defaults --section startup --format json` and `agentic-workspace config --target ./repo --format json` before broader prose.

## Small-task mode

- For very local changes, skip plans unless this manifest, the active plan, or the nearest descendant `AGENTS.md` says they are needed.
- Keep direct tasks in `.agentic-workspace/planning/state.toml` only when one coherent pass can finish them and the row can stay compact: `ID`, `Status`, `Surface`, `Why now`, `Next action`, and `Done when`.
- Use `.agentic-workspace/docs/capability-aware-execution.md` when deciding whether the cheap direct path is still safe or whether medium reasoning is a better fit; prefer silent task shaping over repeated executor-selection prompts.
- Do not create a checked-in plan just because a stronger model could write one; escalate only when the artifact should save more rediscovery, restart cost, or coordination risk than it costs to produce.

## When to create a plan

- Create or update a plan when work spans multiple milestones, will be handed across threads or models, or carries enough ambiguity that implementation should not start from chat context alone.
- Promote a direct task once it picks up blocker handling, validation scope, rollback or migration detail, ownership reconciliation, enough context pressure that a smaller or less capable agent would need checked-in state, or enough narrative that the TODO row stops being self-sufficient.
- If the task is no longer a good fit for the current execution capability, use `.agentic-workspace/docs/capability-aware-execution.md` to decide whether stronger planning, delegation, explicit escalation, or quieter task shaping is the right next step.
- If multi-agent or multi-model delegation is available, a more capable agent may write the compact plan first and hand implementation to a smaller one only when that is likely to save tokens without sacrificing quality.
- Use `.agentic-workspace/docs/execution-flow-contract.md` for orchestrator-worker handoff rules.

## Source of truth

- Active queue and lightweight direct tasks: `.agentic-workspace/planning/state.toml`
- Active feature plans: `.agentic-workspace/planning/execplans/`
- Archived plans: `.agentic-workspace/planning/execplans/archive/`
- Long-horizon planning: `.agentic-workspace/planning/state.toml`
- Machine-readable routing: `.agentic-workspace/planning/agent-manifest.json`

## Validation flow

- Run the narrowest validation that proves the change.
- Use `.agentic-workspace/planning/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, `tools/AGENT_ROUTING.md`, and the nearest subsystem `AGENTS.md` for task-specific commands.
- Escalate to broader checks only when the change crosses subsystem boundaries or invalidates the narrower proof.

## Completion reminders

- Do not leave completed task detail in `.agentic-workspace/planning/state.toml` once it no longer changes execution.
- If the completed slice came from the active queue or roadmap state, clear the matched queue residue in the same pass.
- When direct execution changes durable knowledge or leaves meaningful follow-up, record only that minimal residue in memory, canonical docs, the roadmap state in `.agentic-workspace/planning/state.toml`, or a promoted execplan.

## Generated surfaces

- `tools/agent-manifest.json` is a generated mirror of `.agentic-workspace/planning/agent-manifest.json`.
- `tools/AGENT_QUICKSTART.md` is generated from `.agentic-workspace/planning/agent-manifest.json` by `python scripts/render_agent_docs.py`.
- `tools/AGENT_ROUTING.md` is generated from `.agentic-workspace/planning/agent-manifest.json` by `python scripts/render_agent_docs.py`.

## Common task classes

- `review_workflow`
  Use when: Handling a bounded review, audit, or review-shaped request that should capture findings without activating work automatically.
  Prefer this route when: the request asks for a review, audit, or compact finding capture over one repo area or change.
  Touches: `.agentic-workspace/planning/reviews/`, `.agentic-workspace/docs/extraction-and-discovery-contract.md`, `.agentic-workspace/planning/skills/planning-review-pass/SKILL.md`, `.agentic-workspace/planning/skills/REGISTRY.json`
  Validate: `uv run agentic-workspace skills --target ./repo --task "<task>" --format json`; `make maintainer-surfaces`
- `planning_surface_change`
  Use when: Editing planning-for-execution surfaces, plan templates, or planning-surface checks.
  Prefer this route when: the change affects planning state, execplans, generated agent docs, or the planning bootstrap itself.
  Touches: `AGENTS.md`, `.agentic-workspace/planning/state.toml`, `.agentic-workspace/planning/upstream-task-intake.md`, `.agentic-workspace/docs/lifecycle-and-config-contract.md`, `.agentic-workspace/docs/routing-contract.md`, `.agentic-workspace/docs/execution-flow-contract.md`, `.agentic-workspace/planning/execplans/`, `scripts/check/check_maintainer_surfaces.py`, `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`, `.agentic-workspace/planning/agent-manifest.json`, `tools/AGENT_QUICKSTART.md`, `tools/AGENT_ROUTING.md`
  Validate: `make maintainer-surfaces`; `make render-agent-docs`

## Skills

- Repo development skills: `tools/skills`
- Shared memory workflow skills: `.agentic-workspace/memory/skills`
- Repo-specific memory skills: `memory/skills`

## Core invariants

- .agentic-workspace/planning/state.toml owns active queue state and lightweight direct tasks.
- Active execplans own milestone sequencing, blockers, validation scope, and completion detail for planned work.
- .agentic-workspace/planning/state.toml also owns inactive long-horizon candidate lanes and promotion signals.
- Package-owned planning state belongs under `.agentic-workspace/planning/` and should be summarized before root queue files are read.
- Checked-in memory, when installed, owns durable routed knowledge rather than active planning state.
- Planning should remain useful without memory being installed.
- Direct execution is a valid success mode for small local work.
- Do not bulk-read all planning surfaces for ordinary execution work.
