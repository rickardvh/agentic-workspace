# Modules

Modules add independently owned domain capabilities to the Agentic Workspace operating kernel. They should enrich the ordinary operating loop without forcing Workspace to absorb their domain semantics or requiring agents to learn a separate first-contact framework for each capability.

Planning, Memory, and Verification are the current first-party modules. They are bundled batteries and examples of the module model, not fixed architectural slots.

## Module ownership

One concern should have one primary owner:

| Module | Primary concern | Must not become |
| --- | --- | --- |
| Planning | active execution continuity, bounded intent, handoff, domain closeout state | ticket tracker, backlog mirror, durable knowledge base |
| Memory | durable anti-rediscovery repository knowledge | active task state, execution log, broad canonical docs mirror |
| Verification | reusable soft-verification protocols, bounded evidence, known gaps, proof-route hints | generic CI/test runner, universal proof or completion authority |

Workspace owns the cross-cutting kernel concerns around those domains: compatibility admission, compact routing, lifecycle coordination, conflict visibility, effect/mutation boundaries, and the final composition of proof/claim/continuation state.

## Extensibility model

Modules are intended to participate through declared capabilities rather than Workspace branches keyed to module identity.

The stable public module boundary should remain deliberately smaller than AW's full internal participation vocabulary. An independent module should eventually need only the contract required for safe composition, such as:

- module identity and compatibility;
- declared capabilities and activation/relevance;
- owned state/resources and writable roots;
- stable operations with input/result/effect contracts;
- lifecycle, dependencies, and conflicts;
- bounded proof/authority effects;
- generated discovery/reference metadata.

Internal implementation metadata may be broader. A lifecycle hook, workflow phase, posture fragment, renderer packet, or first-party callback is not automatically a public extension primitive merely because it exists in the registry today.

See [Extensibility and public boundary](../extension-boundary.md) for the distinction between the core extensibility goal and the current support-bearing public contract.

## Ordinary participation

Modules contribute to existing operating questions rather than defining independent workflows wherever possible:

| Ordinary question | Example module contribution |
| --- | --- |
| What context matters before acting? | compact routed domain facts or state references |
| What currently owns continuation? | Planning owner/current-work contribution when applicable |
| What work or effects are safe now? | domain capability, authority, or blocker facts |
| What proof is required? | Verification protocol or module-specific proof route |
| What may be claimed and what survives? | bounded closeout obligations, residue route, or continuation owner |

An irrelevant installed module should stay out of first-line output. A relevant module should contribute through compact structured state or operations, with deeper module detail available by selector or module-owned reference.

Modules must not silently widen repo mutation, Planning, proof, or completion authority outside their declared domain.

## Repo customization is not a module

Host repositories can configure workflow obligations, skills, canonical guidance, ownership, proof policy, and local/shared settings without creating a new package capability.

Use repo customization for host-specific operating rules. Use a module when there is an independently owned reusable domain capability with its own lifecycle, resources/state, operations, and compatibility boundary.

Keeping those mechanisms separate avoids turning every repo rule into a package extension.

## External adapters are not modules

External adapters integrate AW into other agents, CLIs, IDEs, or vendor services through stable AW operations. They own transport and vendor/tool lifecycle; AW remains unaware of the adapter package.

An adapter should not become a module merely because it invokes AW, and AW should not gain an adapter registry or credential store to manage it.

## Current first-party selections

A repo can select the capabilities that pay back for its workflow:

| Selection | Use when |
| --- | --- |
| none / routing-only | compact root routing, config, ownership, and workspace skills are enough |
| `memory` | agents repeatedly rediscover repo invariants, runbooks, traps, or subsystem boundaries |
| `planning` | active intent, proof expectations, handoff, or continuation must survive interruption |
| `verification` | reusable manual/semi-automated verification protocols and bounded evidence need a repo-visible owner |
| combinations | more than one capability independently saves enough future work to justify its state |

Module selection controls checked-in host-repo footprint. The current root Python distribution still bundles all first-party module packages for lifecycle convenience; that packaging choice should not define the semantic extension architecture.

## Planning

Planning owns active execution continuity. Use it when work must remain bounded, resumable, and honestly closeable across sessions or agents.

Typical Planning concerns:

- current bounded work and continuation owner;
- execution plans or lane/slice relationships that are expensive to reconstruct;
- handoff and restart state;
- proof expectations tied to active work;
- domain closeout/archive transitions.

Module implementation: [Planning README](../../packages/planning/README.md).

## Memory

Memory owns durable repository knowledge that is expensive to rediscover.

Typical Memory concerns:

- invariants and authority boundaries;
- subsystem orientation;
- recurring traps and verified failure lessons;
- operator runbooks;
- compact routing facts that let agents read less.

Module implementation: [Memory README](../../packages/memory/README.md).

## Verification

Verification owns reusable soft-verification protocols, bounded evidence summaries, known verification gaps, and proof-route hints.

Typical Verification concerns:

- activation of manual or semi-automated verification protocols;
- bounded evidence and residual-risk summaries;
- known gaps and stale conditions;
- proof-route information consumed by the broader Workspace proof/claim boundary.

Module implementation: [Verification README](../../packages/verification/README.md).

## Contract authority

The machine-readable module registry and related schemas own exact current module/component metadata. Conceptual docs should explain roles and boundaries rather than duplicate every registry field.

Use:

- [Module registry reference](../reference/module-registry.md) for generated field-level contract information;
- [Contracts and references](contracts.md) for how source contracts and generated projections relate;
- [Architecture](../architecture.md) for kernel/module/repo/adapter composition.
