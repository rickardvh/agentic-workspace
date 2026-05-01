# Contracts And References

Agentic Workspace uses machine-readable contracts to keep behavior inspectable without reading the implementation first. Conceptual docs explain what the package does; contracts define precise shapes.

## Contract Layers

| Layer | Location | Role |
| --- | --- | --- |
| contract data | `src/agentic_workspace/contracts/*.json` | package-owned declarations for CLI commands, module registry, proof routes, report sections, and related surfaces |
| JSON schemata | `src/agentic_workspace/contracts/schemas/*.schema.json` | validation and generated-reference source for contract shapes |
| generated reference docs | `docs/reference/*.md` | field-level Markdown generated from schemata |
| runtime outputs | `agentic-workspace ... --format json` | live answers derived from package code, installed repo state, and contracts |
| installed contract docs | `.agentic-workspace/docs/*.md` | product-managed target-repo contracts and workflow adapters |

Generated reference docs are not the primary explanation layer. They answer exact field and schema questions after the reader understands the package concept.

## High-Value References

- [Workspace config](../reference/workspace-config.md): repo-owned `.agentic-workspace/config.toml` shape.
- [Startup context](../reference/startup-context.md): `start --format json` payload.
- [Workspace report](../reference/workspace-report.md): combined report payload.
- [CLI commands](../reference/cli-commands.md): declared root command surface.
- [Module registry](../reference/module-registry.md): module profiles, components, and package footprint metadata.
- [Proof selection rules](../reference/proof-selection-rules.md): proof routing contract.
- [Operation contracts](../reference/operation-contracts.md): operation contract registry.

## Editing Rule

When a contract changes:

1. edit the source contract or schema;
2. regenerate the reference docs;
3. run schema reference and contract tooling checks;
4. update conceptual docs only if the behavior or user-facing model changed.

Do not hand-edit generated files under `docs/reference/`.
