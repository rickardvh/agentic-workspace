# agentic-workspace

Agentic Workspace gives a repo a durable operating layer for agents without making the repo feel like a workflow product first.

## Why This Exists

Agent work often loses context at the worst time: after a tool switch, a short session, a branch handoff, or a long-running task that needs proof before it can close. Agentic Workspace puts the durable parts of that work in the repository so the next agent can start from checked-in state instead of chat history.

The package is intentionally quiet. It does not replace issue trackers, docs, local agent memory, or human review. It gives those things a shared routing layer: startup, durable repo knowledge, active planning, proof expectations, and handoff state.

## What It Does Today

- Adds compact startup/config/report commands for agent first contact.
- Installs optional checked-in Memory for durable repo knowledge.
- Installs optional checked-in Planning for active work continuity.
- Keeps generated handoff adapters such as `AGENTS.md`, `llms.txt`, and helper docs thin over structured state.
- Exposes maintainer diagnostics for ownership, proof selection, external work reconciliation, and install/update health.

## Current Modules

- `workspace`: startup, lifecycle, routing, install/update, and combined workspace reporting.
- `memory`: durable anti-rediscovery repo knowledge.
- `planning`: active execution state, bounded plans, proof expectations, and continuation.

## Current Capability Status

| Capability | Status | What this means today |
| --- | --- | --- |
| Workspace lifecycle and compact routing | shipped/current | Public `agentic-workspace` CLI entrypoint for install, init, status, doctor, config, start, report, defaults, proof, and preflight. |
| Memory module | shipped/current | First-party checked-in repo-memory contract, installable alone or with Planning. |
| Planning module | shipped/current | First-party checked-in active-work contract, installable alone or with Memory. |
| Workspace composition presets | shipped/current | `memory`, `planning`, and `full` select installed module shape; `routing-only` is the smallest checked-in footprint when only routing is needed. |
| Review artifacts and external intake/reconciliation | optional/internal | Available diagnostics and evidence surfaces, generally behind explicit advanced features or maintainer workflows. |
| Agent aids and local integration helpers | optional/internal | Advisory helper storage and local-only runtime integration areas; they do not become required workflow by existing locally. |
| Generated command adapters | source-checkout-only | Maintainer proof and adapter-generation infrastructure; not a public adapter API. |
| External modules, plugins, MCP-style adapters, and third-party extension | future candidate | The internal contracts are being sharpened, but external plugin/module APIs are not supported public contracts yet. |
| Runtime orchestration, project management, ticketing, or database-backed planning | not supported | Keep those responsibilities in existing tools; Agentic Workspace only preserves bounded repo-native operating state. |

For freshness and role signals across public docs, see [`docs/documentation-status.md`](docs/documentation-status.md).

## Choose A Preset

Choose the smallest preset that matches the repo problem:

- `memory`: durable knowledge without active planning; the smallest useful shared operating layer
- `planning`: active planning without memory
- `full`: both together, when the repo needs both durable knowledge and checked-in execution continuity

`routing-only` is the smallest checked-in repo footprint when a repo only needs compact startup/config/report routing. The current root Python package still bundles the first-party planning and memory packages so the root lifecycle command stays simple; routing-only does not mean a smaller Python dependency install.

Then run:

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target ./repo --preset memory
```

Use `--preset planning` when active work continuity is the main problem, and `--preset full` only when both memory and planning are justified. If you use `pipx` instead of `uvx`, keep the same command shape.

## What Gets Installed

The selected preset writes a small `.agentic-workspace/` operating layer plus thin adapter files that point agents at the structured state. `full` selects Planning plus Memory. It does not activate source-checkout maintainer tooling, package extraction, codegen development, or self-improvement surfaces.

Module manifests also declare adapter-ready components such as resources, tools, prompt-like skills, schemas, and owned roots. Those declarations keep future adapters thin, but they are internal readiness data today, not a supported external plugin or MCP API.

## Ordinary work

Agentic Workspace exposes one context-router family through several compact views:

- `start`: ordinary entry into the repo
- `summary`: current planning, active work, or handoff state
- `report`: combined workspace routing, diagnostics, warnings, and section selectors
- `defaults`: policy, contract, setup, proof, and startup answers
- `preflight`: takeover, recovery, or one-call startup plus active state

The ordinary startup path in a repo using Agentic Workspace is:

1. Read `AGENTS.md`.
2. Ask `agentic-workspace start --format json`.
3. Read `SYSTEM_INTENT.md` as a compass when you need the repo's higher-level direction.
4. Ask `agentic-workspace summary --format json` only when the current work state is the question.
5. Read the active execplan only when the compact output points there.

`AGENTS.md`, `llms.txt`, and the generated helper docs are compatibility adapters over the structured workspace config.
New durable workflow behavior should land in the structured substrate first, then flow outward into those prose adapters.

The compact planning home is:

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/`

## Module ownership

- `workspace`: startup, lifecycle, routing, and combined workspace reporting
- `planning`: active execution state, sequencing, proof expectations, and continuation
- `memory`: durable anti-rediscovery repo knowledge

Use `memory` when durable repo knowledge is the main problem. Add `planning` when active work needs checked-in continuity.

## Maintainers

For agent maintainers, the primary operating path is:

1. Read `AGENTS.md`.
2. Read `SYSTEM_INTENT.md` as a compass when shaping or evaluating broader repo work.
3. Read `agentic-workspace summary --format json`.
4. Read the active execplan only when the summary points there.
5. Read `docs/contributor-playbook.md` before widening into broader maintainer surfaces.

Use `docs/maintainer-commands.md` for operational commands, `docs/design-principles.md` for must-internalize doctrine, and `docs/dogfooding-feedback.md` when repo friction might need to become product work.

## External handoff

For install or adopt first contact from another agent, use:

- [`llms.txt`](llms.txt)
- [`.agentic-workspace/docs/routing-contract.md`](.agentic-workspace/docs/routing-contract.md)

After bootstrap, return to the ordinary startup path above.
