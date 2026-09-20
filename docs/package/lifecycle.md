# Repository adoption, refresh and removal

Use this reference when implementing a client that manages AW's repository integration. For interactive use, follow [Getting started](../agentic-workspace-install.md) or [Your repository and data](installed-surfaces.md).

Installation supplies the executable. **Adoption** establishes its small repository integration. **Refresh** reconciles that integration with the installed package. **Removal** relinquishes the package integration without deleting independent project data.

## Request the change

Call `start` for the actual target/task and inspect Configuration's returned `repository_adoption_request`. Submit that exact request through `start --input` to obtain the available adoption, refresh, removal or recovery requests. Inspect the proposal and supply only its requested authorisation before invoking the returned action.

Do not generate effect-bearing fields from filenames or a schema example. An absent operation is an unsupported path for that artefact, not permission to emulate it with file copies. The [CLI reference](../reference/cli-catalogue.md) describes the transport.

## Preserve the right material

The [host-surface contract](../../src/agentic_workspace/contracts/workspace_surfaces.json) drives the package file set and its materialisation. Some files match package bytes; ownership combines portable package facts with supported project declarations; the read profile derives from the resulting ownership ledger.

Use those operations rather than maintaining a second install/removal list. Package provenance does not make unrelated project content removable. Shared configuration, independent domain records, local state and unknown content remain separately owned. Edited or conflicting package material can require resolution before replacement or deletion.

Remove authenticated host-discovery links through the existing skill-exposure operation before removing their canonical targets. Do not recursively remove `.agents/skills`.

## Handle interruption

Separate a committed file change from a failure to produce its continuation. Preserve returned effect/recovery information and request current recovery rather than replaying a possibly committed action.

Check the resulting repository after completion. A second current refresh should not rewrite already-current content; removal should leave the integration absent while preserving independent material. Later adoption uses the ordinary path, not a retained uninstall history.

Historical source-maintenance profiles are not native lifecycle commands. See [Troubleshooting](../troubleshooting.md) for user-facing recovery symptoms and the [generated catalogue](../reference/installed-surface-catalogue.md) for exact files.
