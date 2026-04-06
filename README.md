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

`init` defaults to the full preset when you omit module selection. It bootstraps mechanically, detects whether the repo should stay in clean-install mode or switch to conservative adopt mode, and can print or write a repo-specific handoff prompt when finishing work still needs judgment.

After bootstrap, use the same root CLI for the shared lifecycle verbs:

```bash
agentic-workspace status --target /path/to/repo
agentic-workspace doctor --target /path/to/repo
agentic-workspace upgrade --target /path/to/repo
agentic-workspace uninstall --target /path/to/repo --preset planning
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

Use the module-specific CLIs when you want package-local control. Use `agentic-workspace` when you want the thin composition layer to select modules, sequence them, and aggregate the bootstrap report and handoff prompt.

## Maturity Today

- `agentic-memory-bootstrap`: beta
- `agentic-planning-bootstrap`: alpha

See `docs/maturity-model.md` for what `alpha` and `beta` mean here.

## Docs Map

For adopters:

- `docs/which-package.md` - choose Memory, Planning, or both.
- `docs/architecture.md` - see the public ecosystem shape and thin-workspace boundary.
- `docs/integration-contract.md` - understand how memory, planning, managed surfaces, and generated docs interact.
- `docs/maturity-model.md` - understand current alpha/beta expectations.

For boundaries and ecosystem policy:

- `docs/boundary-and-extraction.md` - decide what belongs in a package, the workspace layer, or a generated surface.
- `docs/ecosystem-roadmap.md` - see long-horizon direction for the ecosystem shape.
- `docs/design-principles.md` - review the product rules that constrain future changes.

For maintainers:

- `docs/contributor-playbook.md` - choose the right ownership surface and validation lane before editing.
- `docs/maintainer-commands.md` - canonical command index for routine maintenance.
- `docs/collaboration-safety.md` - concurrent-edit and git hygiene rules.
- `docs/installed-contract-design-checklist.md` - review bar for new or changed shipped surfaces.
- `docs/dogfooding-feedback.md` - classify internal friction before routing it onward.
- `docs/workflow-contract-changes.md` - compact record of recent workflow-surface changes.

For agent maintainers, the primary operating path is `AGENTS.md`, `TODO.md`, the active execplan, and `docs/contributor-playbook.md`.

For maintainer workflow, command routing, and generated-surface checks, go straight to `docs/contributor-playbook.md` and `docs/maintainer-commands.md`.
