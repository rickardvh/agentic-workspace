---
name: memory-hygiene
description: Review and clean a repository's checked-in memory and execution-state docs. Use when a task asks to prune `/memory`, run the freshness audit, condense `TODO.md`, update note metadata, merge duplicate notes, or clean up stale durable knowledge after code or workflow changes.
---

# Memory Hygiene

Use this skill to keep checked-in memory accurate, compact, and aligned with the codebase.

## Workflow

1. Read the repo's local contract:
   - `AGENTS.md`
   - `TODO.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
2. Load only the memory notes relevant to the files, commands, or behaviours that changed.
3. Run the memory freshness audit if the repo has one.
4. Inspect the affected notes for:
   - contradicted behaviour
   - duplicate or overlapping guidance
   - stale placeholders
   - oversized history or narrative that no longer affects future work
5. Update the smallest set of files needed:
   - edit existing notes before creating new ones
   - merge or delete stale notes instead of accumulating near-duplicates
   - keep `TODO.md` as execution state, not durable technical memory
6. If note names, roles, or routing changed, update `memory/index.md` in the same change.
7. Before finishing, rerun the audit or explain why it could not be run.

## Guardrails

- Keep the core operating model in checked-in docs; do not move repo purpose, invariants, or milestone state into a skill.
- Preserve useful current guidance; remove only what no longer helps the next contributor.
- Replace completed `TODO.md` detail with short outcome notes once it no longer affects next actions.
- Mark uncertain notes `Needs verification` instead of guessing.

## Typical outputs

- pruned or merged memory notes
- refreshed `Last confirmed` metadata
- a shorter `TODO.md`
- an updated `memory/index.md` when routing changed
