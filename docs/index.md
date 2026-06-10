# Agentic Workspace Documentation

This documentation is organized around the shipped package first, then the supporting references that define and maintain it.

## Canonical Owners

Use this map when updating docs so each page stays complete at its level without restating deeper operational detail.

| Question | Canonical owner | Link instead of repeating when |
| --- | --- | --- |
| What is Agentic Workspace and when does it pay back? | [Package overview](package/overview.md) | another page only needs the product thesis or adoption boundary |
| Which preset/profile should a repo start with? | [Which package should I install?](which-package.md) | repeating the memory/planning/full threshold would duplicate install guidance |
| What does the root CLI do? | [Lifecycle and context commands](package/lifecycle.md) and [Command map](package/commands.md) | a page only needs to name a command or compact router |
| Which CLI output profile should an agent use? | [CLI output profiles](package/output-profiles.md) | next-decision policy belongs in one command-output contract |
| What files are installed and who owns them? | [Installed surfaces](package/installed-surfaces.md) | explaining startup adapters, managed fences, local-only state, or source-checkout boundaries |
| How should agents route governing knowledge and source authority? | [Knowledge routing and source authority](package/knowledge-routing.md) | a page only needs to name a source kind, authority class, route trigger, freshness rule, or capture obligation |
| When should governing knowledge block or constrain work? | [Pre-work knowledge gates](package/knowledge-gates.md) | a page only needs to name gate force, blocked actions, closeout evidence, or fallback behavior |
| What do Planning and Memory own? | [Modules](package/modules.md), then the module READMEs | a page only needs to distinguish active execution state from durable repo knowledge |
| What are the exact fields and generated references? | [Contracts and references](package/contracts.md) and [Reference material](reference/index.md) | hand-written docs would otherwise copy generated schema detail |
| What is source-checkout maintainer workflow? | [Maintainer index](maintainer/index.md) | ordinary host-repo docs mention internal validation, dogfooding, or generation only as a boundary |
| What is current maturity or freshness? | [Documentation status](documentation-status.md) and [Maturity model](maturity-model.md) | status wording starts becoming a second product overview |

## Start Here

- [Package overview](package/overview.md): what `agentic-workspace` ships and why it exists.
- [Lifecycle and context commands](package/lifecycle.md): how the root command initializes, inspects, routes, verifies, upgrades, and removes installed surfaces.
- [Command map](package/commands.md): quick human map of the shipped CLI surface.
- [Installed surfaces](package/installed-surfaces.md): what files the package writes into a host repository and who owns them.
- [Modules](package/modules.md): how the root package composes Planning and Memory.
- [Knowledge routing and source authority](package/knowledge-routing.md): how startup, posture, closeout, Memory, Planning, issues, docs, and external sources route governing knowledge without broad mirroring.
- [Pre-work knowledge gates](package/knowledge-gates.md): when routed knowledge should block design, edits, claims, or closeout until resolved.
- [Contracts and references](package/contracts.md): how JSON contracts, schemata, generated reference docs, and runtime outputs relate.
- [Jumpstart contract](jumpstart-contract.md): how a newly installed or adopted workspace in a lived-in repo should discover candidate durable surfaces without bulk importing repo prose.
- [Collaboration safety](collaboration-safety.md): git-native collaboration model, merge recovery, and shared-state pressure rules.

## Reference Material

- [Generated schema reference](reference/index.md): generated field-level documentation for machine-readable contracts.
- [Workspace configuration reference](reference/workspace-config.md): schema reference for `.agentic-workspace/config.toml`.
- [CLI command contract](reference/cli-commands.md): generated reference for the declared root command surface.
- [Module registry contract](reference/module-registry.md): generated reference for module profiles, components, and package footprint metadata.

## Maintainer Material

- [Maintainer index](maintainer/index.md): source-checkout workflows, validation lanes, dogfooding policy, and internal review bars.
- [Contributor playbook](maintainer/contributor-playbook.md): maintainer routing, ownership, and validation guidance.
- [Maintainer commands](maintainer/maintainer-commands.md): literal command index.

## Supporting Context

- [Which package should I install?](which-package.md): compact preset selector and package-choice explanation.
- [Architecture](architecture.md): current composition and module-boundary summary.
- [Documentation status](documentation-status.md): role and freshness index after the package docs answer the current behavior question.
- [Maturity model](maturity-model.md): support and adoption expectations, not a product map.
- [Design principles](design-principles.md): product doctrine and tradeoff guidance, not first-contact package documentation.
- [Setup findings contract](setup-findings-contract.md): how optional setup findings are promoted, dismissed, or kept transient.
- [Host-repo learning](host-repo-learning.md): how agents turn repo-specific evidence into the right owner surface instead of relying on hard-coded assumptions.
- [Continuation readiness projections](continuation-readiness-projections.md): completion, repair, findings, external-evidence, migration, compaction, and automation-readiness report sections.
- [Collaboration safety](collaboration-safety.md): practical merge expectations for Planning, Memory, config, generated surfaces, and managed fences.
- [Planning live-state collaboration design](planning-live-state-collaboration-design.md): design note for lower-conflict live-state alternatives and the current compact-state choice.
- [Historical reviews](reviews/): dated audits and evidence. These support future work, but they are not first-contact package documentation.
