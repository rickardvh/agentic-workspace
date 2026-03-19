---
name: memory-hygiene
description: Review and clean a repository's checked-in memory and workflow docs. Use when a task asks to prune `/memory`, run the freshness audit, update note metadata, merge duplicate notes, or clean up stale durable knowledge after code or workflow changes.
---

# Memory Hygiene

This is a checked-in core skill shipped with the payload. Add repo-specific sibling skills under `memory/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill to keep checked-in memory accurate, compact, and aligned with the codebase.

It operates on checked-in memory files. It does not replace them.

## Workflow

1. Read the repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
   - `memory/system/SKILLS.md` when deciding whether a repo-specific skill should be created
   - `memory/current/project-state.md` if the repo uses it as an overview note
   - `memory/current/task-context.md` if the repo uses it as checked-in current-task compression
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
   - keep the overview and task-context notes short and avoid turning current-memory files into task trackers
6. If note names, roles, or routing changed, update `memory/index.md` and `memory/manifest.toml` in the same change when used.
7. Before finishing, rerun the audit or explain why it could not be run.

## Guardrails

- Keep the core operating model in checked-in docs; do not move repo purpose, invariants, or task state into a skill.
- Keep durable knowledge in checked-in files so the result stays visible and reviewable in git.
- Preserve useful current guidance; remove only what no longer helps the next contributor.
- Do not move durable technical knowledge into task tooling.
- Mark uncertain notes `Needs verification` instead of guessing.

## Typical outputs

- pruned or merged memory notes
- refreshed `Last confirmed` metadata
- cleaner workflow docs and memory notes
- an updated `memory/index.md` or `memory/manifest.toml` when routing changed
