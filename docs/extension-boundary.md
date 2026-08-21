# Extensibility and Public Boundary

Extensibility is a core Agentic Workspace property because the generic operating loop should be able to gain specialized capabilities without changing its mental model **or making capability authors learn AW's internal choreography**.

The architecture is broader than the deliberately small support-bearing third-party contract. This page distinguishes the public seam from internal and host-owned extension surfaces.

## Core stance

AW resolves bounded repo operating context into one current operating contract, lets the agent act through a supported route, and reconciles the result.

Modules are peer extensions of what that loop can know and do. Planning, Memory, and Verification are current first-party examples, not fixed outer slots.

The authoring rule is: **a module describes its domain; Workspace owns the loop.** `resolve -> act -> reconcile` is how Workspace consumes capability declarations, not a requirement that every module implement three hooks or describe AW's phases back to it.

The extension architecture has three distinct forms:

1. **Modules** add reusable domain capabilities through small declarative capability/ownership/relevance/operation/result contracts.
2. **Repo customization** supplies host-owned control inputs through config, obligations, skills, canonical guidance, ownership, proof declarations, and repository operations.
3. **External adapters** integrate AW with other tools/vendors by consuming stable AW operations from outside core.

These forms must not collapse into one generic plugin mechanism because they have different ownership, trust, lifecycle, and compatibility semantics.

## What a module should need to declare

A stable public module boundary should expose domain semantics rather than arbitrary callbacks or phase registration.

For an ordinary capability, the contract should reduce toward:

- **identity / compatibility** — what capability this is, whether it is available, and whether core can admit it safely;
- **ownership** — which state/resources/roots/effects belong to it;
- **relevance** — bounded facts that make the capability worth considering for the current task or changed surface;
- **capabilities** — source-owned resources/context, lazily discoverable procedures/skills, and typed operations the module provides;
- **result semantics** — bounded state/evidence/blocker/residue/continuation/effect meaning returned by those operations or observations.

Dependencies/conflicts may compose with compatibility/ownership where required.

Those dimensions are optional when a module does not need them. A read-only context/retrieval module should not declare dummy action or reconciliation hooks. An operation-oriented module should not invent startup posture, workflow phases, report slots, or closeout behavior simply because AW currently has those internal concepts.

Workspace decides how admitted declarations participate in resolve/act/reconcile through the existing compiled operating decision.

The module's full domain state does not need to be copied into a central AW context store. Workspace should consume only the bounded current contribution needed to compose the operating contract.

## Current support boundary

### First-party modules

Planning, Memory, and Verification are the currently shipped support-bearing module implementations. The coordinated root distribution may bundle them for lifecycle convenience.

They should increasingly exercise the same generic capability path expected of independent modules. Bundling and default selection are distribution/product presets, not semantic authority.

### Independent modules

Independent modules can publish an `agentic_workspace.modules` entry point whose value is an `agentic-workspace/module-capability/v2` descriptor. Core discovers and validates that descriptor without learning the module's identity, derives its bounded `resolve -> act -> reconcile` participation, and admits declared typed operations through the same effect and ownership checks used by first-party contributions.

The public contribution contract remains narrower than the full internal registry/runtime vocabulary. Independent authors should not assume that lifecycle hooks, posture fragments, workflow phases, renderer packets, report slots, callbacks, or internal descriptor fields are stable API.

See [Module capability contract](module-capability-contract.md) for the exact authoring and compatibility boundary.

### External adapters

External adapters follow an inverted dependency model: the integration knows about AW; AW does not need to know the integration package or vendor.

Adapters may translate native events, invoke AW operations, and keep disposable local integration state. They own transport, authentication, credentials, and vendor-specific lifecycle. They do not gain repository policy, module, proof, or completion authority merely by transporting a result.

Core should not gain an adapter registry, marketplace, credential store, or vendor-specific configuration solely to support integrations.

## Practical extension boundary

A generic contract is not useful merely because it can describe many module shapes. It is useful when a later independent module is cheap to add.

The expected ordinary authoring path is approximately:

- module package/implementation;
- public descriptor/contracts;
- module-owned tests and fixtures.

Adding a new independent module should not require semantic Workspace edits merely to recognize that module's identity/domain. In particular, it should not require adding the module to runtime switches, core enums/name lists, fixed module-slot maps, canonical operating skills, proof/closeout branches, global posture dimensions, or another core-owned per-module registry entry.

An in-repo fixture may need generic test/package wiring, but that wiring must not encode the fixture's domain semantics. A real out-of-tree/external-consumer module should be able to install/admit/use the same public contract without modifying the AW repository.

If a deliberately small module needs many AW-specific declarations or core-file edits, that is evidence that the extension contract is still too framework-shaped.

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
- **one control path** — modules contribute to the existing compiled operating decision instead of creating peer decision engines or mandatory workflows;
- **low-coupling authoring** — a module declares its domain; core derives loop participation rather than requiring the author to register AW-specific phase/slot choreography.

## What the kernel may assume

The kernel may assume only semantics declared by an admitted compatible capability or host-repo contract.

It should not infer behavior from package name, source-tree layout, first-party status, or similarity to Planning/Memory/Verification. Where the public contract is insufficient, extend it deliberately or keep the behavior internal; do not hide a module-name branch behind generic-looking metadata.

Nor should core move module-name coupling from Python into a central JSON/TOML list and call the result generic. A core-owned per-module registration edit is still coupling when every independent module requires one.

## What extensibility does not imply

Extensibility does not require:

- a repository knowledge database, semantic index, RAG layer, or knowledge graph in core;
- arbitrary untrusted in-process code loading;
- a remote module marketplace;
- a generic callback/event-bus/workflow engine;
- mandatory `on_resolve`, `on_act`, or `on_reconcile` hooks;
- every internal hook becoming public API;
- adapter discovery or credentials inside AW;
- fixed module slots matching today's first-party products;
- a new user-visible command or phase for every capability.

A richer repository-knowledge capability can be a module if useful; it does not redefine the core operating-context model.

## Readiness standard for independent modules

A capability should be described as support-bearing for independent authors only when:

1. its public contribution contract is versioned, capability-first, and mechanically distinguishable from internal metadata;
2. first-party modules use that same semantic path where applicable;
3. modules can omit irrelevant contribution dimensions without dummy hooks/phase declarations;
4. an independent non-core module can be discovered, routed, acted through when applicable, reconciled when applicable, disabled, and removed without Workspace learning its identity;
5. an out-of-tree/external-consumer module can participate without modifying the AW repository merely to register its identity/domain;
6. compatibility, conflict, authority, absence, and removal fail closed;
7. reusable conformance fixtures prove the boundary outside first-party assumptions;
8. ordinary-agent scenarios show that relevant capability appears progressively, irrelevant capability stays quiet, and direct work does not materially regress;
9. extension-effort evidence shows any non-module changes are generic infrastructure/test wiring rather than per-module semantic coupling.

This is a readiness bar for how extensibility is exposed safely and practically, not a gate on whether extensibility belongs in the product.

## Related documentation

- [Architecture](architecture.md) — operating-context/control/module/repo/adapter model.
- [Modules](package/modules.md) — capability-first module authoring model and current first-party examples.
- [Contracts and references](package/contracts.md) — machine-readable contracts and generated projections.
- [`SYSTEM_INTENT.md`](../SYSTEM_INTENT.md) — durable product intent.
