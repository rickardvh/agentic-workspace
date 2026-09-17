# Installed surfaces

The public host footprint contains a managed instruction fence, repository-local skills and their declared dependencies, source ownership/read-profile metadata, payload provenance, and an adoption identity. Configuration establishes, refreshes, and removes this same set through exact current requests/actions.

The generated [installed-surface catalogue](../reference/installed-surface-catalogue.md) lists every path, owner, lifetime, consumer, and retired preimage. It is generated from `workspace_surfaces.json`, which also drives native payload compilation. There are no public footprint profiles or implicit module selections.

Repository config and instructions outside the managed fence remain repository-owned. Planning, Memory, Verification, promoted outputs, and local state retain their independent owners and lifetimes. Adoption creates none of these domain records; removal preserves them. Unknown and edited content remains in place for source-owner reconciliation.

Repository-only readers use the same startup skill and its ownership-bound read profile. Executable fallback rendering and historical mirrored docs/templates belong only to the separate [source-maintenance inventory](../reference/source-maintenance-surface-catalogue.md).

See [repository lifecycle](lifecycle.md) for first adoption, convergence, recovery, and removal; see [installation](../agentic-workspace-install.md) for acquiring an exact published artifact. Documentation on a newer branch does not upgrade installed release bytes.
