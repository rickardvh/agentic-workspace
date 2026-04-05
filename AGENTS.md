# Agent Instructions

Local bootstrap contract for agents working in this repository.

## Precedence

Resolve instruction conflicts in this order:

1. Explicit user request.
2. Active feature plan in `docs/execplans/`, when the task belongs to that plan.
3. `AGENTS.md`.
4. Checked-in workflow or memory policy docs, when present.
5. Repo docs explicitly referenced by the active route or plan.

Prefer checked-in knowledge over durable chat memory when both exist.

## Startup Procedure

1. Read `AGENTS.md`.
2. Read `TODO.md`.
3. Read `docs/execplans/README.md`.
4. Read the active feature plan in `docs/execplans/` when the task belongs to one.
5. Read `ROADMAP.md` only when promoting work, reprioritising, or reviewing candidate epics.
6. Prefer `tools/agent-manifest.json` and `tools/AGENT_QUICKSTART.md` before freeform exploration.
7. Read only the repo docs relevant to the touched subsystem.
8. Read checked-in memory or workflow policy only when the task actually touches those surfaces.

Do not bulk-read all planning surfaces for ordinary execution work. Start from `TODO.md`, then read at most one relevant active execplan.

Do not start coding from chat context alone when the same knowledge should live in checked-in files.

## Sources Of Truth

- Active queue and lightweight direct tasks: `TODO.md`
- Active feature execution contracts: `docs/execplans/`
- Long-horizon planning: `ROADMAP.md`
- Machine-readable routing and command bundles: `tools/agent-manifest.json`
- Agent quickstart and rendered hot paths: `tools/AGENT_QUICKSTART.md`

## Repo Rules

- This is `agentic-planning-bootstrap`.
- Repository purpose: package and maintain a reusable checked-in planning bootstrap that complements `agentic-memory`.
- Key repo docs: `README.md`, `docs/execplans/README.md`, `docs/execplans/TEMPLATE.md`.
- Key subsystems: `bootstrap/`, `src/repo_planning_bootstrap/`, `scripts/check/`, `tools/`.
- Do not broaden migrations, refactors, or schema changes beyond the active task unless a required adjacent fix is necessary for correctness.
- Prefer updating an existing plan over creating overlapping plan files for the same feature.
- Keep durable implementation facts in canonical docs or memory, not in planning surfaces.

## Tooling And Validation

- Primary build command: `uv build`.
- Primary test command: `uv run pytest`.
- Other key commands: `uv run python scripts/render_agent_docs.py`; `uv run python scripts/check/check_planning_surfaces.py`; `uv run ruff check .`.
- Run the narrowest validation that proves the change; escalate to broader checks only when the change crosses subsystem boundaries or the user explicitly asks for it.

## Completion Contract

1. Update `TODO.md`.
2. Update the active plan in `docs/execplans/` when working from one.
3. If a task leaves meaningful follow-up work, record it in the appropriate planning surface before closing the task.
4. Remove completed task detail from `TODO.md` once it no longer changes the next contributor's queue decision.
