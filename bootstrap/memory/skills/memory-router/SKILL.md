---
name: memory-router
description: Route to the smallest relevant set of checked-in memory notes for the current work. Use when the task touches particular files, interfaces, or surfaces and the agent needs to know which memory notes to load first without bulk-reading the entire memory tree.
---

# Memory Router

This is a checked-in core skill shipped with the payload. Add repo-specific sibling skills under `memory/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill to select the smallest relevant working set of memory notes before or during implementation.

It helps the agent load memory selectively instead of scanning the whole repository memory tree.

## Workflow

1. Read the routing contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
   - `memory/system/SKILLS.md` when deciding whether a repo-specific skill should be created
2. Start with the always-relevant current-memory notes:
   - `memory/current/project-state.md`
   - `memory/current/task-context.md` if present and useful
3. Identify the surfaces in play:
   - touched files or modules
   - commands being changed
   - interface, runtime, retrieval, testing, or architecture surfaces
4. Use the repo's routing help first:
   - run `agentic-memory-bootstrap route --files <paths...>` when file paths are known
   - run `agentic-memory-bootstrap route --surface <surface...>` when the work is easier to describe by surface
   - when `memory/manifest.toml` exists, trust its note records and file globs before falling back to looser index-only routing
5. Load only the suggested notes that are relevant to the actual task.
6. If the routing seems weak or outdated, inspect `memory/index.md`, `memory/manifest.toml`, and create a repo-specific routing skill if the repeated need is local rather than shared.

## Selection rules

- Prefer a small precise note set over "just in case" loading.
- Load additional notes only when a first note points to another durable dependency.
- Use `Applies to`, `Load when`, and `Review when` metadata to narrow the set further.

## Guardrails

- Do not treat routing as a substitute for judgement.
- Do not bulk-load `/memory` just because routing is uncertain.
- Keep routing logic visible in `memory/index.md` and `memory/manifest.toml`; do not hide durable routing knowledge inside the skill.
- If the route result is repeatedly noisy, fix the checked-in routing layer or add a repo-specific sibling skill instead of compensating with more core-skill prose.

## Typical outputs

- a small set of relevant memory notes to read next
- a clearer explanation of why those notes matter
- an updated `memory/index.md` or `memory/manifest.toml` when routing drift is discovered
