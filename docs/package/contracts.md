# Contracts And References

The main AW skill supplies procedure. Current repository policy and domain owners
supply authority and state; one Rust core owns deterministic semantics. Contracts
make precise shapes inspectable but do not grant authority by their existence.

## Current public reference

| Question | Authority and reference |
| --- | --- |
| Which native commands and options exist? | `source_decision_contract.json`'s `native_cli` declaration, projected in the [native CLI catalogue](../reference/cli-catalogue.md) and executable `--help` |
| What request/action/currentness does this task need? | The current Rust-owner response through `start`; see the [native tool map](commands.md) |
| How do native, JSON, Python and Node relate? | The [shared Rust authority graph](../architecture/shared-rust-core.md); bindings carry exact envelopes rather than implementing domain logic |
| Which repository/local configuration shapes are declared? | [Workspace config](../reference/workspace-config.md) and [local override](../reference/workspace-local-override.md); native owner admission still determines support and applicability |
| What is the declared package footprint? | The [surface catalogue](../reference/installed-surface-catalogue.md), explicitly a source-maintenance lifecycle/profile inventory, not proof of native initialization |
| Which installation bytes are admitted? | The selected release's immutable receipt; follow the [installation guide](../agentic-workspace-install.md). The [support-bearing projection](../reference/support-bearing-install.md) applies only to its named stable release |

Generated reference pages answer exact questions after the product model is
understood. Use the [reference index](../reference/index.md) for their current
versus maintenance/historical classification. A declared field or profile does
not establish an available operation, installed-platform support or proof success.

## Maintenance and historical contracts

The retained `cli_commands.json` and `cli_option_groups.json` describe historical
CLI/generated adapters and source-maintenance tooling. Their root/nested command
model is not the native CLI catalogue's source. The generated startup-context,
implementer-context, report and selector pages likewise document their named
retained representations, not current `start` output or native command support.

Module, lifecycle, operation-IR and generated-adapter schemas remain useful for
explicit maintenance and historical investigation. Do not infer another executable
runtime or native fallback from their presence. Installed payload documents also
remain subject to their named source/owner and artifact identity.

## Editing rule

Edit the authoritative source contract or schema, regenerate its reference and
run the existing contract/freshness checks. Update conceptual prose when the
user-facing meaning changes. Do not hand-edit generated schema pages or
catalogues. The reference index and this page are hand-authored navigation.
