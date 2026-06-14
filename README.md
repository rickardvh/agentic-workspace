# Agentic Workspace

Agentic Workspace is for repositories where agent work must survive time: multiple sessions, tools, branches, contributors, or non-trivial proof expectations. It adds a small repo-native operating layer so agents can preserve intent, recover context, validate changes, and hand off safely without relying on chat history.

Installing into another repo? Start with [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md). Do not clone this source repo into a temporary folder as the host-repo install strategy.

The simplest mental model is temporary technical contributors. Agents can move quickly, but they enter and leave a codebase with partial local context. Agentic Workspace gives the repo a small checked-in way to onboard them, bound their work, preserve useful lessons, and make handoff reviewable.

## Why Use It?

Use Agentic Workspace when agent work keeps depending on context that disappears between sessions, tools, branches, or handoffs.

It is not zero-overhead productivity tooling. It adds small, intentional coordination overhead so large or long-running agent-heavy projects avoid larger future costs: rediscovery, unsafe handoff, stale context, weak proof, duplicated work, and unreviewable output.

- Agents can start from repo state instead of chat history.
- Durable repo knowledge can live in checked-in Memory.
- Active work can use checked-in Planning when continuity matters.
- Proof, startup, and handoff routes become explicit and cheaper to rediscover.
- Repeated friction can become a checked-in note, plan, doc, test, scaffold, or issue instead of staying tribal knowledge.

In short:

| Question | Agentic Workspace answer |
| --- | --- |
| Why does this exist? | Agent work loses intent, context, proof, and ownership when those live only in chat. |
| What does it add? | A small repo-native operating layer for durable context, active work, startup routing, proof, and handoff. |
| How does it help? | It makes the correct operating path cheaper than guessing, and makes recurring friction visible enough to improve the repo. |

## When It Pays Back

Good fit:

- a repo needs a repeatable agent startup path;
- agents keep rediscovering the same repo facts;
- active work needs resumable plans, proof expectations, or handoff state;
- context loss between sessions, branches, or tools is costly;
- long-running intent or partial closeout needs a checked-in owner;
- recurring mistakes should become repo knowledge, proof, or follow-up work.

Not a fit:

- you need project management, ticketing, runtime orchestration, or database-backed planning;
- you want a plugin platform or third-party extension API;
- the repo is small enough to reread cheaply;
- tasks usually finish in one sitting;
- a simple README note or existing repo command already solves the problem.

It can still pay back for solo work. The question is not team size; the question is whether the handoff to a future session, future branch, or future agent would otherwise lose important context, intent, or proof expectations.

## What Lightweight Means

Lightweight means a small checked-in footprint, no database or service, selective adoption, compact command outputs, no full project-management system, and no runtime orchestration. It does not mean free to use or zero cognitive overhead.

## Install

Choose the smallest module set that solves the repo problem. Start with `memory` unless active planning is the main need.

```bash
agentic-workspace init --target ./repo --modules memory
```

Use an installed `agentic-workspace` CLI from the target repo's environment when available. If it is unavailable, install the package into that repo or its tool environment first, then rerun the same command. Use `--modules planning` when active work continuity is the main problem, and `--modules planning,memory` when both durable knowledge and active planning are justified. `uvx` or `pipx run` are temporary/debug fallbacks, not the default install path.

## Core Modules

| Module selection | Use when |
| --- | --- |
| `memory` | The repo needs durable knowledge and anti-rediscovery context, without checked-in active plans. |
| `planning` | The repo needs active work continuity, proof expectations, or handoff state, without shared Memory. |
| `planning,memory` | The repo needs both durable knowledge and checked-in active planning. |

For the full package map and lower-footprint routing-only setup, see [`docs/index.md`](docs/index.md).

## What Gets Installed

The selected modules write a small `.agentic-workspace/` operating layer plus thin adapter files that point agents at structured state. The root `agentic-workspace` command owns lifecycle, startup routing, combined reporting, and updates. Memory and Planning are selectable core modules installed through that root entrypoint and persisted in `[modules].enabled`.

Selecting `planning,memory` does not activate source-checkout maintainer tooling, package extraction, codegen development, or self-improvement surfaces.

## How Agents Use It

After install, the ordinary first question is:

```bash
agentic-workspace start --format json
```

That compact answer routes the agent to Memory, Planning, proof, report, doctor, or repo docs only when needed. If the current question is active work state, use:

```bash
agentic-workspace summary --format json
```

The generated startup file, normally `AGENTS.md`, is a thin adapter over the structured workspace state. It should point agents at the right compact command instead of becoming a second operating manual.

## Boundaries

Agentic Workspace preserves bounded repo-native operating state. It does not replace issue trackers, review, project management, local agent memory, runtime orchestration, or existing repo commands.

Advanced diagnostics, source-checkout maintainer workflows, local integration helpers, and adapter-generation infrastructure are documented separately and are not ordinary host-repo workflow. For the current package hierarchy, start with [`docs/index.md`](docs/index.md). For documentation roles, freshness, and maturity signals, see [`docs/documentation-status.md`](docs/documentation-status.md) and [`docs/maturity-model.md`](docs/maturity-model.md).

For agent maintainers, the primary operating path is `AGENTS.md`, the active execplan when one is surfaced by compact startup output, and `docs/maintainer/contributor-playbook.md`.

## Learn More

- Documentation map: [`docs/index.md`](docs/index.md)
- Package overview and adoption boundary: [`docs/package/overview.md`](docs/package/overview.md)
- CLI, installed surfaces, modules, and contracts: [`docs/package/`](docs/package/overview.md)
- Architecture and ownership boundaries: [`docs/architecture.md`](docs/architecture.md)
- Collaboration and merge safety: [`docs/collaboration-safety.md`](docs/collaboration-safety.md)
- Documentation roles and maturity: [`docs/documentation-status.md`](docs/documentation-status.md), [`docs/maturity-model.md`](docs/maturity-model.md)
- Memory module: [`packages/memory/README.md`](packages/memory/README.md)
- Planning module: [`packages/planning/README.md`](packages/planning/README.md)
- Maintainer workflow: [`docs/maintainer/contributor-playbook.md`](docs/maintainer/contributor-playbook.md)
