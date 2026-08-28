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

For setup reconciliation, use the structured `config.policy-apply` operation returned by `setup`. It accepts only a bounded shared/local field inventory, requires both the exact config revision and setup identity, preserves unrelated TOML source, and rejects secret material or shared absolute machine paths. Nested ownership, assurance, and Verification semantics remain reviewed repository source; this bounded operation is not a general config patch language.

Readiness completion is a separate no-change reconciliation decision. It must carry the exact current capability basis and semantic concern receipt map returned by `setup`; the operation recomputes both before writing. Receipts retain only the current applicable concern identities with semantic/source revisions, materiality, and owner. They are not a setup generation counter or history. Explicitly enabling a compatible module may add pressure, a semantic/source revision may invalidate its concern, cosmetic metadata stays quiet, and disabling the module retires that concern without enabling, upgrading, or mutating any capability automatically.

Temporary setup deferral and optional-prompt suppression are local user dispositions, not configuration freshness. Select the exact decision under `configuration_concerns.continuation.actions`; it records only revision-bound unresolved concern ids in `.agentic-workspace/config.local.toml [setup]`. Deferred startup stays compact, affected required work re-elevates setup, explicit resume clears the local disposition, and successful readiness completion retires the local residue. A repository-wide decline or capability disable remains an explicit shared owner decision, never an inference from local deferral.
