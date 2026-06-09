# Installed Surfaces

An installed host repository gets a small set of checked-in surfaces. Their purpose is to make startup, ownership, active work, durable knowledge, and verification discoverable from repository state.

## Root Surfaces

| Surface | Owner | Purpose |
| --- | --- | --- |
| `AGENTS.md` | repo-owned adapter with managed fences | first file an agent can read; routes to compact workspace commands |
| `.agentic-workspace/` | product-managed enclave | shared workspace configuration, contracts, module roots, and local boundaries |
| `.agentic-workspace/config.toml` | repo-owned config | selected modules, posture, workflow obligations, and repo-specific settings |
| `.agentic-workspace/OWNERSHIP.toml` | repo-owned ledger | managed paths, fences, and authority metadata |
| `.agentic-workspace/WORKFLOW.md` | product-managed workflow adapter | CLI-first bootstrap router and Markdown fallback for installed workspaces |
| `.agentic-workspace/docs/module-map.md` | product-managed module router | compact abstraction ladder for Workspace, Planning, Memory, and generated references |
| `.agentic-workspace/skills/` | product-managed workspace skills | first-contact workflow skills for startup, routing, proof, closeout, and module boundaries |
| `.agentic-workspace/local/` | local-only ignored area | machine-local overrides, caches, and non-shared runtime aids |

The package keeps `AGENTS.md` thin. Durable rules and structured state live under `.agentic-workspace/` or in repo-owned docs, not in a growing startup manual.

## Participation Boundary

Installed surfaces should expose the operating loop, not every implementation
detail. The ordinary path starts from `AGENTS.md` and compact Workspace commands;
module roots, reports, skills, and generated references are opened only when
that loop routes there.

Modules participate by declaring resources, tools, prompts or skills, schemas,
roots, reports, gates, proof routes, lifecycle hooks, workflow phases, startup
routing hints, state owners, and safety metadata. Repo-configured
`workflow_obligations` participate by stage and scope tag. Both are surfaced
through compact routing and reports so a host repo can add obligations or
modules without turning the first-contact surface into a manual.

Planning, Memory, and Verification are first-party examples of the same open
participation model. Their installed roots demonstrate active state, durable
knowledge, and soft verification ownership, but they are not the limit of what a
module can contribute.

## Surface Classes

The installed and source-checkout surfaces fall into different classes. Keeping those classes distinct is what prevents the docs set from becoming another startup burden.

| Class | Examples | How readers should use it |
| --- | --- | --- |
| core entrypoint | `AGENTS.md`, `agentic-workspace start`, `agentic-workspace summary` | start here or let compact commands route deeper |
| secondary/deep surface | `.agentic-workspace/WORKFLOW.md`, `.agentic-workspace/docs/`, `.agentic-workspace/planning/`, `.agentic-workspace/memory/` | open only when a compact command or package doc points there |
| machine contract | `.agentic-workspace/OWNERSHIP.toml`, contract JSON, schema JSON, manifest files | inspect through commands or generated references before hand-reading |
| generated adapter | generated agent aids, `docs/reference/*.md` | treat as derived output; edit the source contract or renderer instead |
| local-only surface | `.agentic-workspace/local/` | machine-local cache or override, not shared authority |
| review artifact | `docs/reviews/*.md` | dated evidence for future work, not current product documentation |
| maintainer machinery | `scripts/`, package bootstrap payloads, generated-package development files | source-checkout workflow only, not ordinary host-repo operation |

Stable conclusions in this table come from the dated visible-surface and shipped-payload reviews, now promoted here so readers do not need to mine review history for the current answer.

## Planning Surfaces

Planning adds active execution state:

| Surface | Purpose |
| --- | --- |
| `.agentic-workspace/planning/state.toml` | active items, roadmap lanes, and current planning state |
| `.agentic-workspace/planning/execplans/` | bounded execution plans and archives |
| `.agentic-workspace/planning/agent-manifest.json` | module-managed manifest for generated agent aids |
| `.agentic-workspace/planning/schemas/` | planning-specific schema contracts |

Raw planning files are opened only when `summary`, `preflight`, or another compact route points there.

## Memory Surfaces

Memory adds durable anti-rediscovery knowledge:

| Surface | Purpose |
| --- | --- |
| `.agentic-workspace/memory/repo/index.md` | route-indexed memory entrypoint |
| `.agentic-workspace/memory/repo/manifest.toml` | machine-readable memory note metadata |
| `.agentic-workspace/memory/repo/domains/` | subsystem orientation |
| `.agentic-workspace/memory/repo/invariants/` | contracts and authority boundaries |
| `.agentic-workspace/memory/repo/runbooks/` | repeatable operator procedures |
| `.agentic-workspace/memory/repo/decisions/` | longer-lived rationale |
| `.agentic-workspace/memory/skills/` | package-managed memory skills |

Memory should reduce rediscovery cost. It is not a task tracker, execution log, or broad product documentation replacement.

## Payload And Source Boundaries

The root workspace package, Planning package, Memory package, and command-generation package have different delivery roles:

| Area | Shipped or installed role | Hidden/source-checkout role |
| --- | --- | --- |
| root workspace package | root CLI, shared lifecycle orchestration, contracts, generated adapters, workspace skills, config/report/proof routing | contract tooling, generated-package development, maintainer checks |
| Planning | active planning state, execplan templates, selected installed contract docs, planning schemas | package tests, payload verification, optional richer planning surfaces |
| Memory | durable memory note skeleton, manifest, workflow, package-managed skills, note templates | memory package tests, payload verification, package-local bootstrap source |
| command generation | none in ordinary host-repo operation | internal renderer and schema boundary for generated CLI packages |

For exact contract fields behind this overview, see [Workspace config](../reference/workspace-config.md), [Workspace surfaces manifest](../reference/workspace-surfaces-manifest.md), [Module registry](../reference/module-registry.md), and [Command package IR](../reference/command-package-ir.md).

## Ownership Rule

The stable rule is one owner per concern:

- active execution state belongs in Planning;
- durable repo knowledge belongs in Memory or canonical docs;
- package-managed installed contracts live under `.agentic-workspace/`;
- repo-owned startup and documentation stay outside managed areas unless they use explicit managed fences;
- local-only runtime residue stays under `.agentic-workspace/local/`.

For exact ownership and path metadata, use:

```bash
agentic-workspace ownership --target ./repo --format json
```
