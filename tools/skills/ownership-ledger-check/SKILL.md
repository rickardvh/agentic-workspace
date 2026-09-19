---
name: ownership-ledger-check
description: Recheck that shared startup guidance, managed fences, and installer behavior still align with the workspace orchestrator and ownership ledger.
---

# Ownership Ledger Check

Use this skill when editing startup guidance, managed docs, install paths, or lifecycle ownership rules.

## Check

1. Confirm `.agentic-workspace/WORKFLOW.md` remains a startup pointer, not policy or a second procedure owner. Resolve ownership through `.agentic-workspace/OWNERSHIP.toml` and its referenced source owners; follow the configured startup skill for procedure.
2. Confirm repo-owned root surfaces stay outside product-managed ownership except for explicit fences.
3. Confirm installer and lifecycle behavior still converge on the ledger rather than scattered heuristics.

## Typical surfaces

- `.agentic-workspace/WORKFLOW.md`
- `.agentic-workspace/OWNERSHIP.toml`
- `AGENTS.md`
- installer source and tests
