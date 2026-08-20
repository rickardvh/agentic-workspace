# Contracts And References

Agentic Workspace uses machine-readable contracts to keep behavior inspectable without reading the implementation first. Conceptual docs explain what the package does; contracts define precise shapes.

## Contract Layers

| Layer | Location | Role |
| --- | --- | --- |
| contract data | `src/agentic_workspace/contracts/*.json` | package-owned declarations for CLI commands, module registry, proof routes, report sections, and related surfaces |
| JSON schemata | `src/agentic_workspace/contracts/schemas/*.schema.json` | validation and generated-reference source for contract shapes |
| generated schema references | most `docs/reference/*.md` | field-level shape documentation generated from schemata |
| generated current-value catalogues | `cli-catalogue.md`, `installed-surface-catalogue.md`, `support-bearing-install.md` | exact values generated from command, surface/module, and release-install contracts |
| runtime outputs | `agentic-workspace ... --format json` | live answers derived from package code, installed repo state, and contracts |
| installed contract docs | `.agentic-workspace/docs/*.md` | product-managed target-repo contracts and workflow adapters |

Generated reference docs are not the primary explanation layer. They answer exact field and schema questions after the reader understands the package concept.

## High-Value References

- [Generated reference index](../reference/index.md): topic map for all generated reference pages.
- [Workspace config](../reference/workspace-config.md): repo-owned `.agentic-workspace/config.toml` shape.
- [Workspace local override](../reference/workspace-local-override.md): local-only `.agentic-workspace/config.local.toml` shape.
- [Startup context](../reference/startup-context.md): `start --format json` payload.
- [Workspace report](../reference/workspace-report.md): combined report payload.
- [Current CLI catalogue](../reference/cli-catalogue.md): exact current root/nested commands and options.
- [Current installed-surface catalogue](../reference/installed-surface-catalogue.md): exact supported profile/module footprint cells.
- [Current support-bearing install](../reference/support-bearing-install.md): immutable receipt-bound install command.
- [CLI commands schema](../reference/cli-commands.md): command-manifest shape.
- [CLI option groups schema](../reference/cli-option-groups.md): shared option-group shape.
- [Module registry](../reference/module-registry.md): module profiles, components, and package footprint metadata.
- [Proof selection rules](../reference/proof-selection-rules.md): proof routing contract.
- [Report contract manifest](../reference/report-contract-manifest.md): report contract registry.
- [Selector contracts manifest](../reference/selector-contracts-manifest.md): selector contract registry.
- [Operation contracts](../reference/operation-contracts.md): operation contract registry.

## Editing Rule

When a contract changes:

1. edit the source contract or schema;
2. regenerate the reference docs;
3. run schema reference and contract tooling checks;
4. update conceptual docs only if the behavior or user-facing model changed.

Do not hand-edit generated schema pages or current-value catalogues under `docs/reference/`; `docs/reference/index.md` is the hand-authored navigation page.
