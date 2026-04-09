---
name: path-consolidation-check
description: Recheck that memory and planning installs still live under .agentic-workspace and that package docs and tests still reflect the consolidated path contract.
---

# Path Consolidation Check

Use this skill when a change may affect installed bootstrap paths, payload roots, or docs that reference `.agentic-workspace/{memory,planning}`.

## Check

1. Verify package docs, payloads, and tests still point at `.agentic-workspace/memory/` and `.agentic-workspace/planning/`.
2. Verify upgrade or install flows still render the consolidated paths.
3. Update decision or domain notes only if the durable boundary changed.

## Typical surfaces

- `packages/memory/`
- `packages/planning/`
- `README.md`
- installer tests
