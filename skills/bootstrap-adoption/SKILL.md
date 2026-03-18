---
name: bootstrap-adoption
description: Add the bootstrap to an existing repository conservatively. Use when a repo does not fully use the `agentic-memory-bootstrap` structure yet and needs `doctor`, `install`, or `adopt` guidance, manual review of local workflow docs, or careful alignment of local docs with the bootstrap model.
---

# Bootstrap Adoption

Use this skill to introduce the bootstrap into an existing repository without treating local files as disposable.

It is an execution layer for applying the memory system. The installed files remain the durable source of truth.

## Workflow

1. Inspect the target repository first:
   - read `AGENTS.md` if it exists
   - check whether `memory/` and `scripts/check/check_memory_freshness.py` already exist
   - note any existing repo-local task system without trying to replace it
2. Run `agentic-memory-bootstrap doctor --target <repo>` to see the current state.
3. Decide which path fits:
   - `install` for general bootstrap application
   - `adopt` when the repo already has local files that should be preserved conservatively
4. Review manual-review items before changing anything, especially:
   - older `AGENTS.md` files that embed shared workflow rules
   - local docs that mix task-tracking instructions into the memory contract
   - customised starter memory notes
5. Apply only the safe bootstrap actions automatically.
6. Manually align local docs where needed:
   - slim `AGENTS.md` back to the local contract
   - keep the task system external to the installed memory contract
   - preserve repo-specific scope and commands
7. Run the memory freshness audit if the repo includes it.
8. If adoption created fresh current-memory files, offer to use `bootstrap-populate` as the next conservative step so those files are populated from existing repo docs and visible repo state instead of being left as raw templates.

## Guardrails

- Do not overwrite repo-local files just because the bootstrap has a newer generic version.
- Keep bootstrap payload behaviour repo-agnostic.
- Do not auto-install optional skills into the target repo.
- Keep durable knowledge in checked-in files rather than moving it into procedural guidance.
- Treat sibling repos outside the explicit target as out of scope.

## Typical outputs

- a bootstrap doctor summary
- safe install or adopt actions applied
- manually aligned `AGENTS.md` and memory guidance where necessary
- a clear note about the overview, task-context, and durable-memory surfaces
- an offer to populate new current-memory files conservatively when adoption created them
