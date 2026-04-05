---
name: memory-hygiene
description: Review and clean a repository's checked-in memory and workflow docs. Use when a task asks to prune `/memory`, run the freshness audit, update note metadata, merge duplicate notes, or clean up stale durable knowledge after code or workflow changes.
---

# Memory Hygiene

This is a bootstrap-managed core skill shipped with the payload under `.agentic-memory/skills/`. Add repo-specific sibling skills under `memory/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill to keep checked-in memory accurate, compact, and aligned with the codebase.

It operates on checked-in memory files. It does not replace them.

## Workflow

1. Read the repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `.agentic-memory/SKILLS.md` when deciding whether a repo-specific skill should be created
2. Load only the memory notes relevant to the files, commands, or behaviours that changed.
3. Treat `.agentic-memory/WORKFLOW.md` as reference policy only when the cleanup touches the memory contract or policy boundary.
4. Pull in current-state notes only when they genuinely need compression or shared-orientation cleanup.
5. Run the memory freshness audit if the repo has one.
6. Inspect the affected notes for:
   - contradicted behaviour
   - duplicate or overlapping guidance
   - stale placeholders
   - oversized history or narrative that no longer affects future work
7. Update the smallest set of files needed:
   - edit existing notes before creating new ones
   - merge or delete stale notes instead of accumulating near-duplicates
   - keep the overview and task-context notes short and avoid turning current-memory files into task trackers
   - ask whether a repeated note should instead become canonical docs, a skill, a script suggestion, a regression test suggestion, or a refactor suggestion
8. If note names, roles, or routing changed, update `memory/index.md` and `memory/manifest.toml` in the same change when used.
9. Before finishing, rerun the audit or explain why it could not be run.
10. If a note still exists mainly because of friction, use `promotion-report` to choose the upstream target and the intended post-remediation memory shape before expanding the note further.

## Guardrails

- Keep the core operating model in checked-in docs; do not move repo purpose, invariants, or task state into a skill.
- Keep durable knowledge in checked-in files so the result stays visible and reviewable in git.
- Preserve useful current guidance; remove only what no longer helps the next contributor.
- Do not move durable technical knowledge into task tooling.
- Mark uncertain notes `Needs verification` instead of guessing.
- If memory keeps compensating for the same awkward subsystem or workflow, suggest the upstream improvement instead of only expanding the note.
- Do not assume good hygiene means fewer notes in every repo; it means clearer, cheaper, better-justified notes and less dependence on memory for avoidable complexity.

## Typical outputs

- pruned or merged memory notes
- refreshed `Last confirmed` metadata
- cleaner workflow docs and memory notes
- an updated `memory/index.md` or `memory/manifest.toml` when routing changed
