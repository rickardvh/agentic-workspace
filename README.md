# agentic-workspace

Monorepo host for two distributable packages:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

This repository is the packaging source and dogfooding home for two external products:

- Agentic Memory, currently distributed as `agentic-memory-bootstrap`
- Agentic Planning, currently distributed as `agentic-planning-bootstrap`

## Start Here

If you are landing here for the first time, start with the chooser page:

- `docs/which-package.md`

Short version:

| If you want to add... | Use... | Start with... |
| --- | --- | --- |
| Shared durable repo memory for agents and humans | Agentic Memory | `packages/memory/README.md` |
| Checked-in execution planning surfaces for active work | Agentic Planning | `packages/planning/README.md` |
| Both together | Both packages, optionally composed through `agentic-workspace` | `docs/which-package.md` |

## Why adopt this?

Agentic Workspace gives a repository a durable, checked-in operating system for agents.

Instead of relying on chat history, one model's private memory, or a maintainer repeatedly re-explaining the same context, it puts the repo's working contract into versioned files that agents and humans can share.

Adopt it when you want to make work in a repo:

- easier to restart
- cheaper to continue across sessions
- less dependent on one specific tool or model
- more resistant to drift, rediscovery, and partial work
- easier for multiple agents or contributors to hand off cleanly

What it gives you:

- **Checked-in execution state** through Agentic Planning, so active work stays bounded, resumable, and finishable.
- **Checked-in anti-rediscovery knowledge** through Agentic Memory, so expensive-to-reconstruct context, traps, invariants, and runbooks stop living only in chat or in one contributor's head.
- **One public lifecycle entrypoint** through `agentic-workspace`, so install, adopt, doctor, upgrade, and uninstall stay consistent without collapsing module boundaries.
- **File-native, reviewable state** in Markdown, JSON, and TOML, so the repo's agent contract lives in Git and can be inspected, discussed, and improved like any other code or docs.
- **Selective adoption**: install Memory only, Planning only, or both together, depending on the repo's actual needs.
- **Lower token cost over time** by reducing startup friction, repeated reading, repeated reasoning, and chat-only continuity loss.
- **A built-in improvement loop** that helps turn recurring friction into better docs, checks, scripts, tests, and workflows instead of letting workaround notes accumulate forever.

In short: it helps a repo carry its own context, execution discipline, and agent workflow in checked-in form, so agents can produce higher-quality work with less wasted effort.

## Product Names

The stable ecosystem names in docs are:

- Agentic Memory
- Agentic Planning

The current package and CLI names remain:

- `agentic-memory-bootstrap`
- `agentic-planning-bootstrap`

Treat `-bootstrap` as the current distribution identity for the checked-in contract installers, not as the only human-facing product name.

## Quick Start

The default public bootstrap path is the root workspace CLI:

```bash
# Preferred when uv is available: Agentic Memory only
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target /path/to/repo --preset memory

# Preferred when uv is available: Agentic Planning only
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target /path/to/repo --preset planning

# Preferred when uv is available: both together
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace init --target /path/to/repo --preset full

# Alternative when pipx is available instead: Agentic Memory only
pipx run --spec git+https://github.com/rickardvh/agentic-workspace agentic-workspace init --target /path/to/repo --preset memory

# Alternative when pipx is available instead: Agentic Planning only
pipx run --spec git+https://github.com/rickardvh/agentic-workspace agentic-workspace init --target /path/to/repo --preset planning

# Alternative when pipx is available instead: both together
pipx run --spec git+https://github.com/rickardvh/agentic-workspace agentic-workspace init --target /path/to/repo --preset full
```

Prefer `uvx` when `uv` is already available. Support `pipx` as the equivalent no-install path when it is the runner a repo already uses.

`init` defaults to the full preset when you omit module selection. It bootstraps mechanically, then chooses clean install, conservative adopt, or high-ambiguity adopt based on the repo state. See `docs/init-lifecycle.md` for the mode matrix and prompt requirement semantics.

After bootstrap, use the same root CLI for the shared lifecycle verbs:

```bash
agentic-workspace status --target /path/to/repo
agentic-workspace doctor --target /path/to/repo
agentic-workspace upgrade --target /path/to/repo
agentic-workspace uninstall --target /path/to/repo --preset planning
```

