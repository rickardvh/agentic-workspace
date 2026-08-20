# Agentic Workspace

Agentic Workspace is a quiet, repo-native operating substrate for agents working in repositories where intent, context, proof, and continuation must survive across sessions, branches, tools, models, or contributors.

It gives agents a small set of repository-owned contracts and compact routing surfaces so they can recover the right context, act within the right authority, prove the right claim, and leave useful continuation state without reconstructing the task from chat history.

## Why it exists

Agent work becomes expensive when the same context has to be rediscovered, when active intent exists only in conversation, when proof expectations are implicit, or when a later agent cannot tell which work is actually complete.

AW is meant to reduce that total cost. It keeps only state that is expensive to reconstruct and useful for future decisions, and it tries to make the next safe action cheaper than broad repository scavenging.

Use it when continuation, handoff, proof, recurring repo knowledge, or agent/tool switching are genuine sources of friction. Do not use it merely because a repository contains agents: if ordinary docs, tests, and a short task finish the work cheaply, AW should stay unnecessary.

## Product shape

Workspace is the small operating kernel. Capabilities compose around it through three distinct mechanisms:

- **Modules** add independently owned domain capabilities, state/resources, operations, and bounded effects on the ordinary operating loop.
- **Repo customization** uses repository-owned config, obligations, skills, and canonical guidance to adapt that loop to the host repository.
- **External adapters** integrate AW into other agents, IDEs, CLIs, MCP-style clients, or vendor workflows by consuming stable AW operations from outside the core package.

Planning, Memory, and Verification are the current first-party modules. They are batteries supplied by the project and examples of the module model, not the fixed architectural boundary of Agentic Workspace.

AW should remain adapter-unaware: an integration may know how to invoke AW, but AW should not need a vendor registry, marketplace, credential store, or reverse dependency on that integration.

Extensibility is a core product property, but it is not a promise that every internal hook is a stable public plugin API. The supported public module boundary is intentionally being kept smaller than the full internal participation vocabulary. See [`docs/extension-boundary.md`](docs/extension-boundary.md).

## Ordinary operating loop

Agents should not need to learn the CLI as a workflow. The root command exposes compact answers to the current question:

| Question | Ordinary route |
| --- | --- |
| What is the smallest safe context before acting? | `start` |
| What work currently owns continuation? | `summary` |
| What changes are safe and relevant now? | `implement` and routed owner operations |
| What evidence is required for the intended claim? | `proof` |
| What may be claimed, what must survive, and who owns the remainder? | compact closeout/continuation state |

Modules and repo policy enrich those answers when relevant. An installed capability should not normally require a new first-contact mental model.

## First-party modules

- **Memory** preserves durable repo knowledge that is expensive to rediscover.
- **Planning** preserves active execution continuity, bounded intent, handoff, and honest closeout.
- **Verification** preserves reusable soft-verification protocols, bounded evidence, proof-route hints, and known gaps.

A repo can use the root routing layer with none of these, select only the capabilities that pay back, or combine them. Module selection controls the host-repo footprint; the current Python distribution still bundles the first-party module packages for lifecycle convenience.

See [`docs/package/modules.md`](docs/package/modules.md) for ownership and selection guidance.

## What it is not

Agentic Workspace is not a ticket tracker, backlog manager, database, general analytics system, or vendor/plugin host. It is not a replacement for canonical repository documentation, tests, code review, or external issue trackers.

It should also not become a framework that scripts ordinary agent judgment. The kernel should own mechanical continuity, compatibility, authority, routing, proof/claim boundaries, and lifecycle coordination while leaving domain intent and implementation judgment with the proper owner.

## Trust boundary

**Agentic Workspace is not a sandbox.** Treat the repository and its configured proof/executor commands as trusted before allowing AW to execute them. Admitted repository shell routes and explicitly supplied executor commands inherit the caller's filesystem and credential authority.

External issue, PR, and service content should be treated as data rather than executable instruction. Local logs and caches are useful diagnostics but are not proof, Planning, or completion authority merely because they exist.

See [`docs/security/threat-model.md`](docs/security/threat-model.md) for the full trust and supply-chain boundary.

## Adoption

The support-bearing install path is a versioned GitHub Release. Each coordinated release publishes `distribution-install-readiness.json`, which identifies the exact project-controlled root wheel and SHA-256-bound install command. Mutable branches and ordinary registry resolution are not support-bearing installation identities unless a future release policy explicitly says otherwise.

After installing the CLI, initialize or adopt the target repository with the smallest useful module set. AW writes a small `.agentic-workspace/` enclave plus thin routing adapters such as `AGENTS.md`; selected modules add their own owned roots. Package-managed and local-only state should remain distinguishable and removable.

For exact installation and environment guidance, use [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md). For installed ownership and footprint concepts, use [`docs/package/installed-surfaces.md`](docs/package/installed-surfaces.md).

## Documentation

Start with:

- [`docs/package/overview.md`](docs/package/overview.md) — product model and ordinary operating shape.
- [`docs/package/modules.md`](docs/package/modules.md) — modules, capability ownership, and extension model.
- [`docs/architecture.md`](docs/architecture.md) — kernel, module, repo-customization, and adapter boundaries.
- [`docs/agentic-workspace-install.md`](docs/agentic-workspace-install.md) — installation and adoption.
- [`docs/security/threat-model.md`](docs/security/threat-model.md) — trust and supply-chain boundary.
- [`docs/package/contracts.md`](docs/package/contracts.md) — machine-readable contracts and generated references.
- [`docs/index.md`](docs/index.md) — full documentation map.

Exact fields and generated contract references should be treated as reference material rather than duplicated into conceptual pages.

## Source checkout

This README describes the shipped product and adoption model. When maintaining Agentic Workspace itself, follow [`AGENTS.md`](AGENTS.md) and the [`maintainer documentation`](docs/maintainer/index.md). Source-checkout proof commands, dogfooding procedures, migration inventories, and historical design evidence belong in maintainer/review surfaces rather than the public product model.
