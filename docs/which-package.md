# Which Package Should I Install?

Use this page when you are deciding what to adopt in a target repository.

## Product Names And Package Names

- Product name: Agentic Memory
  Current package/CLI: `agentic-memory-bootstrap`
- Product name: Agentic Planning
  Current package/CLI: `agentic-planning-bootstrap`
- Composition layer: `agentic-workspace`

In other words, the ecosystem names are `Agentic Memory` and `Agentic Planning`; the current distributable package names still carry `-bootstrap` because they install the checked-in repo contracts.

For the stable-versus-mutable surface policy that underpins this chooser, see `docs/compatibility-policy.md`.

## Fast Chooser

| If your main problem is... | Install... | Why |
| --- | --- | --- |
| Agents and contributors keep re-discovering stable repo knowledge | `agentic-workspace --preset memory` | The workspace CLI routes lifecycle through the memory module contract without changing module ownership. |
| Active work keeps drifting, fragmenting, or losing completion discipline | `agentic-workspace --preset planning` | The workspace CLI routes lifecycle through the planning module contract without making planning depend on memory. |
| You want both durable memory and checked-in execution planning | `agentic-workspace --preset full` | The workspace layer composes both modules through one public lifecycle entrypoint without replacing their boundaries. |

## Good Fits

### Memory Good Fits

- Polyglot repositories where subsystem knowledge is expensive to rediscover.
- Multi-agent or multi-contributor repos where recurring failures and operator sequences should be shared.
- Repositories that already have task tracking, but lack a durable knowledge layer.

### Planning Good Fits

- Repositories where work spans many short agent sessions.
- Teams that want a checked-in active queue and bounded execplans instead of chat-only task continuity.
- Repositories where backlog tools exist, but active execution still drifts.

### Both

- Repositories using agents as regular maintainers, where active work and durable knowledge both need checked-in homes.
- Repositories that want restartable execution plus minimal rediscovery cost.

## Bad Fits

### Memory Bad Fits

- Repos that only need a task list or milestone tracker.
- Repos where every important fact is already cheap to rediscover from code and docs.

### Planning Bad Fits

- Repos looking for a full project-management system or ticket database.
- Repos that only need durable technical documentation and not checked-in execution steering.

## Partial-Adoption Compatibility Matrix

| Combination | Supported | Installs | Primary writable surfaces |
| --- | --- | --- | --- |
| Memory only | Yes | `memory/`, `.agentic-workspace/memory/`, memory skills, memory freshness tooling | Durable `memory/` notes plus optional weak-authority `memory/current/`; no planning dependency |
| Planning only | Yes | `TODO.md`, `ROADMAP.md`, `docs/execplans/`, `.agentic-workspace/planning/`, generated routing docs, planning checks | Repo planning surfaces; generated `tools/` docs stay rerendered outputs |
| Memory + Planning | Yes | Both module installs, with planning and memory remaining separate owners | Planning for active-now state, memory for durable knowledge, `memory/current/` for compact re-orientation only |
| Workspace lifecycle entrypoint with `--preset memory`, `--preset planning`, or `--preset full` | Yes | Shared lifecycle entrypoint over the same memory/planning module contracts | Same module-owned writable surfaces, plus thin root orchestration entrypoints |
| Workspace layer without memory or planning | No | The workspace layer is intentionally thin and not a standalone domain product | Not applicable |

## Proof Bar

- Memory-only repos should install and adopt cleanly without planning assumptions.
- Planning-only repos should install and adopt cleanly without memory assumptions.
- Repos with both modules should keep ownership separate while the root workspace layer stays thin.
- Single-module repos may still use the workspace CLI as the public lifecycle entrypoint; selective adoption stays enforced by presets, not by forcing direct package CLIs.
- Evidence should come from package tests plus at least one real temporary-repo proof for each supported shape.

## Next Reads

- Memory path: `packages/memory/README.md`
- Planning path: `packages/planning/README.md`
- Workspace lifecycle path: `README.md`
- Architecture and boundaries: `docs/architecture.md`, `docs/boundary-and-extraction.md`, `docs/extension-boundary.md`
- Maturity and support expectations: `docs/maturity-model.md`
