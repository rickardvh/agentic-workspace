---
name: memory-router
description: Route to the smallest relevant set of checked-in memory notes for the current work. Use when the task touches particular files, interfaces, or surfaces and the agent needs to know which memory notes to load first without bulk-reading the entire memory tree.
---

# Memory Router

This is a bootstrap-managed core skill shipped with the payload under `.agentic-workspace/memory/skills/`. Add repo-specific sibling skills under `.agentic-workspace/memory/repo/skills/` instead of customising this core skill unless the shared reusable procedure itself changed.

Use this skill to select the smallest relevant working set of memory notes before or during implementation.

It helps the agent load memory selectively instead of scanning the whole repository memory tree.

## Workflow

1. Read the routing contract:
   - `AGENTS.md`
   - `.agentic-workspace/memory/repo/index.md`
   - `.agentic-workspace/memory/SKILLS.md` when deciding whether a repo-specific skill should be created
2. Identify the surfaces in play:
   - touched files or modules
   - commands being changed
   - interface, runtime, retrieval, testing, or architecture surfaces
3. Use the repo's routing help first:
   - run `agentic-memory-bootstrap route --files <paths...>` when file paths are known
   - run `agentic-memory-bootstrap route --surface <surface...>` when the work is easier to describe by surface
   - when `.agentic-workspace/memory/repo/manifest.toml` exists, trust its note records first and use `.agentic-workspace/memory/repo/index.md` as the compact fallback routing layer
   - treat `.agentic-workspace/memory/WORKFLOW.md` as reference policy only when the task touches the memory contract or policy boundary
4. Load only the suggested notes that are relevant to the actual task.
5. Pull in current-state notes only when they reduce re-orientation cost:
   - `.agentic-workspace/memory/repo/current/project-state.md` for overview-level context
   - `.agentic-workspace/memory/repo/current/task-context.md` only for active continuation state
6. If the routing seems weak or outdated, inspect `.agentic-workspace/memory/repo/index.md`, `.agentic-workspace/memory/repo/manifest.toml`, and create a repo-specific routing skill if the repeated need is local rather than shared.

## Selection rules

- Prefer a small precise note set over "just in case" loading.
- Load additional notes only when a first note points to another durable dependency.
- Use `Applies to`, `Load when`, and `Review when` metadata to narrow the set further.

## Guardrails

- Do not treat routing as a substitute for judgement.
- Do not bulk-load `/memory` just because routing is uncertain.
- Keep routing logic visible in `.agentic-workspace/memory/repo/index.md` and `.agentic-workspace/memory/repo/manifest.toml`; do not hide durable routing knowledge inside the skill.
- If the route result is repeatedly noisy, fix the checked-in routing layer or add a repo-specific sibling skill instead of compensating with more core-skill prose.

## Typical outputs

- a small set of relevant memory notes to read next
- a clearer explanation of why those notes matter
- an updated `.agentic-workspace/memory/repo/index.md` or `.agentic-workspace/memory/repo/manifest.toml` when routing drift is discovered
