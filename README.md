# agentic-workspace

Agentic Workspace gives a repository a durable, checked-in operating layer for agents.

It is intentionally repo-native and quiet:

- `agentic-workspace` is the normal lifecycle entrypoint
- Agentic Planning owns active execution state
- Agentic Memory owns durable anti-rediscovery knowledge

The public shape should stay smaller than the internal machinery behind it.

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

## What changes in a repo

The normal startup path is:

1. Read `AGENTS.md`
2. Query `agentic-workspace summary --format json`
3. Read the active execplan only when the summary points there

Planning state now lives in:

- `.agentic-workspace/planning/state.toml`
- `docs/execplans/`

Generated thin views may exist under `.agentic-workspace/planning/`, but they are derived from `state.toml`. They are not repo-root authority surfaces.

For agent maintainers, the primary operating path is `AGENTS.md`, the active execplan, and `docs/contributor-playbook.md`.

Memory state lives under:

- `.agentic-workspace/memory/`
- `memory/`

## When to use it

Use Agentic Workspace when repo work should become:

- easier to restart
- cheaper to continue across sessions
- less dependent on one model or tool
- more resistant to rediscovery and partial-work drift

Use `memory` when durable repo knowledge is the main problem.
Add `planning` when active work needs checked-in continuity.

## External-agent handoff

For another agent bootstrapping a repo, start from:

- [`docs/routing-contract.md`](docs/routing-contract.md)
- [`llms.txt`](llms.txt)

After install or adopt, compact first-contact queries are:

- `agentic-workspace defaults --section startup --format json`
- `agentic-workspace config --target ./repo --format json`
- `agentic-workspace summary --format json`

## Normal commands

```bash
agentic-workspace status --target ./repo
agentic-workspace doctor --target ./repo
agentic-workspace upgrade --target ./repo
agentic-workspace skills --target ./repo --task "implement the current active milestone" --format json
```

## Read next

- [`docs/which-package.md`](docs/which-package.md)
- [`docs/routing-contract.md`](docs/routing-contract.md)
- [`docs/lifecycle-and-config-contract.md`](docs/lifecycle-and-config-contract.md)
- [`tools/AGENT_QUICKSTART.md`](tools/AGENT_QUICKSTART.md)
- [`tools/AGENT_ROUTING.md`](tools/AGENT_ROUTING.md)
