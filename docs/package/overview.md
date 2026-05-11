# Package Overview

`agentic-workspace` is the root package and CLI. It installs a small, repo-native operating layer for repositories where agent work must survive time: multiple sessions, tools, branches, contributors, or non-trivial proof expectations.

The package is deliberately not a project-management system, runtime orchestrator, database, or plugin platform. It provides file-based contracts and compact command outputs that let agents preserve intent, recover context, verify changes, and hand off safely through repository state instead of chat history.

Agentic Workspace is an amortized coordination layer. It adds small, intentional overhead now so long-running agent work avoids larger future costs: rediscovery, stale context, weak proof, duplicated work, unsafe handoff, and unreviewable output. For small or short-lived repos, that overhead may not pay back.

## What Ships

The root package ships:

- the `agentic-workspace` CLI;
- lifecycle commands for installing, adopting, upgrading, checking, and removing managed surfaces;
- compact context commands such as `start`, `summary`, `preflight`, `report`, `proof`, `ownership`, and `config`;
- first-party module composition for Planning and Memory;
- package-managed workspace skills for first-contact startup, routing, proof, closeout, and module-boundary orientation;
- machine-readable contracts under `src/agentic_workspace/contracts/`;
- JSON schemata and generated reference docs for those contracts;
- a thin startup adapter such as `AGENTS.md` when installed into a host repository.

The root package currently depends on the first-party Planning and Memory packages so one command can orchestrate ordinary lifecycle work. Presets control the checked-in repository footprint, not the Python dependency graph.

Exact profile and footprint metadata is defined in the generated [Module registry](../reference/module-registry.md). Exact command metadata is defined in [CLI commands](../reference/cli-commands.md).

## Runtime Model

Installed repositories get a `.agentic-workspace/` directory plus small adapter files. The adapters route agents to compact CLI answers instead of becoming a second handbook.

Startup and report outputs should make the investment visible. They are useful when they show what cost was avoided or contained: rediscovery avoided by Memory, scope contained by Planning, proof selected by repo state, continuation routed to a checked-in owner, or repeated friction converted into a durable improvement target.

Ordinary startup is:

```bash
agentic-workspace start --target ./repo --format json
```

If active work state is the question, use:

```bash
agentic-workspace summary --target ./repo --format json
```

If takeover, recovery, config, and active state should be bundled in one answer, use:

```bash
agentic-workspace preflight --target ./repo --format json
```

For exact startup and report payload shapes, see [Startup context](../reference/startup-context.md) and [Workspace report](../reference/workspace-report.md).

## Presets

| Preset | Selected modules | Use when |
| --- | --- | --- |
| routing-only | none | the repo only needs compact entrypoint, config, workspace skills, module-map, and report routing surfaces |
| memory | Memory | durable repo knowledge should prevent repeated rediscovery |
| planning | Planning | active execution state, proof expectations, handoff, or lane closeout must be recoverable |
| full | Planning and Memory | both active execution state and durable repo knowledge are worth the shared footprint |

`memory` is the usual smallest starting point when the problem is repeated rediscovery. `planning` is the right starting point when active work continuity is the fragile part. `full` is justified when both durable knowledge and active execution continuity are recurring bottlenecks.

The threshold is not team size. A solo maintainer and one agent can still benefit when the handoff is to a future session, future branch, or future agent and the missing context would be expensive to reconstruct.

## Read Next

- [Lifecycle and context commands](lifecycle.md)
- [Command map](commands.md)
- [Installed surfaces](installed-surfaces.md)
- [Modules](modules.md)
- [Contracts and references](contracts.md)
