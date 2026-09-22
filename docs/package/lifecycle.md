# Repository adoption, refresh and removal

Use this reference when implementing a client that manages AW's repository integration. For interactive use, follow [Getting started](../agentic-workspace-install.md) or [Your repository and data](installed-surfaces.md).

Installation supplies the executable. **Adoption** establishes its small repository integration. **Refresh** reconciles that integration with the installed package. **Removal** relinquishes the package integration without deleting independent project data.

## Human setup entry point

From the Git working-tree root, `agentic-workspace setup` proposes adoption or
refresh and asks before applying it. It preserves surrounding `AGENTS.md` prose
and independently owned state. `--dry-run --format json` shows the exact proposed
file changes; `--yes` authorises that bounded proposal for automation. JSON mode
does not prompt. `--recover` explicitly selects an interrupted owner transaction
for inspection and authorisation. A stale proposal fails closed; inspect a fresh
proposal before retrying. Successful setup ends with ordinary agent work.

This command is in the development version; published 1.2.0 does not contain it.
The composition below remains the integration protocol and the only repository
writer. Python, npm and Cargo launch the same Rust CLI composition.

## Automatic setup assessment

Ordinary native `start` exposes Configuration's `setup_assessment` independently
of task wording and payload-target policy. Compact entry provides a consequence
route to the same owner. The main skill obtains that observation at session entry
and after a possible dependency change, reusing a sufficient current observation.
Existing users may run `agentic-workspace setup` to refresh the installed package
integration, including the managed fence.
Subsequent compatible changes are observed at ordinary entry. Installation only
supplies the executable: there are no package-manager or interpreter hooks.
Without runtime observation an external update is unknown.

Submit `setup_assessment.request` to receive current installed setup text and
configuration declarations, even if repository skills are stale or absent. After
authorised integration, observe the affected consumer and fill the returned
`record_request` with coverage, relevant source dependencies and grounded
dispositions. Invoke its exact Configuration action. This uses the existing
writer and recovery contract; reading never writes or grants policy consent.

The current repository assessment lives in
`.agentic-workspace/configuration-assessment.json`; machine-local assessment uses
`.agentic-workspace/local/configuration-assessment.json`. These are current owner
records, not human version checklists or domain evidence stores. A package-owned
setup revision determines whether semantic review is due. Maintainers change it
when setup needs reconsideration, including same-version development changes.
A separate build-prepared managed revision detects changes anywhere in the shipped
payload and routes existing refresh without repeating setup. Cosmetic edits and
version-only releases do not reopen semantic review. Ordinary comparison does not
construct setup text/schemas, hash the shipped payload or explore other owners.
It reads the bounded selected configuration/intent sources through existing
currentness, without repository scanning. Selected review alone loads material.

Effective dispositions are verified at publication through the existing consumer.
Unchanged deferred/blocked work retains its reason and precise resume route, with
`review_complete: true` and `integration_complete: false`; it creates no repeated
assessment consequence. Resume for a relevant source/prerequisite change, dependent
work or explicit `reconsider`. Changed sources retain previous decisions for the
agent to revisit only affected integration. Exclusions stay binding. Unknown
formats and major/newer integration remain preserved.

The assessment restriction targets `claim:configuration-integration-complete`.
Existing payload policies and other owners keep their own restrictions. Package
bytes, assessment and actual integration remain distinct; neither a provenance
label nor a successful configuration write proves all three.

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
