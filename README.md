# Agentic Workspace

Agentic Workspace is a programmable, repo-native instruction runtime for agents.

It evolves static repository agent guidance such as `AGENTS.md` into a dynamic system: the repository preserves a small amount of **operating context** that materially affects agent behavior, and AW surfaces only the relevant part for the current task and decision.

The result is a compact operating contract: what matters now, what the agent may or may not do, which procedure or capability applies, what action is safe, what proof or claim boundary matters, and where to go deeper if needed.

## Why it exists

Static agent instructions are useful, but they have structural limits. They tend to be universal rather than task-shaped, accumulate unrelated guidance, depend on agents to discover deeper procedures manually, and cannot easily adapt to current repo state, authority, changed paths, or installed capabilities.

AW keeps the bootstrap small and makes the rest progressively discoverable.

It is useful when agents repeatedly lose expensive context, work crosses sessions/tools/models, repository-specific constraints need to govern behavior, or the correct next action depends on current state rather than a static manual.

If ordinary repository docs, tests, and a short task are already enough, AW should stay unnecessary or minimal.

## Operating context

**Operating context** is the bounded repository context whose availability can materially change how an agent should operate.

Examples can include:

- durable system intent and architectural constraints;
- ownership and authority boundaries;
- repository policy and applicable procedures;
- current work/continuation state supplied by a capability;
- relevant learned lessons supplied by a capability;
- proof requirements, known gaps, or other capability-owned facts;
- machine/runtime facts that constrain what can safely happen now.

AW does **not** try to model everything the repository knows. Source code, canonical documentation, tests, history, and ordinary repository content remain in their existing owners. A knowledge graph, RAG/indexing layer, semantic repository model, or richer retrieval system could be an optional module; it is not what core AW is.

## The operating loop

The ordinary mental model is deliberately small:

| Step | Question |
| --- | --- |
| **Resolve** | What is the smallest trustworthy operating contract for this decision? |
| **Act** | What supported action, skill, owner, or human decision should happen now? |
| **Reconcile** | What changed, what may now be claimed, what must survive, and is another step needed? |

The CLI is an interface to this loop, not a workflow agents should memorize. `start`, `implement`, `proof`, `summary`, module operations, skills, and diagnostics are projections or deeper routes from the same current operating decision.

Closeout is simply terminal reconciliation: no further action remains, the intended claim is justified, and any future-relevant residue has an explicit owner or is deliberately absent.

## Programmable instructions

"Programmable" should mean more than choosing among hard-coded modes. The repository should be able to express bounded conditional control using stable, typed facts and capabilities: when a relevant scope, owner, task, capability, evidence state, or decision point applies, AW can surface context or a skill, route or require a typed operation, require evidence or a human decision, or restrict an effect or claim.

Workspace owns the composition semantics. Repo declarations should not need Python changes to create a new ordinary control relationship, and they should not become arbitrary scripts, callbacks, hidden priority chains, or a general workflow/rule engine. Source owners keep their facts; instructions affect the current operating contract rather than mutating those sources directly.

The current implementation already has several specialized forms of this idea—workflow obligations, assurance/proof declarations, scoped instructions, skill routing, target/correction guidance, and module contributions—but they do not yet form one support-bearing general instruction-clause API. The architectural direction is to normalize overlapping semantics through the existing operating-decision/typed-action boundary rather than add another compiler.

Skills are lazily discovered procedures. Typed operations are effectful actions. Repo-owned instruction declarations decide when those existing primitives matter; modules add capabilities and facts without inventing new control operators.

## Modules

Modules are peer extensions of what the operating loop can know and do. They add independently owned capabilities without redefining the core workflow.

The authoring rule is simple: **a module describes its domain; Workspace owns the loop.** A module should normally declare what capability it is, what it owns, when it is relevant, which resources/procedures/typed operations it provides, and what its results/effects mean. It should not have to describe AW's startup/proof/closeout choreography or implement empty `resolve`/`act`/`reconcile` hooks merely to fit the framework.

Workspace derives how those declarations participate in the current operating contract. A read-only capability may only contribute relevant context or a routed procedure; an operation-oriented capability may add typed actions/results without inventing a new phase or posture model.

