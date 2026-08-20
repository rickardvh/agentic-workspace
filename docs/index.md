# Agentic Workspace Documentation

Use the smallest documentation layer that answers the question. Public conceptual docs explain stable product roles; machine-generated references should answer exact contract questions; maintainer docs own source-checkout procedure; dated reviews and Planning retain implementation evidence rather than current product doctrine.

## Start here

- [Package overview](package/overview.md) — what AW is, when it pays back, and the ordinary operating shape.
- [Modules](package/modules.md) — capability ownership, module selection, and the module/repo/adapter distinction.
- [Architecture](architecture.md) — kernel, module, repo-customization, and external-adapter boundaries.
- [Installation and adoption](agentic-workspace-install.md) — support-bearing install and lifecycle entrypoint.
- [Threat model](security/threat-model.md) — trust, shell execution, credentials, repository, and supply-chain boundaries.
- [Installed surfaces](package/installed-surfaces.md) — conceptual host-repo ownership and footprint model.
- [Contracts and references](package/contracts.md) — how source contracts, schemas, runtime outputs, and generated references relate.

## Canonical conceptual owners

| Question | Canonical conceptual owner |
| --- | --- |
| What is Agentic Workspace and when should a repo use it? | [Package overview](package/overview.md) |
| What do modules own and how does extensibility work? | [Modules](package/modules.md) and [Extensibility and public boundary](extension-boundary.md) |
| What does the kernel own versus modules, repo policy, and adapters? | [Architecture](architecture.md) |
| How do I install/adopt it? | [Installation and adoption](agentic-workspace-install.md) |
| What is the security/trust boundary? | [Threat model](security/threat-model.md) |
| What files/state exist in a host repo and who owns them? | [Installed surfaces](package/installed-surfaces.md) |
| How do lifecycle/context commands fit the product? | [Lifecycle and context commands](package/lifecycle.md) and [Command map](package/commands.md) |
| How do contracts and generated references relate? | [Contracts and references](package/contracts.md) |
| What is current maturity/support status? | [Maturity model](maturity-model.md) and [Documentation status](documentation-status.md) |
| How do maintainers build, validate, dogfood, and release AW? | [Maintainer index](maintainer/index.md) |

A second conceptual page should link to these owners instead of restating their full model.

## Exact reference material

Generated references are for exact contract shapes and values after the conceptual model is understood.

- [Reference index](reference/index.md)
- [Workspace configuration](reference/workspace-config.md)
- [Module registry](reference/module-registry.md)
- [Startup context](reference/startup-context.md)
- [Workspace report](reference/workspace-report.md)
- [Operation contracts](reference/operation-contracts.md)

The current CLI schema/reference pages describe declared contract structure. Work to generate a true current command catalogue and exact installed-surface matrix is tracked separately; conceptual docs should not claim a schema-shape page already answers those current-value questions.

## Supporting product concepts

Use these only when the ordinary conceptual pages route you deeper:

- [Knowledge routing and source authority](package/knowledge-routing.md)
- [Pre-work knowledge gates](package/knowledge-gates.md)
- [CLI output profiles](package/output-profiles.md)
- [Collaboration safety](collaboration-safety.md)
- [Jumpstart contract](jumpstart-contract.md)
- [Host-repo learning](host-repo-learning.md)
- [Setup findings contract](setup-findings-contract.md)

## Maintainer and design material

Source-checkout procedure, generator/test inventories, implementation-shaping audits, and migration closure evidence are not first-contact package documentation.

Start with:

- [Maintainer index](maintainer/index.md)
- [Contributor playbook](maintainer/contributor-playbook.md)
- [Maintainer commands](maintainer/maintainer-commands.md)

The following existing package-path documents currently function primarily as design/maintainer evidence and should be treated that way until the documentation-ladder cleanup gives them a final move/merge/delete disposition:

- `package/ordinary-continuity-loop.md`
- `package/operating-loop-substeps.md`
- `package/cli-boundary-tests.md`
- `package/generated-behavior-test-inventory.md`
- `package/generated-behavior-closure-inventory.md`

Do not use active issue numbers or migration inventories in those pages as the current public product definition.

## Historical evidence

- [Historical reviews](reviews/) contain dated audits and evidence.
- Planning state and execplans contain active implementation shaping.
- Git and merged PRs retain completed implementation history.

Historical evidence may explain why the product changed, but it is not current authority unless a current owner explicitly promotes or references the conclusion.

## Documentation maintenance rule

Prefer this ladder:

1. explain stable meaning once in a conceptual owner;
2. derive exact facts from machine-readable authority;
3. keep source-checkout procedure in maintainer docs;
4. keep dated evidence historical;
5. delete or demote duplicated current prose instead of adding another index or compatibility explanation.
