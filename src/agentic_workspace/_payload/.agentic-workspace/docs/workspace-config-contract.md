# Workspace Config Contract

This installed contract is the no-CLI companion to `.agentic-workspace/config.toml`.
It is intentionally self-contained so a necessary-surface footprint does not depend on source-checkout documentation.

## Authority

- `.agentic-workspace/config.toml` is repo-owned policy.
- `.agentic-workspace/config.local.toml` is optional machine-local policy and must not become shared authority.
- `.agentic-workspace/OWNERSHIP.toml` owns subsystem and managed-surface boundaries.
- Planning owns active execution state; Memory owns durable anti-rediscovery knowledge; Verification owns reported evidence.
- `AGENTS.md` and installed skills are routing adapters over these structured owners.

## Safe fallback

When the configured CLI is unavailable, preserve the last known forbidden actions and avoid mutating managed Planning, Memory, Verification, provenance, or generated surfaces by hand. Read the installed startup skill and module map, then inspect only the named owner surface. Restore a compatible configured invocation before claiming implementation or closeout.

When the CLI works, prefer compact `start`, `config`, `ownership`, `summary`, and `report` JSON over broad raw-file reads.

## Editing rule

Edit shared config only for an intentional repo-policy change. Keep machine paths, credentials, and local execution preferences in local config. Module state is not workspace config and must be changed through its owning module when that command surface is available.
