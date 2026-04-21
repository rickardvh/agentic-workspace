---
name: foundation-stability-check
description: Recheck that root-owned planning and memory remain the monorepo's operational authority and that new work is still routed through bounded planning surfaces.
---

# Foundation Stability Check

Use this skill when a repo change might affect whether the monorepo still behaves as one root-owned operational install.

## Check

1. Confirm `.agentic-workspace/planning/state.toml`, `.agentic-workspace/planning/execplans/`, and root memory remain the live operational surfaces.
2. Confirm package-local fixtures or payload copies are not acting as operational state.
3. Confirm the relevant root validation lanes still pass.

## Typical surfaces

- `.agentic-workspace/planning/state.toml`
- `.agentic-workspace/planning/execplans/`
- `AGENTS.md`
- `Makefile`
- package READMEs
