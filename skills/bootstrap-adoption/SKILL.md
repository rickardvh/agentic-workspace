---
name: bootstrap-adoption
description: Add the bootstrap to an existing repository conservatively. Use when a repo does not fully use the `agentic-memory-bootstrap` structure yet and needs `doctor`, `install`, or `adopt` guidance, manual review of existing `AGENTS.md` or `TODO.md`, or careful alignment of local docs with the bootstrap model.
---

# Bootstrap Adoption

Use this skill to introduce the bootstrap into an existing repository without treating local files as disposable.

## Workflow

1. Inspect the target repository first:
   - read `AGENTS.md` and `TODO.md` if they exist
   - check whether `memory/` and `scripts/check/check_memory_freshness.py` already exist
2. Run `agentic-memory-bootstrap doctor --target <repo>` to see the current state.
3. Decide which path fits:
   - `install` for general bootstrap application
   - `adopt` when the repo already has local files that should be preserved conservatively
4. Review manual-review items before changing anything, especially:
   - older `AGENTS.md` files that embed shared workflow rules
   - local `TODO.md`
   - customised starter memory notes
5. Apply only the safe bootstrap actions automatically.
6. Manually align local docs where needed:
   - slim `AGENTS.md` back to the local contract
   - keep `TODO.md` as the execution surface
   - preserve repo-specific scope and commands
7. Run the memory freshness audit if the repo includes it.

## Guardrails

- Do not overwrite repo-local files just because the bootstrap has a newer generic version.
- Keep bootstrap payload behaviour repo-agnostic.
- Do not auto-install optional skills into the target repo.
- Treat sibling repos outside the explicit target as out of scope.

## Typical outputs

- a bootstrap doctor summary
- safe install or adopt actions applied
- manually aligned `AGENTS.md` and `TODO.md` where necessary
- a short `TODO.md` outcome note in the target repo
