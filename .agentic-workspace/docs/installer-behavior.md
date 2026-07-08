# Installer Behavior & Payload Resolution

This document defines how the Agentic Workspace installer resolves its payload root and manages the transition between workspace development and standalone installation.

## Payload Root Resolution

Both the `planning` and `memory` bootstrap installers determine their source of truth (`payload_root`) using a hierarchical resolution strategy:

1. **Packaged Mode**: If a `_payload/` directory exists alongside the installer script (typical in a pip-installed package), that directory is used as the payload root.
2. **Workspace/Development Mode**: If no `_payload/` directory is found, the installer traverses upwards to find the monorepo's `bootstrap/` directory:
   - Planning: `packages/planning/bootstrap/`
   - Memory: `packages/memory/bootstrap/`

This dual-mode behavior allows the installer to work during development inside this monorepo while remaining portable once packaged.

## Payload Mirroring (Maintenance Responsibility)

In the monorepo, many payload files (such as `AGENTS.md`, `.agentic-workspace/planning/state.toml`, and core contracts in `docs/`) are authored in the workspace root but must be mirrored into the respective bootstrap directories to be included in the shipped package.

Maintainers are responsible for ensuring that:

- Any change to a root-level contract is mirrored to its bootstrap counterpart.
- The `REQUIRED_PAYLOAD_FILES` (Planning) and `PAYLOAD_REQUIRED_FILES` (Memory) lists are kept in sync with the actual repository structure.

## Drift Detection

The `agentic-workspace report` command (when run in a development workspace) automatically detects "payload drift" by comparing root-level files with their bootstrap mirrors.

The detector now identifies:

- **Content Mismatch**: When a file in the mirror differs from the workspace root.
- **Missing Mirror File**: When a required file exists in the root but hasn't been copied to the bootstrap mirror.
- **Extra Mirror File**: When a file exists in the bootstrap mirror but is not registered in the required files list.

If drift is detected:

- A `payload-drift` finding will be surfaced in the report.
- Maintainers should sync the files manually to restore consistency.

## Managed vs. Local Files

The installer distinguishes between three classes of files:

1. **Root Surfaces**: `AGENTS.md` and `.agentic-workspace/planning/state.toml`. These are seeded once and then owned by the repository.
2. **Package Managed**: Contracts and scripts in `docs/` or `scripts/`. These are updated by the installer during upgrades.
3. **Generated**: Artifacts like `AGENT_QUICKSTART.md` that are derived from canonical manifests.

## Bootstrap Footprint

Root `agentic-workspace init` and `agentic-workspace install` use the necessary-surface footprint by default. They create repo-owned config/startup, a compact adoption receipt, and the smallest selected module state anchors; they preserve durable pre-existing local-mode Planning, Memory, and Verification state; and they omit generic package payload, bundled skills, payload provenance, and upgrade-source provenance.

The invocation source does not decide the host-repo footprint. A released package, dev dependency, editable install, or source checkout can all provide package payload at runtime. Use `--mirror-payload` only when a host repo explicitly wants bundled docs, templates, schemas, skills, provenance, and module upgrade-source files checked in.

Ordinary handoff files live under `.agentic-workspace/local/scratch/` instead of tracked bootstrap handoff paths. Status and doctor treat omitted package payload as healthy only when the checked-in adoption receipt records that package mirroring is not enabled.

## Local-only Installation

The workspace-level `agentic-workspace install --local-only` command installs the shared workspace surfaces in the normal repository layout, but records `.agentic-workspace/` in git-local exclude metadata instead of expecting the package surfaces to be checked in.

In local-only mode:

- local package-owned state is recorded in `.agentic-workspace/LOCAL-ONLY.toml`
- repo-local `.git/info/exclude` is updated to ignore `.agentic-workspace/`
- `AGENTS.local.md` carries the managed workflow fence
- `AGENTS.md` is kept to a tiny `AGENTS.local.md` reference when the repo did not already have its own startup file
- the installed workspace continues to use the same managed planning and memory payloads
- ordinary checked-in installs do not create `AGENTS.local.md`
- `agentic-workspace uninstall --local-only` removes the entire `.agentic-workspace/` tree and deletes the git-local exclude block when it was the only residue

For more on lifecycle management, see [`.agentic-workspace/docs/lifecycle-and-config-contract.md`](lifecycle-and-config-contract.md).
