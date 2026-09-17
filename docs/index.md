# Agentic Workspace Documentation

Start with the repository [README](../README.md) for first contact. Use the smallest documentation layer that answers the next question. Public conceptual docs explain the skills-first product model and release-bound adoption/support boundaries; generated references answer exact source-bound questions; maintainer docs own source-checkout procedure; reviews and Planning retain evidence rather than current product doctrine.

## Start here

- [Everyday use](everyday-use.md) — the canonical AW skill, scoped policy, continuity, retention, and precise owner tools in ordinary work.
- [Package overview](package/overview.md) — source-owned operating context and dynamic control without a mandatory command/phase loop.
- [Installation and adoption](agentic-workspace-install.md) — release identity, prerequisites, repository adoption/removal, and support boundaries.
- [Architecture](architecture.md) — source ownership, compiled control, modules, repo customization, and adapters.
- [Modules](package/modules.md) — peer capability contributions and current first-party examples.
- [Public glossary](glossary.md) — the small stable vocabulary for operating context, dynamic control, modules, authority, and support.
- [Evidence and support](evidence-and-support.md) — deterministic proof, live-agent evidence, weak cases, provider limits, and support claims.
- [Threat model](security/threat-model.md) — trust, shell execution, credentials, repository, and supply-chain boundaries.
- [Installed surfaces](package/installed-surfaces.md) — host-repo ownership and footprint model.
- [Contracts and references](package/contracts.md) — source contracts, runtime outputs, schemas, and generated references.

## Canonical conceptual owners

| Question | Canonical owner |
| --- | --- |
| What is AW? | [README](../README.md), then [Package overview](package/overview.md) for the deeper model |
| What is operating context and what is deliberately outside it? | [Package overview](package/overview.md) and [Architecture](architecture.md) |
| How does an agent use AW? | [Everyday use](everyday-use.md) and the [canonical skill](../.agentic-workspace/skills/workspace-startup/SKILL.md) |
| What does Workspace own versus repository sources? | [Architecture](architecture.md) |
| How do modules extend AW without changing the loop? | [Modules](package/modules.md) and [Extensibility and public boundary](extension-boundary.md) |
| How does repo customization differ from modules/adapters? | [Architecture](architecture.md) |
| How do I install, adopt, or remove AW? | [Installation and adoption](agentic-workspace-install.md) |
| What is the security/trust boundary? | [Threat model](security/threat-model.md) |
| What files/state exist in a host repo and who owns them? | [Installed surfaces](package/installed-surfaces.md) and generated [surface catalogue](reference/installed-surface-catalogue.md) |
| Which precise tools exist? | [Native tool map](package/commands.md) and the [native catalogue](reference/cli-catalogue.md) |
| How do contracts and generated references relate? | [Contracts and references](package/contracts.md) |
| What is the current maturity/support status? | [Maturity model](maturity-model.md), [Evidence and support](evidence-and-support.md), and the selected release receipts |
| How do maintainers build, validate, dogfood, and release AW? | [Maintainer index](maintainer/index.md) |

A second conceptual page should link to these owners rather than invent another product abstraction.

## Terminology boundary

`Operating context` means only source-owned context whose availability can materially affect how an agent should operate. It is not a promise that AW ingests, indexes, embeds, or semantically models arbitrary repository content.

Source code, canonical docs, tests, and history remain ordinary repository content. Richer semantic retrieval can be provided by a module without changing the core product model.

Planning, Memory, Verification, assurance, delegation, proof, and other specialized capabilities should be documented under their owners when relevant, not taught as mandatory core concepts.

## Exact reference material

Use generated/current references for exact changing values. The reference index classifies contracts as current, maintenance, or historical; a schema is not live operation admission and a source checkout is not a published release identity.

- [Reference index](reference/index.md)
- [Workspace configuration](reference/workspace-config.md)
- [Module registry](reference/module-registry.md)
- [Native CLI catalogue](reference/cli-catalogue.md)
- [Installed-surface catalogue](reference/installed-surface-catalogue.md)
- [Support-bearing install projection](reference/support-bearing-install.md)
- [Shared Rust authority](architecture/shared-rust-core.md)

Conceptual docs should not duplicate exhaustive command, option, footprint, module, version, or release-receipt data.

## Supporting and retained design material

These deeper pages include source-maintenance and historical mechanisms. They are not additional native commands or adoption procedures. Consult the current native catalogue and owners before treating any command/selector example as available:

- [Knowledge routing and source authority](package/knowledge-routing.md)
- [Pre-work knowledge gates](package/knowledge-gates.md)
- [Historical CLI output profiles](package/output-profiles.md)
- [Collaboration safety](collaboration-safety.md)
- [Retained jumpstart contract](jumpstart-contract.md)
- [Host-repo learning](host-repo-learning.md)
- [Setup findings contract](setup-findings-contract.md)

These pages explain retained mechanisms and design context, not the canonical current command-reference path. Historical generated/lifecycle schemas remain reachable through the explicitly classified [reference index](reference/index.md).

## Maintainer and design material

Source-checkout procedure, generator/test inventories, implementation-shaping audits, and migration closure evidence are not first-contact package documentation.

Start with:

- [Maintainer index](maintainer/index.md)
- [Contributor playbook](maintainer/contributor-playbook.md)
- [Maintainer commands](maintainer/maintainer-commands.md)

Source-maintenance operation/profile catalogues remain explicitly classified as maintenance material. They do not define the public native host footprint or create additional public lifecycle commands.

## Historical evidence

- [Historical reviews](reviews/) contain dated audits and evidence.
- Planning state and execplans contain active implementation shaping.
- Git and merged PRs retain completed implementation history.

Historical evidence may explain why the product changed, but it is not current authority unless a current owner explicitly promotes or references the conclusion.

## Documentation maintenance rule

Prefer this ladder:

1. let the README explain the first-contact product experience;
2. explain the stable operating-context/control model once in conceptual owners;
3. progressively disclose specialized capability concepts only when relevant;
4. derive exact facts from machine-readable or immutable release authority;
5. keep source-checkout procedure in maintainer docs;
6. keep dated evidence historical;
7. delete or demote duplicated current prose instead of adding another abstraction layer.
