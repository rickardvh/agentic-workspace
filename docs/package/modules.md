# Modules

Modules add independently owned capabilities to Agentic Workspace. They extend what the generic operating loop can know and do without changing the loop itself or forcing Workspace to absorb their domain semantics.

Planning, Memory, and Verification are the current first-party modules. They are bundled batteries and examples of the module model, not fixed architectural slots.

## Participation model

The core loop is `resolve -> act -> reconcile`.

A module may contribute at any of those points through stable declared semantics:

| Loop step | Module contribution |
| --- | --- |
| **Resolve** | bounded relevant context, capability availability, constraints, owner/procedure references, or selectors that can change the current decision |
| **Act** | stable typed operations with explicit inputs, results, effects, and authority |
| **Reconcile** | bounded domain state changes, evidence, residue, continuation facts, or other result semantics owned by the module |

The module keeps ownership of its domain state and meaning. Workspace consumes only the bounded current effect needed to compose the operating decision.

A module should not define an independent mandatory workflow when its capability can enrich the existing loop.

## Source ownership

Module-owned context remains module-owned. AW should not copy all module state into a generic central context store merely to make composition uniform.

A resolve contribution should normally expose only what Workspace needs for current relevance, provenance, routing, and decision composition. Deeper domain detail stays behind the module's selectors, skills, operations, or references.

This keeps the operating-context model narrow and prevents module extensibility from becoming a repository knowledge platform.

## Public contribution contract

The stable public module boundary should remain deliberately smaller than AW's full internal participation vocabulary.

An independent module should need only semantics required for safe composition, such as:

- module identity, compatibility, and availability;
- declared capabilities and relevance/activation;
- owned state/resources and writable/effect boundaries;
- compact resolve contributions and routed procedure references;
- stable typed operations and result/effect contracts;
- bounded reconcile/result contributions;
- lifecycle, dependencies, conflicts, safe absence, and removal;
- generated discovery/reference metadata.

Internal implementation metadata may be broader. Lifecycle hooks, arbitrary workflow phases, posture fragments, renderer packets, and first-party callbacks are not automatically public primitives because they exist today.

See [Extensibility and public boundary](../extension-boundary.md).

## Progressive discovery

An installed module should stay quiet until relevant.

The ordinary agent should not need a fixed module map to work safely. When a module matters, the resolved operating contract should name the relevant capability, owner, operation, selector, or specialized skill. When it does not matter, its domain and procedures should be absent from first-line context.

Adding a module should not add a mandatory new first-contact command, phase, or mental model.

## Authority and conflicts

Modules do not gain global authority by registering a contribution.

A module must not silently widen unrelated:

- repository mutation authority;
- repo policy;
- Planning/current-work authority;
- proof or claim authority;
- parent-intent or completion authority.

Compatibility and ownership/effect conflicts should fail closed before incompatible contributions influence the operating decision. Removal or disappearance must demote the module's active contribution without making unrelated workspace state uninterpretable.

## Repo customization is not a module

Host repositories can program AW through repo-owned config, obligations, skills, canonical guidance, ownership, proof declarations, and deterministic repository operations.

Use repo customization for host-specific policy and operating choices. Use a module for an independently owned reusable capability with its own lifecycle, state/resources, operations, and compatibility boundary.

Keeping those mechanisms separate avoids turning every repo rule into a package extension.

## External adapters are not modules

External adapters integrate AW into other agents, CLIs, IDEs, or vendor services by consuming stable AW operations.

Adapters own transport and vendor/tool lifecycle. AW remains unaware of the adapter package. An adapter should not become a module merely because it invokes AW, and AW should not gain an adapter registry or credential store to manage it.

## Current first-party examples

### Planning

Planning owns active execution continuity and bounded intent when that capability is useful.

Typical concerns include:

- current bounded work and continuation ownership;
- execution plans or relationships expensive to reconstruct;
- handoff/restart state;
- active-work proof expectations;
- Planning-domain archive/continuation transitions.

Planning can contribute current-work context during resolve, Planning operations during act, and progress/continuation facts during reconcile.

Module implementation: [Planning README](../../packages/planning/README.md).

### Memory

Memory owns learned anti-rediscovery repository knowledge.

Typical concerns include:

- invariants and authority boundaries learned during work;
- subsystem orientation expensive to rederive;
- recurring traps and verified failure lessons;
- operator runbooks and routing facts worth retaining.

Memory can contribute relevant learned context during resolve, capture/retrieval operations during act, and durable lesson promotion during reconcile.

Memory is one module; it is not AW's abstract persistence layer. Other durable context keeps its own canonical owner.

Module implementation: [Memory README](../../packages/memory/README.md).

### Verification

Verification owns reusable soft-verification protocols, bounded evidence summaries, known gaps, and proof-route hints.

Typical concerns include:

- activation of manual or semi-automated verification protocols;
- bounded evidence and residual-risk summaries;
- known gaps and stale conditions;
- proof-route information consumed by the broader claim boundary.

Verification can contribute applicable proof context during resolve, verification operations during act, and evidence/gap facts during reconcile.

Module implementation: [Verification README](../../packages/verification/README.md).

## Future modules

The architecture should allow future capabilities—delegation, deployment, richer knowledge retrieval, security, or domains not anticipated today—to use the same generic contribution model.

A future RAG, knowledge-graph, semantic-index, or repository-model capability would therefore be a module layered onto AW. Core AW does not need those capabilities to preserve and route bounded operating context.

## Selection and packaging

A repo can use the root routing/control layer with no modules, select only capabilities that pay back, or combine several.

Module selection controls the host-repo footprint. The current root Python distribution still bundles first-party module packages for lifecycle convenience; that packaging choice does not define semantic privilege.

## Contract authority

Machine-readable module contracts own exact current metadata. Conceptual docs explain roles and boundaries rather than duplicating registry fields.

Use:

- [Module registry reference](../reference/module-registry.md) for generated field-level information;
- [Contracts and references](contracts.md) for source-contract and generated-projection relationships;
- [Architecture](../architecture.md) for operating-context/control/module/repo/adapter composition.