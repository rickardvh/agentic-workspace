# Installer Behavior & Payload Resolution

This document defines how the Agentic Workspace installer resolves its payload root and manages the transition between workspace development and standalone installation.

## Payload Root Resolution

The `installer.py` script determines its source of truth (`payload_root`) using a hierarchical resolution strategy:

1. **Packaged Mode**: If a `_payload/` directory exists alongside the installer script (typical in a pip-installed package), that directory is used as the payload root.
2. **Workspace/Development Mode**: If no `_payload/` directory is found, the installer traverses upwards to find the monorepo's `bootstrap/` directory (specifically `packages/planning/bootstrap/`).

This dual-mode behavior allows the installer to work during development inside this monorepo while remaining portable once packaged.

## Payload Mirroring (Maintenance Responsibility)

In the monorepo, many payload files (such as `AGENTS.md`, `TODO.md`, and core contracts in `docs/`) are authored in the workspace root but must be mirrored into `packages/planning/bootstrap/` to be included in the shipped package.

Maintainers are responsible for ensuring that:
- Any change to a root-level contract is mirrored to its bootstrap counterpart.
- The `REQUIRED_PAYLOAD_FILES` list in `installer.py` is kept in sync with the actual repository structure.

## Drift Detection

The `agentic-workspace report` command (when run in a development workspace) automatically detects "payload drift" by comparing root-level files with their bootstrap mirrors. 

If drift is detected:
- A `payload-drift` finding will be surfaced in the report.
- Maintainers should sync the files manually or use the provided automation scripts to restore consistency.

## Managed vs. Local Files

The installer distinguishes between three classes of files:
1. **Root Surfaces**: `AGENTS.md`, `TODO.md`, `ROADMAP.md`. These are seeded once and then owned by the repository.
2. **Package Managed**: Contracts and scripts in `docs/` or `scripts/`. These are updated by the installer during upgrades.
3. **Generated**: Artifacts like `AGENT_QUICKSTART.md` that are derived from canonical manifests.

For more on lifecycle management, see [`docs/lifecycle-and-config-contract.md`](lifecycle-and-config-contract.md).
