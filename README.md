# Agentic Workspace

Agentic Workspace adds a small repo-native operating layer for repositories where agent work must preserve intent, context, proof expectations, and handoff state across sessions, tools, branches, or contributors.

It is built around checked-in workspace contracts, compact routing, explicit ownership, selected modules, and thin adapter files that point agents at the right repo-local commands.

## Why it exists

Agents can move quickly, but they enter and leave a repository with partial context. In longer-running work, important state often lives only in chat: why a task matters, what has already been tried, which repo facts matter, what proof is expected, and what remains unsafe to claim.

Agentic Workspace gives that operating state a repo-native home so future agents can start from the repository instead of reconstructing intent from conversation history.

## What it does

Agentic Workspace helps agents:

* start from compact repo state instead of broad rereading;
* preserve durable lessons that would otherwise be rediscovered;
* keep active work bounded, resumable, and honestly closeable;
* route proof expectations and evidence through reviewable surfaces;
* hand off unfinished or risky work without hiding uncertainty.

It does this through compact command surfaces, selected module state under `.agentic-workspace/`, thin adapter files such as `AGENTS.md`, and file-based contracts that can be generated, packaged, or projected into agent-facing integrations.

## What it is not

Agentic Workspace is not:

* a project-management system;
* a ticket tracker;
* a runtime orchestrator;
* a database;
* a generic runtime plugin platform;
* a replacement for tests, review, issue trackers, or canonical repo documentation.

It should make the correct agent operating path cheaper. If it adds more coordination cost than it removes, it is the wrong tool or the wrong module set.

## When it pays back

Use Agentic Workspace when:

* agents repeatedly reread or rediscover the same repo facts;
* work crosses sessions, branches, tools, or contributors;
* tasks need explicit proof expectations;
* handoff or continuation state matters;
* recurring friction should become durable repo knowledge or follow-up work.

Do not use it when:

* the repo is cheap to reread;
* work usually finishes in one sitting;
* a README note or existing repo command is enough;
* the added coordination surface would cost more than it saves.

The threshold is not team size. The threshold is whether future continuation would otherwise lose expensive context, intent, or proof obligations.

## How to adopt it

The usual adoption path has two parts.

First, choose how Agentic Workspace should be made available to the target repository. Today that is usually the CLI installed as a repo development dependency. Future integrations may use another surface, such as an MCP server.

Then give an agent a small bootstrap instruction in the target repo, or point it at the remote instructions in [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md) so it can perform the operation itself. The agent should use the target repo’s tooling environment, choose the smallest useful module footprint, inspect the generated surfaces, and leave a bounded handoff for any manual initialization that remains.

Modules can be selected during initialization and added or removed later. Humans should normally choose the installation surface and review the result rather than operate lifecycle commands directly.

For exact installation paths, current package targets, and environment-specific invocation, see [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md).

## How it works

Agentic Workspace keeps agent work moving through a small continuity loop:

| Step              | What it protects                                                                                                    |
| ----------------- | ------------------------------------------------------------------------------------------------------------------- |
| Startup           | The agent starts from the smallest relevant repo state instead of chat history or broad rereading                   |
| Work shaping      | The task is treated as direct work, bounded work, lane work, takeover, or continuation instead of drifting silently |
| Durable knowledge | Expensive-to-rediscover repo facts are pulled only when relevant and captured only when worth keeping               |
| Proof             | Validation expectations are selected from changed surfaces, repo policy, and configured verification protocols      |
| Closeout          | Completion claims are checked against intent, proof, residue, and the next owner before work is called done         |

Installed adapters such as `AGENTS.md` point agents at the right compact command surface. Users should not need to remember the command sequence during ordinary work.

## Core modules

Agentic Workspace can be installed with only the modules a repo needs.

* **Memory** preserves durable repo knowledge that is expensive to rediscover. See [`packages/memory/README.md`](packages/memory/README.md).
* **Planning** preserves active execution state, bounded work, handoff, and honest closeout. See [`packages/planning/README.md`](packages/planning/README.md).
* **Verification** preserves reusable soft verification protocols, proof-route hints, bounded evidence, and known gaps. See [`packages/verification/README.md`](packages/verification/README.md).

For module-selection detail, see [`docs/package/modules.md`](docs/package/modules.md).

## Installed footprint

An installed repo gets a small `.agentic-workspace/` operating layer plus thin adapter files such as `AGENTS.md`. Selected modules add their own roots under that operating layer.

Module selection controls the host-repo footprint. Package-owned state should stay quiet, checked in when useful for continuation, and plausibly removable. Adapter files should route agents to compact commands instead of becoming a second operating manual.

For installed surfaces and ownership boundaries, see [`docs/package/installed-surfaces.md`](docs/package/installed-surfaces.md).

## Documentation map

* Installing into a repo: [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md)
* Understanding the package: [`docs/package/overview.md`](docs/package/overview.md)
* Choosing modules: [`docs/package/modules.md`](docs/package/modules.md)
* Lifecycle and context commands: [`docs/package/lifecycle.md`](docs/package/lifecycle.md)
* Installed files and ownership: [`docs/package/installed-surfaces.md`](docs/package/installed-surfaces.md)
* Contracts and generated references: [`docs/package/contracts.md`](docs/package/contracts.md)
* Documentation status and maturity: [`docs/documentation-status.md`](docs/documentation-status.md), [`docs/maturity-model.md`](docs/maturity-model.md)
* Full documentation index: [`docs/index.md`](docs/index.md)

## Source checkout note

If you are working on Agentic Workspace itself, follow [`AGENTS.md`](AGENTS.md) and the [`maintainer documentation`](docs/maintainer/contributor-playbook.md). This README describes the shipped package and ordinary adoption path, not the full source-checkout workflow.