`agentic-workspace doctor` now surfaces each module's frozen compatibility-contract shortlist inside the nested module reports, so maintainers can inspect the current contract boundary from the root CLI without dropping into package-local doctor commands first.

The root `agentic-workspace modules --format json` surface also exposes the current first-party capability, compatibility, and result-contract metadata that the workspace registry relies on; see `docs/module-capability-contract.md`.

Use `agentic-workspace skills --target /path/to/repo --format json` to inspect the explicit installed bundled-skill registries and any checked-in repo-owned skill registries that complement them.

Use `agentic-workspace skills --target /path/to/repo --task "implement the current active milestone" --format json` when the agent needs a registry-backed recommendation for which skill to apply to a task without relying on the user to know skill names.

Use `agentic-workspace` as the normal public lifecycle entrypoint for memory-only, planning-only, and combined installs. Use the module-specific CLIs only for package-local maintainer work, advanced debugging, or when you are working directly on one package contract.

No-install workspace-first prompt lane:

```bash
# Memory-only repo
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target /path/to/repo --preset memory

# Planning-only repo
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target /path/to/repo --preset planning

# Combined install
uvx --from git+https://github.com/rickardvh/agentic-workspace@master agentic-workspace prompt init --target /path/to/repo --preset full
```

Direct module CLIs still exist for maintainers, power users, and package-local workflows:

```bash
# Preferred when uv is available: Agentic Memory advanced path
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt install --target /path/to/repo

# Preferred when uv is available: Agentic Planning advanced path
uvx --from git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target /path/to/repo

# Alternative when pipx is available instead: Agentic Memory advanced path
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/memory agentic-memory-bootstrap prompt install --target /path/to/repo

# Alternative when pipx is available instead: Agentic Planning advanced path
pipx run --spec git+https://github.com/rickardvh/agentic-workspace@master#subdirectory=packages/planning agentic-planning-bootstrap prompt install --target /path/to/repo
```

Use the module-specific CLIs when you want package-local control. Use `agentic-workspace` when you want the public lifecycle entrypoint to select modules, sequence them, and aggregate the bootstrap report and handoff prompt.

## Maturity Today

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: alpha

See `docs/maturity-model.md` for what `alpha` and `beta` mean here.

## Docs Map

For adopters:

- `docs/which-package.md` - choose Memory, Planning, or both.
- `docs/init-lifecycle.md` - understand the root `init` mode matrix and prompt requirements.
- `docs/architecture.md` - see the public ecosystem shape and thin-workspace boundary.
- `docs/integration-contract.md` - understand how memory, planning, managed surfaces, and generated docs interact.
- `docs/maturity-model.md` - understand current alpha/beta expectations.

For boundaries and ecosystem policy:

- `docs/compatibility-policy.md` - understand which surfaces are stable, mutable, or generated before changing a contract.
- `docs/boundary-and-extraction.md` - decide what belongs in a package, the workspace layer, or a generated surface.
- `docs/extension-boundary.md` - understand what module extension is and is not supported today.
- `docs/ecosystem-roadmap.md` - see the long-horizon ecosystem shape; use `ROADMAP.md` as the short sequencing queue.
- `docs/design-principles.md` - review the product rules that constrain future changes.

For maintainers:

- `docs/contributor-playbook.md` - choose the right ownership surface and validation lane before editing.
- `docs/maintainer-commands.md` - canonical command index for routine maintenance.
- `docs/generated-surface-trust.md` - understand the canonical sources and freshness rules for generated maintainer surfaces.
- `docs/collaboration-safety.md` - concurrent-edit and git hygiene rules.
- `docs/installed-contract-design-checklist.md` - review bar for new or changed shipped surfaces.
- `docs/dogfooding-feedback.md` - classify internal friction before routing it onward.
- `docs/workflow-contract-changes.md` - compact record of recent workflow-surface changes.

For agent maintainers, the primary operating path is `AGENTS.md`, `TODO.md`, the active execplan, and `docs/contributor-playbook.md`.

For maintainer workflow, command routing, and generated-surface checks, go straight to `docs/contributor-playbook.md` and `docs/maintainer-commands.md`.
