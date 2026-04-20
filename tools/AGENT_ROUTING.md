<!-- GENERATED FILE: do not edit manually. -->

# Agent Routing

> GENERATED FILE. Do not edit manually. Update `.agentic-workspace/planning/agent-manifest.json` and rerender with `python scripts/render_agent_docs.py`.

Focused routing reference derived from `.agentic-workspace/planning/agent-manifest.json`.

## Precedence

- Explicit user request.
- Active feature plan in `docs/execplans/`, when the task belongs to that plan.
- `AGENTS.md`.
- Repo docs explicitly referenced by the active route or plan.

## Task Routes

### `review_workflow`

- Use when: Handling a bounded review, audit, or review-shaped request that should capture findings without activating work automatically.
- Prefer when: the request asks for a review, audit, or compact finding capture over one repo area or change.
- Touches:
  - `docs/reviews/`
  - `docs/extraction-and-discovery-contract.md`
  - `.agentic-workspace/planning/skills/planning-review-pass/SKILL.md`
  - `.agentic-workspace/planning/skills/REGISTRY.json`
- Validation:
  - `uv run agentic-workspace skills --target ./repo --task "<task>" --format json`
  - `make maintainer-surfaces`

### `planning_surface_change`

- Use when: Editing planning-for-execution surfaces, plan templates, or planning-surface checks.
- Prefer when: the change affects planning state, execplans, generated agent docs, or the planning bootstrap itself.
- Touches:
  - `AGENTS.md`
  - `.agentic-workspace/planning/state.toml`
  - `docs/upstream-task-intake.md`
  - `docs/lifecycle-and-config-contract.md`
  - `docs/routing-contract.md`
  - `docs/execution-flow-contract.md`
  - `docs/execplans/`
  - `scripts/check/check_maintainer_surfaces.py`
  - `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
  - `.agentic-workspace/planning/agent-manifest.json`
  - `tools/AGENT_QUICKSTART.md`
  - `tools/AGENT_ROUTING.md`
- Validation:
  - `make maintainer-surfaces`
  - `make render-agent-docs`

