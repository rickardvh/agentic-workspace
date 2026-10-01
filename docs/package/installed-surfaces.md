# Your repository and AW files

AW keeps its integration and saved work primarily under `.agentic-workspace/`.
Your source, tests, ordinary documentation and project decisions stay where they
already are. Installing AW does not import the repository into a separate
knowledge database.

## What AW may add

```text
your-project/
├── AGENTS.md                 # Your instructions, with a small AW-managed section
├── src/, tests/, docs/       # Your existing project
└── .agentic-workspace/
    ├── skills/               # Installed AW procedures
    ├── OWNERSHIP.toml        # Which AW/project files are managed by whom
    ├── READING.json          # References for readers without the AW runtime
    ├── adoption.json         # Record of this repository's AW setup
    ├── payload-provenance.json
    ├── config.toml           # Shared AW settings, when configured
    ├── config.local.toml     # Machine-specific settings, when configured
    ├── instructions/         # Shared project guidance, when authored
    ├── planning/, memory/, verification/  # Optional saved work
    └── local/                # Machine-local runtime data
```

This is an annotated map, not a promise that every installation creates every
file. Setup creates only the files needed for repository integration. Optional
settings and component records appear when the project actually uses them.

The [generated file catalogue](../reference/installed-surface-catalogue.md) lists
the exact package-managed file set.

## What to commit

Commit shared AW integration and the project rules or work records your team
should inherit. Keep them consistent with the code and documentation they refer
to.

Do not commit machine-specific settings, credentials, temporary files, caches or
diagnostic logs. Check `git status` and the relevant ignore rules before staging.

The `local/` directory is for this checkout or machine. Another checkout must not
assume those files exist.

A shared plan can help another session understand unfinished work. It does not
transfer a running process, credentials or all local execution details.

## What you can edit directly

Write project guidance in project-owned files. Use AW's supported operations when
changing package-managed records whose format or safety checks AW is responsible
for.

Text outside the AW-managed section in `AGENTS.md` remains yours.

Do not edit installed package skills in place. If you need repository-specific
procedure, create project-owned guidance instead so an AW update can still tell
package files from your changes.

`OWNERSHIP.toml` records both package-managed files and supported project
declarations; do not replace it wholesale. `READING.json` is generated from the
current records and should be regenerated rather than hand-edited.

When correcting saved information, update the existing lesson or plan instead of
keeping contradictory copies.

## Privacy and external agents

AW itself is not a hosted storage service. An agent host can still send the files
it reads to its model provider, and configured commands or delegated work can
contact external services. Check those services' policies and credentials before
giving them access.

Review diagnostic output before sharing it; it may contain sensitive project
information even when local paths are masked.

AW is not a sandbox and does not replace your host's execution restrictions. See
the [security guide](../security/threat-model.md).

## Update AW

Update the repository's AW dependency with the package manager you used.

On the next relevant use, AW compares its package-managed repository files with
the installed version. If setup files need refreshing, it returns the setup or
refresh action needed for that repository. Unrelated read-only work can continue
when the missing refresh does not affect it.

Review and commit the shared diff. Repeating a completed refresh should not keep
changing the same files.

If a package-managed file was edited manually, AW should stop before overwriting
it. Preserve any useful project-specific change in a project-owned file, then
continue the refresh.

See the [lifecycle reference](lifecycle.md) for detailed update behaviour.

## Remove AW

Keep the runtime available until repository removal is finished. Ask:

> Remove AW's integration from this repository. Show what will be removed and what
> will remain. Preserve project instructions, configuration, plans, lessons and
> verification records.

AW removes only integration files it can verify it manages. Project-owned,
component-owned, machine-local and unknown content is preserved. Edited package
files may require you to move useful changes before removal can continue.

Do not delete `.agentic-workspace/` wholesale.

Inspect the final diff. The AW integration should be gone, while retained project
records should still be readable. Decide separately whether to keep, move or
delete those retained records, then uninstall the runtime with the package manager
you used.

Uninstalling the executable alone does not remove checked-in repository files.

## Optional host skill discovery

Native entry plugins are optional repository integration. Their generated bundle
lives under `.agentic-workspace/plugins/agentic-workspace-entry/` and refreshes
with the repository's package files. Configuration owns only the added Codex
marketplace entry and project enablement, or Claude catalogue and selected-scope
marketplace declaration and enablement. It preserves unrelated host settings and
refuses unowned collisions.

Commit Codex's `.agents/plugins/marketplace.json` and `.codex/config.toml` changes,
or Claude's `.claude/settings.json` and repository catalogue. Claude's
`.claude/settings.local.json` is local-only; exclude it before local exposure.
Claude reads the relative directory source from `extraKnownMarketplaces` in the
selected settings file after project trust. Each collaborator's registration/cache
material belongs to the host; shared enablement does not install their bytes.
Repository removal
requires removing owned plugin exposure before deleting its bundle. Removing
only plugin exposure preserves the generic `AGENTS.md` entry. See the
[installation guide](../agentic-workspace-install.md#optional-installed-entry-skill)
for the repository lifecycle and deliberate global option.

The small `AGENTS.md` entry works for agents that read repository instructions.
Some hosts can also discover AW skills through `.agents/skills/` links to the
installed skill directories.

Use AW setup/configuration to add or remove those links so unrelated existing
links are preserved. Do not maintain copied skill bodies.

After moving a Windows checkout, existing junctions may need repair.
[Troubleshooting](../troubleshooting.md) covers missing discovery and interrupted
updates.
