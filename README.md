# agentic-workspace

Agentic Workspace gives a repo a durable operating layer for agents without making the repo feel like a workflow product first.

## Default path

Choose one preset:

- `memory`: durable knowledge without active planning
- `planning`: active planning without memory
- `full`: both together

Then run:

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target ./repo --preset full
```

If you use `pipx` instead of `uvx`, keep the same command shape.

## Ordinary work

The ordinary startup path in a repo using Agentic Workspace is:

1. Read `AGENTS.md`.
2. Read `SYSTEM_INTENT.md` as a compass when you need the repo's higher-level direction.
3. Ask `agentic-workspace summary --format json`.
4. Ask `agentic-workspace defaults --section agent_configuration_queries --format json` when you need the next compact routing answer.
5. Read the active execplan only when the summary points there.

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
