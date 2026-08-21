# Modules

Modules add independently owned capabilities to Agentic Workspace. They extend what the generic operating loop can know and do without changing the loop itself or forcing Workspace to absorb their domain semantics.

Planning, Memory, and Verification are the current first-party modules. They are bundled batteries and examples of the module model, not fixed architectural slots.

## Authoring model

The core loop is `resolve -> act -> reconcile`, but those are **Workspace responsibilities**, not three module interfaces.

A module should describe its own domain:

1. **Identity / compatibility** — what capability is this, is it available, and which public contract/runtime range can admit it?
2. **Ownership** — what state, resources, roots, and effects belong to it?
3. **Relevance** — what bounded task/path/state facts make it worth considering now?
4. **Capabilities** — what source-owned resources/context, lazily discoverable skills/procedures, and typed operations can it provide?
5. **Result semantics** — what do its operation results mean inside its own domain: state change, evidence, blocker, residue, continuation fact, or bounded effect?

Dependencies and conflicts belong alongside compatibility/ownership where needed.

Contribution dimensions are optional. A read-only retrieval module may expose only relevance plus resources or a skill. A mechanical action module may expose an operation/result without inventing startup posture, a workflow phase, or a closeout hook. Modules should not implement empty `on_resolve`, `on_act`, or `on_reconcile` callbacks just to fit the framework.

Workspace consumes those declarations through its own loop:

| Workspace step | What Workspace does with module declarations |
| --- | --- |
| **Resolve** | selects relevant resources, constraints, procedures, or action candidates that can change the current decision |
| **Act** | invokes a declared typed operation or routed skill when the current contract selects it |
| **Reconcile** | consumes bounded typed results/effects through the module owner and composes their effect on the next decision |

The module keeps ownership of its domain state and meaning. Workspace consumes only the bounded current effect needed to compose the operating decision.

## Source ownership

Module-owned context remains module-owned. AW should not copy all module state into a generic central context store merely to make composition uniform.

A relevance/context contribution should normally expose only what Workspace needs for current relevance, provenance, routing, and decision composition. Deeper domain detail stays behind the module's selectors, skills, operations, or references.

This keeps the operating-context model narrow and prevents module extensibility from becoming a repository knowledge platform.

## Public contribution contract

The stable public module boundary should remain deliberately smaller than AW's full internal participation vocabulary.

The public contract should be centered on the authoring model above and reuse existing generic primitives where they already fit:

- component/resource declarations for source-owned context;
- routed skills/prompts for deeper procedure;
- typed operation/result/effect/authority contracts for actions;
- declared ownership and compatibility for safe admission;
- bounded relevance sufficient for progressive discovery;
- safe absence/removal and conflict semantics where required.

Internal implementation metadata may be broader. Lifecycle hooks, arbitrary workflow phases, posture fragments, renderer packets, report slots, startup fragments, proof/closeout hooks, and first-party callbacks are not automatically public primitives because they exist today.

The test for every proposed public field is: **does the module author need this to describe their capability, or are we asking them to describe AW's choreography back to AW?** Prefer deriving the latter inside Workspace.

See [Extensibility and public boundary](../extension-boundary.md).

## Practical extension test

Genericity is useful only when it reduces module integration cost.

An ordinary independent module should normally require:

- its own package/implementation;
- its public descriptor/contracts;
- its own tests and fixtures.

Adding that module should not require semantic Workspace edits merely to teach core its identity or domain: no new runtime name switch, core module enum, fixed slot/phase, canonical-skill branch, proof/closeout branch, global posture dimension, or another core-owned per-module list.

Monorepo test/package wiring may exist to exercise an in-repo fixture, but it must remain semantically ignorant of the module. An out-of-tree/external-consumer module should be able to participate through the same public contract without modifying the AW repository.

If a small independent module needs many AW-specific concepts or core-file edits, treat that as evidence that the public seam is still too framework-shaped.

## Progressive discovery

An installed module should stay quiet until relevant.

The ordinary agent should not need a fixed module map to work safely. When a module matters, the resolved operating contract should name the relevant capability, owner, operation, selector, or specialized skill. When it does not matter, its domain and procedures should be absent from first-line context.

Adding a module should not add a mandatory new first-contact command, phase, or mental model.

## Authority and conflicts

Modules do not gain global authority by registering a capability.

A module must not silently widen unrelated:

- repository mutation authority;
- repo policy;
- Planning/current-work authority;
- proof or claim authority;
- parent-intent or completion authority.

Compatibility and ownership/effect conflicts should fail closed before incompatible contributions influence the operating decision. Removal or disappearance must demote the module's active contribution without making unrelated workspace state uninterpretable.

## Repo customization is not a module

Host repositories can program AW through repo-owned config, obligations, skills, canonical guidance, ownership, proof declarations, and deterministic repository operations.

Use repo customization for host-specific policy and operating choices. Use a module for an independently owned reusable capability with its own compatibility/ownership boundary and whatever resources, procedures, operations, or state its domain actually needs.

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

Planning can expose relevant current-work context, Planning operations, and bounded progress/continuation results through the generic capability path. Its rich participation does not define what every module must implement.

Module implementation: [Planning README](../../packages/planning/README.md).

### Memory

Memory owns learned anti-rediscovery repository knowledge.

Typical concerns include:

- invariants and authority boundaries learned during work;
- subsystem orientation expensive to rederive;
- recurring traps and verified failure lessons;
- operator runbooks and routing facts worth retaining.

Memory can expose relevant learned context and capture/retrieval operations/results through the same capability path.

Memory is one module; it is not AW's abstract persistence layer. Other durable context keeps its own canonical owner.

Module implementation: [Memory README](../../packages/memory/README.md).

### Verification

Verification owns reusable soft-verification protocols, bounded evidence summaries, known gaps, and proof-route hints.

Typical concerns include:

- activation of manual or semi-automated verification protocols;
- bounded evidence and residual-risk summaries;
- known gaps and stale conditions;
- proof-route information consumed by the broader claim boundary.

Verification can expose applicable proof context, verification operations, and bounded evidence/gap results through the same capability path.

Module implementation: [Verification README](../../packages/verification/README.md).

## Future modules

The architecture should allow future capabilities—delegation, deployment, richer knowledge retrieval, security, or domains not anticipated today—to use the same generic capability model.

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