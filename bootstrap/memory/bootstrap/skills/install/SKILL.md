---
name: install
description: Finish bootstrap installation conservatively after the CLI has created the temporary bootstrap workspace in the target repository.
---

# Install

Use this skill after `agentic-memory-bootstrap init`, `install`, or `adopt`.

It finishes installation review from the checked-in temporary bootstrap workspace in the target repo.

## Workflow

1. Read the target repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
2. Inspect the bootstrap result:
   - review `agentic-memory-bootstrap doctor --target <repo>` output when available
   - review created files and manual-review items
3. Finish the conservative installation review:
   - keep repo-specific `AGENTS.md` content local and compact
   - keep task tracking outside the installed memory contract
   - preserve repo-specific notes and starter files unless there is clear evidence they should be aligned
4. If installation created new current-memory files, offer `populate` from the same path as the next step.
5. Point out the checked-in core memory skills under `memory/skills/`.
6. When install work is complete, offer `cleanup` from the same path.

## Guardrails

- Do not overwrite repo-local files just because the bootstrap has a generic version.
- Keep durable knowledge in checked-in files.
- Keep repo-specific workflows under `memory/skills/`, not under `memory/bootstrap/skills/`.
- Treat `memory/bootstrap/` as temporary bootstrap workspace only.

## Typical outputs

- a concise review of install results
- manual-review items called out clearly
- a follow-up to `populate` when relevant
- a follow-up to `cleanup` when bootstrap work is complete
