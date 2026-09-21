# Repository adoption, refresh and removal

Use this reference when implementing a client that manages AW's repository integration. For interactive use, follow [Getting started](../agentic-workspace-install.md) or [Your repository and data](installed-surfaces.md).

Installation supplies the executable. **Adoption** establishes its small repository integration. **Refresh** reconciles that integration with the installed package. **Removal** relinquishes the package integration without deleting independent project data.

## Automatic setup assessment

Ordinary native `start` exposes Configuration's `setup_assessment` independently
of task wording and payload-target policy. Compact entry provides a consequence
route to the same owner. The main skill obtains that observation at session entry
and after a possible dependency change, reusing a sufficient current observation.
Product-owned triggers bridge preceding bootstraps by publishing a minimal
Configuration notice in the authenticated adopted `AGENTS.md` entry. npm uses
post-install; Python uses installed `.pth` material at the next ordinary
interpreter startup, without an AW import. `uv sync` itself has no wheel callback.
Both carry only the same returned `package.update-notice` Configuration write.
They cannot choose capabilities, change policy or settle assessment. The stable
notice requests current observation and reuses a settled result; it is not a
last-seen version record. Removal relinquishes the exact product notice.

No user-maintained lifecycle hook is required. An unadopted directory, absent
custody, edited notice, incompatible integration or explicitly disabled host
hooks cannot silently acquire write authority. Native entry remains the recovery
path; without any supported observation, an external update is unknown.

Submit `setup_assessment.request` to receive current installed setup text and
configuration declarations, even if repository skills are stale or absent. After
authorised integration, observe the affected consumer and fill the returned
`record_request` with coverage, relevant source dependencies and grounded
dispositions. Invoke its exact Configuration action. This uses the existing
writer and recovery contract; reading never writes or grants policy consent.

The current repository assessment lives in
`.agentic-workspace/configuration-assessment.json`; machine-local assessment uses
`.agentic-workspace/local/configuration-assessment.json`. These are current owner
records, not human version checklists or domain evidence stores. Setup material
and managed host-surface identity, together with relevant repository source
identity, determine reuse; tasks and HEAD do not. Changes outside the setup bundle
also reopen assessment. A version-only release with identical material remains
quiet. Effective
dispositions require a current consumer witness. Pending, deferred, blocked and
unavailable dispositions retain a reason and continuation. Exclusion settles
consideration without asserting that a capability works. Unknown formats and
major/newer integration are preserved for bounded reconciliation.

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
