# agentic-workspace

Agentic Workspace gives a repository a durable, checked-in operating layer for agents.

It is intentionally quiet, repo-native, and user-light. The public shape should stay smaller than the internals behind it.

It is built around two complementary products:

- **Agentic Planning** for active execution
- **Agentic Memory** for anti-rediscovery knowledge

The root `agentic-workspace` CLI is the normal public lifecycle entrypoint.

The goal is efficiency: higher-quality work with less rereading, rediscovery, and chat-only continuity loss over time.

## Why adopt it?

Use Agentic Workspace when you want repo work to become:

- easier to restart
- cheaper to continue across sessions
- less dependent on one tool or model
- more resistant to drift, rediscovery, and partial work
- easier to hand off across agents or contributors

What it adds:

- checked-in execution state through Agentic Planning
- checked-in anti-rediscovery knowledge through Agentic Memory
- one public lifecycle entrypoint through `agentic-workspace`
- selective adoption: either module alone or both together
- an improvement loop that turns recurring friction into better contracts, docs, checks, and workflows

## Product posture

Agentic Workspace is primarily a quiet repo-native capability layer, not a framework the user has to operate continuously.

The default should be compact surfaces, background continuity, and selective retrieval. If a user-facing surface becomes visibly heavy, it should justify that visibility or move into a quieter contract.

## Default path

1. Express the outcome once with `--preset`:
   - `memory`: set up this repo for Agentic Memory
   - `planning`: set up this repo for Agentic Planning
   - `full`: set up this repo for both
2. Run `agentic-workspace init`.
3. Let the workspace CLI infer the safest lifecycle path for the repo shape.
4. Keep using `agentic-workspace` for the normal lifecycle.

Normal install path:

```bash
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target ./repo --preset full
```

If you only want one module, switch `--preset full` to `--preset memory` or `--preset planning`.

## Lightweight operational profile

The smallest useful profile is `memory`.

Use it when a repo mainly needs durable knowledge, compact routing, and a quiet adoption path without checked-in active execution state.

Add `planning` only when the repo needs restartable active work. Use `full` when both durable knowledge and active execution matter enough to justify the extra surface area.

If you use `pipx` instead of `uvx`, keep the same command shape:

```bash
pipx run --spec git+https://github.com/rickardvh/agentic-workspace agentic-workspace init --target ./repo --preset full
```

## External-agent install handoff

If you want an external coding agent to bootstrap Agentic Workspace into another repository, give it this prompt:

```text
Install or adopt Agentic Workspace in the repository you are working in by following the instructions in that repository's `docs/routing-contract.md`. Do not assume `agentic-workspace` is already installed. Use the workspace lifecycle path described there as the default bootstrap route.
```

Canonical handoff surfaces after install:

- [`docs/routing-contract.md`](docs/routing-contract.md) is the authoritative routing home and external install/adopt handoff.
- [`llms.txt`](llms.txt) is the agent entrypoint router.
- [`AGENTS.md`](AGENTS.md) is the canonical ordinary repo startup entrypoint after install/adopt.
- [`TODO.md`](TODO.md) is the canonical active queue once normal repo work starts.
- [`tools/AGENT_QUICKSTART.md`](tools/AGENT_QUICKSTART.md) is a generated compact helper, not a doctrine owner.
- [`tools/AGENT_ROUTING.md`](tools/AGENT_ROUTING.md) is a generated routing helper, not a doctrine owner.
- `.agentic-workspace/bootstrap-handoff.md` is the bounded next-action brief when bootstrap reports that review or reconciliation is still required.

Compact first-contact queries after install/adopt:

- `agentic-workspace defaults --section startup --format json`
- `agentic-workspace config --target ./repo --format json`
- `agentic-workspace summary --format json`

## Normal next commands

```bash
agentic-workspace status --target ./repo
agentic-workspace skills --target ./repo --task "implement the current active milestone" --format json
agentic-workspace doctor --target ./repo
agentic-workspace upgrade --target ./repo
```

## Choose a preset

| If your main problem is... | Use... |
| --- | --- |
| Durable repo knowledge keeps getting rediscovered | `agentic-workspace init --preset memory` |
| Active work keeps drifting or losing completion discipline | `agentic-workspace init --preset planning` |
| You want both together | `agentic-workspace init --preset full` |

If you need more than that table, use [`docs/which-package.md`](docs/which-package.md).

## What each module does

### Agentic Planning

