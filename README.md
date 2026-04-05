# agentic-planning-bootstrap

A small CLI and packaged payload for installing a checked-in planning system into a repository.

This repo is the planning-system sister package to `agentic-memory`. Memory owns durable repo knowledge; planning owns active queue state, active execution contracts, and inactive strategic candidates.

## What it installs

- `AGENTS.md`
- `TODO.md`
- `ROADMAP.md`
- `docs/execplans/README.md`
- `docs/execplans/TEMPLATE.md`
- `docs/execplans/archive/README.md`
- `tools/agent-manifest.json`
- `tools/AGENT_QUICKSTART.md`
- `scripts/render_agent_docs.py`
- `scripts/check/check_planning_surfaces.py`

## Commands

- `agentic-planning-bootstrap install --target <repo>`
- `agentic-planning-bootstrap adopt --target <repo>`
- `agentic-planning-bootstrap doctor --target <repo>`
- `agentic-planning-bootstrap status --target <repo>`
- `agentic-planning-bootstrap list-files`
- `agentic-planning-bootstrap verify-payload`
- `agentic-planning-bootstrap prompt install --target <repo>`

## Development

```bash
uv sync --group dev
uv run pytest
uv run python scripts/render_agent_docs.py
uv run python scripts/check/check_planning_surfaces.py
```
