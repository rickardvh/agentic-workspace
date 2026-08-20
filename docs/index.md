# Agentic Workspace Documentation

Use the smallest documentation layer that answers the question. Public conceptual docs explain the stable product model; generated references answer exact contract questions; maintainer docs own source-checkout procedure; reviews and Planning retain evidence rather than current product doctrine.

## Start here

- [Package overview](package/overview.md) — operating context, dynamic control, and the `resolve -> act -> reconcile` loop.
- [Architecture](architecture.md) — source ownership, compiled control, modules, repo customization, and adapters.
- [Modules](package/modules.md) — peer capability contributions and current first-party examples.
- [Installation and adoption](agentic-workspace-install.md) — support-bearing installation and lifecycle entrypoint.
- [Public glossary](glossary.md) — the small stable vocabulary for operating context, dynamic control, modules, authority, and support.
- [Evidence and support](evidence-and-support.md) — deterministic proof, live-agent evidence, weak cases, provider limits, and current support claims.
- [Threat model](security/threat-model.md) — trust, shell execution, credentials, repository, and supply-chain boundaries.
- [Installed surfaces](package/installed-surfaces.md) — host-repo ownership and footprint model.
- [Contracts and references](package/contracts.md) — source contracts, runtime outputs, schemas, and generated references.

## Canonical conceptual owners

| Question | Canonical owner |
| --- | --- |
| What is AW? | [Package overview](package/overview.md) |
| What is operating context and what is deliberately outside it? | [Package overview](package/overview.md) and [Architecture](architecture.md) |
| How does the ordinary agent loop work? | [Package overview](package/overview.md) |
| What does Workspace own versus repository sources? | [Architecture](architecture.md) |
| How do modules extend AW without changing the loop? | [Modules](package/modules.md) and [Extensibility and public boundary](extension-boundary.md) |
| How does repo customization differ from modules/adapters? | [Architecture](architecture.md) |
| How do I install/adopt AW? | [Installation and adoption](agentic-workspace-install.md) |
| What is the security/trust boundary? | [Threat model](security/threat-model.md) |
| What files/state exist in a host repo and who owns them? | [Installed surfaces](package/installed-surfaces.md) and generated [surface catalogue](reference/installed-surface-catalogue.md) |
| How do commands relate to the operating loop? | [Command map](package/commands.md) and generated [CLI catalogue](reference/cli-catalogue.md) |
| How do contracts and generated references relate? | [Contracts and references](package/contracts.md) |
| What is current maturity/support status? | [Maturity model](maturity-model.md) and [Documentation status](documentation-status.md) |
| How do maintainers build, validate, dogfood, and release AW? | [Maintainer index](maintainer/index.md) |

A second conceptual page should link to these owners rather than invent another product abstraction.

## Terminology boundary

`Operating context` means only source-owned context whose availability can materially affect how an agent should operate. It is not a promise that AW ingests, indexes, embeds, or semantically models arbitrary repository content.

Source code, canonical docs, tests, and history remain ordinary repository content. Richer semantic retrieval can be provided by a module without changing the core product model.

Planning, Memory, Verification, assurance, delegation, proof, and other specialized capabilities should be documented under their owners when relevant, not taught as mandatory core concepts.

## Exact reference material

Generated references are for exact contract shapes and values after the conceptual model is understood.

- [Reference index](reference/index.md)
- [Workspace configuration](reference/workspace-config.md)
- [Module registry](reference/module-registry.md)
- [Startup context](reference/startup-context.md)
- [Workspace report](reference/workspace-report.md)
- [Operation contracts](reference/operation-contracts.md)

Conceptual docs should not duplicate exhaustive command, option, footprint, module, or schema data.

## Supporting product concepts

Use these only when the ordinary conceptual pages or current operating contract route you deeper:

- [Knowledge routing and source authority](package/knowledge-routing.md)
- [Pre-work knowledge gates](package/knowledge-gates.md)
- [CLI output profiles](package/output-profiles.md)
- [Collaboration safety](collaboration-safety.md)
- [Jumpstart contract](jumpstart-contract.md)
- [Host-repo learning](host-repo-learning.md)
- [Setup findings contract](setup-findings-contract.md)

These pages explain supporting mechanisms, not additional pillars of the product.

## Maintainer and design material

Source-checkout procedure, generator/test inventories, implementation-shaping audits, and migration closure evidence are not first-contact package documentation.

Start with:

- [Maintainer index](maintainer/index.md)
- [Contributor playbook](maintainer/contributor-playbook.md)
- [Maintainer commands](maintainer/maintainer-commands.md)

Two generated-behavior proof owners remain at package compatibility paths but are explicitly maintainer-only: `package/cli-boundary-tests.md` and `package/generated-behavior-test-inventory.md`. The older ordinary-loop/substep/closure inventories were removed after their stable conclusions moved to the overview, generated catalogues, and maintainer closure report.

## Historical evidence

- [Historical reviews](reviews/) contain dated audits and evidence.
- Planning state and execplans contain active implementation shaping.
- Git and merged PRs retain completed implementation history.

Historical evidence may explain why the product changed, but it is not current authority unless a current owner explicitly promotes or references the conclusion.

## Documentation maintenance rule

Prefer this ladder:

1. explain the stable operating-context/control model once;
2. progressively disclose specialized capability concepts only when relevant;
3. derive exact facts from machine-readable authority;
4. keep source-checkout procedure in maintainer docs;
5. keep dated evidence historical;
6. delete or demote duplicated current prose instead of adding another abstraction layer.
