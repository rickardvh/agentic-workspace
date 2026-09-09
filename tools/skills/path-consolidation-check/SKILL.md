---
name: path-consolidation-check
description: Verify current module-managed Planning and Memory install roots remain consolidated under .agentic-workspace when install, payload, or path topology changes.
---

# Path Consolidation Check

Use this skill only when a change may alter installed roots, bootstrap/payload
paths, upgrade behavior, or durable documentation of the Planning/Memory path
contract. It is not an ambient check for ordinary package work.

## Check

1. Verify the current ownership ledger still places the installed Planning and
   Memory module roots under `.agentic-workspace/planning/` and
   `.agentic-workspace/memory/`.
2. Verify package bootstrap, generated payload, docs, and tests project those paths
   without becoming live repository operational state themselves.
3. Verify install/upgrade/uninstall behavior preserves the declared ownership and
   path boundary rather than reintroducing former top-level or package-local
   operational roots.
4. Update durable decision/domain notes only when the path or ownership boundary
   actually changed. Do not refresh prose merely because implementation moved.

## Typical surfaces

- `.agentic-workspace/OWNERSHIP.toml`
- `packages/memory/`
- `packages/planning/`
- generated/bootstrap payload surfaces
- install and upgrade tests
