# Workspace Config Contract

## Purpose

This contract defines the repo-owned structured agent configuration substrate that the workspace layer hosts.

Use it when the question is:

- what classes of structured agent configuration exist here?
- which surface is authoritative for each class?
- how do planning and memory attach to the substrate?
- which startup or handoff prose surfaces are adapters rather than primary authority?
- which compact query should answer a configuration question first?

## Core Model

Treat Agentic Workspace as a repo-owned agent configuration system with four configuration classes:

| Class | Purpose | Primary owner | Compact query |
| --- | --- | --- | --- |
| Startup and adapter policy | Canonical startup entrypoint, prose adapter role, and runtime-artifact profile. | workspace config plus this contract | `agentic-workspace defaults --section startup --format json` |
| Workspace policy | Repo-owned default preset, improvement latitude, optimization bias, and update intent. | `.agentic-workspace/config.toml` | `agentic-workspace config --target ./repo --format json` |
| Module attachment | Which behavior modules exist, what they own, and how they compose without merging ownership. | module descriptors plus `.agentic-workspace/OWNERSHIP.toml` | `agentic-workspace ownership --target ./repo --format json`; `agentic-workspace modules --format json` |
| Module state | Active planning state and durable memory state that consume the substrate but stay module-owned. | planning and memory surfaces | `agentic-workspace report --target ./repo --format json` |

The workspace layer owns the substrate and composition logic.
Planning and Memory remain behavior modules inside that substrate rather than ambient prose branches.

## Authority Map

- **Repo-owned workspace policy** lives in `.agentic-workspace/config.toml`.
- **Workspace-owned shared contract docs** live in `.agentic-workspace/docs/`.
- **Ownership and authority lookup** live in `.agentic-workspace/OWNERSHIP.toml` and `agentic-workspace ownership --target ./repo --format json`.
- **Module descriptors** define installed module capabilities, workflow surfaces, generated artifacts, dependencies, and conflicts.
- **Planning** owns active execution state and near-term continuation.
- **Memory** owns durable anti-rediscovery understanding.
- **Repo-owned prose startup surfaces** remain useful, but they are adapters over the structured substrate once the workspace is installed.

Do not treat prose surfaces as the primary authority once the structured substrate can answer the same question directly.

## Module Attachment Points

Behavior modules attach to the substrate through descriptor-owned metadata:

- module name and description
- lifecycle commands and install detection
- workflow surfaces and generated artifacts
- startup steps and sources of truth
- capability, dependency, and conflict declarations
- result-contract shape

The workspace layer may compose those descriptors, report on them, and route startup through them.
It must not absorb module-owned domain rules or mutate planning/memory state as part of the substrate definition itself.

## Selective Loading Rule

Prefer the smallest compact query that answers the current configuration question:

1. `agentic-workspace defaults --section agent_configuration_system --format json`
2. `agentic-workspace config --target ./repo --format json`
3. `agentic-workspace ownership --target ./repo --format json`
4. `agentic-workspace modules --format json`
5. `agentic-workspace report --target ./repo --format json`

Open deeper docs or module-local surfaces only when the compact query is insufficient.

## Compact Query Classes

The structured substrate should answer a small number of high-value questions cheaply:

| Query class | Ask first | Deeper only if needed |
| --- | --- | --- |
| Startup path | `agentic-workspace defaults --section startup --format json` | `agentic-workspace config --target ./repo --format json`, then `AGENTS.md` |
| Active behavior modules | `agentic-workspace ownership --target ./repo --format json` | `agentic-workspace modules --format json`, then `agentic-workspace report --target ./repo --format json` |
| Proof and ownership rules | `agentic-workspace ownership --target ./repo --format json` | `agentic-workspace defaults --section validation --format json`, then `agentic-workspace report --target ./repo --format json` |
| Repo-local current work | `agentic-workspace summary --format json` | `agentic-workspace report --target ./repo --format json`, then the active execplan only if summary points there |
| Relevant subinstructions | `agentic-workspace defaults --section agent_configuration_queries --format json` | `agentic-workspace report --target ./repo --format json`, then only the module-local docs or runbooks already in scope |

Selective loading means:

- prefer one compact answer over broad rereads
- route from defaults, config, ownership, report, or summary before opening module-local prose
- load planning or memory details only when the compact answer points at active work or durable module-owned state
- leave unrelated modules and subinstructions unloaded unless the current surface, proof lane, or active planning state makes them relevant

## Prose Adapter Rule

The structured substrate is authoritative.
The following prose surfaces are compatibility adapters and routing bridges:

- `AGENTS.md`
- `llms.txt`
- generated helper guidance exposed through compact report/default surfaces

They should:

- route toward the substrate
- stay compact
- avoid inventing new durable behavior first
- preserve weaker-agent compatibility without reclaiming primary authority

## Repo-Custom Workflow Obligations

Repo-custom workflow additions should be declared in `.agentic-workspace/config.toml` under `workflow_obligations`, not invented first in `AGENTS.md` or active planning.

Each obligation stays small and reviewable:

- `summary`: what repo-local expectation matters
- `stage`: when it matters, such as `before-claiming-completion`, `before-commit`, or `review`
- `scope_tags`: which slices or surfaces should treat it as relevant
- `commands`: the bounded checks or finishing steps the repo expects
- `review_hint`: the compact reminder review or closure should carry forward

The workspace layer owns declaration and reporting of these obligations.
Planning consumes only the obligations relevant to the current touched scope.
Do not use this mechanism to create a scheduler, a giant static workflow catalog, or a substitute for task-specific proof.

## System Intent Boundary

`SYSTEM_INTENT.md` remains a compass for shaping means and review.
It is not itself the configuration substrate, active planning state, or enforcement layer.

Use the substrate to make relevant system-intent hooks queryable and operational.
Declare repo-owned intent sources in `.agentic-workspace/config.toml [system_intent]`, then let the workspace-owned mirrored declaration at `.agentic-workspace/system-intent/intent.toml` carry the normalized system-intent view consumed by package operations.
Refresh source metadata with `agentic-workspace system-intent --target ./repo --sync --format json`, then refine the mirrored declaration through `.agentic-workspace/system-intent/WORKFLOW.md`.

System intent should shape:

- which compact query or workflow obligation is worth surfacing for the current slice
- which local tradeoffs favor cheaper continuation, sharper boundaries, lower residue, or lower operating cost
- how review talks about whether the landed slice served the repo's declared direction instead of only satisfying task intent

Do not turn system intent into a scheduler or a replacement for bounded task intent.

## Repo-Custom Extension Boundary

Repo-custom workflow additions should attach at the workspace/module-descriptor layer, not as planning-local extension machinery.

They must stay:

- bounded
- explicit about owner and trigger
- reviewable through the substrate
- narrow enough that planning only consumes the resulting obligation when it matters to active work

Do not treat the substrate as permission to encode arbitrary repo choreography or full automation graphs.

## Relationship To Other Docs

- Use [lifecycle-and-config-contract.md](lifecycle-and-config-contract.md) for bootstrap, config authority, and recovery mechanics.
- Use [ownership-authority-contract.md](ownership-authority-contract.md) for current owner and authoritative-surface lookup.
- Use [minimum-operating-model.md](minimum-operating-model.md) for the startup-facing boundary map.
- Use [system-intent-contract.md](system-intent-contract.md) when the question is how higher-level system intent remains durable and recoverable.
