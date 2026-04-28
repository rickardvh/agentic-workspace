# agentic-workspace

Agentic Workspace gives a repo a durable operating layer for agents without making the repo feel like a workflow product first.

## Default path

Choose the smallest preset that matches the repo problem:

- `memory`: durable knowledge without active planning; the smallest useful shared operating layer
- `planning`: active planning without memory
- `full`: both together, when the repo needs both durable knowledge and checked-in execution continuity

These presets map to generic module profiles. `routing-only` is the smallest checked-in repo footprint when a repo only needs compact startup/config/report routing. The current root Python package still bundles the first-party planning and memory packages so the root lifecycle command stays simple; routing-only does not mean a smaller Python dependency install. `full` is an installer profile that selects planning plus memory; it does not activate source-checkout maintainer tooling, package extraction, codegen development, or self-improvement surfaces.

Module manifests also declare adapter-ready components: read-only resources, mutating tools, prompt-like skills, schemas, and owned roots. This keeps future MCP-style adapters thin without adding an MCP runtime dependency to the core package.

Then run:

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target ./repo --preset memory
```

Use `--preset planning` when active work continuity is the main problem, and `--preset full` only when both memory and planning are justified. If you use `pipx` instead of `uvx`, keep the same command shape.

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
