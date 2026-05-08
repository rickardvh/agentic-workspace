# Minimum Operating Model

This page defines the tiny safe model for ordinary work in a repo using Agentic Workspace.

Use it when the goal is to start useful work without loading the repo's full internal machinery up front.

## Tiny Safe Model

Start from:

1. one repo startup entrypoint: `AGENTS.md` by default
2. one compact query path: `agentic-workspace defaults --section startup --format json`, `agentic-workspace config --target ./repo --format json`, and `agentic-workspace summary --format json`
3. conditional deeper reads only after those compact answers show that the task has crossed a real boundary

The ordinary rule is:

- do not open raw planning state, execplan prose, or broad routing docs until the compact startup answer is insufficient
- do not front-load memory or deeper module doctrine unless the task has crossed that boundary
- keep the first-contact model smaller than the repo's full internal concept set

## Boundary-Triggered Discovery

Escalate into a deeper layer only when the task makes that layer relevant.

| Boundary | Escalation cue | Load next | Why |
| --- | --- | --- | --- |
| `workspace` | Startup order, lifecycle behavior, config, ownership, or combined workspace state is the actual question. | `agentic-workspace defaults --section startup --format json`, `agentic-workspace config --target ./repo --format json`, `agentic-workspace report --target ./repo --format json` | Workspace-level surfaces own routing, lifecycle orchestration, and cross-module coordination. |
| `planning` | The task needs active sequencing, blockers, proof expectations, promotion decisions, or cross-session continuation. | `agentic-workspace summary --format json`, `.agentic-workspace/planning/state.toml`, `.agentic-workspace/planning/execplans/` | Planning owns active execution state and near-term follow-through. |
| `memory` | The work keeps rediscovering repo facts, prior decisions, failure modes, or domain context that should survive the current slice. | `.agentic-workspace/memory/repo/`, `.agentic-workspace/memory/WORKFLOW.md` | Memory owns durable anti-rediscovery knowledge instead of active execution state. |

## Top-Level Capability Advertisement

Each top-level module should advertise only four things on startup-facing surfaces:

1. what it owns
2. what cue should escalate into it
3. what new capability becomes available after escalation
4. what compact surface should be loaded first

Current advertisement pattern:

| Module | Owns | Escalate when | Capability unlocked | Compact first surface |
| --- | --- | --- | --- | --- |
| `workspace` | startup, lifecycle, routing, and combined workspace reporting | the task crosses config, install/adopt, ownership, or cross-module coordination boundaries | compact defaults/config/report guidance plus authoritative workspace contracts | `agentic-workspace defaults --section startup --format json` |
| `planning` | active execution state, sequencing, proof expectations, and promotion-ready follow-through | the task needs milestones, blockers, queue updates, or explicit continuation semantics | summary, active queue state, execplans, and planning validation surfaces | `agentic-workspace summary --format json` |
| `memory` | durable repo knowledge, routed decisions, failure modes, and anti-rediscovery context | relevant repo understanding should persist beyond the current chat or implementation slice | routed memory notes and memory workflow guidance | `.agentic-workspace/memory/repo/` |

## Relationship To Other Docs

- Use [routing-contract.md](routing-contract.md) for the authoritative routing home and first-contact ordering.
- Use [compact-contract-profile.md](compact-contract-profile.md) for the selector pattern that makes this small model queryable.
- Use [delegation-posture-contract.md](delegation-posture-contract.md) when the task shape makes execution-mode choice part of the boundary question.
