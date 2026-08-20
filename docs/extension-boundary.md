# Extensibility and Public Boundary

Extensibility is a core Agentic Workspace property because the generic operating loop should be able to gain specialized capabilities without changing its mental model.

The architectural goal is broader than the current support-bearing third-party contract. This page distinguishes the two.

## Core stance

AW resolves bounded repo operating context into one current operating contract, lets the agent act through a supported route, and reconciles the result.

Modules are peer extensions of what that loop can know and do. Planning, Memory, and Verification are current first-party examples, not fixed outer slots.

The extension architecture has three distinct forms:

1. **Modules** add reusable domain capabilities through bounded contributions to resolve, act, and reconcile.
2. **Repo customization** supplies host-owned control inputs through config, obligations, skills, canonical guidance, ownership, proof declarations, and repository operations.
3. **External adapters** integrate AW with other tools/vendors by consuming stable AW operations from outside core.

These forms must not collapse into one generic plugin mechanism because they have different ownership, trust, lifecycle, and compatibility semantics.

## What a module contributes

A stable module boundary should expose declarative semantics rather than arbitrary callbacks.

A module may need to declare:

- identity, compatibility, capability, and availability;
- relevance/activation for the current task or changed surface;
- source-owned state/resources and writable/effect ownership;
- compact context/procedure/constraint references that may affect resolve;
- stable typed operations for act;
- bounded domain results/state/evidence/residue for reconcile;
- dependencies, conflicts, absence, removal, and lifecycle;
- generated discovery/reference metadata.

The module's full domain state does not need to be copied into a central AW context store. Workspace should consume only the bounded current contribution needed to compose the operating contract.

## Current support boundary

### First-party modules

Planning, Memory, and Verification are the currently shipped support-bearing module implementations. The coordinated root distribution may bundle them for lifecycle convenience.

They should increasingly exercise the same generic contribution path expected of independent modules. Bundling and default selection are distribution/product presets, not semantic authority.

### Independent modules

Independent modules are part of the intended architecture, but the public contribution contract must remain narrower than the full internal registry/runtime vocabulary.

Until a versioned public compatibility profile is explicitly published and conformance-tested, independent authors should not assume that every lifecycle hook, posture fragment, workflow phase, renderer packet, callback, or internal descriptor field is stable API.

The public boundary should stabilize only the semantics necessary for safe composition through the existing operating decision.

### External adapters

External adapters follow an inverted dependency model: the integration knows about AW; AW does not need to know the integration package or vendor.

Adapters may translate native events, invoke AW operations, and keep disposable local integration state. They own transport, authentication, credentials, and vendor-specific lifecycle. They do not gain repository policy, module, proof, or completion authority merely by transporting a result.

Core should not gain an adapter registry, marketplace, credential store, or vendor-specific configuration solely to support integrations.

## Guarantees extensions must preserve

Any support-bearing extension path must preserve the same dynamic-control invariants:

- **compatibility before authority** — incompatible contributions do not partially influence the current decision;
- **source ownership** — module state and repo policy keep their own owners; the compiled operating contract is a projection, not a new source of truth;
- **bounded relevance** — irrelevant installed capabilities stay out of first-line context and instructions;
- **constructible actions** — relevant capability should expose supported operations/skills/routes rather than conceptual transitions with no implementation path;
- **bounded effects** — a module cannot widen unrelated mutation, policy, proof, or completion authority;
- **conflict visibility** — collisions name competing owners and the resolution owner rather than relying on hidden precedence;
- **safe absence/removal** — a missing or removed capability leaves the rest of the workspace interpretable and clears its active authority;
- **progressive discovery** — adding capability does not proportionally increase startup burden;
- **one control path** — modules contribute to the existing compiled operating decision instead of creating peer decision engines or mandatory workflows.

## What the kernel may assume

The kernel may assume only semantics declared by an admitted compatible capability or host-repo contract.

It should not infer behavior from package name, source-tree layout, first-party status, or similarity to Planning/Memory/Verification. Where the public contract is insufficient, extend it deliberately or keep the behavior internal; do not hide a module-name branch behind generic-looking metadata.

## What extensibility does not imply

Extensibility does not require:

- a repository knowledge database, semantic index, RAG layer, or knowledge graph in core;
- arbitrary untrusted in-process code loading;
- a remote module marketplace;
- a generic callback/event-bus/workflow engine;
- every internal hook becoming public API;
- adapter discovery or credentials inside AW;
- fixed module slots matching today's first-party products;
- a new user-visible command or phase for every capability.

A richer repository-knowledge capability can be a module if useful; it does not redefine the core operating-context model.

## Readiness standard for independent modules

A capability should be described as support-bearing for independent authors only when:

1. its public contribution contract is versioned and mechanically distinguishable from internal metadata;
2. first-party modules use that same semantic path where applicable;
3. an independent non-core module can be discovered, routed, acted through, reconciled, disabled, and removed without Workspace learning its identity;
4. compatibility, conflict, authority, absence, and removal fail closed;
5. reusable conformance fixtures prove the boundary outside first-party assumptions;
6. ordinary-agent scenarios show that relevant capability appears progressively, irrelevant capability stays quiet, and direct work does not materially regress.

This is a readiness bar for how extensibility is exposed safely, not a gate on whether extensibility belongs in the product.

## Related documentation

- [Architecture](architecture.md) — operating-context/control/module/repo/adapter model.
- [Modules](package/modules.md) — module contribution model and current first-party examples.
- [Contracts and references](package/contracts.md) — machine-readable contracts and generated projections.
- [`SYSTEM_INTENT.md`](../SYSTEM_INTENT.md) — durable product intent.