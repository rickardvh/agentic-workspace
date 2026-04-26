<!-- GENERATED FILE: do not edit manually. -->

# Agent Routing

> GENERATED STATIC ROUTING ADAPTER. Do not edit manually. Rerender with `python scripts/render_agent_docs.py`.

Generated, state-free routing helper. Use compact commands for current truth.

## Precedence

1. Explicit user request.
2. Active execplan when `uv run agentic-workspace summary --format json` reports one.
3. `AGENTS.md` and the nearest package-local `AGENTS.md` for the files being edited.
4. Repo docs explicitly referenced by the active route.

## Compact Queries

- `uv run agentic-workspace start --format json` for ordinary compact startup context.
- `uv run agentic-workspace preflight --format json` for bundled takeover or recovery context.
- `uv run agentic-workspace summary --format json` for active planning, queue, proof, or continuation.
- `uv run agentic-workspace config --target . --format json` for configured entrypoint, posture, or obligations.
- `uv run agentic-workspace report --target . --format json` for health, warnings, and selectors to deeper detail.

## Boundaries

- Keep mutable execution state in `.agentic-workspace/planning/state.toml` and active execplans.
- Keep durable repo knowledge in memory or canonical docs, not in these generated adapters.
- Keep this file state-free; rerendering should not expand it into a manifest mirror.

