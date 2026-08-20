# Agentic Workspace Design Principles

## Purpose

Agentic Workspace should make repositories easier and cheaper for agents to operate while staying quiet about its own machinery.

Its core product idea is simple:

- preserve a bounded set of **operating context** because it can materially change agent behavior;
- dynamically resolve the relevant part into the current operating contract;
- let specialized modules extend what the loop can know and do without changing the loop itself.

The product should feel smaller than the implementation behind it and should earn every visible surface it keeps.

For the current product model, start with [`docs/package/overview.md`](package/overview.md) and [`SYSTEM_INTENT.md`](../SYSTEM_INTENT.md). This page explains the design pressure that should keep that model coherent.

## Doctrine

### 1. Keep context only when it changes future decisions

Repository persistence is not free. Preserve a fact, state, procedure, or lesson when its current or durable availability materially changes safe agent behavior and its future value exceeds its reread and maintenance cost.

Do not persist chat, logs, plans, reviews, histories, or arbitrary repository facts merely because they exist.

### 2. Operating context is not a repository knowledge model

AW should not ingest or mirror the repository simply to make it knowable.

Source code, canonical docs, tests, history, and normal project artifacts keep their existing owners. Rich semantic search, RAG, embeddings, knowledge graphs, or broader repository models may be useful specialized modules, but core AW should remain simpler.

### 3. Surface less, later

The system succeeds when first contact contains only what can change the current decision.

Prefer:

- compact current decisions;
- exact selectors;
- lazy skill/module discovery;
- owner references;
- typed actions;
- bounded evidence bundles.

Avoid broad reading lists and always-loaded capability manuals.

### 4. One operating decision, many source owners

Repository and module sources keep semantic authority. Workspace composes their current effect; it should not create a second source of truth.

A generated instruction or operating contract is useful because it is cheap to consume, not because it replaces the source that authorized it.

### 5. Make the next action constructible

Good dynamic control should normally end in something the agent can actually do:

- a typed operation;
- a derived command;
- a routed skill;
- an exact selector/owner;
- a bounded recovery;
- or an explicit human decision with the relevant facts.

A transition name without a supported route is not an adequate instruction.

### 6. Use one generic loop

The ordinary mental model is `resolve -> act -> reconcile`.

Startup, implementation, proof, handoff, closeout, and continuation are common situations, not independent core frameworks. Closeout is terminal reconciliation.

Do not create another phase-specific decision engine when the existing operating-decision path can carry the result.

### 7. Modules specialize the loop; they do not redefine it

Modules own independently reusable domain capabilities. They may contribute relevant context/procedure, typed operations, and bounded result/reconciliation facts.

Planning, Memory, and Verification are current first-party examples, not privileged architectural slots. Future modules should fit without adding a mandatory new first-contact question or requiring Workspace to understand their domain state shape.

### 8. Preserve one semantic owner per concern

Ownership should follow meaning rather than convenience.

- canonical repository truth stays in canonical repository surfaces;
- Workspace owns cross-cutting control composition;
- modules own their domain state and semantics;
- repo customization owns host policy and durable operating choices;
- external adapters own transport/vendor integration;
- local runtime state remains lower-authority local state unless deliberately promoted.

Do not duplicate an owner merely to make another subsystem easier to implement.

### 9. Configuration must earn durable authority

Shared config should express real repo policy, ownership, capability selection, or durable operating choices. Local config should express machine/runtime capability or preference with appropriately weaker authority.

Do not preserve a growing `posture` or personality framework simply because more knobs can be represented. Retain a control when it materially changes the current contract or has demonstrated completion-cost value.

### 10. Direct work must stay direct

Small, obvious work should not acquire Planning, Memory, Verification, review, handoff, or other artifacts merely because those capabilities are installed.

Irrelevance and absence are valid states. A capability that is not needed should be silent.

### 11. Help the agent do the job; do not script the job

AW should be opinionated about authority, effects, proof/claim boundaries, ownership, and safe transitions. It should not micromanage ordinary implementation judgment.

Prefer thin contracts and exact escalation over scheduler-like choreography.

### 12. Optimize total successful-completion cost

Measure the whole path: rereads, rediscovery, clarification, retries, route reversals, proof reruns, handoff reconstruction, repair, and user roundtrips.

Token count, bytes, latency, commands, and file count are useful proxies only when they improve the total path to a correct result.

Do not save model tokens by creating human bureaucracy.

### 13. Improve the deterministic owner before compensating elsewhere

Repeated human steering, wrong-owner work, stale context, repeated rediscovery, proof confusion, or late reconciliation repair should create pressure to improve the actual owner or control path.

