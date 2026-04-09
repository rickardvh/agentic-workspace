# agentic-workspace

Agentic Workspace gives a repository a durable, checked-in operating system for agents.

It helps agents and humans work in a repo with less rediscovery, less chat-only continuity loss, and lower restart cost over time by keeping the repo's working contract in versioned files instead of scattering it across sessions, tools, or one maintainer's head.

This repository is the packaging source and dogfooding home for two external products:

- Agentic Memory
- Agentic Planning

The root `agentic-workspace` CLI is the normal public lifecycle entrypoint that composes those modules through one thin workspace layer.

## Why adopt this?

Adopt Agentic Workspace when you want work in a repo to become:

- easier to restart
- cheaper to continue across sessions
- less dependent on one specific tool or model
- more resistant to drift, rediscovery, and partial work
- easier for multiple agents or contributors to hand off cleanly
- more efficient over time in token usage and reasoning effort

What it gives you:

- **Checked-in execution state** through Agentic Planning, so active work stays bounded, resumable, and finishable.
- **Checked-in anti-rediscovery knowledge** through Agentic Memory, so expensive-to-reconstruct context, traps, invariants, and runbooks stop living only in chat or in one contributor's head.
- **One public lifecycle entrypoint** through `agentic-workspace`, so install, adopt, doctor, upgrade, and uninstall stay consistent without collapsing module boundaries.
- **File-native, reviewable state** in Markdown, JSON, and TOML, so the repo's agent contract lives in Git and can be inspected, discussed, and improved like any other code or docs.
- **Selective adoption**: install Memory only, Planning only, or both together, depending on the repo's actual needs.
- **Lower token cost over time** by reducing startup friction, repeated reading, repeated reasoning, and chat-only continuity loss.
- **A built-in improvement loop** that helps turn recurring friction into better docs, checks, scripts, tests, and workflows instead of letting workaround notes accumulate forever.

In short:

- **Memory helps future agents understand the repo.**
- **Planning helps agents start, do, resume, and finish work in the repo.**
- **Together they make execution restartable, bounded, and cheaper over time.**

## Choose your install shape

| If your main problem is... | Use... | What you get |
| --- | --- | --- |
| Agents and contributors keep rediscovering stable repo knowledge | `agentic-workspace --preset memory` | Durable anti-rediscovery knowledge without adopting a planning system |
| Active work keeps drifting, fragmenting, or losing completion discipline | `agentic-workspace --preset planning` | Checked-in execution steering without adopting a memory system |
| You want both durable memory and checked-in execution planning | `agentic-workspace --preset full` | One public lifecycle entrypoint over both module contracts |

Memory and Planning are also supported independently. The workspace layer is intentionally thin and is not a standalone domain product by itself.

## Quick start

The normal public bootstrap path is the root workspace CLI.

### With uvx

```bash
# Memory only
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target /path/to/repo --preset memory

# Planning only
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target /path/to/repo --preset planning

# Both together
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target /path/to/repo --preset full
````

### With pipx

```bash
# Memory only
pipx run --spec git+https://github.com/rickardvh/agentic-workspace agentic-workspace init --target /path/to/repo --preset memory

# Planning only
pipx run --spec git+https://github.com/rickardvh/agentic-workspace agentic-workspace init --target /path/to/repo --preset planning

# Both together
pipx run --spec git+https://github.com/rickardvh/agentic-workspace agentic-workspace init --target /path/to/repo --preset full
```

`init` defaults to the full preset if you omit module selection. It bootstraps mechanically, then chooses a clean install, conservative adopt, or high-ambiguity adopt path based on the repo state.

After bootstrap, keep using the same root CLI for normal lifecycle work:

```bash
agentic-workspace status --target /path/to/repo
agentic-workspace doctor --target /path/to/repo
agentic-workspace upgrade --target /path/to/repo
agentic-workspace uninstall --target /path/to/repo --preset planning
```

If you want a no-install handoff prompt for an external agent, use:

```bash
# Memory only
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target /path/to/repo --preset memory

# Planning only
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target /path/to/repo --preset planning

# Both together
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target /path/to/repo --preset full
```

## What each module does

### Agentic Memory

Use Agentic Memory when the repo needs a durable, shared knowledge layer for things that are expensive to rediscover.

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

Memory is the anti-rediscovery layer around code, docs, and planning. It is designed to help agents read less, not more.

### Agentic Planning

Use Agentic Planning when the repo needs a checked-in execution layer for active work.

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

Planning is the execution layer for what matters now, what comes next, and what counts as done.

## How the modules work together

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

The system is intentionally designed so that:

- Planning can reference Memory when active work depends on durable context.
- Completed Planning work can promote durable residue into Memory or canonical docs.
- Neither module has to absorb the other's job.

## Public shape

The current ecosystem shape is:

- **Agentic Memory** - durable repo knowledge
- **Agentic Planning** - active execution state
- **agentic-workspace** - thin workspace orchestrator for shared lifecycle verbs

The workspace layer stays thin on purpose. It composes modules; it does not absorb their domain logic.

## Skills and discovery

The workspace CLI exposes registry-backed discovery surfaces so agents do not need to infer everything from prose.

Useful commands:

```bash
# Inspect first-party module capability and contract metadata
agentic-workspace modules --format json

# Inspect installed bundled and repo-owned skill registries
agentic-workspace skills --target /path/to/repo --format json

# Ask for a registry-backed skill recommendation for a task
agentic-workspace skills --target /path/to/repo --task "implement the current active milestone" --format json
```

Use these when the agent needs structured discovery instead of guessing from docs alone.

## Advanced and maintainer paths

Direct module CLIs still exist for maintainers, power users, and package-local workflows.

Use them when you want package-local control, advanced debugging, or direct work on one package contract.

For normal repo adoption and lifecycle work, prefer the root `agentic-workspace` CLI.

## Maturity today

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: alpha

See `docs/maturity-model.md` for the support expectations behind those labels.

## Start here next

### For adopters

- `docs/which-package.md`
- `docs/init-lifecycle.md`
- `docs/architecture.md`
- `docs/integration-contract.md`
- `docs/maturity-model.md`

### For boundaries and ecosystem policy

- `docs/compatibility-policy.md`
- `docs/boundary-and-extraction.md`
- `docs/extension-boundary.md`
- `docs/ecosystem-roadmap.md`
- `docs/design-principles.md`

### For maintainers

- `docs/contributor-playbook.md`
- `docs/maintainer-commands.md`
- `docs/generated-surface-trust.md`
- `docs/collaboration-safety.md`
- `docs/installed-contract-design-checklist.md`
- `docs/dogfooding-feedback.md`
- `docs/workflow-contract-changes.md`

For agent maintainers, the primary operating path is:

`AGENTS.md -> TODO.md -> active execplan -> docs/contributor-playbook.md`
