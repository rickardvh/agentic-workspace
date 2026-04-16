# Which Package Should I Install?

Use `agentic-workspace` as the public entrypoint.
Pick the preset that matches the repo problem.

Agentic Workspace is primarily a quiet repo-native capability layer. The lightweight operational profile is memory-first: useful when the repo needs durable knowledge and a small visible surface rather than checked-in active execution.

## Fast Chooser

| If your main problem is... | Install... | Why |
| --- | --- | --- |
| Stable repo knowledge keeps getting rediscovered | `agentic-workspace --preset memory` | Memory is the lightweight operational profile: the smallest useful core for quiet durable context. |
| Active work keeps drifting or fragmenting | `agentic-workspace --preset planning` | Planning gives a checked-in active queue and bounded execplans. |
| You want both durable knowledge and checked-in execution | `agentic-workspace --preset full` | The workspace layer composes both modules through one lifecycle entrypoint. |

Default answer: use `agentic-workspace` and choose the preset that matches the repo problem.

## Compact Operating Map

Ask the smallest useful question first:

| If you need to know... | Ask this first | Then, only if needed |
| --- | --- | --- |
| how to start or which lifecycle path applies | `AGENTS.md`, then `agentic-workspace config --target ./repo --format json` | [`docs/default-path-contract.md`](default-path-contract.md) |
| what is active right now | `agentic-planning-bootstrap summary --format json` | `TODO.md`, then one active execplan |
| what the combined workspace state looks like | `agentic-workspace report --target ./repo --format json` | raw module files or maintainer docs |
| which proof or ownership answer is enough | `agentic-workspace defaults --section proof_selection --format json`, `agentic-workspace proof --target ./repo --format json`, or `agentic-workspace ownership --target ./repo --format json` | [`docs/default-path-contract.md`](default-path-contract.md) and the referenced contract doc |
| where handoff or setup work lives | `llms.txt` or `agentic-workspace setup --target ./repo --format json` | `.agentic-workspace/bootstrap-handoff.md` or `.json` when bootstrap says review is still needed |
| what mixed-agent posture is in effect | `agentic-workspace config --target ./repo --format json` | [`docs/workspace-config-contract.md`](workspace-config-contract.md) |

Stop at the first compact surface that answers the question.
Use broader docs or raw files only when the compact surface is insufficient.

## What Stays Secondary

These are real but secondary:

- direct package CLIs
- package-local maintainer workflows
- debugging-oriented lifecycle paths

Use them when you explicitly need module-level control, not for normal adoption.

## Good Fits

### Memory

- subsystem knowledge is expensive to rediscover
- recurring traps or operator sequences should be shared
- the repo already has task tracking but lacks durable shared knowledge

### Planning

- work spans many short sessions
- active execution drifts without a checked-in queue
- backlog tools exist, but active implementation still fragments

### Full

- the repo wants both restartable execution and lower rediscovery cost
- agents are regular maintainers and need both active state and durable context

## Partial Adoption

| Combination | Supported | Primary writable surfaces |
| --- | --- | --- |
| Memory only | Yes | `memory/` plus optional weak-authority `memory/current/` |
| Planning only | Yes | `TODO.md`, `ROADMAP.md`, `docs/execplans/` |
| Memory + Planning | Yes | Planning for active-now state, memory for durable knowledge |
| Workspace lifecycle entrypoint | Yes | Same module-owned surfaces, with thin root orchestration |

## Lightweight Operational Profile

If you want the smallest useful core, choose `memory`.

That profile is for repos that need durable knowledge and compact routing but do not yet need checked-in active execution state. It keeps the visible surface smaller than `planning` or `full` while still giving the repo a useful agent-facing baseline.

## Read Next

- Compact operating map and first question: [`docs/default-path-contract.md`](default-path-contract.md)
- Memory path: [`packages/memory/README.md`](../packages/memory/README.md)
- Planning path: [`packages/planning/README.md`](../packages/planning/README.md)
- Architecture: [`docs/architecture.md`](architecture.md)
