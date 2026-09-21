# Your repository and data

AW keeps its integration and retained working context primarily under `.agentic-workspace/`. Your source, tests, ordinary documentation and decisions stay in their existing locations. Installing AW does not import the repository into a separate knowledge database.

## What appears in the repository

```text
your-project/
├── AGENTS.md                 # Your instructions, with a small AW entry section
├── src/, tests/, docs/       # Your existing project
└── .agentic-workspace/
    ├── skills/              # Installed AW procedures
    ├── OWNERSHIP.toml       # Package facts combined with project declarations
    ├── READING.json         # References for repository-only readers
    ├── adoption.json        # Package integration identity
    ├── payload-provenance.json
    ├── config.toml          # Shared choices, when configured
    ├── config.local.toml    # Machine-specific choices, when configured
    ├── instructions/        # Shared project guidance, when authored
    ├── planning/, memory/, verification/  # Optional retained work
    └── local/               # Machine-local runtime state
```

This is an annotated map, not a list of files every installation creates. Adoption establishes the integration, not optional configuration or domain records. The [generated file catalogue](../reference/installed-surface-catalogue.md) lists the exact package footprint.

## What to commit

Commit the reviewed shared integration and the project rules or work records your team should inherit. Keep them consistent with the code and documents they describe.

Do not commit machine-specific settings, credentials, temporary scratch, caches or diagnostic logs. Check `git status` and the relevant ignore rules before staging. The `local` directory is the home for machine-local runtime material, not shared evidence that another checkout can assume exists.

A shared plan helps another session understand the work. It does not transfer a running process, credentials or every piece of local execution evidence.

## What you can change

Write project guidance and methods in repository-owned sources; ask the agent to use the current AW operation when publishing or changing managed records. Do not customise installed package skills in place: an update must be able to distinguish your work from package material.

Text outside the AW section in `AGENTS.md` remains yours. `OWNERSHIP.toml` combines portable package facts with supported project declarations, so it is not a template to replace wholesale. `READING.json` is generated from that ledger; changing its contents manually can make the read path stale.

To inspect or correct retained information, ask for the exact record and its assumptions. Update an existing lesson or plan rather than keeping contradictory copies. A settled project decision should remain in the project's normal decision location where one is configured.

## Privacy and external agents

Local AW operation is not itself a hosted storage service. However, an agent host can send the context it reads to its model provider, and configured commands or delegation transports can contact external services. Check those hosts' policies and credentials before giving them access.

Review diagnostic output before sharing it; it may contain sensitive project details even when local paths are masked. AW is not a sandbox and does not replace your host's execution restrictions. See the [security guide](../security/threat-model.md).

## Update AW

Update the repository's development dependency using its normal package manager,
then continue ordinary work. At runtime-capable entry the agent checks the resolved
AW artefact. Changed setup material or an absent assessment routes it through
Configuration to refresh managed files and assess useful optional capabilities
against your repository's purpose. No refresh-specific prompt or target-version
bookkeeping is required for a compatible update.

The agent applies authorised integrations and checks the affected behaviour.
Explicit exclusions remain binding; a genuinely new policy choice can need your
answer. Unfinished setup remains visible without blocking unrelated work. Review
and commit the shared diff. A settled assessment stays quiet until relevant
sources change; it does not certify machine-local readiness elsewhere.

An edited package file or conflicting declaration should block replacement until its useful changes are preserved in the proper project source. Repeating a completed refresh should not keep changing the same files. Detailed client handling is in the [lifecycle reference](lifecycle.md).

## Remove AW

Keep the runtime available until repository removal is finished. Ask:

> Remove AW's integration from this repository. Show what will be removed and what will remain. Preserve project instructions, configuration, plans, lessons and verification records.

The agent uses Configuration's removal proposal. Owned host-discovery links are removed before their canonical skill targets. Removal preserves independently owned and unknown content; edited package material may need explicit resolution first. Do not delete `.agentic-workspace/` wholesale.

Inspect the final diff. The package integration should be gone, and retained project material should still be readable. Decide separately whether to keep, move or retire that material. Then uninstall the runtime through the installer you used. Uninstalling the executable alone does not remove checked-in integration.

## Optional host skill discovery

The small `AGENTS.md` entry works for agents that read repository instructions. A compatible host can additionally discover skills through `.agents/skills/` links to the canonical bundles. Ask the agent to configure that exposure through Configuration; do not maintain copied skill bodies.

Colliding links should be preserved, not replaced. After moving a Windows checkout, existing junctions may need reconciliation. [Troubleshooting](../troubleshooting.md) covers missing discovery and interrupted operations.
