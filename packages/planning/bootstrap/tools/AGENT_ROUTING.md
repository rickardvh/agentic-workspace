# Agent Routing

Focused routing reference derived from `.agentic-workspace/planning/agent-manifest.json`.

## Precedence

- Explicit user request.
- Active feature plan in `docs/execplans/`, when the task belongs to that plan.
- `AGENTS.md`.
- Repo docs explicitly referenced by the active route or plan.

## Task Routes

### `planning_surface_change`

- Use when: Editing planning-for-execution surfaces, plan templates, or planning-surface checks.
- Prefer when: the change affects TODO, ROADMAP, execplans, or the planning bootstrap itself.
- Touches:
  - `AGENTS.md`
  - `TODO.md`
  - `ROADMAP.md`
  - `docs/execplans/`
  - `.agentic-workspace/planning/scripts/check/check_planning_surfaces.py`
  - `.agentic-workspace/planning/scripts/render_agent_docs.py`
  - `.agentic-workspace/planning/agent-manifest.json`
  - `tools/AGENT_QUICKSTART.md`
  - `tools/AGENT_ROUTING.md`
- Validation:
  - `make plan-check`
  - `python scripts/render_agent_docs.py`

