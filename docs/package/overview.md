# Package Overview

`agentic-workspace` is the root package and CLI for a small repo-native operating substrate. It exists for repositories where agent work must survive time, tool changes, branches, model changes, handoff, or non-trivial proof expectations without forcing each new agent to reconstruct the task from chat history.

AW is an amortized coordination layer: it adds bounded structure when that structure costs less than future rediscovery, repair, proof ambiguity, or handoff loss. For short-lived work in a repo that is already cheap to understand, the right AW footprint may be minimal or none.

## Product model

Workspace is the kernel. It owns the cross-cutting mechanics needed for safe composition and continuity:

- compact startup and current-work routing;
- compatibility and lifecycle admission;
- ownership and authority composition;
- effect, mutation, proof, and claim boundaries;
- conflict visibility and bounded recovery;
- stable operation contracts for modules and external consumers.

Domain semantics should stay outside that kernel.

Capabilities extend AW through three different boundaries:

| Boundary | Owner | Purpose |
| --- | --- | --- |
| Modules | module package/domain owner | add domain capabilities, owned state/resources, operations, and bounded effects on the ordinary loop |
| Repo customization | host repository | declare repo-owned config, workflow obligations, skills, and canonical guidance |
| External adapters | independent integration package/tool | translate vendor/tool transport to AW's stable public operations without becoming AW authority |

Planning, Memory, and Verification are the bundled first-party modules and the current proving grounds for the module model. They should not require permanent semantic privilege in Workspace merely because they ship with the root distribution.

See [Modules](modules.md), [Architecture](../architecture.md), and [Extensibility and public boundary](../extension-boundary.md).

## What ships

The coordinated distribution currently includes:

- the `agentic-workspace` root CLI and shared lifecycle/routing behavior;
- first-party Planning, Memory, and Verification packages;
- package-managed workspace skills and compact routing adapters;
- machine-readable command, operation, module, proof, report, selector, ownership, and lifecycle contracts;
- JSON schemata and generated reference projections;
- installable payload used to create the small `.agentic-workspace/` host-repo enclave.

The current root Python distribution bundles all three first-party module distributions for lifecycle convenience. That packaging decision is not the intended architectural definition of the module boundary. Host-repo module selection controls which module state is installed and active in the repository.

## Ordinary operation

The ordinary product is phase-question first. Commands are affordances, not a workflow the agent should memorize.

| Question | Ordinary affordance |
| --- | --- |
| What is the smallest safe context before acting? | `agentic-workspace start --target ./repo --task "<task>" --format json` |
| What work currently owns continuation? | `agentic-workspace summary --target ./repo --format json` |
| What changed surfaces and obligations matter now? | `agentic-workspace implement --target ./repo --changed <paths> --task "<task>" --format json` |
| What evidence is required for the intended claim? | `agentic-workspace proof --target ./repo --changed <paths> --format json` |
| What may be claimed and what must survive? | the compact current-owner/closeout projection routed by the ordinary decision path |

Diagnostics such as `report`, `doctor`, `ownership`, `modules`, `defaults`, and verbose/raw state should stay behind routing unless the current question needs them.

A module should normally enrich one of these existing questions. Installing more capabilities should not require agents to learn a proportionally larger first-contact framework.

## Ownership model

Keep one primary owner per concern:

- **Planning** owns active execution continuity and bounded intent when Planning is selected.
- **Memory** owns durable anti-rediscovery repo knowledge.
- **Verification** owns reusable soft-verification protocols, bounded evidence records, and known verification gaps.
- **Workspace** owns cross-cutting composition, compatibility, routing, lifecycle coordination, and final kernel-level claim/effect boundaries.
- **The host repository** owns its canonical docs, policies, ordinary source, and promoted output.
- **Local state** may support diagnostics, integrations, or machine-specific preferences but is not shared authority by existence alone.

External trackers and services normally provide evidence rather than automatically owning Planning completion or repo intent.

## Trust model

AW is not a sandbox. A repository can configure proof or executor commands that inherit the caller's filesystem and credential authority. Treat the repository and those commands as trusted before execution. See [Threat model and supply-chain boundary](../security/threat-model.md).

## Module selection

The bundled first-party capabilities are independently useful:

| Selection | Use when |
| --- | --- |
| routing-only / no modules | compact startup, config, ownership, skills, and shared routing are enough |
| Memory | agents repeatedly rediscover repo invariants, runbooks, traps, or subsystem boundaries |
| Planning | active work must survive interruption, task switching, proof obligations, or handoff |
| Verification | reusable manual/semi-automated verification protocols and bounded evidence need a repo-visible owner |
| combinations | more than one of those problems is independently expensive enough to justify its owner |

The threshold is expected future value, not team size. Solo work can benefit when the handoff is to a future session, branch, or model.

## Documentation layers

Use the documentation at the level of the question:

1. **Conceptual package docs** explain stable product roles and boundaries.
2. **Generated/current-value references** should answer exact command, schema, module, and footprint questions from machine-readable authority.
3. **Maintainer docs** own source-checkout generation, validation, release, and dogfooding procedure.
4. **Reviews and Planning** retain dated evidence and active implementation shaping; they are not current public product explanation.

Read next:

- [Modules](modules.md)
- [Lifecycle and context commands](lifecycle.md)
- [Installed surfaces](installed-surfaces.md)
- [Contracts and references](contracts.md)
- [Architecture](../architecture.md)
- [Documentation index](../index.md)