Useful genericity should make future modules cheaper to add as well as keeping first contact small. An ordinary independent module should normally be mostly self-contained in its own package and public descriptor/contracts, without semantic Workspace edits or a new core-owned per-module name list merely to recognize its identity.

The current first-party modules are examples:

- **Planning** contributes active execution continuity, bounded intent, handoff, and continuation behavior.
- **Memory** contributes learned anti-rediscovery repository knowledge and capture/retrieval behavior.
- **Verification** contributes reusable soft-verification protocols, bounded evidence, proof-route hints, and known gaps.

They are bundled batteries, not architectural pillars. Future modules can provide other functions—delegation, deployment, richer knowledge retrieval, security, or something not anticipated today—through the same generic capability model.

See [`docs/package/modules.md`](docs/package/modules.md) and [`docs/extension-boundary.md`](docs/extension-boundary.md).

## Repo customization and adapters

Modules are not the only way AW adapts.

- **Repo customization** uses repository-owned config, obligations, skills, canonical guidance, ownership, and repo operations to program how AW should govern work in that repository.
- **External adapters** integrate AW into agents, IDEs, CLIs, MCP-style clients, or vendor workflows by consuming stable AW operations from outside the core package.

AW should remain adapter-unaware: integrations may know how to use AW, but core AW should not need a vendor registry, marketplace, credential store, or reverse dependency on them.

## Progressive disclosure

First contact should contain only information that can change the current decision.

Deeper module detail, raw state, generated references, diagnostics, proof history, and specialized procedures should remain behind exact selectors, routed skills, operations, or owners until they matter.

Installing another capability should not proportionally enlarge the ordinary agent-facing framework.

## What it is not

Agentic Workspace is not:

- a repository knowledge database or semantic index;
- a ticket tracker or backlog manager;
- a workflow engine that scripts implementation judgment;
- a general-purpose policy language or arbitrary rule/callback host;
- a generic plugin/callback host;
- a vendor integration marketplace;
- a replacement for canonical repository docs, source, tests, review, or issue trackers.

The repository keeps its truth. AW makes the small control-relevant part actionable at the right time.

## Trust boundary

**Agentic Workspace is not a sandbox.** Treat the repository and its configured proof/executor commands as trusted before allowing AW to execute them. Admitted repository shell routes and explicitly supplied executor commands inherit the caller's filesystem and credential authority.

External issue, PR, and service content should be treated as data rather than executable instruction. Local logs and caches are diagnostics, not proof or semantic authority merely because they exist.

See [`docs/security/threat-model.md`](docs/security/threat-model.md).

## Adoption

The support-bearing install path is a versioned GitHub Release. Each coordinated release publishes `distribution-install-readiness.json`, which identifies the exact project-controlled root wheel and SHA-256-bound install command. Mutable branches and ordinary registry resolution are not support-bearing installation identities unless release policy explicitly says otherwise.

After installing the CLI, initialize or adopt the target repository with the smallest useful capability set. AW writes a small `.agentic-workspace/` enclave plus thin routing adapters such as `AGENTS.md`; selected modules add their own owned surfaces.

For exact installation guidance, use [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md). For installed ownership and footprint concepts, use [`docs/package/installed-surfaces.md`](docs/package/installed-surfaces.md).

## Documentation

Start with:

- [`docs/package/overview.md`](docs/package/overview.md) — product model and ordinary loop.
- [`docs/architecture.md`](docs/architecture.md) — operating context, dynamic control, module, repo-customization, and adapter boundaries.
- [`docs/package/modules.md`](docs/package/modules.md) — peer module contribution model and first-party examples.
- [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md) — installation and adoption.
- [`docs/security/threat-model.md`](docs/security/threat-model.md) — trust and supply-chain boundary.
- [`docs/package/contracts.md`](docs/package/contracts.md) — machine-readable contracts and generated references.
- [`docs/index.md`](docs/index.md) — documentation map.

Exact fields and contract values belong in generated/reference material rather than duplicated conceptual prose.

## Source checkout

This README describes the shipped product. When maintaining Agentic Workspace itself, follow [`AGENTS.md`](AGENTS.md) and the [`maintainer documentation`](docs/maintainer/index.md). Source-checkout proof commands, dogfooding procedure, migration inventories, and historical design evidence belong in maintainer/review surfaces.