# Agentic Workspace Documentation

This documentation is organized around the shipped package first, then the supporting references that define and maintain it.

## Start Here

- [Package overview](package/overview.md): what `agentic-workspace` ships and why it exists.
- [Lifecycle and context commands](package/lifecycle.md): how the root command initializes, inspects, routes, verifies, upgrades, and removes installed surfaces.
- [Command map](package/commands.md): quick human map of the shipped CLI surface.
- [Installed surfaces](package/installed-surfaces.md): what files the package writes into a host repository and who owns them.
- [Modules](package/modules.md): how the root package composes Planning and Memory.
- [Contracts and references](package/contracts.md): how JSON contracts, schemata, generated reference docs, and runtime outputs relate.

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
- [Historical reviews](reviews/): dated audits and evidence. These support future work, but they are not first-contact package documentation.
