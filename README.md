# agentic-workspace

Agentic Workspace gives a repository a durable, checked-in operating system for agents:

- Agentic Planning for active execution
- Agentic Memory for anti-rediscovery knowledge
- `agentic-workspace` as the normal public lifecycle entrypoint

The goal is efficiency: higher-quality work with less rereading, rediscovery, and chat-only continuity loss over time.

## Default Path

1. Choose a preset:
   - `memory`
   - `planning`
   - `full`
2. Install through `agentic-workspace init`.
3. Keep using `agentic-workspace` for the normal lifecycle.

Normal install path:

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target /path/to/repo --preset full
```

If you only want one module, switch `--preset full` to `--preset memory` or `--preset planning`.
If you use `pipx` instead of `uvx`, keep the same command shape.

Normal next commands:

```bash
agentic-workspace status --target /path/to/repo
agentic-workspace skills --target /path/to/repo --task "implement the current active milestone" --format json
agentic-workspace doctor --target /path/to/repo
agentic-workspace upgrade --target /path/to/repo
```

## Why Adopt It

Use it when you want repo work to become:

- easier to restart
- cheaper to continue across sessions
- less dependent on one tool or model
- more resistant to drift and rediscovery
- easier to hand off across agents or contributors

What it adds:

- checked-in execution state through Agentic Planning
- checked-in anti-rediscovery knowledge through Agentic Memory
- one public lifecycle entrypoint through `agentic-workspace`
- selective adoption: either module alone or both together
- an improvement loop that turns recurring friction into better contracts, docs, checks, and workflows

## Choose A Preset

| If your main problem is... | Use... |
| --- | --- |
| Durable repo knowledge keeps getting rediscovered | `agentic-workspace --preset memory` |
| Active work keeps drifting or losing completion discipline | `agentic-workspace --preset planning` |
| You want both together | `agentic-workspace --preset full` |

If you need more than that table, use [`docs/which-package.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/which-package.md).

## Machine-Readable Defaults

For the structured default-route contract, use:

```bash
agentic-workspace defaults --format json
```

That surface is the queryable contract for:

- startup
- lifecycle
- skill discovery
- validation
- combined-install operation

For agent maintainers, the primary operating path is:

- read [`AGENTS.md`](/C:/Users/ricka/Documents/src/agentic-workspace/AGENTS.md)
- read [`TODO.md`](/C:/Users/ricka/Documents/src/agentic-workspace/TODO.md)
- read the active execplan when `TODO.md` points at one
- then use [`docs/contributor-playbook.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/contributor-playbook.md) for the maintainer workflow details

## Advanced Paths

These are secondary:

- direct package CLIs such as `agentic-memory-bootstrap` or `agentic-planning-bootstrap`
- package-local maintainer workflows
- deeper lifecycle debugging

Use them when you explicitly need module-level control, not as the default path for normal adoption.

## Product Names

- Agentic Memory -> `agentic-memory-bootstrap`
- Agentic Planning -> `agentic-planning-bootstrap`
- Composition layer -> `agentic-workspace`

The `-bootstrap` names are still the current package and CLI identities.

## Maturity

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: alpha

See [`docs/maturity-model.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/maturity-model.md) for the current maturity expectations.

## Read Next

Start here:

- [`docs/which-package.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/which-package.md)
- [`docs/default-path-contract.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/default-path-contract.md)

Then, if needed:

- [`docs/init-lifecycle.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/init-lifecycle.md)
- [`docs/architecture.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/architecture.md)
- [`docs/integration-contract.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/integration-contract.md)
- [`docs/contributor-playbook.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/contributor-playbook.md)
- [`docs/maintainer-commands.md`](/C:/Users/ricka/Documents/src/agentic-workspace/docs/maintainer-commands.md)