A permanent warning in another subsystem is a poor substitute for fixing deterministic behavior.

### 14. Preserve graceful partial compliance

AW must work with mixed agents and cannot assume perfect adherence, hidden reasoning, or one vendor.

Make the intended path progressively discoverable and cheaper than bypass. When an agent ignores a routed contract, lower trust explicitly rather than allowing silent authority expansion.

### 15. Extensibility must stay bounded

Prefer declarative capability identity, relevance, ownership, typed operations, effects, lifecycle, and bounded results over arbitrary callbacks and workflow hooks.

Do not turn extensibility into:

- a generic plugin runtime;
- an event bus;
- a module marketplace;
- an adapter registry;
- a credential store;
- or a new user-visible command/phase for every capability.

### 16. Repo customization is different from a module

Host-specific rules belong in repo-owned config, obligations, skills, canonical guidance, ownership, or deterministic repo operations when that is the smallest owner.

A reusable domain capability with its own state/resources, operations, compatibility, and lifecycle may justify a module. Do not turn every repository rule into one.

### 17. External adapters remain outside core

An integration may know how to consume AW; AW should not need to know the integration package or vendor.

Transport does not create semantic authority. Credentials and vendor lifecycle remain adapter concerns.

### 18. Keep package ownership quiet and removable

Package-owned machinery should stay under `.agentic-workspace/` as far as practical. Local caches and diagnostics do not become shared authority by existence alone. Promoted output should become normal repo-owned output.

The package should remain plausibly removable.

### 19. Collaboration safety matters

Normal git pressure should not make AW brittle.

- keep shared hot state compact;
- prefer bounded owner-scoped files over giant mutable dashboards;
- archive/compact completed active state when future value is low;
- make derived surfaces reproducible when they must exist.

### 20. Compatibility layers must have a beneficiary and an exit

Do not preserve old and new models in parallel by default.

A compatibility layer should protect a named consumer, exist for a concrete transition reason, and have a credible removal/demotion path. Otherwise it is likely permanent ambiguity.

### 21. Generated surfaces derive; they do not own

Generated docs, clients, adapters, or prose are useful when they derive from one authoritative contract and remove more cost than they create.

Do not keep generated mirrors of changing truth simply because generation is possible.

### 22. Documentation should demonstrate progressive disclosure

Public docs should be simpler than the implementation.

Use an abstraction ladder:

1. core product model;
2. specialized capability concepts only when relevant;
3. generated exact references;
4. maintainer procedure;
5. historical evidence.

Links compose docs; copied truth creates drift.

### 23. Portability beats dogfooding cleverness

Do not generalize this repository's language, structure, environment manager, provider, or current modules into universal requirements without evidence.

Prefer narrow contracts and plain ownership boundaries that still make sense in another repository and with another agent.

### 24. Proof should beat preference

Features that claim to reduce restart cost, context cost, handoff burden, or agent failure should earn their place through deterministic proof and representative ordinary work.

Keep weak, negative, and unavailable evidence visible rather than averaging it into a broad success claim.

## Design tests

A change is moving in the right direction when it helps answer yes to questions such as:

- Does this preserve or route operating context that materially changes behavior?
- Does the right information arrive later and more selectively than before?
- Does the current agent get one coherent, constructible next action?
- Does source ownership remain explicit?
- Does this reduce total successful-completion cost rather than shifting it elsewhere?
- Can direct work ignore the capability entirely?
- Can another module provide a different domain capability without changing the core mental model?
- Does the change remove, derive, merge, or background an older concept instead of merely adding one?
- Would it still make sense outside this monorepo?

A change is suspicious when it tends to:

- create a general repository knowledge store in core;
- create another packet/phase authority beside the compiled operating decision;
- expose irrelevant context at first contact;
- hard-code a first-party module identity in generic composition;
- add a new policy/identity/lifecycle concept without naming what it replaces;
- persist history with no clear future decision value;
- save agent work mainly by creating maintainer ceremony;
- make generated projections compete with their source authority;
- preserve old and new models indefinitely.

## Tactical policy lives elsewhere

Use narrower owner docs for maintainer procedure and implementation details:

- `docs/maintainer/contributor-playbook.md` for maintainer routing and validation;
- `docs/maintainer/dogfooding-feedback.md` for dogfooding/product-friction routing;
- `.agentic-workspace/docs/` contracts for installed/source-checkout tactical details;
- generated references for exact machine contract fields.

## Short version

Preserve the context that governs agent work.
Surface only what matters now.
Act through the supported route.
Reconcile what changed.
Let modules specialize the loop without enlarging it.
Stay quiet.