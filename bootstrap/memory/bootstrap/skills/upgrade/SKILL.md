---
name: upgrade
description: Finish bootstrap upgrade review conservatively after the CLI has refreshed the target repository.
---

# Upgrade

Use this skill after `agentic-memory-bootstrap upgrade`.

## Workflow

1. Read the target repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
   - `memory/current/project-state.md` if present
   - `memory/current/task-context.md` if present
2. Review changed shared files and manual-review items.
3. Finish the conservative upgrade review:
   - preserve repo-specific scope and commands in `AGENTS.md`
   - keep task tooling separate from the memory contract
   - confirm the active memory surfaces are still correct
4. Run the memory freshness audit when available.
5. When upgrade work is complete, prefer `agentic-memory-bootstrap bootstrap-cleanup --target <repo>`.

## Guardrails

- Do not flatten repo-local customisation.
- Treat `memory/bootstrap/` as temporary bootstrap workspace only.
- Keep repo-specific memory skills under `memory/skills/`; general non-memory skills belong elsewhere.
- Shared product-managed files are safe replacement candidates; repo-owned notes and checked-in repo-local skills require conservative manual review when customised.
- Runtime-local mirrored skill copies are cache-only artefacts; align them to checked-in repo skills instead of treating them as the source of truth.

## Typical outputs

- a concise upgrade review
- manual-review items called out clearly
- a follow-up to `bootstrap-cleanup` when bootstrap work is complete
