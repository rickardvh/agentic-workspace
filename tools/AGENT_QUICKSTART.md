<!-- GENERATED FILE: do not edit manually. -->

# Agent Quickstart

> GENERATED STATIC ROUTING ADAPTER. Do not edit manually. Rerender with `python scripts/render_agent_docs.py`.

Static, non-authoritative entry table for agents that need one obvious next surface.

## Start Here

- Read `AGENTS.md` first.
- Run `uv run agentic-workspace preflight --format json` for startup guidance plus active state.
- Run `uv run agentic-workspace summary --format json` when active planning recovery is the question.
- Run `uv run agentic-workspace defaults --section startup --format json` when startup order is the question.

## Authority Table

| Need | Use |
| --- | --- |
| ordinary repo startup | `AGENTS.md` |
| compact startup/config state | `uv run agentic-workspace preflight --format json` |
| active planning and continuation | `uv run agentic-workspace summary --format json` |
| configured entrypoint/posture | `uv run agentic-workspace config --target . --format json` |
| machine-readable routing mirror | `.agentic-workspace/planning/agent-manifest.json` |

## Constraints

- This file is a generated static adapter, not a doctrine or state owner.
- Do not bulk-read all planning surfaces; follow compact query results to the one needed file.
- Keep changing operational truth in structured/queryable surfaces, not in this helper.

## Escalation Table

| Boundary | First move |
| --- | --- |
| workspace startup, lifecycle, ownership, or config | `uv run agentic-workspace defaults --section startup --format json` |
| planning sequence, blockers, proof, or continuation | `uv run agentic-workspace summary --format json` |
| durable repo knowledge or repeated rediscovery | read `.agentic-workspace/memory/WORKFLOW.md` |
