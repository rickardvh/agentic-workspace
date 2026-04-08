---
name: ownership-ledger-check
description: Recheck that shared startup guidance, managed fences, and installer behavior still align with the workspace orchestrator and ownership ledger.
---

# Ownership Ledger Check

Use this skill when editing startup guidance, managed docs, install paths, or lifecycle ownership rules.

## Check

1. Confirm `.agentic-workspace/WORKFLOW.md` and `.agentic-workspace/OWNERSHIP.toml` remain the shared ownership contract.
2. Confirm repo-owned root surfaces stay outside product-managed ownership except for explicit fences.
3. Confirm installer and lifecycle behavior still converge on the ledger rather than scattered heuristics.

## Typical surfaces

- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/OWNERSHIP.toml`
- `AGENTS.md`
- installer source and tests
