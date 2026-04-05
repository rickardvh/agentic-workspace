---
name: planning-surface-change
description: Edit or prune planning-for-execution surfaces in repositories that use this bootstrap. Use when work touches `TODO.md`, `ROADMAP.md`, `docs/execplans/`, `tools/agent-manifest.json`, generated agent docs, or planning-surface validation/render scripts, and the task needs the repo's checked-in planning contract preserved.
---

# Planning Surface Change

Keep planning surfaces compact, execution-shaped, and validated against the checked-in contract.

## Workflow

1. Start from the active routing surfaces.
   Read `AGENTS.md`, `TODO.md`, `docs/execplans/README.md`, and `tools/agent-manifest.json`.
   Read `ROADMAP.md` only when promoting work, reprioritising, or pruning candidate epics.
   Read only the one active execplan that owns the task.

2. Decide which surface owns the change.
   Use `TODO.md` for the active queue and small direct tasks.
   Use `docs/execplans/` for multi-step execution contracts, milestone sequencing, blockers, and validation scope.
   Use `ROADMAP.md` for inactive candidate epics and strategic residue only.
   Keep durable technical facts in canonical docs or memory, not in planning surfaces.

3. Keep edits contract-shaped.
   Do not turn `TODO.md` into a notebook or backlog dump.
   Prefer updating an existing active execplan over creating an overlapping plan.
   Keep one active milestone and one immediate next action by default.
   Remove completed detail from active surfaces once it no longer affects the next contributor.

4. Regenerate manifest-driven docs when routing changes.
   Run `python scripts/render_agent_docs.py` after changing `tools/agent-manifest.json` or generated agent-surface content.
   Keep `tools/AGENT_QUICKSTART.md` and `tools/AGENT_ROUTING.md` aligned with the manifest.

5. Close the thread cleanly.
   Update `TODO.md`.
   Update the active execplan when working from one.
   Record only meaningful follow-on work in the right surface, then prune completed residue.

## Validation

- Run `python scripts/render_agent_docs.py` when generated agent docs may have changed.
- Run `python scripts/check/check_planning_surfaces.py` to catch drift in TODO, ROADMAP, and execplans.
- Escalate to broader repo validation only when the planning change also touched package code or generated payload files.

## Archive Helper

- Use `agentic-planning-bootstrap archive-plan <plan> --apply-cleanup` when archiving a completed execplan and you want the helper to remove completed TODO references plus the matching `ROADMAP.md` Active Handoff residue.
- Expect the helper to restore the TODO empty-state marker when the last active item is removed.
