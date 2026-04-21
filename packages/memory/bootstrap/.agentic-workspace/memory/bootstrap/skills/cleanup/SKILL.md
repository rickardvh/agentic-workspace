---
name: cleanup
description: Remove the temporary bootstrap workspace after bootstrap installation or upgrade work is complete.
---

# Cleanup

Use this skill when bootstrap install, populate, or upgrade work is complete and the CLI cleanup command is not being used.

## Workflow

1. Confirm there is no remaining bootstrap work that still depends on `.agentic-workspace/memory/bootstrap/`.
2. Point out any last manual-review items that must be handled before cleanup.
3. Remove `.agentic-workspace/memory/bootstrap/`.
4. Confirm that the persistent repo surfaces remain:
   - `AGENTS.md`
   - `.agentic-workspace/memory/repo/`
   - `.agentic-workspace/memory/skills/`
   - `.agentic-workspace/memory/repo/skills/`

## Guardrails

- Do not remove `.agentic-workspace/memory/skills/`, repo-owned `.agentic-workspace/memory/repo/skills/`, or any other durable memory content.
- Stop and report if cleanup would discard unresolved bootstrap work.

## Typical outputs

- confirmation that bootstrap work is complete
- removal of `.agentic-workspace/memory/bootstrap/`
