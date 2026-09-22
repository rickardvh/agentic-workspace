# Contracts and reference maintenance

A contract describes a supported input, result or ownership boundary. Generated
references let developers inspect those details without maintaining a second
handwritten field list. For using the product, start with the
[user guide](../index.md); for looking up an interface, use the
[reference index](../reference/index.md).

## Which source answers which question?

| Question | Source |
| --- | --- |
| Commands and flags in this build | `native_cli` in [source_decision_contract.json](../../src/core/contracts/source_decision_contract.json), the [CLI catalogue](../reference/cli-catalogue.md), and executable `--help` |
| Current requests and permitted actions | The responsible native component's response for the target repository |
| Shared and local settings | [Configuration](../reference/workspace-config.md) and [local override](../reference/workspace-local-override.md) schemas |
| Files managed by repository adoption | [Installed-surface catalogue](../reference/installed-surface-catalogue.md), derived from the public footprint contract |
| Published versions and supported platforms | The selected release and [installation guidance](../agentic-workspace-install.md) |

A schema describes valid structure. It does not authorise an operation or establish
that an old installed version provides the feature.

## Internal and historical material

The reference directory also contains retained operation IR, former command-host
schemas and generated-adapter maintenance contracts. They describe their named
sources, not alternative public commands. Use the
[source layout](../architecture.md) and
[maintainer commands](../maintainer/maintainer-commands.md) for the current build
boundary. Completed migration explanations remain recoverable from
Git history and dated reviews; new API documentation should not narrate that history.

## Change a reference

Read the generated page's source notice. Edit the named contract or schema,
regenerate with the appropriate command in [Maintainer commands](../maintainer/maintainer-commands.md),
and run its freshness check. Do not edit generated Markdown directly.

Handwritten guides should explain the reader's task and include verified examples.
Keep exhaustive field definitions in their reference, but do not make a user
assemble a basic command from several schemas.
