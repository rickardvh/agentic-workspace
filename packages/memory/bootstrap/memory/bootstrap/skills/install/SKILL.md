---
name: install
description: Finish bootstrap installation conservatively after the CLI has created the temporary bootstrap workspace in the target repository.
---

# Install

Use this skill after `agentic-memory-bootstrap init`, `install`, or `adopt` to finish installation review from the temporary bootstrap workspace.

## Workflow

1. Read the target repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `.agentic-memory/WORKFLOW.md`
2. Review created files and manual-review items.
3. Finish the conservative installation review:
   - keep repo-specific `AGENTS.md` content local and compact
   - keep task tracking outside the installed memory contract
   - preserve repo-specific notes unless there is clear evidence they should be aligned
4. If installation created new current-memory files, use `populate` from the same path.
5. Point out the shipped bootstrap-managed memory skills under `.agentic-memory/skills/` and any repo-specific memory skills under `memory/skills/`, keeping the managed package home concentrated under `.agentic-workspace/` rather than spreading package-managed machinery across the wider repo.
6. When install work is complete, prefer `agentic-memory-bootstrap bootstrap-cleanup --target <repo>`.

## Guardrails

- Do not overwrite repo-local files just because the bootstrap has a generic version.
- Keep durable knowledge in checked-in files.
- Keep repo-specific memory workflows under `memory/skills/`, not under `.agentic-memory/bootstrap/skills/`.
- General non-memory workflows do not belong under `memory/skills/`.
- Treat `.agentic-memory/bootstrap/` as temporary bootstrap workspace only.

## Typical outputs

- a concise review of install results
- manual-review items called out clearly
- a follow-up to `populate` when relevant
- a follow-up to `bootstrap-cleanup` when bootstrap work is complete
