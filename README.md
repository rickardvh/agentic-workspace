# Agentic Workspace

Agentic Workspace installs a small repo-native operating layer that helps agents enter, resume, hand off, and verify work from checked-in state.

## Why Use It?

Use Agentic Workspace when agent work keeps depending on context that disappears between sessions, tools, branches, or handoffs.

- Agents can start from repo state instead of chat history.
- Durable repo knowledge can live in checked-in Memory.
- Active work can use checked-in Planning when continuity matters.
- Proof, startup, and handoff routes become explicit and cheaper to rediscover.

## When To Use It

Good fit:

- a repo needs a repeatable agent startup path;
- agents keep rediscovering the same repo facts;
- active work needs resumable plans, proof expectations, or handoff state;
- a team wants lightweight repo-owned context without a database or service.

Not a fit:

- you need project management, ticketing, runtime orchestration, or database-backed planning;
- you want a plugin platform or third-party extension API;
- a simple README note or existing repo command already solves the problem.

## Install

Choose the smallest preset that solves the repo problem. Start with `memory` unless active planning is the main need.

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target ./repo --preset memory
```

Use `--preset planning` when active work continuity is the main problem, and `--preset full` only when both durable knowledge and active planning are justified. If you use `pipx` instead of `uvx`, keep the same command shape.

## Presets

| Preset | Use when |
| --- | --- |
| `memory` | The repo needs durable knowledge and anti-rediscovery context, without checked-in active plans. |
| `planning` | The repo needs active work continuity, proof expectations, or handoff state, without shared Memory. |
| `full` | The repo needs both durable knowledge and checked-in active planning. |

For lower-footprint routing-only setup and detailed preset selection, see [`docs/which-package.md`](docs/which-package.md).

## What Gets Installed

The selected preset writes a small `.agentic-workspace/` operating layer plus thin adapter files that point agents at structured state. The root `agentic-workspace` command owns lifecycle, startup routing, combined reporting, and updates. Memory and Planning are selectable capabilities installed through that root entrypoint.

`full` selects Planning plus Memory. It does not activate source-checkout maintainer tooling, package extraction, codegen development, or self-improvement surfaces.

## How Agents Use It

After install, the ordinary first question is:

```bash
agentic-workspace start --format json
```

That compact answer routes the agent to Memory, Planning, proof, report, doctor, or repo docs only when needed. If the current question is active work state, use:

```bash
agentic-workspace summary --format json
```

The generated startup files, including `AGENTS.md` and `llms.txt`, are thin adapters over the structured workspace state. They should point agents at the right compact command instead of becoming a second operating manual.

## Boundaries

Agentic Workspace preserves bounded repo-native operating state. It does not replace issue trackers, review, project management, local agent memory, runtime orchestration, or existing repo commands.

Advanced diagnostics, source-checkout maintainer workflows, local integration helpers, and adapter-generation infrastructure are documented separately and are not ordinary host-repo workflow. For documentation roles, freshness, and maturity signals, see [`docs/documentation-status.md`](docs/documentation-status.md) and [`docs/maturity-model.md`](docs/maturity-model.md).

## Learn More

- Choosing an install shape: [`docs/which-package.md`](docs/which-package.md)
- Architecture and ownership boundaries: [`docs/architecture.md`](docs/architecture.md)
- Documentation freshness and roles: [`docs/documentation-status.md`](docs/documentation-status.md)
- Maturity model: [`docs/maturity-model.md`](docs/maturity-model.md)
- Memory module: [`packages/memory/README.md`](packages/memory/README.md)
- Planning module: [`packages/planning/README.md`](packages/planning/README.md)
- Maintainer workflow: [`docs/contributor-playbook.md`](docs/contributor-playbook.md)
