<!-- GENERATED FILE: do not edit manually. -->

# Agent Routing

> GENERATED STATIC ROUTING ADAPTER. Do not edit manually. Rerender with `python scripts/render_agent_docs.py`.

Static routing table for weak-agent discovery. It does not mirror active state.

## Precedence

1. Explicit user request.
2. Active execplan when `uv run agentic-workspace summary --format json` reports one.
3. `AGENTS.md` and the nearest package-local `AGENTS.md` for the files being edited.
4. Repo docs explicitly referenced by the active route.

## Routing Table

| Situation | Route |
| --- | --- |
| startup order or first-contact routing | `uv run agentic-workspace defaults --section startup --format json` |
| active work, queue, proof, or continuation | `uv run agentic-workspace summary --format json` |
| startup guidance plus resolved config and active state | `uv run agentic-workspace preflight --format json` |
| configured entrypoint, posture, or obligations | `uv run agentic-workspace config --target . --format json` |
| combined workspace/module state | `uv run agentic-workspace report --target . --format json` |
| task-specific package rules | nearest package-local `AGENTS.md` |

## Boundaries

- Keep mutable execution state in `.agentic-workspace/planning/state.toml` and active execplans.
- Keep durable repo knowledge in memory or canonical docs, not in these generated adapters.
- Keep this file state-free; rerendering should not expand it into a manifest mirror.

