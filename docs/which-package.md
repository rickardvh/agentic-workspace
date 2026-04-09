# Which Package Should I Install?

Use `agentic-workspace` as the public entrypoint.
Pick the preset that matches the repo problem.

## Fast Chooser

| If your main problem is... | Install... | Why |
| --- | --- | --- |
| Stable repo knowledge keeps getting rediscovered | `agentic-workspace --preset memory` | Memory gives durable anti-rediscovery context without adding planning surfaces. |
| Active work keeps drifting or fragmenting | `agentic-workspace --preset planning` | Planning gives a checked-in active queue and bounded execplans. |
| You want both durable knowledge and checked-in execution | `agentic-workspace --preset full` | The workspace layer composes both modules through one lifecycle entrypoint. |

Default answer: use `agentic-workspace` and choose the preset that matches the repo problem.

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

## Read Next

- Memory path: [`packages/memory/README.md`](/C:/Users/ricka/Documents/src/agentic-workspace/packages/memory/README.md)
- Planning path: [`packages/planning/README.md`](/C:/Users/ricka/Documents/src/agentic-workspace/packages/planning/README.md)
- Shared defaults: [`docs/default-path-contract.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/default-path-contract.md)
- Architecture: [`docs/architecture.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/architecture.md)