Use Agentic Planning when the repo needs checked-in execution state for active work.

Good fit for:

- a small active queue in `TODO.md`
- bounded execution contracts in `docs/execplans/`
- inactive future candidates in `ROADMAP.md`
- review artifacts in `docs/reviews/` before promotion
- restartable execution across fragmented sessions

Not for:

- durable technical knowledge
- subsystem documentation or runbooks
- a full project-management or ticketing system

### Agentic Memory

Use Agentic Memory when the repo needs durable, shared knowledge for things that are expensive to rediscover.

Good fit for:

- invariants and authority boundaries
- subsystem orientation
- recurring traps and verified failure lessons
- operator procedures and runbooks
- compact weak-authority reorientation notes

Not for:

- active task state
- backlog or milestone tracking
- execution logs
- issue triage or bug-history catch-all
- broad canonical product documentation

## How they work together

When both are installed:

- **Planning owns active execution state**
- **Memory owns durable repo knowledge**
- **The workspace layer coordinates lifecycle**
- **Generated maintainer docs mirror canonical managed sources and should be rerendered, not edited**

The shortest interaction model is:

1. Planning says what matters now.
2. Memory says what is expensive to forget.
3. Managed module surfaces support those contracts.
4. Generated docs mirror managed sources and should be rerendered, not edited.

In combined installs, the goal is stronger than simple compatibility:

- Planning should borrow durable context from Memory instead of re-explaining it.
- Completed Planning work should promote durable residue into Memory or canonical docs.
- Repeated restart friction or repeated plan re-explanation is a product signal that the combined install still needs clearer docs, memory, validation, or decomposition.

## Machine-readable defaults

For the structured default-route contract, use:

```bash
agentic-workspace defaults --format json
```

That surface is the queryable contract for:

- startup
- lifecycle
- supported intents
- canonical external-agent handoff
- canonical bootstrap next action
- delegated judgment boundaries
- skill discovery
- validation
- combined-install operation

For the resolved repo-owned customization layer, use:

```bash
agentic-workspace config --target ./repo --format json
```

That surface layers `agentic-workspace.toml` over product defaults and reports the effective default preset, canonical root startup-entrypoint filename, per-module update intent, and whether repo policy is authoritative or defaults-only.
It also reports the current mixed-agent contract boundary: repo policy source, optional local-override posture from `agentic-workspace.local.toml`, and whether runtime inference is still tool-owned rather than workspace-controlled.

For the repo-owned config contract itself, use [`docs/lifecycle-and-config-contract.md`](docs/lifecycle-and-config-contract.md).

For the bounded "human sets direction, agent owns local means" contract, use [`docs/execution-flow-contract.md`](docs/execution-flow-contract.md).

For agent maintainers, the primary operating path is:

- read [`AGENTS.md`](AGENTS.md)
- read [`TODO.md`](TODO.md)
- read the active execplan when `TODO.md` points at one
- then use [`docs/contributor-playbook.md`](docs/contributor-playbook.md) for maintainer workflow details

## Advanced paths

These are secondary:

- direct package CLIs such as `agentic-memory-bootstrap` or `agentic-planning-bootstrap`
- package-local maintainer workflows
- deeper lifecycle debugging

Use them only when you explicitly need module-level control, not as the default path for normal adoption.

## Product names

- Agentic Memory -> `agentic-memory-bootstrap`
- Agentic Planning -> `agentic-planning-bootstrap`
- Composition layer -> `agentic-workspace`

The `-bootstrap` names are still the current package and CLI identities.

## Maturity

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: beta

See [`docs/maturity-model.md`](docs/maturity-model.md) for the current maturity expectations.

## Read next

Start here:

- [`tools/AGENT_QUICKSTART.md`](tools/AGENT_QUICKSTART.md)
- [`tools/AGENT_ROUTING.md`](tools/AGENT_ROUTING.md)
- [`docs/which-package.md`](docs/which-package.md) for the compact operating map
- [`docs/routing-contract.md`](docs/routing-contract.md)
- [`docs/lifecycle-and-config-contract.md`](docs/lifecycle-and-config-contract.md)

Then, if needed:

- [`docs/lifecycle-and-config-contract.md`](docs/lifecycle-and-config-contract.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/integration-contract.md`](docs/integration-contract.md)
- [`docs/contributor-playbook.md`](docs/contributor-playbook.md)
- [`docs/maintainer-commands.md`](docs/maintainer-commands.md)
