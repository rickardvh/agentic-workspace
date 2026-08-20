# Extensibility and Public Boundary

Extensibility is a core Agentic Workspace product property. The current support boundary is narrower than that architectural intent: AW already has generic module participation machinery and a stable external-operation direction, while the public third-party module compatibility contract is still being deliberately stabilized.

This page distinguishes **product direction** from **current support-bearing compatibility** so those concepts do not get conflated.

## Core stance

Workspace should be a small operating kernel that composes independently owned capabilities. Planning, Memory, and Verification are first-party batteries and proving grounds for that model, not the fixed outer boundary of the architecture.

The extension architecture has three distinct forms:

1. **Modules** add domain capabilities, owned state/resources, operations, lifecycle, and bounded effects on the ordinary operating decision.
2. **Repo customization** uses host-owned config, obligations, skills, canonical guidance, ownership, and proof declarations.
3. **External adapters** integrate AW with other tools and vendors by consuming stable AW operations from outside core.

These forms must not collapse into one generic plugin mechanism because they have different ownership, trust, lifecycle, and compatibility semantics.

## Current support boundary

### First-party modules

Planning, Memory, and Verification are the currently shipped support-bearing module implementations. The coordinated root distribution may bundle them for lifecycle convenience.

They should increasingly exercise the same generic composition path expected of independently implemented modules. Bundling is a distribution choice, not a reason for Workspace to hard-code their domain semantics.

### Independent modules

Independent modules are part of the intended architecture, but the public module contract must remain narrower than the full internal participation registry.

Until a versioned public module compatibility profile is explicitly published and conformance-tested, external module authors should not assume that every field, lifecycle hook, posture fragment, workflow phase, or internal descriptor detail is a stable API.

The public boundary should stabilize only what independent capability authors need for safe composition, including the equivalent of:

- module identity and compatibility;
- declared capabilities and activation/relevance;
- owned resources/state and writable roots;
- stable operations and effect/result contracts;
- lifecycle, dependencies, and conflicts;
- bounded proof/authority effects;
- generated discovery/reference metadata.

Internal implementation flexibility may remain broader.

### External adapters and integrations

External adapters follow an inverted dependency model: the integration knows about AW; AW does not need to know the integration package or vendor.

Adapters may translate native tool events, invoke public AW operations, and keep disposable local integration state. They own transport, authentication, credentials, and vendor-specific lifecycle. They do not own AW Planning state, proof semantics, completion permission, or unrelated repository mutations.

Core should not gain an adapter registry, marketplace, credential store, or vendor-specific configuration solely to support integrations.

## Kernel guarantees extensions must preserve

Any support-bearing extension path must preserve the same kernel invariants:

- **compatibility before authority**: incompatible or unsupported contributions do not partially influence current semantic decisions;
- **explicit ownership**: modules and adapters cannot silently claim unrelated roots, state, proof, or completion authority;
- **bounded relevance**: irrelevant installed capabilities stay out of the first-line operating context;
- **conflict visibility**: collisions name the competing owners and resolution owner instead of relying on hidden precedence;
- **safe absence**: missing or removed capabilities leave the remaining workspace interpretable;
- **clean removal**: package/module/local/promoted output boundaries remain distinguishable when a capability is removed;
- **projection discipline**: generated docs, clients, catalogue entries, and adapters derive from authority rather than becoming parallel sources of truth;
- **ordinary-loop stability**: adding capabilities should normally enrich existing startup/work/proof/closeout/continuation questions instead of multiplying first-contact concepts.

## What the kernel may assume

The kernel may assume only the capabilities declared by an admitted compatible module or host-repo contract. It should not infer behavior from a module's package name, source-tree layout, first-party status, or similarity to Planning/Memory/Verification.

Where the public contract is insufficient, the correct outcome is to extend that contract deliberately or keep the behavior first-party/internal—not to add a hidden module-name special case and call the boundary generic.

## What extensibility does not imply

Extensibility does not require:

- arbitrary in-process code loading from untrusted sources;
- a remote module marketplace;
- a generic event bus or workflow engine;
- every internal callback becoming public API;
- adapter discovery or credentials inside AW;
- fixed module slots matching today's first-party products;
- a new user-visible command for every capability.

## Readiness standard for a public module contract

A module capability should be described as support-bearing for independent authors only when:

1. its public contract is versioned and mechanically distinguishable from internal participation metadata;
2. first-party modules use that same semantic path where applicable;
3. an independently implemented non-core module can be discovered, activated, used, disabled, and removed without Workspace learning its identity;
4. compatibility, conflict, authority, absence, and removal behavior fail closed;
5. reusable conformance fixtures prove the boundary from outside first-party assumptions;
6. ordinary-agent scenarios show that the extension stays quiet when irrelevant and does not materially regress direct work.

This is a readiness bar for **how** the core extensibility goal is exposed safely, not a gate on whether extensibility belongs in the product at all.

## Related documentation

- [Architecture](architecture.md) — kernel/module/repo/adapter ownership model.
- [Modules](package/modules.md) — capability ownership and current first-party modules.
- [Contracts and references](package/contracts.md) — machine-readable contract layers and generated projections.
- [`SYSTEM_INTENT.md`](../SYSTEM_INTENT.md) — durable product intent.
