---
name: memory-refresh
description: Refresh checked-in memory after code, docs, tests, commands, or behaviour changes. Use when files have changed and the agent needs to decide which memory notes to update, verify, deprecate, or route differently so durable memory stays aligned with the repository.
---

# Memory Refresh

This is a bootstrap-managed core skill shipped with the payload under `.agentic-workspace/memory/skills/`. Add repo-specific sibling skills under `memory/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill to inspect changed work and update the affected memory notes without over-editing the rest of the memory tree.

It operates on checked-in memory files and keeps them aligned with the codebase.

## Workflow

1. Read the repo's local contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `.agentic-workspace/memory/SKILLS.md` when deciding whether a repo-specific skill should be created
2. Identify the changed surfaces:
   - explicit changed files from the task
   - or repo changes discovered from version control
3. Use the repo's routing help first:
   - run `agentic-memory-bootstrap sync-memory --files <paths...>` when available
   - run `agentic-memory-bootstrap route --files <paths...>` when useful for note selection
   - when `memory/manifest.toml` exists, prefer manifest-triggered note matches as the first stale-memory candidates
   - treat `.agentic-workspace/memory/WORKFLOW.md` as reference policy only when the task touches the memory contract or policy boundary
4. Load only the affected notes.
5. Pull in `memory/current/project-state.md` or `memory/current/task-context.md` only when the change materially affects shared orientation or active continuation context.
6. For each affected note, decide the smallest correct action:
   - `review` if the note should be checked manually
   - `update` if it is now partly wrong or incomplete
   - `mark needs verification` if the change is plausible but not yet confirmed
   - `deprecate/remove` if the note no longer applies
   - `update index` if routing changed
7. Apply the minimal checked-in edits needed.
8. If current shared orientation changed, refresh `memory/current/project-state.md` or `memory/current/task-context.md`.
9. If the repeated procedure is repository-specific, create a new sibling skill under `memory/skills/` instead of expanding this shared core skill.
10. Run the memory freshness audit when available.
11. If a note is acting as an improvement signal, run `agentic-memory-bootstrap promotion-report --notes <note>` and prefer the smallest justified post-remediation memory shape: keep the note only if it still saves rediscovery cost, otherwise shrink it to a stub or remove it.

## Decision rules

- Update the note in the same change when the new behaviour is clear.
- Mark the note `Needs verification` when the impact is likely but still unconfirmed.
- Remove or deprecate memory that is contradicted by the new state.
- Prefer a small precise update over broad rewrites of unrelated notes.

## Guardrails

- Do not edit memory speculatively when there is no durable impact.
- Do not treat changed code as a reason to bulk-refresh all of `/memory`.
- Keep current-memory notes concise and oriented toward fast continuation.
- Preserve one-home discipline: avoid duplicating the same rule across multiple notes.

## Typical outputs

- updated memory notes aligned with the latest code or docs
- notes marked `Needs verification` where certainty is incomplete
- deprecated or removed stale notes
- an updated `memory/index.md` or `memory/manifest.toml` when routing changed
