# Contracts And References

Agentic Workspace uses machine-readable contracts to keep behavior inspectable without reading the implementation first. Conceptual docs explain what the package does; contracts define precise shapes.

## Contract Layers

| Layer | Location | Role |
| --- | --- | --- |
| contract data | `src/agentic_workspace/contracts/*.json` | package-owned declarations for CLI commands, module registry, proof routes, report sections, and related surfaces |
| JSON schemata | `src/agentic_workspace/contracts/schemas/*.schema.json` | validation and generated-reference source for contract shapes |
| generated reference docs | `docs/reference/*.md` except `docs/reference/index.md` | field-level Markdown generated from schemata |
| runtime outputs | `agentic-workspace ... --format json` | live answers derived from package code, installed repo state, and contracts |
| installed contract docs | `.agentic-workspace/docs/*.md` | product-managed target-repo contracts and workflow adapters |

Generated reference docs are not the primary explanation layer. They answer exact field and schema questions after the reader understands the package concept.

## High-Value References

- [Generated reference index](../reference/index.md): topic map for all generated reference pages.
- [Workspace config](../reference/workspace-config.md): repo-owned `.agentic-workspace/config.toml` shape.
- [Workspace local override](../reference/workspace-local-override.md): local-only `.agentic-workspace/config.local.toml` shape.
- [Startup context](../reference/startup-context.md): `start --format json` payload.
- [Workspace report](../reference/workspace-report.md): combined report payload.
- [CLI commands](../reference/cli-commands.md): declared root command surface.
- [CLI option groups](../reference/cli-option-groups.md): shared option groups used by root commands.
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

Do not hand-edit generated schema pages under `docs/reference/`; `docs/reference/index.md` is the hand-authored navigation page for those generated files.
