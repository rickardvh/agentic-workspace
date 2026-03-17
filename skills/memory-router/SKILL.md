---
name: memory-router
description: Route to the smallest relevant set of checked-in memory notes for the current work. Use when the task touches particular files, interfaces, or surfaces and the agent needs to know which memory notes to load first without bulk-reading the entire memory tree.
---

# Memory Router

Use this skill to select the smallest relevant working set of memory notes before or during implementation.

It helps the agent load memory selectively instead of scanning the whole repository memory tree.

## Workflow

1. Read the routing contract:
   - `AGENTS.md`
   - `memory/index.md`
   - `memory/system/WORKFLOW.md`
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
5. Load only the suggested notes that are relevant to the actual task.
6. If the routing seems weak or outdated, inspect `memory/index.md` and improve it in the same change.

## Selection rules

- Prefer a small precise note set over "just in case" loading.
- Load additional notes only when a first note points to another durable dependency.
- Use `Applies to`, `Load when`, and `Review when` metadata to narrow the set further.
- In this source repo, local-only notes such as `memory/current/active-decisions.md` may be relevant for cross-cutting implementation choices, but they are not part of the general shipped baseline.

## Guardrails

- Do not treat routing as a substitute for judgement.
- Do not bulk-load `/memory` just because routing is uncertain.
- Keep routing logic visible in `memory/index.md`; do not hide durable routing knowledge inside the skill.
- If the route result is repeatedly noisy, fix the checked-in routing layer instead of compensating with more skill prose.

## Typical outputs

- a small set of relevant memory notes to read next
- a clearer explanation of why those notes matter
- an updated `memory/index.md` when routing drift is discovered
