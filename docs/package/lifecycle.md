# Repository setup, update and removal

Use this reference when implementing a client that manages AW's repository
integration. For interactive use, follow [Getting started](../agentic-workspace-install.md)
or [Your repository and AW files](installed-surfaces.md).

Installing a package supplies the executable. Repository **setup** adds AW's small
checked-in integration. **Update** refreshes package-managed files when the
installed version changes. **Removal** removes AW's integration while preserving
project-owned records.

## Setup

From the Git working-tree root, `agentic-workspace setup` shows the proposed file
changes and asks before applying them.

It preserves text outside AW's managed section in `AGENTS.md` and preserves
project-owned data. Use `--dry-run --format json` to inspect the proposal and
`--yes` to accept that exact proposal in automation.

If a previous setup/update may have been interrupted, use the recovery mode the
CLI reports rather than repeating writes blindly.

## Detecting that setup files need attention

The `start` result can report when repository integration files are missing,
out of date or need review. The exact stored fields and request names are part of
the API; ordinary users do not need to maintain a separate version checklist.

Package installation alone never edits the repository. There are no package
manager or interpreter hooks that silently run setup.

When setup or refresh is needed, follow the exact Configuration request AW
returns. Reading setup state does not change files.

## Applying a change

Use the request returned for the actual repository and task. Inspect the proposed
file changes and provide only the approval or decision the request asks for.

Do not reconstruct write-capable request fields from filenames or schema examples.
If AW does not offer an operation for a file, that is not permission to emulate it
with manual package-file copies.

## Preserve project-owned information

The package file set comes from the
[installed file contract](../../src/core/contracts/workspace_surfaces.json).

Use that contract and AW's normal operations rather than keeping a second
hand-written install/removal list.

Package metadata does not make unrelated project files removable. Shared project
configuration, Planning/Memory/Verification records, machine-local data and
unknown files remain separate from package-managed integration files.

Host-discovery links should be removed through the same supported setup/removal
path that created them. Do not recursively delete `.agents/skills/`.

## Interruption and recovery

A file change may have completed even when AW failed to return the next response.
Keep confirmed changes. If the outcome is unknown, inspect the current result or
use the returned recovery path before trying the operation again.

After a successful update, running the same update again should make no changes.
After removal, AW integration files should be absent while project-owned records
remain.

Later setup uses the normal setup path; it does not depend on an uninstall
history.

See [Troubleshooting](../troubleshooting.md) for user-facing recovery and the
[generated file catalogue](../reference/installed-surface-catalogue.md) for exact
package-managed paths.
