# Reference

Use this section when you know what you want to do and need an exact command,
setting or API. For a first task, start with [Getting started](../agentic-workspace-install.md).

| Look up | Reference |
| --- | --- |
| Run AW from a terminal | [CLI examples](../package/commands.md) and [all commands and options](cli-catalogue.md) |
| Configure a project | [Shared settings](workspace-config.md) and [local overrides](workspace-local-override.md) |
| Call AW from a program | [Rust, Python and TypeScript APIs](../architecture/shared-rust-core.md) |
| Write project instructions or skills | [Configuration guide](../customization.md) |
| Inspect files installed in a repository | [Installed-surface catalogue](installed-surface-catalogue.md) |
| Add an independent capability | [Native module contract](../module-capability-contract.md) |

Use the documentation for the version you installed. The CLI's `--help` reports
that executable's commands; a newer source reference does not add them to an older
installation. See [compatibility and support](../evidence-and-support.md) for release
and platform limits.

## Schemas and implementation references

Generated pages name the contract or schema they describe. Some files in this
directory describe internal or retired representations, not public commands.
[Contracts and reference maintenance](../package/contracts.md) explains that
boundary and where contributors should make changes.

The [source-maintenance inventory](source-maintenance-surface-catalogue.md) is for
package-build work. The public installed-surface catalogue above instead describes
the footprint used by current repository adoption, refresh and removal.
